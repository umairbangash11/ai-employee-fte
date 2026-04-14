"""Data models for LinkedIn publisher."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ApprovedPost:
    """Represents an approved LinkedIn post ready for publishing.

    Parsed from Markdown files in /Approved/linkedin/ with YAML frontmatter.

    Attributes:
        file_path: Path to the approval file
        content: Post content to publish
        frontmatter: Full YAML frontmatter as dict
        created_at: When the approval request was created
        source_path: Path to source that triggered this post
    """

    file_path: Path
    content: str
    frontmatter: dict
    created_at: datetime
    source_path: Optional[str] = None

    def __post_init__(self):
        """Ensure file_path is Path object."""
        self.file_path = Path(self.file_path)


@dataclass
class PublishResult:
    """Result of a LinkedIn publish attempt.

    Attributes:
        success: Whether publish succeeded
        post_url: URL of published post (if retrievable)
        error: Error message (if failed)
        error_type: Exception class name (if failed)
        retry_count: Number of attempts made
        timestamp: When the attempt completed
        publish_duration_ms: Time taken for publish (milliseconds)
    """

    success: bool
    post_url: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    publish_duration_ms: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "success": self.success,
            "post_url": self.post_url,
            "error": self.error,
            "error_type": self.error_type,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat() + "Z",
            "publish_duration_ms": self.publish_duration_ms,
        }


@dataclass
class ExecutionState:
    """State for tracking published posts (idempotency).

    Stored in .watcher-state/linkedin/publisher.json to prevent
    duplicate posts and track statistics.

    Attributes:
        processed_hashes: Set of SHA256 hashes of published posts
        last_run: When the publisher last ran
        total_published: Total successful publishes
        total_failed: Total failed publishes
    """

    processed_hashes: set[str] = field(default_factory=set)
    last_run: Optional[datetime] = None
    total_published: int = 0
    total_failed: int = 0

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "processed_hashes": list(self.processed_hashes),
            "last_run": self.last_run.isoformat() + "Z" if self.last_run else None,
            "total_published": self.total_published,
            "total_failed": self.total_failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionState":
        """Create from dict (loaded from JSON)."""
        last_run = None
        if data.get("last_run"):
            last_run_str = data["last_run"]
            # Handle both with and without Z suffix
            if last_run_str.endswith("Z"):
                last_run_str = last_run_str[:-1]
            last_run = datetime.fromisoformat(last_run_str)

        return cls(
            processed_hashes=set(data.get("processed_hashes", [])),
            last_run=last_run,
            total_published=data.get("total_published", 0),
            total_failed=data.get("total_failed", 0),
        )
