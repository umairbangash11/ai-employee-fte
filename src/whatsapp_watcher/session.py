"""Playwright session management for WhatsApp Web.

Handles browser context creation, QR authentication, and session persistence.
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, TimeoutError as PlaywrightTimeoutError

from .config import WatcherConfig
from .selectors import Selectors, Timeouts


class SessionExpiredError(Exception):
    """Raised when WhatsApp Web session is expired or invalid."""

    def __init__(self, message: str = "WhatsApp session expired. Run `whatsapp-watcher --auth` to re-authenticate."):
        self.message = message
        super().__init__(self.message)


class QRTimeoutError(Exception):
    """Raised when QR code scan times out."""

    def __init__(self, message: str = "QR code scan timeout. Please scan faster and try again."):
        self.message = message
        super().__init__(self.message)


async def detect_session_state(page: Page) -> str:
    """Detect current WhatsApp Web session state.

    Args:
        page: Playwright page with WhatsApp Web loaded

    Returns:
        "qr_code" if QR code visible
        "authenticated" if main interface visible
        "loading" if neither visible yet
    """
    try:
        # Check for QR code
        qr_element = await page.query_selector(Selectors.QR_CODE)
        if qr_element:
            return "qr_code"

        # Check for main interface
        main_element = await page.query_selector(Selectors.MAIN_INTERFACE)
        if main_element:
            return "authenticated"

        # Still loading
        return "loading"
    except Exception:
        return "loading"


async def wait_for_qr_authentication(page: Page, timeout: int = Timeouts.QR_SCAN) -> None:
    """Wait for user to scan QR code and authenticate.

    Polls page state until QR code disappears and main interface loads.

    Args:
        page: Playwright page showing QR code
        timeout: Maximum wait time in milliseconds (default: 120000ms / 2 minutes)

    Raises:
        QRTimeoutError: If QR not scanned within timeout
    """
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = timeout / 1000

    print("Waiting for QR code scan... Please scan the QR code with your phone.", file=sys.stderr)

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            raise QRTimeoutError()

        state = await detect_session_state(page)

        if state == "authenticated":
            print("QR code scanned successfully!", file=sys.stderr)
            return

        # Wait a bit before checking again
        await asyncio.sleep(2)


async def wait_for_whatsapp_ready(page: Page, timeout: int = Timeouts.PAGE_LOAD) -> bool:
    """Wait for WhatsApp Web main interface to load.

    Args:
        page: Playwright page
        timeout: Maximum wait time in milliseconds (default: 30000ms)

    Returns:
        True if loaded successfully

    Raises:
        TimeoutError: If main interface not detected within timeout
    """
    try:
        await page.wait_for_selector(Selectors.MAIN_INTERFACE, timeout=timeout)
        print("WhatsApp Web loaded successfully.", file=sys.stderr)
        return True
    except PlaywrightTimeoutError:
        raise TimeoutError(f"WhatsApp Web main interface not loaded within {timeout}ms")


async def create_browser_context(
    config: WatcherConfig,
    playwright: Playwright
) -> BrowserContext:
    """Create Playwright browser context with WhatsApp Web session.

    If config.headless=False (--auth mode):
        - Launch headed browser
        - Navigate to web.whatsapp.com
        - Wait for QR code scan or existing session
        - Save session to storage_state_path

    If config.headless=True (normal mode):
        - Launch headless browser
        - Load session from storage_state_path
        - Navigate to web.whatsapp.com
        - Verify session is valid

    Args:
        config: WatcherConfig with session settings
        playwright: Playwright instance

    Returns:
        BrowserContext ready for scraping

    Raises:
        SessionExpiredError: If session invalid in headless mode
        QRTimeoutError: If QR not scanned within timeout in auth mode
    """
    # Ensure session directory exists
    config.session_path.mkdir(parents=True, exist_ok=True)

    # Launch browser
    browser = await playwright.chromium.launch(headless=config.headless)

    if config.headless:
        # Headless mode: Load existing session
        if not config.storage_state_path.exists():
            await browser.close()
            raise SessionExpiredError("Session file not found. Run `whatsapp-watcher --auth` first.")

        print(f"Loading session from {config.storage_state_path}", file=sys.stderr)
        context = await browser.new_context(storage_state=str(config.storage_state_path))
        page = await context.new_page()

        # Navigate to WhatsApp Web
        await page.goto("https://web.whatsapp.com", timeout=config.page_timeout)

        # Detect session state
        state = await detect_session_state(page)

        if state == "qr_code":
            # Session expired
            await context.close()
            await browser.close()
            raise SessionExpiredError()

        # Wait for main interface
        await wait_for_whatsapp_ready(page, timeout=config.page_timeout)
        print("Session loaded successfully (headless mode).", file=sys.stderr)

    else:
        # Headed mode: QR authentication
        print("Launching browser for QR authentication...", file=sys.stderr)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to WhatsApp Web
        await page.goto("https://web.whatsapp.com", timeout=config.page_timeout)

        # Detect current state
        state = await detect_session_state(page)

        if state == "qr_code":
            # Wait for QR scan
            await wait_for_qr_authentication(page)
            await wait_for_whatsapp_ready(page, timeout=config.page_timeout)
        elif state == "authenticated":
            # Already authenticated
            print("Already authenticated (no QR needed).", file=sys.stderr)
        else:
            # Wait for page to settle
            await asyncio.sleep(3)
            await wait_for_whatsapp_ready(page, timeout=config.page_timeout)

        # Save session
        await context.storage_state(path=str(config.storage_state_path))
        print(f"Session saved to {config.storage_state_path}", file=sys.stderr)
        print("Authentication complete! You can now run `whatsapp-watcher` to start polling.", file=sys.stderr)

    return context
