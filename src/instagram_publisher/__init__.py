"""instagram_publisher — approval-gated Instagram post publisher.

Monitors vault/Approved/instagram/ for human-approved post proposals
and publishes them to Instagram via Playwright browser automation.
"""

from instagram_publisher.config import InstagramPublisherConfig
from instagram_publisher.executor import InstagramPublisher

__all__ = ["InstagramPublisher", "InstagramPublisherConfig"]
