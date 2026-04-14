"""Custom exceptions for Facebook Publisher."""


class FacebookPublishError(Exception):
    """Base exception for Facebook publishing errors."""

    pass


class SessionExpiredError(FacebookPublishError):
    """Raised when the Facebook session has expired.

    Actionable message: Run `facebook-publish auth` to re-authenticate.
    """

    def __init__(self, message: str = "Facebook session expired"):
        self.message = message
        self.action = "Run `facebook-publish auth` to re-authenticate."
        super().__init__(f"{message}. {self.action}")


class FrontmatterValidationError(FacebookPublishError):
    """Raised when frontmatter validation fails.

    Includes details about which fields are missing or invalid.
    """

    def __init__(self, message: str, missing_fields: list[str] | None = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(message)


class DetectionError(FacebookPublishError):
    """Raised when file detection fails."""

    pass


class PublishTimeoutError(FacebookPublishError):
    """Raised when a publish operation times out."""

    pass


class SelectorNotFoundError(FacebookPublishError):
    """Raised when a required DOM selector cannot be found."""

    def __init__(self, selector_name: str, tried_selectors: list[str] | None = None):
        self.selector_name = selector_name
        self.tried_selectors = tried_selectors or []
        message = f"Could not find element: {selector_name}"
        if tried_selectors:
            message += f" (tried: {', '.join(tried_selectors)})"
        super().__init__(message)
