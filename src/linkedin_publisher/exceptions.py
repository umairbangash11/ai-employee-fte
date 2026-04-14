"""Exceptions for LinkedIn publisher."""


class LinkedInPublishError(Exception):
    """Base exception for LinkedIn publisher."""

    pass


class InvalidFrontmatterError(LinkedInPublishError):
    """Raised when approval file has invalid or missing frontmatter.

    Required frontmatter fields:
    - type: approval_request
    - action_type: publish_linkedin_post
    - status: pending (in /Approved/ means approved by human)
    - target.platform: linkedin
    - target.post_type: text
    """

    def __init__(self, message: str = "Invalid frontmatter", file_path: str = ""):
        self.file_path = file_path
        super().__init__(f"{message}: {file_path}" if file_path else message)


class PublishError(LinkedInPublishError):
    """Raised when LinkedIn publish operation fails.

    Includes retry count and whether error is retryable.
    """

    def __init__(
        self,
        message: str = "Publish failed",
        retry_count: int = 0,
        retryable: bool = True,
    ):
        self.retry_count = retry_count
        self.retryable = retryable
        super().__init__(f"{message} (attempt {retry_count}, retryable={retryable})")


class AuthenticationError(LinkedInPublishError):
    """Raised when LinkedIn session is invalid or expired.

    Not retryable - requires manual re-authentication via `linkedin-publish auth`.
    """

    def __init__(self, message: str = "LinkedIn authentication required"):
        super().__init__(message)


class DuplicatePostError(LinkedInPublishError):
    """Raised when post content has already been published.

    Prevents duplicate posts via content hash checking.
    """

    def __init__(self, message: str = "Duplicate post content", hash_value: str = ""):
        self.hash_value = hash_value
        super().__init__(f"{message} (hash: {hash_value[:8]}...)" if hash_value else message)


def is_retryable_error(error: Exception) -> bool:
    """Check if error is retryable.

    Retryable errors:
    - Network timeouts
    - Transient DOM issues
    - PublishError with retryable=True

    Non-retryable errors:
    - AuthenticationError
    - InvalidFrontmatterError
    - DuplicatePostError
    - PublishError with retryable=False

    Args:
        error: Exception to check

    Returns:
        True if error is retryable, False otherwise
    """
    if isinstance(error, AuthenticationError):
        return False
    if isinstance(error, InvalidFrontmatterError):
        return False
    if isinstance(error, DuplicatePostError):
        return False
    if isinstance(error, PublishError):
        return error.retryable

    # Default: assume retryable for unknown errors
    error_str = str(error).lower()
    non_retryable_keywords = [
        "auth",
        "login",
        "permission",
        "forbidden",
        "invalid",
        "malformed",
    ]
    return not any(keyword in error_str for keyword in non_retryable_keywords)
