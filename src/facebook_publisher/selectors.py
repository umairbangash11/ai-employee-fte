"""Facebook DOM selectors for Playwright automation.

IMPORTANT: Facebook's DOM structure changes frequently.
These selectors may need maintenance. Each selector list provides
fallback options - try each in order until one works.

Last verified: 2026-03-22
"""

# Selectors organized by action, with fallbacks
SELECTORS: dict[str, list[str]] = {
    # Trigger to open the post composer ("What's on your mind?")
    "new_post_trigger": [
        "[aria-label*=\"What's on your mind\"]",
        "[data-testid='creation-composer-trigger']",
        "div[role='button'][aria-label*='Create']",
        ".x1i10hfl[role='button']",  # Generic button class that Facebook uses
        "span:has-text('What\\'s on your mind')",
    ],
    # The text editor area in the post composer
    "post_editor": [
        "[contenteditable='true'][role='textbox']",
        "div[role='textbox'][aria-label*=\"What's on your mind\"]",
        "[contenteditable='true'][data-lexical-editor='true']",
        ".notranslate[contenteditable='true']",
        "[data-testid='post-box-text']",
    ],
    # Button to open visibility/audience selector
    "visibility_button": [
        "[aria-label='Edit audience']",
        "[aria-label='Select audience']",
        "[data-testid='visibility-selector']",
        "div[aria-haspopup='menu'][role='button']",
    ],
    # Visibility options in the dropdown
    "visibility_public": [
        "[aria-label='Public']",
        "span:has-text('Public')",
        "[role='menuitem']:has-text('Public')",
    ],
    "visibility_friends": [
        "[aria-label='Friends']",
        "span:has-text('Friends')",
        "[role='menuitem']:has-text('Friends')",
    ],
    "visibility_only_me": [
        "[aria-label='Only me']",
        "span:has-text('Only me')",
        "[role='menuitem']:has-text('Only me')",
    ],
    # The Post button to submit
    "post_button": [
        "[aria-label='Post'][role='button']",
        "div[aria-label='Post']",
        "[data-testid='post-button']",
        "span:has-text('Post'):visible",
        "div[role='button']:has-text('Post')",
    ],
    # Indicators that post was successful
    "post_success_indicator": [
        "[data-testid='post_message']",
        "div[data-pagelet='FeedUnit']",
        "[role='article']",
        ".x1yztbdb",  # Feed post container class
    ],
    # Indicators that user is logged in (feed page elements)
    "logged_in_indicator": [
        "[aria-label='Home']",
        "[data-testid='home_nav']",
        "[aria-label='Your profile']",
        "[data-pagelet='LeftRail']",
    ],
    # Login page elements (to detect if session expired)
    "login_page_indicator": [
        "input[name='email']",
        "input[name='pass']",
        "[data-testid='royal_email']",
        "#loginbutton",
    ],
    # Close button for dialogs/modals
    "close_dialog": [
        "[aria-label='Close']",
        "[data-testid='dialog-close-button']",
        "div[role='button'][aria-label='Close']",
    ],
}

# Timeout configurations (in milliseconds)
TIMEOUTS = {
    "selector_wait": 10000,  # Wait for selector to appear
    "page_load": 30000,  # Wait for page to load
    "post_submit": 60000,  # Wait for post to be submitted
    "navigation": 15000,  # Wait for navigation
}

# Facebook URLs
URLS = {
    "home": "https://www.facebook.com/",
    "login": "https://www.facebook.com/login/",
}
