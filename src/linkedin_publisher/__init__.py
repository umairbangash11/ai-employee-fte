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
