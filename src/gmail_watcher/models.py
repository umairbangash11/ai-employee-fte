"""Data models for Gmail API watcher."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Attachment:
    """Metadata for email attachment (content not downloaded)."""

    filename: str
    mime_type: str
    size: int  # bytes

    @property
    def size_human(self) -> str:
        """Return human-readable size."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size // 1024} KB"
        else:
            return f"{self.size // (1024 * 1024)} MB"


@dataclass
class EmailMessage:
    """Data extracted from Gmail API representing a single email."""

    message_id: str
    thread_id: str
    sender: str
    subject: str
    date: datetime
    snippet: str
    body: str
    label_ids: list[str] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    @property
    def is_unread(self) -> bool:
        """True if UNREAD label present."""
        return "UNREAD" in self.label_ids

    @property
    def is_starred(self) -> bool:
        """True if STARRED label present."""
        return "STARRED" in self.label_ids

    @property
    def is_important(self) -> bool:
        """True if IMPORTANT label present."""
        return "IMPORTANT" in self.label_ids

    @property
    def urgency(self) -> str:
        """Return 'urgent' if starred or important, else 'normal'."""
        if self.is_starred or self.is_important:
            return "urgent"
        return "normal"


@dataclass
class DeduplicationState:
    """Hash registry tracking captured messages to prevent duplicates."""

    version: int = 1
    last_poll: datetime | None = None
    message_ids: dict[str, str] = field(default_factory=dict)  # message_id -> captured_at ISO
