"""Data models for Facebook Publisher."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ApprovedPost:
    """Represents a Facebook post file approved for publication.

    Attributes:
        file_path: Path to the approval file
        content: The post content to publish
        frontmatter: Parsed YAML frontmatter
        created_at: When the approval was created
        visibility: Post visibility (public, friends, only_me)
    """

    file_path: Path
    content: str
    frontmatter: dict[str, Any]
    created_at: datetime
    visibility: str = "public"

    @property
    def action_type(self) -> str:
        """Get action_type from frontmatter."""
        return self.frontmatter.get("action_type", "")

    @property
    def source_path(self) -> str:
        """Get source path from frontmatter."""
        source = self.frontmatter.get("source", {})
        return source.get("path", "")

    @property
    def status(self) -> str:
        """Get current status from frontmatter."""
        return self.frontmatter.get("status", "pending")

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        # Extract visibility from frontmatter if not provided
        if self.visibility == "public" and "target" in self.frontmatter:
            self.visibility = self.frontmatter["target"].get("visibility", "public")


@dataclass
class PublishResult:
    """Outcome of a publish attempt.

    Attributes:
        success: Whether the publish succeeded
        post_url: URL of the published post (if successful)
        error: Error message (if failed)
        error_type: Type of error (if failed)
        retry_count: Number of attempts made
        timestamp: When the publish was attempted
        duration_ms: Duration of the publish attempt in milliseconds
    """

    success: bool
    post_url: str | None = None
    error: str | None = None
    error_type: str | None = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0

    @property
    def is_retryable(self) -> bool:
        """Check if this failure can be retried."""
        non_retryable_errors = [
            "SessionExpiredError",
            "FrontmatterValidationError",
        ]
        return not self.success and self.error_type not in non_retryable_errors


@dataclass
class ExecutionState:
    """Tracks processed files and statistics.

    Attributes:
        processed_hashes: Set of content hashes already processed
        last_run: Timestamp of last execution
        stats: Statistics counters
    """

    processed_hashes: set[str] = field(default_factory=set)
    last_run: datetime | None = None
    stats: dict[str, int] = field(
        default_factory=lambda: {
            "total_published": 0,
            "total_failed": 0,
            "total_skipped": 0,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "processed_hashes": list(self.processed_hashes),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionState":
        """Create from dictionary (JSON deserialization)."""
        last_run = None
        if data.get("last_run"):
            last_run = datetime.fromisoformat(data["last_run"])
        return cls(
            processed_hashes=set(data.get("processed_hashes", [])),
            last_run=last_run,
            stats=data.get("stats", {"total_published": 0, "total_failed": 0, "total_skipped": 0}),
        )
