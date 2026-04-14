"""Data models for HITL approval system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# Action type constants
ACTION_TYPE_EMAIL_REPLY = "send_email_reply"
ACTION_TYPE_EMAIL_FOLLOWUP = "send_email_followup"
ACTION_TYPE_LINKEDIN_POST = "publish_linkedin_post"

VALID_ACTION_TYPES = {
    ACTION_TYPE_EMAIL_REPLY,
    ACTION_TYPE_EMAIL_FOLLOWUP,
    ACTION_TYPE_LINKEDIN_POST,
}

# Source type constants
SOURCE_TYPE_EMAIL = "email"
SOURCE_TYPE_TASK = "task"


@dataclass
class ApprovalRequest:
    """Represents a request for human approval of an external action.

    All sensitive external actions (email sends, LinkedIn posts) must create
    an ApprovalRequest instead of executing directly. The request is written
    to /Pending_Approval/<type>/ and waits for human approval via file move.

    Attributes:
        action_type: Type of action (send_email_reply, send_email_followup, publish_linkedin_post)
        target_recipient: Who receives the action (email address, "linkedin")
        target_subject: Subject line for email, or post title for LinkedIn
        content: Full content to be sent/posted
        source_path: Path to source email/task that triggered this action
        source_type: Type of source (email, task)
        reasoning: Why this action is recommended
        expected_outcome: What should happen after execution
        rollback_strategy: How to handle failure or reversal (required by Constitution IV)
        created_by: Which component created this request
        tags: Metadata tags for categorization
        expires_at: Optional expiry time for the request
    """

    action_type: str
    target_recipient: str
    target_subject: str
    content: str
    source_path: str
    source_type: str
    reasoning: str
    expected_outcome: str
    rollback_strategy: str
    created_by: str
    tags: list[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate required fields."""
        if self.action_type not in VALID_ACTION_TYPES:
            raise ValueError(f"Invalid action_type: {self.action_type}. Must be one of {VALID_ACTION_TYPES}")
        if not self.rollback_strategy:
            raise ValueError("rollback_strategy is required (Constitution Principle IV)")
        if not self.target_recipient:
            raise ValueError("target_recipient is required")
        if not self.source_path:
            raise ValueError("source_path is required")


@dataclass
class ApprovalState:
    """State for tracking created approval requests (deduplication).

    Stored in .watcher-state/approvals.json to prevent duplicate
    approval requests for the same action.

    Attributes:
        created_hashes: Set of SHA256 hashes of created approval requests
        last_updated: When the state was last modified
    """

    created_hashes: set[str] = field(default_factory=set)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "created_hashes": list(self.created_hashes),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalState":
        """Create from dict (loaded from JSON)."""
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        return cls(
            created_hashes=set(data.get("created_hashes", [])),
            last_updated=last_updated,
        )
