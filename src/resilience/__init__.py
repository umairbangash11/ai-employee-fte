"""
Resilience module for AI Employee FTE.

Provides unified error handling, retry logic, circuit breakers,
health monitoring, and failure logging across all subsystems.

Constitution Principle V (Ralph Wiggum Loop) is implemented here.
"""

__version__ = "0.1.0"

# Exception hierarchy (FR-001, FR-002)
from .exceptions import (
    FailureCategory,
    ResilienceError,
    TransientNetworkError,
    SessionExpiredError,
    RateLimitedError,
    CredentialsInvalidError,
    DataMalformedError,
    ResourceUnavailableError,
    ExternalServiceDownError,
    InternalError,
    is_retryable,
)

# Exit codes (FR-007)
from .exit_codes import (
    ExitCode,
    exit_with_code,
)

# Retry utilities (FR-003, Constitution Principle V)
from .retry import (
    RetryPolicy,
    calculate_delay,
    retry_with_backoff,
    async_retry_with_backoff,
    ralph_wiggum_loop,
    async_ralph_wiggum_loop,
)

# Failed item routing (FR-006)
from .failed_routing import (
    FailedItemWrapper,
    route_to_failed_queue,
    get_failed_items,
    recover_failed_item,
)

# Structured failure logging (FR-005)
from .logger import (
    FailureLogEntry,
    write_failure_log,
    get_failure_logs,
)

# Health management (FR-004)
from .health import (
    HealthState,
    CircuitState,
    HealthStatus,
    HealthManager,
    read_all_health_files,
    compute_aggregate_status,
)

# Circuit breaker (FR-008)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)

__all__ = [
    # Version
    "__version__",
    # Exceptions
    "FailureCategory",
    "ResilienceError",
    "TransientNetworkError",
    "SessionExpiredError",
    "RateLimitedError",
    "CredentialsInvalidError",
    "DataMalformedError",
    "ResourceUnavailableError",
    "ExternalServiceDownError",
    "InternalError",
    "is_retryable",
    # Exit codes
    "ExitCode",
    "exit_with_code",
    # Retry utilities (FR-003, Constitution Principle V)
    "RetryPolicy",
    "calculate_delay",
    "retry_with_backoff",
    "async_retry_with_backoff",
    "ralph_wiggum_loop",
    "async_ralph_wiggum_loop",
    # Failed item routing (FR-006)
    "FailedItemWrapper",
    "route_to_failed_queue",
    "get_failed_items",
    "recover_failed_item",
    # Structured failure logging (FR-005)
    "FailureLogEntry",
    "write_failure_log",
    "get_failure_logs",
    # Health management (FR-004)
    "HealthState",
    "CircuitState",
    "HealthStatus",
    "HealthManager",
    "read_all_health_files",
    "compute_aggregate_status",
    # Circuit breaker (FR-008)
    "CircuitBreaker",
    "CircuitOpenError",
]
