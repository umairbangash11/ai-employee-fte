# API Contract: Resilience Module

**Feature**: 015-error-recovery-resilience
**Date**: 2026-04-20

---

## 1. Exception Classes

### src/resilience/exceptions.py

```python
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class FailureCategory(str, Enum):
    """Failure categories per spec FR-002."""
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    RATE_LIMITED = "RATE_LIMITED"
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID"
    DATA_MALFORMED = "DATA_MALFORMED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    EXTERNAL_SERVICE_DOWN = "EXTERNAL_SERVICE_DOWN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ResilienceError(Exception):
    """Base exception for all resilience-aware errors."""

    error_code: str
    category: FailureCategory
    message: str
    retryable: bool = True
    context: dict = field(default_factory=dict)
    source_item: Optional[Path] = None
    subsystem: Optional[str] = None

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __post_init__(self):
        # Set retryable based on category if not explicitly set
        non_retryable = {
            FailureCategory.CREDENTIALS_INVALID,
            FailureCategory.DATA_MALFORMED,
            FailureCategory.INTERNAL_ERROR,
        }
        if self.category in non_retryable:
            self.retryable = False


# Convenience subclasses
class TransientNetworkError(ResilienceError):
    """Network timeout, DNS failure, etc."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_NETWORK_TRANSIENT"),
            category=FailureCategory.TRANSIENT_NETWORK,
            message=message,
            **kwargs
        )


class SessionExpiredError(ResilienceError):
    """OAuth/browser session invalid."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_SESSION_EXPIRED"),
            category=FailureCategory.SESSION_EXPIRED,
            message=message,
            **kwargs
        )


class RateLimitedError(ResilienceError):
    """API quota exceeded."""

    cooldown_seconds: int = 60

    def __init__(self, message: str, cooldown_seconds: int = 60, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_RATE_LIMITED"),
            category=FailureCategory.RATE_LIMITED,
            message=message,
            **kwargs
        )
        self.cooldown_seconds = cooldown_seconds


class CredentialsInvalidError(ResilienceError):
    """Missing or bad credentials."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_CREDS_INVALID"),
            category=FailureCategory.CREDENTIALS_INVALID,
            message=message,
            retryable=False,
            **kwargs
        )


class DataMalformedError(ResilienceError):
    """Invalid input data."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_DATA_MALFORMED"),
            category=FailureCategory.DATA_MALFORMED,
            message=message,
            retryable=False,
            **kwargs
        )


class ResourceUnavailableError(ResilienceError):
    """File/path not found."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_RESOURCE_UNAVAILABLE"),
            category=FailureCategory.RESOURCE_UNAVAILABLE,
            message=message,
            retryable=False,
            **kwargs
        )


class ExternalServiceDownError(ResilienceError):
    """3rd party service unavailable."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_SERVICE_DOWN"),
            category=FailureCategory.EXTERNAL_SERVICE_DOWN,
            message=message,
            **kwargs
        )


class InternalError(ResilienceError):
    """Unexpected code exception."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None, **kwargs):
        super().__init__(
            error_code=kwargs.pop("error_code", "ERR_RESILIENCE_INTERNAL"),
            category=FailureCategory.INTERNAL_ERROR,
            message=message,
            retryable=False,
            **kwargs
        )
        self.original_exception = original_exception


def is_retryable(error: Exception) -> bool:
    """Check if an exception is retryable."""
    if isinstance(error, ResilienceError):
        return error.retryable
    # Default: unknown errors are not retryable
    return False
```

---

## 2. Retry Utilities

### src/resilience/retry.py

