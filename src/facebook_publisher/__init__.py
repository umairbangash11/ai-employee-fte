"""Facebook Publisher - Publishes approved Facebook posts from the vault.

This module provides the execution layer that publishes approved Facebook posts
from /Approved/facebook/ to Facebook via Playwright browser automation.
"""

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
