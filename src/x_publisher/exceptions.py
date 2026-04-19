"""Custom exceptions for X Publisher."""


class XPublishError(Exception):
    """Base exception for X publishing errors."""
    pass


class SessionExpiredError(XPublishError):
    """Raised when the X session has expired."""

    def __init__(self, message: str = "X session expired"):
        self.message = message
        self.action = "Run `x-executor auth` to re-authenticate."
        super().__init__(f"{message}. {self.action}")


class FrontmatterValidationError(XPublishError):
    """Raised when frontmatter validation fails."""

    def __init__(self, message: str, missing_fields: list[str] | None = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(message)


class DetectionError(XPublishError):
    """Raised when file detection fails."""
    pass


class PublishTimeoutError(XPublishError):
    """Raised when a publish operation times out."""
    pass


class SelectorNotFoundError(XPublishError):
    """Raised when a required DOM selector cannot be found."""

    def __init__(self, selector_name: str, tried_selectors: list[str] | None = None):
        self.selector_name = selector_name
        self.tried_selectors = tried_selectors or []
        message = f"Could not find element: {selector_name}"
        if tried_selectors:
            message += f" (tried: {', '.join(tried_selectors)})"
        super().__init__(message)
