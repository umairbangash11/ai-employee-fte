"""Facebook Publisher - Publishes approved Facebook posts from the vault.

This module provides the execution layer that publishes approved Facebook posts
from /Approved/facebook/ to Facebook via Playwright browser automation.
"""

# Resilience module integration (Feature 015, T106)
from pathlib import Path as _Path

from resilience import (
    CircuitBreaker,
    ExitCode,
    HealthManager,
    ResilienceError,
    async_ralph_wiggum_loop,
    async_retry_with_backoff,
    exit_with_code,
    route_to_failed_queue,
)

__version__ = "0.1.0"


def create_facebook_health_manager(
    state_dir: _Path = _Path(".watcher-state"),
) -> HealthManager:
    """Factory for facebook_publisher's HealthManager (T108)."""
    return HealthManager(
        subsystem="facebook_publisher", state_dir=state_dir, version=__version__,
    )


def create_facebook_circuit_breaker(name: str = "facebook_api") -> CircuitBreaker:
    """Factory for Facebook API CircuitBreaker (T109)."""
    return CircuitBreaker(name=name)


from facebook_publisher.models import ApprovedPost, PublishResult, ExecutionState
from facebook_publisher.exceptions import (
    FacebookPublishError,
    SessionExpiredError,
    FrontmatterValidationError,
    DetectionError,
)
from facebook_publisher.handlers import (
    handle_publish_success,
    handle_publish_failure,
)

__version__ = "0.1.0"
__all__ = [
    "ApprovedPost",
    "PublishResult",
    "ExecutionState",
    "FacebookPublishError",
    "SessionExpiredError",
    "FrontmatterValidationError",
    "DetectionError",
    "handle_publish_success",
    "handle_publish_failure",
]
