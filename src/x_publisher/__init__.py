"""x_publisher — approval-gated X (Twitter) post publisher.

Monitors vault/Approved/x/ for human-approved post proposals
and publishes them to X via Playwright browser automation.
"""

from x_publisher.config import XPublisherConfig
from x_publisher.executor import XPublisher

__all__ = ["XPublisher", "XPublisherConfig"]
