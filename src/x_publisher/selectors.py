"""DOM selectors, URLs and timeouts for X (Twitter) Web automation."""

URLS: dict[str, str] = {
    "home": "https://x.com/home",
    "login": "https://x.com/i/flow/login",
}

TIMEOUTS: dict[str, int] = {
    "page_load": 30_000,
    "selector_wait": 10_000,
    "post_confirm": 15_000,
}

SELECTORS: dict[str, list[str]] = {
    "logged_in_indicator": [
        'a[aria-label="Home"]',
        'a[data-testid="AppTabBar_Home_Link"]',
        'div[data-testid="primaryColumn"]',
    ],
    "login_page_indicator": [
        'input[autocomplete="username"]',
        'div[data-testid="LoginForm"]',
    ],
    "compose_button": [
        'a[data-testid="SideNav_NewTweet_Button"]',
        'a[aria-label="Post"]',
        'button[data-testid="tweetButtonInline"]',
    ],
    "tweet_textarea": [
        'div[data-testid="tweetTextarea_0"]',
        'div[role="textbox"][aria-label="Post text"]',
        'div.public-DraftEditor-content',
    ],
    "post_button": [
        'button[data-testid="tweetButton"]',
        'div[data-testid="tweetButton"]',
        'button:has-text("Post")',
    ],
    "post_confirmation": [
        'div[data-testid="toast"]',
        'span:has-text("Your post was sent")',
        'div[aria-label="Your post was sent"]',
    ],
}
