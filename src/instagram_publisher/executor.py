"""Instagram post executor using Playwright browser automation."""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from instagram_publisher.config import InstagramPublisherConfig
from instagram_publisher.exceptions import (
    ImageNotFoundError,
    PublishTimeoutError,
    SelectorNotFoundError,
    SessionExpiredError,
)
from instagram_publisher.models import ApprovedPost, PublishResult
from instagram_publisher.selectors import SELECTORS, TIMEOUTS, URLS
from instagram_publisher.utils import ensure_directory
from social_drafters.vault import ensure_vault_dirs

logger = logging.getLogger(__name__)


class InstagramPublisher:
    """Publishes posts to Instagram via Playwright browser automation.

    Workflow:
    1. Ensure vault directories exist
    2. Launch browser, load storage_state session
    3. Verify authentication
    4. Open new post composer
    5. Upload image (if provided)
    6. Enter caption
    7. Click Share
    8. Wait for confirmation
    9. Extract post URL if possible
    """

    def __init__(self, config: InstagramPublisherConfig):
        self.config = config
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None

    async def initialize(self) -> None:
        """Launch browser and ensure vault directories exist."""
        ensure_vault_dirs(self.config.vault_path, "instagram")
        ensure_directory(self.config.session_path)

        self._playwright = await async_playwright().start()

        storage_state = None
        if self.config.storage_state_path.exists():
            storage_state = str(self.config.storage_state_path)
            logger.debug(f"Loading session from {storage_state}")

        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
        self._context = await self._browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info("Instagram browser initialized")

    async def close(self) -> None:
        """Close browser and Playwright."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Instagram browser closed")

    async def is_authenticated(self) -> bool:
        """Check if Instagram session is valid."""
        if not self._page:
            return False
        try:
            await self._page.goto(URLS["home"], timeout=TIMEOUTS["page_load"])
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            for selector in SELECTORS["logged_in_indicator"]:
                try:
                    el = await self._page.wait_for_selector(selector, timeout=5000)
                    if el:
                        return True
                except Exception:
                    continue

            for selector in SELECTORS["login_page_indicator"]:
                try:
                    el = await self._page.wait_for_selector(selector, timeout=3000)
                    if el:
                        logger.warning("Login page detected — session expired")
                        return False
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.error(f"Auth check failed: {e}")
            return False

    async def publish(self, post: ApprovedPost) -> PublishResult:
        """Publish a single approved Instagram post.

        Args:
            post: Parsed approved post to publish

        Returns:
            PublishResult with success/failure details
        """
        if not self._page:
            return PublishResult(success=False, error="Browser not initialized", error_type="RuntimeError")

        start_time = time.time()

        # Image validation (FR-013)
        if post.image_path and not Path(post.image_path).exists():
            return PublishResult(
                success=False,
                error=f"Image not found: {post.image_path}",
                error_type="ImageNotFoundError",
            )

        try:
            if not await self.is_authenticated():
                raise SessionExpiredError()

            # Open new post dialog
            await self._click_new_post()

            # Handle image upload or text-only post
            if post.image_path:
                await self._upload_image(post.image_path)
                # Advance through the post creation steps
                await self._click_next()
                await self._click_next()  # Filter step (skip)
            else:
                # Text-only: navigate past image step if possible
                await self._click_next()

            # Enter caption
            await self._enter_caption(post.content)

            # Share the post
            await self._click_share()

            # Wait for confirmation
            post_url = await self._wait_for_confirmation()

            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(success=True, post_url=post_url, duration_ms=duration_ms)

        except SessionExpiredError:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )

    async def publish_with_retry(self, post: ApprovedPost) -> PublishResult:
        """Publish with Ralph Wiggum Loop (3 attempts with back-off).

        Constitution Principle V: retry up to 3 times, then route to Needs_Action.
        """
        last_result = PublishResult(success=False, error="No attempts made")

        for attempt in range(1, self.config.retry_attempts + 1):
            logger.info(f"Publish attempt {attempt}/{self.config.retry_attempts}: {post.file_path.name}")
            result = await self.publish(post)
            result.retry_count = attempt

            if result.success:
                return result

            last_result = result
            logger.warning(f"Attempt {attempt} failed: {result.error}")

            if not result.is_retryable:
                logger.info(f"Non-retryable error ({result.error_type}), stopping retries")
                break

            if attempt < self.config.retry_attempts:
                wait = self.config.retry_delay * attempt
                logger.info(f"Waiting {wait}s before retry...")
                await asyncio.sleep(wait)

        last_result.retry_count = self.config.retry_attempts
        return last_result

    # --- Private Playwright helpers ---

    async def _click_new_post(self) -> None:
        for selector in SELECTORS["new_post_button"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("new_post_button", SELECTORS["new_post_button"])

    async def _upload_image(self, image_path: str) -> None:
        for selector in SELECTORS["select_from_computer"]:
            try:
                if "input[type" in selector:
                    el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                    if el:
                        await el.set_input_files(image_path)
                        await asyncio.sleep(2)
                        return
                else:
                    el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                    if el:
                        async with self._page.expect_file_chooser() as fc_info:
                            await el.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(image_path)
                        await asyncio.sleep(2)
                        return
            except Exception:
                continue
        raise SelectorNotFoundError("select_from_computer", SELECTORS["select_from_computer"])

    async def _click_next(self) -> None:
        for selector in SELECTORS["next_button"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("next_button", SELECTORS["next_button"])

    async def _enter_caption(self, content: str) -> None:
        for selector in SELECTORS["caption_textarea"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    await el.fill(content)
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("caption_textarea", SELECTORS["caption_textarea"])

    async def _click_share(self) -> None:
        for selector in SELECTORS["share_button"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("share_button", SELECTORS["share_button"])

    async def _wait_for_confirmation(self) -> str | None:
        """Wait for post confirmation and try to extract post URL."""
        for selector in SELECTORS["post_confirmation"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["post_confirm"])
                if el:
                    logger.info("Post confirmation detected")
                    break
            except Exception:
                continue

        # Try to get current URL as post URL
        current_url = self._page.url
        if "instagram.com" in current_url and "/p/" in current_url:
            return current_url
        return None


async def run_auth_flow(config: InstagramPublisherConfig) -> bool:
    """Run headed authentication flow and export storage_state.json.

    Args:
        config: Publisher configuration (must have headless=False)

    Returns:
        True if auth succeeded and storage_state exported, False otherwise
    """
    playwright = await async_playwright().start()
    try:
        ensure_directory(config.session_path)
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await page.goto(URLS["login"], timeout=TIMEOUTS["page_load"])
        logger.info("Opened Instagram login page. Please log in manually.")
        logger.info(f"Waiting for navigation away from login... (press Ctrl+C to abort)")

        # Wait for the user to log in (URL changes away from /login)
        await page.wait_for_url(
            lambda url: "instagram.com" in url and "/login" not in url,
            timeout=120_000,
        )

        # Export session
        await context.storage_state(path=str(config.storage_state_path))
        logger.info(f"Session exported to {config.storage_state_path}")

        await browser.close()
        return True

    except Exception as e:
        logger.error(f"Auth flow failed: {e}")
        return False
    finally:
        await playwright.stop()
