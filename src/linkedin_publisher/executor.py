"""LinkedIn publisher using Playwright browser automation."""

import asyncio
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .exceptions import AuthenticationError, PublishError, is_retryable_error
from .models import PublishResult
from .selectors import (
    get_selector_with_fallbacks,
    get_all_selectors,
    SELECTORS,
    WAIT_TIMES,
    URLS,
)


class LinkedInPublisher:
    """Publishes text posts to LinkedIn via Playwright.

    Workflow:
    1. Launch browser with persistent session
    2. Navigate to LinkedIn home
    3. Check authentication (re-auth if needed)
    4. Click "Start a post"
    5. Enter post content
    6. Click "Post"
    7. Wait for confirmation
    8. Extract post URL if possible

    Attributes:
        session_path: Path to Playwright persistent context storage
        headless: Run browser in headless mode
    """

    def __init__(
        self,
        session_path: Path,
        headless: bool = True,
        storage_state_path: Optional[Path] = None,
    ):
        """Initialize publisher.

        Args:
            session_path: Directory for Playwright persistent context (auth only).
            headless: Run browser in headless mode (False for auth).
            storage_state_path: Path to storage_state.json exported after auth.
                When provided and the file exists, the session is loaded from
                this JSON instead of the persistent context directory, avoiding
                headed-vs-headless Chrome profile incompatibility.
        """
        self.session_path = Path(session_path)
        self.headless = headless
        self.storage_state_path = Path(storage_state_path) if storage_state_path else None

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def initialize(self) -> None:
        """Launch browser and set up page.

        Strategy:
        - If storage_state_path exists (set by auth): launch a plain browser and
          load the saved session from JSON. Works identically in headless and
          headed mode because it is just cookies/localStorage, not a Chrome
          profile directory.
        - Otherwise (first-time auth): launch a persistent context so the user
          can log in and we can export the session afterwards.
        """
        self.session_path.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()

        use_storage_state = (
            self.storage_state_path is not None
            and self.storage_state_path.exists()
        )

        if use_storage_state:
            click.echo(f"[debug] Loading session from: {self.storage_state_path}")
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context(
                storage_state=str(self.storage_state_path),
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
        else:
            click.echo(f"[debug] No storage_state found — using persistent context at: {self.session_path}")
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def is_authenticated(self) -> bool:
        """Check if the LinkedIn session is valid.

        Strategy (fastest-first):
        1. Navigate to the feed URL.
        2. Check the landed URL — LinkedIn always redirects unauthenticated
           users to /login or /authwall immediately, so the URL alone is
           definitive in most cases.
        3. If the URL is ambiguous (e.g. linkedin.com/ root), wait up to
           10 seconds for a feed element to appear, then fall back to checking
           for a login form.

        Returns:
            True if authenticated, False otherwise.
        """
        if not self._page:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        try:
            click.echo("[debug] Navigating to feed to check session...")
            await self._page.goto(URLS["home"], wait_until="domcontentloaded")

            current_url = self._page.url
            click.echo(f"[debug] Landed on: {current_url}")

            # --- Step 1: URL is definitive ---
            auth_indicators = ("login", "authwall", "checkpoint", "signup", "uas/login")
            if any(x in current_url for x in auth_indicators):
                click.echo("[debug] Redirected to auth page — session is invalid")
                return False

            feed_indicators = ("/feed", "/in/", "mynetwork", "/jobs", "/messaging", "/notifications")
            if any(x in current_url for x in feed_indicators):
                click.echo("[debug] On feed/profile URL — authenticated ✓")
                return True

            # --- Step 2: Ambiguous URL — check DOM ---
            click.echo(f"[debug] Ambiguous URL ({current_url}), checking DOM...")
            feed_selector = get_all_selectors("feed_indicator")
            try:
                await self._page.wait_for_selector(feed_selector, timeout=WAIT_TIMES["very_long"])
                click.echo("[debug] Feed element appeared — authenticated ✓")
                return True
            except Exception:
                pass

            login_selector = get_all_selectors("login_indicator")
            login_element = await self._page.query_selector(login_selector)
            if login_element:
                click.echo("[debug] Login form found in DOM — not authenticated")
                return False

            click.echo("[debug] Could not determine auth state — assuming not authenticated")
            return False

        except Exception as e:
            click.echo(f"[debug] is_authenticated error: {e}")
            return False

    async def save_session(self, path: Path) -> None:
        """Export cookies and localStorage to a portable JSON file.

        This JSON can be loaded by any browser mode (headed or headless)
        via new_context(storage_state=path), avoiding Chrome profile
        directory incompatibilities between Chromium and headless-shell.

        Args:
            path: Destination path for storage_state.json.
        """
        if not self._context:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._context.storage_state(path=str(path))
        click.echo(f"[debug] Session exported to: {path}")

    async def wait_for_login(
        self,
        timeout_ms: int = 300_000,
        storage_state_path: Optional[Path] = None,
    ) -> bool:
        """Navigate to the login page once and wait for the user to log in manually.

        Does NOT poll or re-navigate. Uses Playwright's wait_for_url() to
        passively detect when the browser reaches a post-login page, then
        exports storage_state.json so run/watch can load the session without
        relying on the Chrome profile directory.

        Args:
            timeout_ms: Maximum wait time in milliseconds (default: 5 minutes).
            storage_state_path: Where to export the session JSON after login.

        Returns:
            True if login was detected (and session saved), False if timed out.
        """
        if not self._page:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        click.echo(f"[debug] Navigating to: {URLS['login']}")
        await self._page.goto(URLS["login"], wait_until="domcontentloaded")

        # Matches /feed/, /in/<username>, /mynetwork, /jobs, /messaging, /notifications.
        post_login_pattern = re.compile(
            r"linkedin\.com/(feed|in/|mynetwork|jobs|messaging|notifications)"
        )

        try:
            await self._page.wait_for_url(post_login_pattern, timeout=timeout_ms)
            click.echo(f"[debug] Login detected — URL: {self._page.url}")
            if storage_state_path:
                await self.save_session(storage_state_path)
            return True
        except Exception as e:
            click.echo(f"[debug] wait_for_login timeout/error: {e}")
            return False

    async def _dismiss_overlays(self) -> None:
        """Silently dismiss cookie banners and consent dialogs.

        Tries each cookie-banner selector with a short probe timeout.
        Never raises — if nothing is found, execution continues normally.
        """
        for selector in SELECTORS["cookie_banner"]:
            try:
                element = await self._page.query_selector(selector)
                if element:
                    await element.click()
                    click.echo(f"[debug] Dismissed overlay: {selector}")
                    await self._page.wait_for_timeout(500)
                    return
            except Exception:
                continue
        click.echo("[debug] No overlays to dismiss")

    async def _find_and_click(
        self,
        selector_key: str,
        action_name: str,
        after_click_wait: int = WAIT_TIMES["medium"],
    ) -> str:
        """Try every selector for `selector_key` in order, click the first visible one.

        Each selector is probed with a short per-selector timeout
        (WAIT_TIMES["per_selector"]) so the full list is scanned
        quickly without a long stall on a single missing element.

        Args:
            selector_key: Key into SELECTORS dict.
            action_name: Human-readable name used in error messages.
            after_click_wait: How long to wait after a successful click.

        Returns:
            The selector string that matched.

        Raises:
            PublishError: If no selector matched.
        """
        selectors = SELECTORS[selector_key]
        last_error: Optional[Exception] = None

        for selector in selectors:
            try:
                click.echo(f"[debug] Trying {action_name} selector: {selector}")
                await self._page.wait_for_selector(
                    selector,
                    state="visible",
                    timeout=WAIT_TIMES["per_selector"],
                )
                await self._page.click(selector)
                click.echo(f"[debug] {action_name} clicked with: {selector}")
                await self._page.wait_for_timeout(after_click_wait)
                return selector
            except Exception as e:
                click.echo(f"[debug]   ✗ {selector}")
                last_error = e

        raise PublishError(
            f"Failed to {action_name}: no selector matched out of "
            f"{len(selectors)} tried. Last error: {last_error}",
            retryable=True,
        )

    async def _click_start_post(self, attempt: int = 1) -> None:
        """Click the "Start a post" button using all available selectors.

        Args:
            attempt: Retry attempt number (passed to PublishError for logging).

        Raises:
            PublishError: If no selector matched.
        """
        try:
            await self._find_and_click("start_post_button", "click start-post button")
        except PublishError as e:
            raise PublishError(str(e), retry_count=attempt, retryable=True)

    async def _enter_content(self, content: str, attempt: int = 1) -> None:
        """Type post content into the composer editor.

        Args:
            content: Text to type.
            attempt: Retry attempt number.

        Raises:
            PublishError: If the editor could not be found or typed into.
        """
        selectors = SELECTORS["post_editor"]
        last_error: Optional[Exception] = None

        for selector in selectors:
            try:
                click.echo(f"[debug] Trying editor selector: {selector}")
                await self._page.wait_for_selector(
                    selector,
                    state="visible",
                    timeout=WAIT_TIMES["per_selector"],
                )
                await self._page.click(selector)
                await self._page.wait_for_timeout(WAIT_TIMES["short"])
                await self._page.type(selector, content, delay=20)
                await self._page.wait_for_timeout(WAIT_TIMES["short"])
                click.echo(f"[debug] Content typed with: {selector}")
                return
            except Exception as e:
                click.echo(f"[debug]   ✗ {selector}")
                last_error = e

        raise PublishError(
            f"Failed to enter content: no editor selector matched. Last error: {last_error}",
            retry_count=attempt,
            retryable=True,
        )

    async def _click_post_button(self, attempt: int = 1) -> None:
        """Click the submit "Post" button inside the composer modal.

        Args:
            attempt: Retry attempt number.

        Raises:
            PublishError: If the Post button could not be found or clicked.
        """
        try:
            await self._find_and_click(
                "post_button",
                "click Post button",
                after_click_wait=WAIT_TIMES["very_long"],
            )
        except PublishError as e:
            raise PublishError(str(e), retry_count=attempt, retryable=True)

    async def _extract_post_url(self) -> Optional[str]:
        """Attempt to extract the URL of the newly published post.

        This is best-effort - URL extraction may fail due to DOM timing.

        Returns:
            Post URL if found, None otherwise
        """
        try:
            # Look for recent activity in feed
            selector = get_all_selectors("post_success_indicator")
            await self._page.wait_for_selector(selector, timeout=WAIT_TIMES["long"])

            # Try to find the post URL from data attributes
            elements = await self._page.query_selector_all("[data-urn*='activity']")
            for element in elements:
                urn = await element.get_attribute("data-urn")
                if urn:
                    # Extract activity ID from URN
                    # Format: urn:li:activity:1234567890
                    if "activity:" in urn:
                        activity_id = urn.split("activity:")[-1]
                        return f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"

        except Exception:
            pass

        return None

    async def publish_post(self, content: str) -> PublishResult:
        """Publish text content to LinkedIn.

        Single attempt - use publish_with_retry for retry logic.

        Args:
            content: Post content to publish

        Returns:
            PublishResult with success status and details
        """
        if not self._page:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        start_time = time.time()

        try:
            # Check authentication (navigates to feed, confirms we land there)
            if not await self.is_authenticated():
                raise AuthenticationError("LinkedIn session expired. Run 'linkedin-publish auth' to re-authenticate.")

            # Re-navigate to feed with a full load wait so the composer is ready.
            # is_authenticated() leaves us on the feed, but a second goto with
            # wait_until="load" gives the JS time to fully hydrate the page.
            click.echo("[debug] Loading feed page before posting...")
            await self._page.goto(URLS["home"], wait_until="load")
            await self._page.wait_for_timeout(WAIT_TIMES["medium"])

            # Dismiss cookie banners / consent dialogs before interacting
            await self._dismiss_overlays()

            # Click start post
            await self._click_start_post()

            # Enter content
            await self._enter_content(content)

            # Click post
            await self._click_post_button()

            # Try to extract post URL
            post_url = await self._extract_post_url()

            publish_duration = int((time.time() - start_time) * 1000)

            return PublishResult(
                success=True,
                post_url=post_url,
                timestamp=datetime.utcnow(),
                publish_duration_ms=publish_duration,
            )

        except AuthenticationError:
            raise

        except PublishError:
            raise

        except Exception as e:
            publish_duration = int((time.time() - start_time) * 1000)
            return PublishResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.utcnow(),
                publish_duration_ms=publish_duration,
            )

    async def _adjust_for_retry(self, attempt: int) -> None:
        """Adjust strategy for retry attempt.

        Args:
            attempt: Current attempt number
        """
        # Increase wait times for subsequent attempts
        wait_multiplier = attempt * 1000

        # Close any open modals
        try:
            await self._page.keyboard.press("Escape")
            await self._page.wait_for_timeout(WAIT_TIMES["short"] + wait_multiplier)
        except Exception:
            pass

        # Refresh the page for clean state
        try:
            await self._page.reload()
            await self._page.wait_for_timeout(WAIT_TIMES["medium"] + wait_multiplier)
        except Exception:
            pass

    async def publish_with_retry(self, content: str, max_attempts: int = 3) -> PublishResult:
        """Publish with retry logic per Constitution Principle V.

        Ralph Wiggum Loop:
        - Attempt 1: Execute as planned
        - Attempt 2: Re-read selectors, adjust wait times, retry
        - Attempt 3: Simplify (longer waits, alternative selectors), retry
        - After 3 failures: Return failure result for escalation

        Args:
            content: Post content to publish
            max_attempts: Maximum number of attempts (default 3)

        Returns:
            PublishResult with final status
        """
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                result = await self.publish_post(content)
                if result.success:
                    result.retry_count = attempt
                    return result

                # Publish returned failure without exception
                last_error = result.error

            except AuthenticationError as e:
                # Auth errors are not retryable
                return PublishResult(
                    success=False,
                    error=str(e),
                    error_type="AuthenticationError",
                    retry_count=attempt,
                    timestamp=datetime.utcnow(),
                )

            except PublishError as e:
                last_error = str(e)
                if not is_retryable_error(e):
                    return PublishResult(
                        success=False,
                        error=str(e),
                        error_type="PublishError",
                        retry_count=attempt,
                        timestamp=datetime.utcnow(),
                    )

            except Exception as e:
                last_error = str(e)

            # Adjust for retry if not last attempt
            if attempt < max_attempts:
                await self._adjust_for_retry(attempt)

        # All retries exhausted
        return PublishResult(
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
            error_type="MaxRetriesExceeded",
            retry_count=max_attempts,
            timestamp=datetime.utcnow(),
        )

    async def close(self) -> None:
        """Close browser and release Playwright resources."""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None

        # _browser is only set when using launch() + new_context().
        # launch_persistent_context() returns the context directly (no separate browser object).
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
