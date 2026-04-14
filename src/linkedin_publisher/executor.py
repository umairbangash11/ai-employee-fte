"""LinkedIn publisher using Playwright browser automation."""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .exceptions import AuthenticationError, PublishError, is_retryable_error
from .models import PublishResult
from .selectors import (
    get_selector_with_fallbacks,
    get_all_selectors,
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

    def __init__(self, session_path: Path, headless: bool = True):
        """Initialize publisher.

        Args:
            session_path: Path to store Playwright session (cookies, localStorage)
            headless: Run browser in headless mode (False for auth)
        """
        self.session_path = Path(session_path)
        self.headless = headless

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def initialize(self) -> None:
        """Launch browser with persistent context.

        Uses persistent context to store cookies and localStorage,
        allowing session reuse across runs.
        """
        # Ensure session directory exists
        self.session_path.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()

        # Launch with persistent context for session storage
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Get the default page or create one
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def is_authenticated(self) -> bool:
        """Check if LinkedIn session is valid.

        Navigates to LinkedIn home and checks for feed presence.

        Returns:
            True if authenticated, False if login required
        """
        if not self._page:
            raise RuntimeError("Publisher not initialized. Call initialize() first.")

        try:
            await self._page.goto(URLS["home"], wait_until="domcontentloaded")
            await self._page.wait_for_timeout(WAIT_TIMES["medium"])

            # Check for login form (indicates not authenticated)
            login_selector = get_all_selectors("login_indicator")
            login_element = await self._page.query_selector(login_selector)
            if login_element:
                return False

            # Check for feed (indicates authenticated)
            feed_selector = get_all_selectors("feed_indicator")
            feed_element = await self._page.query_selector(feed_selector)
            return feed_element is not None

        except Exception:
            return False

    async def _click_start_post(self, attempt: int = 1) -> None:
        """Click the "Start a post" button.

        Args:
            attempt: Retry attempt number (affects selector choice)

        Raises:
            PublishError: If button cannot be clicked
        """
        selector = get_selector_with_fallbacks("start_post_button", attempt)

        try:
            # Wait for selector to be visible
            await self._page.wait_for_selector(selector, timeout=WAIT_TIMES["long"])
            await self._page.click(selector)
            await self._page.wait_for_timeout(WAIT_TIMES["medium"])
        except Exception as e:
            raise PublishError(
                f"Failed to click start post button: {e}",
                retry_count=attempt,
                retryable=True,
            )

    async def _enter_content(self, content: str, attempt: int = 1) -> None:
        """Type content into post editor.

        Args:
            content: Post content to type
            attempt: Retry attempt number

        Raises:
            PublishError: If content cannot be entered
        """
        selector = get_selector_with_fallbacks("post_editor", attempt)

        try:
            # Wait for editor to be visible
            await self._page.wait_for_selector(selector, timeout=WAIT_TIMES["long"])

            # Click to focus
            await self._page.click(selector)
            await self._page.wait_for_timeout(WAIT_TIMES["short"])

            # Type content with realistic delay
            await self._page.type(selector, content, delay=20)
            await self._page.wait_for_timeout(WAIT_TIMES["short"])

        except Exception as e:
            raise PublishError(
                f"Failed to enter content: {e}",
                retry_count=attempt,
                retryable=True,
            )

    async def _click_post_button(self, attempt: int = 1) -> None:
        """Click the "Post" button to submit.

        Args:
            attempt: Retry attempt number

        Raises:
            PublishError: If post button cannot be clicked
        """
        selector = get_selector_with_fallbacks("post_button", attempt)

        try:
            # Wait for button to be visible and enabled
            await self._page.wait_for_selector(selector, timeout=WAIT_TIMES["long"])
            await self._page.wait_for_timeout(WAIT_TIMES["short"])

            # Click post button
            await self._page.click(selector)

            # Wait for post to be submitted
            await self._page.wait_for_timeout(WAIT_TIMES["very_long"])

        except Exception as e:
            raise PublishError(
                f"Failed to click post button: {e}",
                retry_count=attempt,
                retryable=True,
            )

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
            # Check authentication
            if not await self.is_authenticated():
                raise AuthenticationError("LinkedIn session expired. Run 'linkedin-publish auth' to re-authenticate.")

            # Navigate to home/feed
            await self._page.goto(URLS["home"], wait_until="domcontentloaded")
            await self._page.wait_for_timeout(WAIT_TIMES["medium"])

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
        """Close browser and save session.

        Session data is automatically persisted by Playwright's
        persistent context.
        """
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