```python
import asyncio
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Optional, TypeVar, ParamSpec

from .exceptions import ResilienceError, FailureCategory, is_retryable


P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 30.0
    jitter_range: float = 0.5


def calculate_delay(attempt: int, policy: RetryPolicy) -> float:
    """Calculate delay for a retry attempt with jitter."""
    delay = policy.base_delay * (policy.backoff_multiplier ** (attempt - 1))
    delay = min(delay, policy.max_delay)
    jitter = random.uniform(0, policy.jitter_range)
    return delay + jitter


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_failure: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for synchronous functions with exponential backoff retry.

    Args:
        max_attempts: Maximum retry attempts (default: 3 per Constitution V)
        base_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for each subsequent delay
        on_retry: Callback called before each retry (exception, attempt)
        on_failure: Callback called after final failure (exception, attempts)

    Returns:
        Decorated function with retry logic
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_multiplier=backoff_multiplier,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if not is_retryable(e) or attempt >= policy.max_attempts:
                        if on_failure:
                            on_failure(e, attempt)
                        raise

                    if on_retry:
                        on_retry(e, attempt)

                    delay = calculate_delay(attempt, policy)
                    time.sleep(delay)

            # Should not reach here, but for type safety
            raise last_error  # type: ignore

        return wrapper

    return decorator


async def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_failure: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions with exponential backoff retry.

    Same interface as retry_with_backoff but uses asyncio.sleep.
    """
    # Similar implementation with asyncio.sleep
    ...


def ralph_wiggum_loop(
    operation: Callable[[], T],
    simplify_fn: Optional[Callable[[], T]] = None,
    on_failure: Optional[Callable[[Exception, int, bool], None]] = None,
    policy: Optional[RetryPolicy] = None,
) -> T:
    """
    Constitution Principle V implementation.

    Args:
        operation: Primary operation to attempt
        simplify_fn: Simplified fallback operation for attempt 3
        on_failure: Called on each failure (exception, attempt, is_final)
        policy: Retry policy (default: 3 attempts, exponential backoff)

    Returns:
        Result of successful operation

    Raises:
        ResilienceError: After all attempts exhausted
    """
    if policy is None:
        policy = RetryPolicy()

    last_error: Optional[Exception] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            if attempt == policy.max_attempts and simplify_fn:
                return simplify_fn()
            return operation()
        except Exception as e:
            last_error = e
            is_final = attempt >= policy.max_attempts

            if on_failure:
                on_failure(e, attempt, is_final)

            if is_final or not is_retryable(e):
                raise

            delay = calculate_delay(attempt, policy)
            time.sleep(delay)

    raise last_error  # type: ignore
```

---

## 3. Health Management

### src/resilience/health.py

```python
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthStatus:
    """Subsystem health status."""

    subsystem: str
    status: HealthState
    last_heartbeat: datetime
    last_success: datetime
    consecutive_failures: int
    degradation_reason: Optional[str] = None
    circuit_state: Optional[CircuitState] = None
    version: str = "0.1.0"

    def to_json(self) -> str:
        """Serialize to JSON for file storage."""
        data = asdict(self)
        data["status"] = self.status.value
        data["last_heartbeat"] = self.last_heartbeat.isoformat()
        data["last_success"] = self.last_success.isoformat()
        if self.circuit_state:
            data["circuit_state"] = self.circuit_state.value
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "HealthStatus":
        """Deserialize from JSON file."""
        parsed = json.loads(data)
        return cls(
            subsystem=parsed["subsystem"],
            status=HealthState(parsed["status"]),
            last_heartbeat=datetime.fromisoformat(parsed["last_heartbeat"]),
            last_success=datetime.fromisoformat(parsed["last_success"]),
            consecutive_failures=parsed["consecutive_failures"],
            degradation_reason=parsed.get("degradation_reason"),
            circuit_state=CircuitState(parsed["circuit_state"]) if parsed.get("circuit_state") else None,
            version=parsed.get("version", "0.1.0"),
        )

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if heartbeat is older than threshold."""
        age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return age > max_age_seconds


class HealthManager:
    """Manages health file for a subsystem."""

    def __init__(self, subsystem: str, state_dir: Path = Path(".watcher-state")):
        self.subsystem = subsystem
        self.health_file = state_dir / f"{subsystem}_health.json"
        self._status: Optional[HealthStatus] = None
        state_dir.mkdir(parents=True, exist_ok=True)

    def record_success(self) -> None:
        """Record a successful operation."""
        now = datetime.utcnow()
        self._status = HealthStatus(
            subsystem=self.subsystem,
            status=HealthState.HEALTHY,
            last_heartbeat=now,
            last_success=now,
            consecutive_failures=0,
        )
        self._write()

    def record_failure(self, reason: str) -> None:
        """Record a failed operation."""
        now = datetime.utcnow()
        if self._status is None:
            self._load()

        failures = (self._status.consecutive_failures if self._status else 0) + 1

        if failures >= 3:
            status = HealthState.UNHEALTHY
        elif failures >= 1:
            status = HealthState.DEGRADED
        else:
            status = HealthState.HEALTHY

        self._status = HealthStatus(
            subsystem=self.subsystem,
            status=status,
            last_heartbeat=now,
            last_success=self._status.last_success if self._status else now,
            consecutive_failures=failures,
            degradation_reason=reason,
        )
        self._write()

    def heartbeat(self) -> None:
        """Update heartbeat timestamp without changing status."""
        if self._status is None:
            self._load()
        if self._status:
            self._status.last_heartbeat = datetime.utcnow()
            self._write()

    def get_status(self) -> Optional[HealthStatus]:
        """Get current health status."""
        self._load()
        return self._status

    def _write(self) -> None:
        """Write status to file."""
        if self._status:
            self.health_file.write_text(self._status.to_json())

    def _load(self) -> None:
        """Load status from file."""
        if self.health_file.exists():
            self._status = HealthStatus.from_json(self.health_file.read_text())
```

