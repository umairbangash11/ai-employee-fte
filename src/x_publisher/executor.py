"""X (Twitter) post executor using Playwright browser automation."""

import asyncio
import logging
import time

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from x_publisher.config import XPublisherConfig
from x_publisher.exceptions import PublishTimeoutError, SelectorNotFoundError, SessionExpiredError
from x_publisher.models import ApprovedPost, PublishResult
from x_publisher.selectors import SELECTORS, TIMEOUTS, URLS
from x_publisher.utils import ensure_directory
from social_drafters.vault import ensure_vault_dirs

logger = logging.getLogger(__name__)


class XPublisher:
    """Publishes posts to X via Playwright browser automation.

    Workflow:
    1. Ensure vault directories exist
    2. Launch browser with storage_state session
    3. Verify authentication
    4. Click compose button
    5. Enter tweet text
    6. Click Post button
    7. Wait for confirmation
    8. Extract post URL if possible
    """

    def __init__(self, config: XPublisherConfig):
        self.config = config
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None

    async def initialize(self) -> None:
        """Launch browser and ensure vault directories exist."""
        ensure_vault_dirs(self.config.vault_path, "x")
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
        logger.info("X browser initialized")

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def is_authenticated(self) -> bool:
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
                        logger.warning("X login page detected — session expired")
                        return False
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.error(f"Auth check failed: {e}")
            return False

    async def publish(self, post: ApprovedPost) -> PublishResult:
        """Publish a single approved X post."""
        if not self._page:
            return PublishResult(success=False, error="Browser not initialized", error_type="RuntimeError")

        start_time = time.time()

        # Log advisory warning for over-limit content
        if post.exceeds_char_limit:
            logger.warning(
                f"Post char_count={post.char_count} exceeds 280. "
                "Operator approved — proceeding (FR-014 advisory only)."
            )

        try:
            if not await self.is_authenticated():
                raise SessionExpiredError()

            await self._click_compose()
            await self._enter_text(post.content)
            await self._click_post()
            post_url = await self._wait_for_confirmation()

            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(success=True, post_url=post_url, duration_ms=duration_ms)

        except SessionExpiredError:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return PublishResult(success=False, error=str(e), error_type=type(e).__name__, duration_ms=duration_ms)

    async def publish_with_retry(self, post: ApprovedPost) -> PublishResult:
        """Publish with Ralph Wiggum Loop (3 attempts with back-off).

        Constitution Principle V.
        """
        last_result = PublishResult(success=False, error="No attempts made")

        for attempt in range(1, self.config.retry_attempts + 1):
            logger.info(f"X publish attempt {attempt}/{self.config.retry_attempts}: {post.file_path.name}")
            result = await self.publish(post)
            result.retry_count = attempt

            if result.success:
                return result

            last_result = result
            logger.warning(f"Attempt {attempt} failed: {result.error}")

            if not result.is_retryable:
                break

            if attempt < self.config.retry_attempts:
                wait = self.config.retry_delay * attempt
                await asyncio.sleep(wait)

        last_result.retry_count = self.config.retry_attempts
        return last_result

    async def _click_compose(self) -> None:
        for selector in SELECTORS["compose_button"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("compose_button", SELECTORS["compose_button"])

    async def _enter_text(self, content: str) -> None:
        for selector in SELECTORS["tweet_textarea"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    await el.fill(content)
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("tweet_textarea", SELECTORS["tweet_textarea"])

    async def _click_post(self) -> None:
        for selector in SELECTORS["post_button"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["selector_wait"])
                if el:
                    await el.click()
                    return
            except Exception:
                continue
        raise SelectorNotFoundError("post_button", SELECTORS["post_button"])

    async def _wait_for_confirmation(self) -> str | None:
        for selector in SELECTORS["post_confirmation"]:
            try:
                el = await self._page.wait_for_selector(selector, timeout=TIMEOUTS["post_confirm"])
                if el:
                    logger.info("X post confirmation detected")
                    break
            except Exception:
                continue

        current_url = self._page.url
        if "x.com" in current_url and "/status/" in current_url:
            return current_url
        return None


async def run_auth_flow(config: XPublisherConfig) -> bool:
    """Run headed authentication flow and export storage_state.json."""
    playwright = await async_playwright().start()
    try:
        ensure_directory(config.session_path)
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await page.goto(URLS["login"], timeout=TIMEOUTS["page_load"])
        logger.info("Opened X login page. Please log in manually.")

        await page.wait_for_url(
            lambda url: "x.com" in url and "/flow/login" not in url,
            timeout=120_000,
        )

        await context.storage_state(path=str(config.storage_state_path))
        logger.info(f"Session exported to {config.storage_state_path}")

        await browser.close()
        return True
    except Exception as e:
        logger.error(f"Auth flow failed: {e}")
        return False
    finally:
        await playwright.stop()
