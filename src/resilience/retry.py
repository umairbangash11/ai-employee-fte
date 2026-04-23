"""
Retry utilities implementing Constitution Principle V (Ralph Wiggum Loop).

Implements FR-003 (Ralph Wiggum Loop Implementation) from the
015-error-recovery-resilience specification.

The Ralph Wiggum Loop pattern:
1. Attempt 1: Execute as planned
2. Attempt 2: Wait, re-read context, retry
3. Attempt 3: Wait longer, simplify approach, retry
4. After 3 failures: Log failure, route to Needs_Action
"""

import asyncio
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, TypeVar, ParamSpec

from .exceptions import is_retryable


P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum retry attempts (default: 3 per Constitution V)
        base_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for each subsequent delay
        max_delay: Maximum delay cap in seconds
        jitter_range: Random jitter range in seconds (prevents thundering herd)
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 30.0
    jitter_range: float = 0.5


# Default policy per Constitution Principle V
DEFAULT_POLICY = RetryPolicy()


def calculate_delay(attempt: int, policy: RetryPolicy) -> float:
    """
    Calculate delay for a retry attempt with exponential backoff and jitter.

    Args:
        attempt: Current attempt number (1-based)
        policy: Retry policy configuration

    Returns:
        Delay in seconds with jitter applied

    Example:
        With default policy (base=1.0, multiplier=2.0):
        - Attempt 1 (after first failure): ~1.0-1.5s
        - Attempt 2 (after second failure): ~2.0-2.5s
        - Attempt 3 (after third failure): ~4.0-4.5s
    """
    # Exponential backoff: base_delay * (multiplier ^ (attempt - 1))
    delay = policy.base_delay * (policy.backoff_multiplier ** (attempt - 1))

    # Cap at max_delay
    delay = min(delay, policy.max_delay)

    # Add random jitter to prevent thundering herd
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

    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def fetch_data():
            response = requests.get("https://api.example.com")
            if response.status_code == 503:
                raise TransientNetworkError("Service unavailable")
            return response.json()
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

                    # Check if we should retry
                    if not is_retryable(e) or attempt >= policy.max_attempts:
                        if on_failure:
                            on_failure(e, attempt)
                        raise

                    # Call retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retry
                    delay = calculate_delay(attempt, policy)
                    time.sleep(delay)

            # Should not reach here, but for type safety
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected state in retry loop")

        return wrapper

    return decorator


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_failure: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions with exponential backoff retry.

    Same interface as retry_with_backoff but uses asyncio.sleep
    to avoid blocking the event loop.

    Args:
        max_attempts: Maximum retry attempts (default: 3 per Constitution V)
        base_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for each subsequent delay
        on_retry: Callback called before each retry (exception, attempt)
        on_failure: Callback called after final failure (exception, attempts)

    Returns:
        Decorated async function with retry logic

    Example:
        @async_retry_with_backoff(max_attempts=3)
        async def fetch_data_async():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com") as resp:
                    if resp.status == 503:
                        raise TransientNetworkError("Service unavailable")
                    return await resp.json()
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_multiplier=backoff_multiplier,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # Check if we should retry
                    if not is_retryable(e) or attempt >= policy.max_attempts:
                        if on_failure:
                            on_failure(e, attempt)
                        raise

                    # Call retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retry (non-blocking)
                    delay = calculate_delay(attempt, policy)
                    await asyncio.sleep(delay)

            # Should not reach here, but for type safety
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected state in retry loop")

        return wrapper

    return decorator


def ralph_wiggum_loop(
    operation: Callable[[], T],
    simplify_fn: Optional[Callable[[], T]] = None,
    on_failure: Optional[Callable[[Exception, int, bool], None]] = None,
    policy: Optional[RetryPolicy] = None,
) -> T:
    """
    Constitution Principle V implementation (Ralph Wiggum Loop).

    The pattern:
    1. Attempt 1: Execute as planned
    2. Attempt 2: Re-read context, adjust parameters, retry
    3. Attempt 3: Simplify approach to minimal viable action, retry
    4. After 3 failures: Log failure, route to Needs_Action for human review

    Args:
        operation: Primary operation to attempt
        simplify_fn: Simplified fallback operation for attempt 3 (optional)
        on_failure: Called on each failure with (exception, attempt, is_final)
        policy: Retry policy (default: 3 attempts, exponential backoff)

    Returns:
        Result of successful operation

    Raises:
        The last exception if all attempts fail

    Example:
        def process_email(email_path):
            def primary_operation():
                content = email_path.read_text()
                return classify_email(content)

            def simplified_fallback():
                # Attempt 3: assume needs reply
                return {"action": "needs_reply", "confidence": 0.5}

            def on_failure(error, attempt, is_final):
                print(f"Attempt {attempt}/3 failed: {error}")
                if is_final:
                    route_to_needs_action(email_path, str(error))

            return ralph_wiggum_loop(
                operation=primary_operation,
                simplify_fn=simplified_fallback,
                on_failure=on_failure,
            )
    """
    if policy is None:
        policy = DEFAULT_POLICY

    last_error: Optional[Exception] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            # On final attempt, use simplified fallback if provided
            if attempt == policy.max_attempts and simplify_fn is not None:
                return simplify_fn()
            return operation()
        except Exception as e:
            last_error = e
            is_final = attempt >= policy.max_attempts

            # Call failure callback
            if on_failure:
                on_failure(e, attempt, is_final)

            # If final attempt or not retryable, raise immediately
            if is_final or not is_retryable(e):
                raise

            # Wait before retry
            delay = calculate_delay(attempt, policy)
            time.sleep(delay)

    # Should not reach here, but for type safety
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in ralph_wiggum_loop")


async def async_ralph_wiggum_loop(
    operation: Callable[[], T],
    simplify_fn: Optional[Callable[[], T]] = None,
    on_failure: Optional[Callable[[Exception, int, bool], None]] = None,
    policy: Optional[RetryPolicy] = None,
) -> T:
    """
    Async version of ralph_wiggum_loop.

    Same interface but uses asyncio.sleep for non-blocking delays.
    Note: operation and simplify_fn should be async functions.
    """
    if policy is None:
        policy = DEFAULT_POLICY

    last_error: Optional[Exception] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            # On final attempt, use simplified fallback if provided
            if attempt == policy.max_attempts and simplify_fn is not None:
                result = simplify_fn()
                if asyncio.iscoroutine(result):
                    return await result
                return result
            result = operation()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            last_error = e
            is_final = attempt >= policy.max_attempts

            # Call failure callback
            if on_failure:
                on_failure(e, attempt, is_final)

            # If final attempt or not retryable, raise immediately
            if is_final or not is_retryable(e):
                raise

            # Wait before retry (non-blocking)
            delay = calculate_delay(attempt, policy)
            await asyncio.sleep(delay)

    # Should not reach here, but for type safety
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in async_ralph_wiggum_loop")
