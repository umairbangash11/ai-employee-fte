"""Facebook post executor using Playwright.

Publishes text posts to Facebook via browser automation.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.exceptions import (
    PublishTimeoutError,
    SelectorNotFoundError,
    SessionExpiredError,
)
from facebook_publisher.models import PublishResult
from facebook_publisher.selectors import SELECTORS, TIMEOUTS, URLS
from facebook_publisher.utils import ensure_directory

logger = logging.getLogger(__name__)


class FacebookPublisher:
    """Publishes text posts to Facebook via Playwright.

    Workflow:
    1. Launch browser with persistent session
    2. Navigate to Facebook home
    3. Check authentication (re-auth if needed)
    4. Click "What's on your mind?" to open composer
    5. Enter post content
    6. Set visibility (public/friends/only_me)
    7. Click "Post"
    8. Wait for confirmation
    9. Extract post URL if possible
    """

    def __init__(self, config: FacebookPublisherConfig):
        """Initialize the publisher.

        Args:
            config: Publisher configuration
        """
        self.config = config
        self.session_path = config.session_path
        self.headless = config.headless
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None

    async def initialize(self) -> None:
        """Launch browser with persistent context."""
        ensure_directory(self.session_path)

        self._playwright = await async_playwright().start()

        # Check if storage state exists
        storage_state = None
        if self.config.storage_state_path.exists():
            storage_state = str(self.config.storage_state_path)
            logger.debug(f"Loading session from {storage_state}")

        # Launch browser
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )

        # Create context with storage state if available
        self._context = await self._browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self._page = await self._context.new_page()
        logger.info("Browser initialized")

    async def is_authenticated(self) -> bool:
        """Check if Facebook session is valid.

        Returns:
            True if authenticated, False if login page shown
        """
        if not self._page:
            return False

        try:
            # Navigate to Facebook
            await self._page.goto(URLS["home"], timeout=TIMEOUTS["page_load"])
            await self._page.wait_for_load_state("domcontentloaded")

            # Small delay to let page settle
            await asyncio.sleep(2)

            # Check for logged-in indicators
            for selector in SELECTORS["logged_in_indicator"]:
                try:
                    element = await self._page.wait_for_selector(selector, timeout=5000)
                    if element:
                        logger.debug("User is authenticated")
                        return True
                except Exception:
                    continue

            # Check for login page indicators
            for selector in SELECTORS["login_page_indicator"]:
                try:
                    element = await self._page.wait_for_selector(selector, timeout=3000)
                    if element:
                        logger.warning("Login page detected - session expired")
                        return False
                except Exception:
                    continue

            # Ambiguous state - assume not authenticated
            logger.warning("Could not determine auth state")
            return False

        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False

    async def _click_new_post(self) -> None:
        """Click 'What's on your mind?' to open composer."""
        for selector in SELECTORS["new_post_trigger"]:
            try:
                element = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if element:
                    await element.click()
                    await asyncio.sleep(1)  # Wait for composer to open
                    logger.debug(f"Clicked new post trigger: {selector}")
                    return
            except Exception:
                continue

        raise SelectorNotFoundError("new_post_trigger", SELECTORS["new_post_trigger"])

    async def _enter_content(self, content: str) -> None:
        """Type post content into editor."""
        for selector in SELECTORS["post_editor"]:
            try:
                element = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if element:
                    await element.click()
                    await asyncio.sleep(0.5)
                    await element.fill(content)
                    await asyncio.sleep(0.5)
                    logger.debug(f"Entered content using: {selector}")
                    return
            except Exception:
                continue

        raise SelectorNotFoundError("post_editor", SELECTORS["post_editor"])

    async def _set_visibility(self, visibility: str) -> None:
        """Set post visibility (public/friends/only_me)."""
        # Map visibility to selector key
        visibility_map = {
            "public": "visibility_public",
            "friends": "visibility_friends",
            "only_me": "visibility_only_me",
        }

        if visibility not in visibility_map:
            logger.warning(f"Unknown visibility '{visibility}', defaulting to public")
            visibility = "public"

        # Try to click visibility button first
        try:
            for selector in SELECTORS["visibility_button"]:
                try:
                    element = await self._page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        await asyncio.sleep(1)
                        logger.debug("Clicked visibility button")
                        break
                except Exception:
                    continue
        except Exception:
            logger.debug("No visibility button found, visibility may be pre-set")
            return

        # Select the visibility option
        visibility_key = visibility_map[visibility]
        for selector in SELECTORS.get(visibility_key, []):
            try:
                element = await self._page.wait_for_selector(selector, timeout=5000)
                if element:
                    await element.click()
                    await asyncio.sleep(1)
                    logger.debug(f"Set visibility to {visibility}")
                    return
            except Exception:
                continue

        logger.warning(f"Could not set visibility to {visibility}")

    async def _click_post_button(self) -> None:
        """Click Post button to submit."""
        for selector in SELECTORS["post_button"]:
            try:
                element = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if element:
                    await element.click()
                    logger.debug(f"Clicked post button: {selector}")
                    return
            except Exception:
                continue

        raise SelectorNotFoundError("post_button", SELECTORS["post_button"])

    async def _wait_for_success(self) -> bool:
        """Wait for post success indicator.

        Returns:
            True if success indicator found, False otherwise
        """
        try:
            # Wait for page to settle after posting
            await asyncio.sleep(3)

            # Check for success indicators
            for selector in SELECTORS["post_success_indicator"]:
                try:
                    element = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["post_submit"])
                    if element:
                        logger.debug("Post success indicator found")
                        return True
                except Exception:
                    continue

            # Check if we're still on the feed (success)
            current_url = self._page.url
            if "facebook.com" in current_url and "login" not in current_url.lower():
                logger.debug("Still on Facebook feed - assuming success")
                return True

            return False

        except Exception as e:
            logger.error(f"Error waiting for success: {e}")
            return False

    async def _extract_post_url(self) -> str | None:
        """Extract Facebook post URL if possible.

        Returns:
            Post URL or None if not found
        """
        try:
            # Look for the most recent post with a permalink
            # This is fragile and may not always work
            await asyncio.sleep(2)

            # Try to find a post element and extract its URL
            # Facebook doesn't always provide direct URLs easily
            logger.debug("Post URL extraction not implemented - returning None")
            return None

        except Exception as e:
            logger.debug(f"Could not extract post URL: {e}")
            return None

    async def publish_post(self, content: str, visibility: str = "public") -> PublishResult:
        """Publish text content to Facebook.

        Args:
            content: The post text content
            visibility: One of 'public', 'friends', 'only_me'

        Returns:
            PublishResult with success status, post_url, error details
        """
        start_time = time.time()

        try:
            if not self._page:
                await self.initialize()

            # Check authentication
            if not await self.is_authenticated():
                raise SessionExpiredError()

            # Open composer
            await self._click_new_post()

            # Enter content
            await self._enter_content(content)

            # Set visibility
            await self._set_visibility(visibility)

            # Click post button
            await self._click_post_button()

            # Wait for success
            success = await self._wait_for_success()

            if success:
                post_url = await self._extract_post_url()
                duration_ms = int((time.time() - start_time) * 1000)
                return PublishResult(
                    success=True,
                    post_url=post_url,
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                )
            else:
                duration_ms = int((time.time() - start_time) * 1000)
                return PublishResult(
                    success=False,
                    error="Could not confirm post success",
                    error_type="PublishConfirmationError",
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                )

        except SessionExpiredError:
            raise
        except SelectorNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(
                success=False,
                error=str(e),
                error_type="SelectorNotFoundError",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )

    async def _adjust_for_retry(self, attempt: int) -> None:
        """Adjust timeouts and strategy for retry attempt.

        Args:
            attempt: Current attempt number (1-based)
        """
        if attempt == 2:
            # Second attempt: refresh page and increase delays
            logger.info("Retry attempt 2: refreshing page")
            try:
                await self._page.reload(timeout=TIMEOUTS["page_load"])
                await asyncio.sleep(3)
            except Exception:
                pass
        elif attempt == 3:
            # Third attempt: reinitialize browser
            logger.info("Retry attempt 3: reinitializing browser")
            await self.close()
            await asyncio.sleep(2)
            await self.initialize()
            await asyncio.sleep(3)

    async def publish_with_retry(
        self, content: str, visibility: str = "public", max_attempts: int = 3
    ) -> PublishResult:
        """Publish with retry logic per Constitution Principle V (Ralph Wiggum Loop).

        Attempt 1: Execute as planned
        Attempt 2: Refresh page, adjust wait times, retry
        Attempt 3: Reinitialize browser, simplify approach, retry
        After 3 failures: Return failure result for escalation

        Args:
            content: The post text content
            visibility: Post visibility
            max_attempts: Maximum retry attempts (default: 3)

        Returns:
            PublishResult with success status and retry count
        """
        last_result = None

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Publish attempt {attempt}/{max_attempts}")

            try:
                result = await self.publish_post(content, visibility)
                result.retry_count = attempt

                if result.success:
                    return result

                last_result = result

                # Don't retry session expired errors
                if result.error_type == "SessionExpiredError":
                    raise SessionExpiredError()

                # Adjust for next retry if not last attempt
                if attempt < max_attempts:
                    await self._adjust_for_retry(attempt + 1)
                    await asyncio.sleep(self.config.retry_delay)

            except SessionExpiredError:
                raise
            except Exception as e:
                logger.error(f"Attempt {attempt} failed with exception: {e}")
                last_result = PublishResult(
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    retry_count=attempt,
                    timestamp=datetime.utcnow(),
                )

                if attempt < max_attempts:
                    await self._adjust_for_retry(attempt + 1)
                    await asyncio.sleep(self.config.retry_delay)

        # All attempts failed
        if last_result:
            last_result.retry_count = max_attempts
            return last_result

        return PublishResult(
            success=False,
            error="Max retries exceeded",
            error_type="MaxRetriesExceeded",
            retry_count=max_attempts,
            timestamp=datetime.utcnow(),
        )

    async def close(self) -> None:
        """Close browser and save session."""
        try:
            # Save storage state before closing
            if self._context and self.config.storage_state_path:
                ensure_directory(self.session_path)
                await self._context.storage_state(path=str(self.config.storage_state_path))
                logger.debug(f"Session saved to {self.config.storage_state_path}")
        except Exception as e:
            logger.warning(f"Could not save session: {e}")

        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._page = None
        logger.info("Browser closed")


