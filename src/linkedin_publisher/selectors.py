"""LinkedIn DOM selectors for Playwright automation.

LinkedIn's DOM structure changes frequently. This module centralizes
all selectors for easier maintenance. Each selector has fallbacks.

When selectors break:
1. Open LinkedIn in browser
2. Use DevTools to find new selectors
3. Update this file
4. Test with `linkedin-publish auth` (headed mode)
"""

# Selectors with fallbacks (tried in order)
SELECTORS = {
    # Button to open "Start a post" modal
    "start_post_button": [
        "button.share-box-feed-entry__trigger",
        "button[aria-label='Start a post']",
        "[data-control-name='share.main-feed-post-prompt']",
        ".share-box-feed-entry__avatar",
    ],
    # Post editor text area inside modal
    "post_editor": [
        ".ql-editor[data-placeholder]",
        "[role='textbox'][aria-label*='post']",
        ".share-creation-state__text-editor .ql-editor",
        "[contenteditable='true'][data-placeholder]",
    ],
    # Button to submit post
    "post_button": [
        "button.share-actions__primary-action",
        "button[aria-label='Post']",
        "button.share-box_actions__primary-action",
        "[data-control-name='share.post']",
    ],
    # Indicator that post was successful
    "post_success_indicator": [
        ".feed-shared-update-v2",
        "[data-urn*='activity']",
        ".update-components-actor",
        ".feed-shared-actor",
    ],
    # Feed presence indicator (for auth check)
    "feed_indicator": [
        ".feed-shared-update-v2",
        ".core-rail",
        "#main",
        ".scaffold-layout__main",
    ],
    # Login form indicator (for auth check)
    "login_indicator": [
        "form.login__form",
        "[data-tracking-control-name='guest_homepage-basic_sign-in-submit']",
        ".sign-in-form",
        "#username",
    ],
}

# Wait times (in milliseconds)
WAIT_TIMES = {
    "short": 1000,      # 1 second
    "medium": 3000,     # 3 seconds
    "long": 5000,       # 5 seconds
    "very_long": 10000, # 10 seconds
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
