"""WhatsApp Web Watcher for Obsidian vault integration.

Polls WhatsApp Web for unread messages and converts them to Markdown files.
Uses Playwright for browser automation with persistent session storage.
"""

__version__ = "0.1.0"

# Resilience module integration (Feature 015, T069)
from resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    ExitCode,
    HealthManager,
    HealthState,
    ResilienceError,
    RetryPolicy,
    async_ralph_wiggum_loop,
    exit_with_code,
    is_retryable,
    ralph_wiggum_loop,
    route_to_failed_queue,
    write_failure_log,
)
