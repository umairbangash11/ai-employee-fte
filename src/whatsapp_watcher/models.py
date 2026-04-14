"""Data models for WhatsApp watcher.

Follows the pattern established by gmail_watcher.models for consistency.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class WhatsAppMessage:
    """Data extracted from WhatsApp Web representing a single message."""

    # Chat context
    chat_name: str
    chat_type: str  # "individual" | "group"

    # Message content
    sender: str
    timestamp: datetime
    body: str

    # Media indicators
    has_media: bool = False
    media_type: str | None = None  # "image" | "video" | "audio" | "document" | None

    # Hash for deduplication (computed on demand)
    _hash: str | None = field(default=None, repr=False)

    @property
    def hash(self) -> str:
        """Return SHA-256 hash for deduplication.

        Hash is computed from: whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}
        Returns first 16 hex characters.
        """
        if self._hash is None:
            timestamp_str = self.timestamp.isoformat()
            content = f"whatsapp|{self.chat_name}|{self.sender}|{timestamp_str}|{self.body[:100]}"
            self._hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self._hash

    @property
    def is_group(self) -> bool:
        """True if message is from a group chat."""
        return self.chat_type == "group"


def compute_hash(chat_name: str, sender: str, timestamp: str, body: str) -> str:
    """Generate deterministic hash for message deduplication.

    Uses SHA-256 of: whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}
    Returns first 16 hex characters.

    Args:
        chat_name: Name of chat/conversation
        sender: Message sender name
        timestamp: ISO format timestamp string
        body: Message body text

    Returns:
        16-character hex hash string
    """
    content = f"whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class WhatsAppConversation:
    """A WhatsApp chat thread (individual or group)."""

    chat_name: str
    chat_type: str  # "individual" | "group"
    unread_count: int
    messages: list[WhatsAppMessage] = field(default_factory=list)


@dataclass
class DeduplicationState:
    """Hash registry tracking captured messages to prevent duplicates."""

    version: int = 1
    last_poll: datetime | None = None
    message_hashes: dict[str, str] = field(default_factory=dict)  # hash -> captured_at ISO


@dataclass
class CapturedMessageFile:
    """Markdown file written to vault with frontmatter and body."""

    message: WhatsAppMessage
    filepath: Path
    frontmatter: str
    body: str

    @property
    def full_content(self) -> str:
        """Return complete file content."""
        return f"{self.frontmatter}\n\n{self.body}\n"
