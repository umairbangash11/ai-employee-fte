"""LinkedIn publisher for approved posts.

This module publishes approved LinkedIn posts from /Approved/linkedin/
to LinkedIn via Playwright browser automation. It detects approved files,
validates frontmatter, publishes content, and moves successful posts
to /Done/linkedin/.

Usage:
    linkedin-publish run       # Process all approved posts (one-shot)
    linkedin-publish watch     # Watch and process continuously
    linkedin-publish list      # List pending approved posts
    linkedin-publish status    # Show statistics
    linkedin-publish auth      # Authenticate with LinkedIn
"""

# Resilience module integration (Feature 015, T100)
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


def create_linkedin_health_manager(
    state_dir: _Path = _Path(".watcher-state"),
) -> HealthManager:
    """Factory for linkedin_publisher's HealthManager (T102)."""
    return HealthManager(
        subsystem="linkedin_publisher", state_dir=state_dir, version=__version__,
    )


def create_linkedin_circuit_breaker(name: str = "linkedin_api") -> CircuitBreaker:
    """Factory for LinkedIn API CircuitBreaker (T103)."""
    return CircuitBreaker(name=name)


from .config import LinkedInPublisherConfig
from .models import ApprovedPost, PublishResult, ExecutionState
from .exceptions import (
    LinkedInPublishError,
    InvalidFrontmatterError,
    PublishError,
    AuthenticationError,
    DuplicatePostError,
)

__all__ = [
    "LinkedInPublisherConfig",
    "ApprovedPost",
    "PublishResult",
    "ExecutionState",
    "LinkedInPublishError",
    "InvalidFrontmatterError",
    "PublishError",
    "AuthenticationError",
    "DuplicatePostError",
]

__version__ = "0.1.0"
