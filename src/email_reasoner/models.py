"""Data models for Email Reasoning Layer.

This module defines all data structures used for email classification,
task generation, and state management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
import re

from pydantic import BaseModel, Field


# =============================================================================
# T007: EmailFile dataclass
# =============================================================================


@dataclass
class EmailFile:
    """Parsed email markdown file from Inbox.

    Represents an email file created by Phase 1 gmail-watcher,
    with YAML frontmatter and markdown body.
    """

    # From YAML frontmatter
    message_id: str
    thread_id: Optional[str] = None
    sender: str = ""
    subject: str = ""
    captured_at: datetime = field(default_factory=datetime.utcnow)
    urgency: str = "normal"  # normal | urgent
    status: str = "unread"
    tags: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)

    # Parsed from markdown body
    body: str = ""

    # File metadata
    file_path: Path = field(default_factory=Path)

    @property
    def relative_path(self) -> str:
        """Return vault-relative path for wikilinks.

        Extracts the path starting from 'Inbox' for use in Obsidian wikilinks.
        """
        parts = self.file_path.parts
        if "Inbox" in parts:
            idx = parts.index("Inbox")
            return "/".join(parts[idx:])
        return str(self.file_path.name)

    @property
    def wikilink(self) -> str:
        """Return Obsidian wikilink to this email."""
        return f"[[{self.relative_path}]]"


# =============================================================================
# T008: ClassificationResult Pydantic model
# =============================================================================


class ClassificationResult(BaseModel):
    """Structured classification output from LLM.

    This model validates the JSON response from GPT-4o email classification.
    """

    classification: Literal["actionable", "informational", "promotional", "ignore"]
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(description="Brief explanation for classification")

    # Only populated for actionable emails
    action: Optional[str] = Field(
        default=None,
        description="Clear 1-sentence action required"
    )
    priority: Optional[Literal["high", "medium", "low"]] = Field(
        default=None,
        description="Task priority level"
    )
    due_date: Optional[str] = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) if deadline mentioned"
    )
    is_multi_step: bool = Field(
        default=False,
        description="True if multiple distinct actions needed"
    )
    steps: Optional[list[str]] = Field(
        default=None,
        description="Ordered list of steps for multi-step actions"
    )

    @property
    def creates_task(self) -> bool:
        """True if this classification should create a task file."""
        return self.classification == "actionable"

    @property
    def creates_plan(self) -> bool:
        """True if this classification should create a plan file."""
        return self.classification == "actionable" and self.is_multi_step and self.steps


# =============================================================================
# T009: TaskFile dataclass
# =============================================================================


@dataclass
class TaskFile:
    """Task file to be written for actionable emails.

    Generates Obsidian-compatible markdown with YAML frontmatter.
    """

    # Metadata (YAML frontmatter)
    type: str = "task"
    created_at: datetime = field(default_factory=datetime.utcnow)
    source_email: str = ""  # Wikilink to original email
    priority: str = "medium"  # high | medium | low
    due_date: Optional[str] = None  # YYYY-MM-DD or null
    status: str = "pending"
    tags: list[str] = field(default_factory=lambda: ["task", "email-derived"])

    # Content (markdown body)
    title: str = ""  # Action title
    context: str = ""  # Brief summary
    action_required: str = ""  # Clear next step(s)

    # Source reference
    email_from: str = ""
    email_subject: str = ""

    @property
    def filename(self) -> str:
        """Generate filename from timestamp and title."""
        timestamp = self.created_at.strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(self.title)[:50]
        return f"{timestamp}_{slug}.md"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to filename-safe slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "_", text)
        return text.strip("_")

    def to_markdown(self) -> str:
        """Render task as markdown file content."""
        due_str = f'"{self.due_date}"' if self.due_date else "null"
        tags_str = str(self.tags).replace("'", '"')

        frontmatter = f"""---
type: {self.type}
created_at: "{self.created_at.isoformat()}Z"
source_email: "{self.source_email}"
priority: {self.priority}
due_date: {due_str}
status: {self.status}
tags: {tags_str}
---"""

        body = f"""
# {self.title}

## Context

{self.context}

## Action Required

{self.action_required}

## Source

- Email: {self.source_email}
- From: {self.email_from}
- Subject: {self.email_subject}
"""
        return frontmatter + body


# =============================================================================
# T010: PlanFile dataclass
# =============================================================================


@dataclass
class PlanFile:
    """Plan file for multi-step actionable emails.

    Generates Obsidian-compatible markdown with checkbox steps.
    """

    # Metadata (YAML frontmatter)
    type: str = "plan"
    created_at: datetime = field(default_factory=datetime.utcnow)
    source_email: str = ""  # Wikilink to original email
    related_task: str = ""  # Wikilink to associated task
    status: str = "pending"
    tags: list[str] = field(default_factory=lambda: ["plan", "email-derived"])

    # Content (markdown body)
    title: str = ""  # Plan title
    overview: str = ""  # Brief description
    steps: list[str] = field(default_factory=list)  # Ordered action steps

    @property
    def filename(self) -> str:
        """Generate filename from timestamp and title."""
        timestamp = self.created_at.strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(self.title)[:50]
        return f"{timestamp}_{slug}.md"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to filename-safe slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "_", text)
        return text.strip("_")

    def to_markdown(self) -> str:
        """Render plan as markdown file content."""
        tags_str = str(self.tags).replace("'", '"')

        frontmatter = f"""---
type: {self.type}
created_at: "{self.created_at.isoformat()}Z"
source_email: "{self.source_email}"
related_task: "{self.related_task}"
status: {self.status}
tags: {tags_str}
---"""

        steps_md = "\n".join(f"- [ ] {step}" for step in self.steps)

        body = f"""
# {self.title}

## Overview

{self.overview}

## Steps

{steps_md}

## Source

- Email: {self.source_email}
"""
        return frontmatter + body


# =============================================================================
# T011: ReasonerState dataclass
# T012: ProcessedEmail dataclass
# =============================================================================


@dataclass
class ProcessedEmail:
    """Record of a processed email for deduplication."""

    classified_at: str  # ISO timestamp
    classification: str  # actionable | informational | promotional | ignore
    task_file: Optional[str] = None  # Relative path if task created


@dataclass
class ReasonerState:
    """Persistent state for email reasoner deduplication.

    Stored in .watcher-state/reasoner.json to track processed emails
    and prevent duplicate task creation.
    """

    version: int = 1
    last_run: Optional[str] = None  # ISO timestamp
    processed: dict[str, ProcessedEmail] = field(default_factory=dict)
    # Key: message_id, Value: ProcessedEmail

    def is_processed(self, message_id: str) -> bool:
        """Check if email has already been processed."""
        return message_id in self.processed

    def mark_processed(
        self,
        message_id: str,
        classification: str,
        task_file: Optional[str] = None
    ) -> None:
        """Record email as processed."""
        self.processed[message_id] = ProcessedEmail(
            classified_at=datetime.utcnow().isoformat() + "Z",
            classification=classification,
            task_file=task_file
        )
        self.last_run = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "version": self.version,
            "last_run": self.last_run,
            "processed": {
                k: {
                    "classified_at": v.classified_at,
                    "classification": v.classification,
                    "task_file": v.task_file
                }
                for k, v in self.processed.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReasonerState":
        """Deserialize from JSON dict."""
        state = cls(
            version=data.get("version", 1),
            last_run=data.get("last_run")
        )
        for msg_id, info in data.get("processed", {}).items():
            state.processed[msg_id] = ProcessedEmail(
                classified_at=info["classified_at"],
                classification=info["classification"],
                task_file=info.get("task_file")
            )
        return state
