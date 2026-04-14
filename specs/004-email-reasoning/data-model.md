# Phase 2: Email Reasoning Layer — Data Model

**Feature Branch**: `004-email-reasoning`
**Phase**: 2 — Email Reasoning Layer
**Created**: 2026-03-07

## Overview

This document defines the data structures, entities, and their relationships for the Email Reasoning Layer.

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐
│  EmailFile      │       │  ClassificationResult│
│  (Input)        │──────▶│  (LLM Output)        │
└─────────────────┘       └──────────┬──────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                          ▼                     ▼
                   ┌─────────────┐      ┌─────────────┐
                   │  TaskFile   │      │  PlanFile   │
                   │  (Output)   │      │  (Optional) │
                   └─────────────┘      └─────────────┘
                          │                     │
                          └──────────┬──────────┘
                                     ▼
                          ┌─────────────────────┐
                          │   ReasonerState     │
                          │   (Deduplication)   │
                          └─────────────────────┘
```

## Core Entities

### 1. EmailFile (Input)

**Source**: Phase 1 gmail-watcher output in `/Inbox/email/`

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class EmailFile:
    """Parsed email markdown file from Inbox."""

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
        """Return vault-relative path for wikilinks."""
        # Assumes path contains vault root
        parts = self.file_path.parts
        if "Inbox" in parts:
            idx = parts.index("Inbox")
            return "/".join(parts[idx:])
        return str(self.file_path.name)

    @property
    def wikilink(self) -> str:
        """Return Obsidian wikilink to this email."""
        return f"[[{self.relative_path}]]"
```

**Validation Rules**:
- `message_id` is required (skip file if missing)
- `sender` and `subject` should be present (warn if missing)
- `body` may be empty (classify on subject only)

---

### 2. ClassificationResult (LLM Output)

**Source**: OpenAI GPT-4o JSON response

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional


class ClassificationResult(BaseModel):
    """Structured classification output from LLM."""

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
        return self.classification == "actionable" and self.is_multi_step
```

**Default Fallback** (when LLM fails):
```python
ClassificationResult(
    classification="informational",
    confidence=0.0,
    reasoning="Classification failed, defaulted to informational"
)
```

---

### 3. TaskFile (Output)

**Destination**: `/Needs_Action/tasks/`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TaskFile:
    """Task file to be written for actionable emails."""

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
        import re
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "_", text)
        return text.strip("_")

    def to_markdown(self) -> str:
        """Render task as markdown file content."""
        frontmatter = f"""---
type: {self.type}
created_at: "{self.created_at.isoformat()}Z"
source_email: "{self.source_email}"
priority: {self.priority}
due_date: {f'"{self.due_date}"' if self.due_date else 'null'}
status: {self.status}
tags: {self.tags}
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
```

---

### 4. PlanFile (Output)

**Destination**: `/Plans/`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PlanFile:
    """Plan file for multi-step actionable emails."""

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
        import re
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "_", text)
        return text.strip("_")

    def to_markdown(self) -> str:
        """Render plan as markdown file content."""
        frontmatter = f"""---
type: {self.type}
created_at: "{self.created_at.isoformat()}Z"
source_email: "{self.source_email}"
related_task: "{self.related_task}"
status: {self.status}
tags: {self.tags}
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
```

---

### 5. ReasonerState (Deduplication)

**Location**: `.watcher-state/reasoner.json`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProcessedEmail:
    """Record of a processed email."""

    classified_at: str  # ISO timestamp
    classification: str  # actionable | informational | promotional | ignore
    task_file: Optional[str] = None  # Relative path if task created


@dataclass
class ReasonerState:
    """Persistent state for email reasoner deduplication."""

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
```

---

## Data Flow

### Processing Pipeline

```
1. SCAN
   /Inbox/email/*.md
         │
         ▼
2. PARSE
   EmailFile objects (frontmatter + body)
         │
         ▼
3. FILTER
   Skip if message_id in ReasonerState
         │
         ▼
4. CLASSIFY
   Send to GPT-4o → ClassificationResult
         │
         ▼
5. GENERATE
   ├─ actionable → TaskFile
   │  └─ is_multi_step → PlanFile
   └─ other → (no output)
         │
         ▼
6. WRITE
   ├─ TaskFile → /Needs_Action/tasks/
   ├─ PlanFile → /Plans/
   └─ Log → /Logs/reasoner-YYYYMMDD.log
         │
         ▼
7. UPDATE
   ReasonerState with processed message_ids
```

### File System Layout

```
vault/
├── Inbox/
│   └── email/
│       ├── 20260307-093000_interview_invitation.md  (input)
│       └── 20260307-094500_sale_promo.md            (input)
├── Needs_Action/
│   └── tasks/
│       └── 20260307-100000_respond_to_interview.md  (output)
├── Plans/
│   └── 20260307-100500_complete_onboarding.md       (output)
├── Logs/
│   └── reasoner-20260307.log                        (output)
└── .watcher-state/
    └── reasoner.json                                (state)
```

---

## Validation Rules

### EmailFile Validation

| Field | Required | Default | Validation |
|-------|----------|---------|------------|
| message_id | Yes | — | Non-empty string |
| sender | No | "" | Warn if empty |
| subject | No | "" | Warn if empty |
| body | No | "" | Classify on subject if empty |
| captured_at | No | now() | Valid ISO datetime |

### ClassificationResult Validation

| Field | Required | Validation |
|-------|----------|------------|
| classification | Yes | One of: actionable, informational, promotional, ignore |
| confidence | Yes | Float 0.0-1.0 |
| action | Conditional | Required if actionable |
| steps | Conditional | Required if is_multi_step |

### TaskFile Validation

| Field | Required | Validation |
|-------|----------|------------|
| source_email | Yes | Valid wikilink |
| title | Yes | Non-empty |
| action_required | Yes | Non-empty |

---

## JSON Schemas

### ClassificationResult JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["classification", "confidence", "reasoning"],
  "properties": {
    "classification": {
      "type": "string",
      "enum": ["actionable", "informational", "promotional", "ignore"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "reasoning": {
      "type": "string"
    },
    "action": {
      "type": ["string", "null"]
    },
    "priority": {
      "type": ["string", "null"],
      "enum": ["high", "medium", "low", null]
    },
    "due_date": {
      "type": ["string", "null"],
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "is_multi_step": {
      "type": "boolean"
    },
    "steps": {
      "type": ["array", "null"],
      "items": {
        "type": "string"
      }
    }
  }
}
```

### ReasonerState JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "processed"],
  "properties": {
    "version": {
      "type": "integer"
    },
    "last_run": {
      "type": ["string", "null"]
    },
    "processed": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["classified_at", "classification"],
        "properties": {
          "classified_at": {
            "type": "string"
          },
          "classification": {
            "type": "string"
          },
          "task_file": {
            "type": ["string", "null"]
          }
        }
      }
    }
  }
}
```

---

**Next Step**: Create `plan.md` with architecture and implementation phases.
