"""Ralph Wiggum Loop — retry logic for file operations.

Per Constitution Principle V: retry up to 3 times before failing.
"""

import time
from typing import TypeVar, Callable

T = TypeVar("T")

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.1


def with_retry(
    func: Callable[[], T],
    on_failure: Callable[[Exception], None] | None = None,
) -> T | None:
    """Execute function with up to 3 retries (Ralph Wiggum Loop).

    Args:
        func: Function to execute.
        on_failure: Optional callback called on final failure with the exception.

    Returns:
        Result of func() on success, or None on failure after 3 attempts.
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    # Final failure after 3 attempts
    if on_failure and last_error:
        on_failure(last_error)
    return None
