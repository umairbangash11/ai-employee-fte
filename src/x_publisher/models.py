"""Data models for X Publisher."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ApprovedPost:
    """Represents an X post file approved for publication.

    Attributes:
        file_path: Path to the approval file
        content: The tweet text to publish
        frontmatter: Parsed YAML frontmatter
        created_at: When the approval was created
        char_count: Character count from frontmatter (may differ from len(content) if edited)
        image_path: Optional local image file path
    """

    file_path: Path
    content: str
    frontmatter: dict[str, Any]
    created_at: datetime
    char_count: int | None = None
    image_path: str | None = None

    @property
    def action_type(self) -> str:
        return self.frontmatter.get("action_type", "")

    @property
    def platform(self) -> str:
        return self.frontmatter.get("platform", "x")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "awaiting_approval")

    @property
    def exceeds_char_limit(self) -> bool:
        """True if char_count in frontmatter exceeds 280 (advisory only)."""
        return self.char_count is not None and self.char_count > 280

    def __post_init__(self) -> None:
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        if self.char_count is None:
            raw = self.frontmatter.get("char_count")
            self.char_count = int(raw) if raw is not None else None
        if self.image_path is None:
            self.image_path = self.frontmatter.get("image_path") or None


@dataclass
class PublishResult:
    """Outcome of a publish attempt."""

    success: bool
    post_url: str | None = None
    error: str | None = None
    error_type: str | None = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0

    @property
    def is_retryable(self) -> bool:
        non_retryable = {"SessionExpiredError", "FrontmatterValidationError"}
        return not self.success and self.error_type not in non_retryable


@dataclass
class ExecutionState:
    """Tracks processed files and statistics."""

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
        return {
            "processed_hashes": list(self.processed_hashes),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionState":
        last_run = None
        if data.get("last_run"):
            last_run = datetime.fromisoformat(data["last_run"])
        return cls(
            processed_hashes=set(data.get("processed_hashes", [])),
            last_run=last_run,
            stats=data.get("stats", {"total_published": 0, "total_failed": 0, "total_skipped": 0}),
        )
