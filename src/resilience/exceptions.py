"""
Unified exception hierarchy for all subsystems.

Implements FR-001 (Unified Exception Hierarchy) and FR-002 (Failure Categories)
from the 015-error-recovery-resilience specification.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class FailureCategory(str, Enum):
    """
    Failure categories per spec FR-002.

    Each category has an associated retry policy:
    - TRANSIENT_NETWORK: Retryable with exponential backoff
    - SESSION_EXPIRED: Retryable after re-authentication
    - RATE_LIMITED: Retryable after cooldown period
    - CREDENTIALS_INVALID: Not retryable (manual fix required)
    - DATA_MALFORMED: Not retryable (data issue)
    - RESOURCE_UNAVAILABLE: Conditional (depends on context)
    - EXTERNAL_SERVICE_DOWN: Retryable with circuit breaker
    - INTERNAL_ERROR: Not retryable (code bug)
    """
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    RATE_LIMITED = "RATE_LIMITED"
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID"
    DATA_MALFORMED = "DATA_MALFORMED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    EXTERNAL_SERVICE_DOWN = "EXTERNAL_SERVICE_DOWN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Categories that are NOT retryable by default
NON_RETRYABLE_CATEGORIES = {
    FailureCategory.CREDENTIALS_INVALID,
    FailureCategory.DATA_MALFORMED,
    FailureCategory.INTERNAL_ERROR,
}


@dataclass
class ResilienceError(Exception):
    """
    Base exception for all resilience-aware errors.

    All subsystem exceptions should inherit from this class
    to enable consistent retry and routing behavior.

    Attributes:
        error_code: Unique error code (ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>)
        category: Failure category for retry policy determination
        message: Human-readable, operator-actionable message
        retryable: Whether this error can be retried
        context: Additional key-value pairs for debugging
        source_item: Path to the item that caused the error
        subsystem: Name of the subsystem that raised the error
    """
    error_code: str
    category: FailureCategory
    message: str
    retryable: bool = True
    context: dict = field(default_factory=dict)
    source_item: Optional[Path] = None
    subsystem: Optional[str] = None

    def __post_init__(self):
        """Set retryable based on category if not explicitly overridden."""
        if self.category in NON_RETRYABLE_CATEGORIES:
            self.retryable = False
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"error_code={self.error_code!r}, "
            f"category={self.category.value!r}, "
            f"message={self.message!r}, "
            f"retryable={self.retryable})"
        )


class TransientNetworkError(ResilienceError):
    """Network timeout, DNS failure, connection refused, etc."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_NETWORK_TRANSIENT",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.TRANSIENT_NETWORK,
            message=message,
            **kwargs
        )


class SessionExpiredError(ResilienceError):
    """OAuth token expired, browser session invalid, cookies stale."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_SESSION_EXPIRED",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.SESSION_EXPIRED,
            message=message,
            **kwargs
        )


class RateLimitedError(ResilienceError):
    """API quota exceeded, rate limit hit."""

    def __init__(
        self,
        message: str,
        cooldown_seconds: int = 60,
        error_code: str = "ERR_RESILIENCE_RATE_LIMITED",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.RATE_LIMITED,
            message=message,
            **kwargs
        )
        self.cooldown_seconds = cooldown_seconds


class CredentialsInvalidError(ResilienceError):
    """Missing or bad credentials, API keys, secrets."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_CREDS_INVALID",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.CREDENTIALS_INVALID,
            message=message,
            retryable=False,
            **kwargs
        )


class DataMalformedError(ResilienceError):
    """Invalid input data, bad YAML frontmatter, parse errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_DATA_MALFORMED",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.DATA_MALFORMED,
            message=message,
            retryable=False,
            **kwargs
        )


class ResourceUnavailableError(ResilienceError):
    """File not found, directory missing, resource doesn't exist."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_RESOURCE_UNAVAILABLE",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.RESOURCE_UNAVAILABLE,
            message=message,
            retryable=False,
            **kwargs
        )


class ExternalServiceDownError(ResilienceError):
    """3rd party service unavailable (503, 502, connection refused)."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_RESILIENCE_SERVICE_DOWN",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.EXTERNAL_SERVICE_DOWN,
            message=message,
            **kwargs
        )


class InternalError(ResilienceError):
    """Unexpected code exception, programming error, assertion failure."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        error_code: str = "ERR_RESILIENCE_INTERNAL",
        **kwargs
    ):
        super().__init__(
            error_code=error_code,
            category=FailureCategory.INTERNAL_ERROR,
            message=message,
            retryable=False,
            **kwargs
        )
        self.original_exception = original_exception


def is_retryable(error: Exception) -> bool:
    """
    Check if an exception is retryable.

    Args:
        error: Any exception

    Returns:
        True if the error is a ResilienceError and marked as retryable,
        False otherwise (unknown errors are not retried by default).
    """
    if isinstance(error, ResilienceError):
        return error.retryable
    # Unknown errors are not retryable by default
    return False
