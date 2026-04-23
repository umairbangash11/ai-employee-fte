"""Gmail API Watcher for Obsidian vault integration.

Polls Gmail for unread messages and converts them to Markdown files.
"""

__version__ = "0.1.0"

# Resilience module integration (Feature 015)
from resilience import (
    # Exceptions
    ResilienceError,
    TransientNetworkError,
    SessionExpiredError,
    RateLimitedError,
    CredentialsInvalidError,
    ExternalServiceDownError,
    is_retryable,
    # Retry utilities
    RetryPolicy,
    retry_with_backoff,
    ralph_wiggum_loop,
    # Health management
    HealthManager,
    HealthState,
    CircuitState,
    # Circuit breaker
    CircuitBreaker,
    CircuitOpenError,
    # Failed item routing
    route_to_failed_queue,
    # Failure logging
    write_failure_log,
    # Exit codes
    ExitCode,
    exit_with_code,
)
