"""LinkedIn DOM selectors for Playwright automation.

LinkedIn's DOM structure changes frequently. This module centralizes
all selectors for easier maintenance. Each selector has fallbacks.

When selectors break:
1. Open LinkedIn in a headed browser: linkedin-publish auth
2. Open DevTools (F12) → Elements, find the element, copy selector
3. Update the relevant list below (prepend — most specific first)
4. Re-run: linkedin-publish --vault-path vault/ run
"""

# Selectors with fallbacks (tried in order, most-likely-current first).
# The executor tries each one with a short per-selector timeout so the
# full list is exhausted quickly without a long overall stall.
SELECTORS = {
    # ── "Start a post" prompt on the feed page ───────────────────────────
    "start_post_button": [
        # Current layout (2024-2025)
        "[data-placeholder*='Start a post']",
        "[aria-placeholder*='Start a post']",
        "button[aria-label*='start a post' i]",
        ".share-creation-state__trigger",
        # Classic layout selectors (still present on some accounts)
        "button.share-box-feed-entry__trigger",
        "div.share-box-feed-entry__trigger",
        "[data-control-name='share.main-feed-post-prompt']",
        # Broadest fallback — the avatar/photo button that also opens the composer
        ".share-box-feed-entry__avatar",
    ],

    # ── Post composer text editor (inside the modal) ──────────────────────
    "post_editor": [
        # Quill-based rich text editor
        ".ql-editor[data-placeholder]",
        "[contenteditable='true'].ql-editor",
        # Role-based (layout-agnostic)
        "[role='textbox'][aria-placeholder*='What do you want to talk about']",
        "[role='textbox'][aria-label*='Text editor']",
        "[role='textbox'][aria-placeholder*='post']",
        # Scoped to the share-creation panel
        ".share-creation-state__text-editor .ql-editor",
        "[contenteditable='true'][data-placeholder]",
        # Broadest fallback — first textbox on the page
        "[role='textbox']",
    ],

    # ── "Post" submit button inside the composer modal ───────────────────
    "post_button": [
        # Explicit aria-label is the most reliable
        "button[aria-label='Post']",
        "button[aria-label*='Post' i]",
        # Class-based (classic layout)
        "button.share-actions__primary-action",
        "button.share-box_actions__primary-action",
        "[data-control-name='share.post']",
        # Broadest: any primary artdeco button (use last — may match other things)
        "button.artdeco-button--primary[aria-label*='Post']",
    ],

    # ── Post-publish confirmation (used to extract the URL) ──────────────
    "post_success_indicator": [
        "[data-urn*='activity']",
        ".feed-shared-update-v2",
        ".update-components-actor",
        ".feed-shared-actor",
    ],

    # ── Feed presence (auth check) ────────────────────────────────────────
    "feed_indicator": [
        ".scaffold-layout__main",
        "#main",
        ".core-rail",
        ".feed-shared-update-v2",
    ],

    # ── Login form presence (auth check) ─────────────────────────────────
    "login_indicator": [
        "#username",
        "form.login__form",
        ".sign-in-form",
        "[data-tracking-control-name='guest_homepage-basic_sign-in-submit']",
    ],

    # ── Cookie / consent banners ──────────────────────────────────────────
    "cookie_banner": [
        "button[action-type='ACCEPT']",
        ".artdeco-global-alert button[action-type='ACCEPT']",
        "#artdeco-global-alert-container button[action-type='ACCEPT']",
        "button[data-tracking-control-name*='cookie-policy-banner.accept']",
        "button[aria-label*='Accept cookies' i]",
    ],
}

# Wait times (in milliseconds)
WAIT_TIMES = {
    "short": 1000,       # 1 s  — brief pause after a click
    "medium": 3000,      # 3 s  — page-settle wait
    "long": 15000,       # 15 s — wait for an element to appear
    "very_long": 15000,  # 15 s — wait after submitting a post
    "per_selector": 3000, # 3 s — per-selector probe in _find_and_click
}

# URLs
URLS = {
    "home": "https://www.linkedin.com/feed/",
    "login": "https://www.linkedin.com/login",
}


def get_selector_with_fallbacks(key: str, attempt: int = 1) -> str:
    """Get selector string for Playwright, with fallback based on attempt.

    Args:
        key: Selector key from SELECTORS dict
        attempt: Retry attempt number (1-3)

    Returns:
        Selector string for Playwright

    Example:
        >>> get_selector_with_fallbacks("post_button", 1)
        "button.share-actions__primary-action"
        >>> get_selector_with_fallbacks("post_button", 2)
        "button[aria-label='Post']"
    """
    selectors = SELECTORS.get(key, [])
    if not selectors:
        raise ValueError(f"Unknown selector key: {key}")

    # Use different selector based on attempt
    index = min(attempt - 1, len(selectors) - 1)
    return selectors[index]


def get_all_selectors(key: str) -> str:
    """Get all selectors as comma-separated string for Playwright.

    Useful for locator.first() to try all selectors at once.

    Args:
        key: Selector key from SELECTORS dict

    Returns:
        Comma-separated selector string

    Example:
        >>> get_all_selectors("post_button")
        "button.share-actions__primary-action, button[aria-label='Post'], ..."
    """
    selectors = SELECTORS.get(key, [])
    if not selectors:
        raise ValueError(f"Unknown selector key: {key}")

    return ", ".join(selectors)