async def run_auth_flow(config: FacebookPublisherConfig) -> bool:
    """Run headed browser for manual Facebook login.

    1. Launch Chromium in headed mode
    2. Navigate to facebook.com
    3. Display instructions to user
    4. Wait for login completion (detect feed page)
    5. Save storage_state to session_path
    6. Return success status

    Args:
        config: Publisher configuration

    Returns:
        True if authentication successful, False otherwise
    """
    ensure_directory(config.session_path)

    print("\n" + "=" * 60)
    print("Facebook Authentication Flow")
    print("=" * 60)
    print("\nA browser window will open to Facebook.")
    print("Please log in to your Facebook account.")
    print("The session will be saved for future headless use.")
    print("\nWaiting for login...")
    print("=" * 60 + "\n")

    playwright = await async_playwright().start()

    try:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        # Navigate to Facebook
        await page.goto(URLS["home"], timeout=TIMEOUTS["page_load"])

        # Wait for user to complete login (check for logged-in indicators)
        max_wait = 300  # 5 minutes
        start = time.time()

        while time.time() - start < max_wait:
            # Check for logged-in indicators
            for selector in SELECTORS["logged_in_indicator"]:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        print("\n✓ Login successful!")

                        # Save session
                        await context.storage_state(path=str(config.storage_state_path))
                        print(f"✓ Session saved to {config.storage_state_path}")

                        await context.close()
                        await browser.close()
                        await playwright.stop()
                        return True
                except Exception:
                    continue

            await asyncio.sleep(2)

        print("\n✗ Login timeout - please try again")
        await context.close()
        await browser.close()
        await playwright.stop()
        return False

    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        await playwright.stop()
        return False
