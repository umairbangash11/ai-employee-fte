"""
Circuit breaker pattern for resilience framework.

Implements FR-008 (Circuit Breaker Pattern) from the
015-error-recovery-resilience specification.

Protects external API calls from cascading failures by
failing fast when a service is unavailable.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

from .health import CircuitState
from .exceptions import ResilienceError, FailureCategory


T = TypeVar("T")


class CircuitOpenError(ResilienceError):
    """
    Exception raised when circuit breaker is open.

    Indicates that requests are being blocked because the
    target service has too many recent failures.
    """

    def __init__(
        self,
        circuit_name: str,
        remaining_seconds: float,
        message: Optional[str] = None,
    ):
        """
        Initialize CircuitOpenError.

        Args:
            circuit_name: Name of the circuit breaker
            remaining_seconds: Seconds until circuit enters half-open
            message: Optional custom message
        """
        if message is None:
            message = (
                f"Circuit '{circuit_name}' is open. "
                f"Retry after {remaining_seconds:.1f} seconds."
            )

        super().__init__(
            error_code=f"ERR_CIRCUIT_{circuit_name.upper()}_OPEN",
            category=FailureCategory.EXTERNAL_SERVICE_DOWN,
            message=message,
            retryable=True,
            context={
                "circuit_name": circuit_name,
                "remaining_seconds": remaining_seconds,
            },
        )
        self.circuit_name = circuit_name
        self.remaining_seconds = remaining_seconds


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for protecting external API calls.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, all requests fail fast
    - HALF_OPEN: Testing if service recovered

    Attributes:
        name: Identifier for this circuit breaker
        failure_threshold: Failures to open circuit (default: 5)
        failure_rate_threshold: Failure rate to open circuit (default: 0.5)
        failure_window_seconds: Time window for failure counting (default: 60)
        recovery_timeout_seconds: Time before OPEN → HALF_OPEN (default: 30)
        success_threshold: Successes in HALF_OPEN to close (default: 3)

    Example:
        circuit = CircuitBreaker(name="gmail_api")

        try:
            result = circuit.execute(lambda: fetch_gmail())
        except CircuitOpenError:
            # Circuit is open, service likely down
            use_cached_data()
    """
    name: str
    failure_threshold: int = 5
    failure_rate_threshold: float = 0.5
    failure_window_seconds: float = 60.0
    recovery_timeout_seconds: float = 30.0
    success_threshold: int = 3

    # Internal state (not part of constructor)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)
    _request_count: int = field(default=0, init=False)
    _failure_times: list = field(default_factory=list, init=False)

    @property
    def state(self) -> CircuitState:
        """
        Get current circuit state with automatic OPEN → HALF_OPEN transition.

        Returns:
            Current CircuitState
        """
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._opened_at is not None:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0

        return self._state

    def _get_recent_failure_count(self) -> int:
        """Count failures within the failure window."""
        now = time.time()
        cutoff = now - self.failure_window_seconds
        self._failure_times = [t for t in self._failure_times if t > cutoff]
        return len(self._failure_times)

    def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Returns:
            True if circuit allows requests, False if open
        """
        current_state = self.state  # Triggers auto-transition

        if current_state == CircuitState.CLOSED:
            return True

        if current_state == CircuitState.HALF_OPEN:
            return True  # Allow test request

        # OPEN state
        return False

    def record_success(self) -> None:
        """
        Record a successful operation.

        In HALF_OPEN state, enough successes will close the circuit.
        """
        self._request_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                # Service recovered, close circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._failure_times.clear()
                self._opened_at = None

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed operation.

        May transition circuit to OPEN if threshold exceeded.
        """
        now = time.time()
        self._request_count += 1
        self._failure_count += 1
        self._failure_times.append(now)
        self._last_failure_time = now

        if self._state == CircuitState.HALF_OPEN:
            # Single failure in half-open returns to open
            self._state = CircuitState.OPEN
            self._opened_at = now
            self._success_count = 0

        elif self._state == CircuitState.CLOSED:
            # Check if we should open the circuit
            recent_failures = self._get_recent_failure_count()

            if recent_failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = now

    def execute(
        self,
        operation: Callable[[], T],
        fallback: Optional[Callable[[], T]] = None,
    ) -> T:
        """
        Execute an operation with circuit breaker protection.

        Args:
            operation: The operation to execute
            fallback: Optional fallback when circuit is open

        Returns:
            Result of operation or fallback

        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            if fallback is not None:
                return fallback()

            # Calculate remaining time
            remaining = 0.0
            if self._opened_at is not None:
                elapsed = time.time() - self._opened_at
                remaining = max(0, self.recovery_timeout_seconds - elapsed)

            raise CircuitOpenError(
                circuit_name=self.name,
                remaining_seconds=remaining,
            )

        try:
            result = operation()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    async def execute_async(
        self,
        operation: Callable[[], T],
        fallback: Optional[Callable[[], T]] = None,
    ) -> T:
        """
        Execute an async operation with circuit breaker protection.

        Args:
            operation: The async operation to execute
            fallback: Optional fallback when circuit is open

        Returns:
            Result of operation or fallback

        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
        """
        import asyncio

        current_state = self.state

        if current_state == CircuitState.OPEN:
            if fallback is not None:
                result = fallback()
                if asyncio.iscoroutine(result):
                    return await result
                return result

            remaining = 0.0
            if self._opened_at is not None:
                elapsed = time.time() - self._opened_at
                remaining = max(0, self.recovery_timeout_seconds - elapsed)

            raise CircuitOpenError(
                circuit_name=self.name,
                remaining_seconds=remaining,
            )

        try:
            result = operation()
            if asyncio.iscoroutine(result):
                result = await result
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def reset(self) -> None:
        """
        Reset circuit breaker to initial closed state.

        Useful for manual recovery or testing.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._request_count = 0
        self._last_failure_time = None
        self._opened_at = None
        self._failure_times.clear()

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dict with state, counts, and timing info
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "request_count": self._request_count,
            "recent_failures": self._get_recent_failure_count(),
            "last_failure_time": self._last_failure_time,
            "opened_at": self._opened_at,
        }
