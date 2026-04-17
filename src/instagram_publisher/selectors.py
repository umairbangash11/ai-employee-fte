"""DOM selectors, URLs and timeouts for Instagram Web automation."""

URLS: dict[str, str] = {
    "home": "https://www.instagram.com/",
    "login": "https://www.instagram.com/accounts/login/",
}

# Timeouts in milliseconds
TIMEOUTS: dict[str, int] = {
    "page_load": 30_000,
    "selector_wait": 10_000,
    "post_confirm": 15_000,
    "upload_wait": 20_000,
}

# CSS/XPath selectors with fallbacks (list = try in order)
SELECTORS: dict[str, list[str]] = {
    # Auth detection
    "logged_in_indicator": [
        'svg[aria-label="Home"]',
        'a[href="/"]',
        'div[role="navigation"]',
    ],
    "login_page_indicator": [
        'input[name="username"]',
        'button[type="submit"]',
    ],
    # New post flow
    "new_post_button": [
        'svg[aria-label="New post"]',
        'a[href="#"][role="link"] svg',
        '[aria-label="New post"]',
    ],
    "select_from_computer": [
        'button:has-text("Select from computer")',
        'input[type="file"]',
        '[aria-label="Select from computer"]',
    ],
    "next_button": [
        'button:has-text("Next")',
        'div[role="button"]:has-text("Next")',
    ],
    "caption_textarea": [
        'div[aria-label="Write a caption..."]',
        'textarea[aria-label="Write a caption..."]',
        'div[contenteditable="true"]',
    ],
    "share_button": [
        'button:has-text("Share")',
        'div[role="button"]:has-text("Share")',
    ],
    # Post confirmation
    "post_confirmation": [
        'span:has-text("Your post has been shared")',
        'div:has-text("Your reel has been shared")',
        '[aria-label="Post shared"]',
    ],
}
