"""Custom exceptions for Instagram Publisher."""


class InstagramPublishError(Exception):
    """Base exception for Instagram publishing errors."""
    pass


class SessionExpiredError(InstagramPublishError):
    """Raised when the Instagram session has expired."""

    def __init__(self, message: str = "Instagram session expired"):
        self.message = message
        self.action = "Run `instagram-executor auth` to re-authenticate."
        super().__init__(f"{message}. {self.action}")


class FrontmatterValidationError(InstagramPublishError):
    """Raised when frontmatter validation fails."""

    def __init__(self, message: str, missing_fields: list[str] | None = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(message)


class ImageNotFoundError(InstagramPublishError):
    """Raised when the image path in the proposal does not exist on disk."""

    def __init__(self, image_path: str):
        self.image_path = image_path
        super().__init__(f"Image not found: {image_path}")


class DetectionError(InstagramPublishError):
    """Raised when file detection fails."""
    pass


class PublishTimeoutError(InstagramPublishError):
    """Raised when a publish operation times out."""
    pass


class SelectorNotFoundError(InstagramPublishError):
    """Raised when a required DOM selector cannot be found."""

    def __init__(self, selector_name: str, tried_selectors: list[str] | None = None):
        self.selector_name = selector_name
        self.tried_selectors = tried_selectors or []
        message = f"Could not find element: {selector_name}"
        if tried_selectors:
            message += f" (tried: {', '.join(tried_selectors)})"
        super().__init__(message)