---

## 4. Circuit Breaker

### src/resilience/circuit_breaker.py

```python
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar, Optional

from .health import CircuitState


T = TypeVar("T")


@dataclass
class CircuitBreaker:
    """Circuit breaker for external API calls."""

    name: str
    failure_threshold: int = 5
    failure_rate_threshold: float = 0.5
    failure_window_seconds: int = 60
    recovery_timeout_seconds: int = 30
    success_threshold: int = 3

    # Internal state
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _success_count: int = 0
    _last_failure_time: Optional[datetime] = None
    _opened_at: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        """Get current state with automatic transitions."""
        now = datetime.utcnow()

        if self._state == CircuitState.OPEN and self._opened_at:
            elapsed = (now - self._opened_at).total_seconds()
            if elapsed >= self.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0

        return self._state

    def can_execute(self) -> bool:
        """Check if call should proceed."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed call."""
        now = datetime.utcnow()
        self._failure_count += 1
        self._last_failure_time = now

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = now
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = now

    def execute(self, operation: Callable[[], T]) -> T:
        """Execute operation with circuit breaker protection."""
        if not self.can_execute():
            raise CircuitOpenError(f"Circuit {self.name} is open")

        try:
            result = operation()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
    pass
```

---

## 5. Failure Logging

### src/resilience/logger.py

```python
from datetime import datetime
from pathlib import Path
from typing import Optional


def write_failure_log(
    logs_dir: Path,
    subsystem: str,
    failure_category: str,
    error_code: str,
    error_message: str,
    retry_count: int,
    is_final_failure: bool,
    action_taken: str,
    source_item: Optional[Path] = None,
    context: Optional[dict] = None,
    stack_trace: Optional[str] = None,
) -> Path:
    """
    Write structured failure log to Logs/ as Markdown with YAML frontmatter.

    Returns:
        Path to created log file
    """
    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    slug = error_code.lower().replace("_", "-").replace("err-", "")[:30]
    filename = f"{timestamp}_failure_{subsystem}_{slug}.md"
    filepath = logs_dir / filename

    logs_dir.mkdir(parents=True, exist_ok=True)

    # Build YAML frontmatter
    frontmatter = {
        "log_id": f"{timestamp}-failure-{subsystem}-{slug}",
        "timestamp": now.isoformat() + "Z",
        "action_type": "failure_record",
        "subsystem": subsystem,
        "failure_category": failure_category,
        "error_code": error_code,
        "retry_count": retry_count,
        "is_final_failure": is_final_failure,
        "source_item": str(source_item) if source_item else None,
        "error_message": error_message,
        "context": context or {},
        "action_taken": action_taken,
    }

    if stack_trace:
        frontmatter["stack_trace"] = stack_trace

    # Generate Markdown content
    lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif value is not None:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append("## Failure Details")
    lines.append("")
    lines.append(error_message)
    lines.append("")

    if stack_trace:
        lines.append("## Stack Trace")
        lines.append("")
        lines.append("```")
        lines.append(stack_trace)
        lines.append("```")
        lines.append("")

    lines.append("## Context")
    lines.append("")
    if context:
        for key, value in context.items():
            lines.append(f"- **{key}**: {value}")
    else:
        lines.append("No additional context.")

    filepath.write_text("\n".join(lines))
    return filepath
```

---

## 6. Exit Codes

### src/resilience/exit_codes.py

```python
from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for all subsystems."""

    SUCCESS = 0           # Clean shutdown
    RECOVERABLE = 1       # Restart with backoff
    CONFIGURATION = 2     # No restart (manual fix)
    FATAL = 3             # No restart (investigation)


def exit_with_code(code: ExitCode, message: str = "") -> None:
    """Exit process with standard code and optional message."""
    import sys

    if message:
        if code == ExitCode.SUCCESS:
            print(message)
        else:
            print(f"Error: {message}", file=sys.stderr)

    sys.exit(code)
```
