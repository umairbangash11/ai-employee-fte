"""Task and plan file writer for Email Reasoning Layer.

Generates Obsidian-compatible markdown files for actionable emails.
All outputs go to /Needs_Action/tasks/ and /Plans/ directories.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import EmailFile, ClassificationResult, TaskFile, PlanFile


logger = logging.getLogger(__name__)


# =============================================================================
# T044: Generate task filename
# =============================================================================


def generate_task_filename(action: str, timestamp: Optional[datetime] = None) -> str:
    """Generate a filename for a task file.

    Format: YYYYMMDD-HHMMSS_<slug>.md

    Args:
        action: Action description to slugify.
        timestamp: Timestamp for filename (default: now).

    Returns:
        Filename string.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    time_str = timestamp.strftime("%Y%m%d-%H%M%S")
    slug = _slugify(action)[:50]
    return f"{time_str}_{slug}.md"


def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text.strip("_")


# =============================================================================
# T045: Generate task frontmatter
# =============================================================================


def generate_task_frontmatter(
    email: EmailFile,
    result: ClassificationResult,
    timestamp: Optional[datetime] = None,
) -> str:
    """Generate YAML frontmatter for a task file.

    Args:
        email: Source email.
        result: Classification result.
        timestamp: Creation timestamp (default: now).

    Returns:
        YAML frontmatter string (including --- delimiters).
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    due_str = f'"{result.due_date}"' if result.due_date else "null"
    priority = result.priority or "medium"
    tags = '["task", "email-derived"]'

    return f"""---
type: task
created_at: "{timestamp.isoformat()}Z"
source_email: "{email.wikilink}"
priority: {priority}
due_date: {due_str}
status: pending
tags: {tags}
---"""


# =============================================================================
# T046: Generate task body
# =============================================================================


def generate_task_body(email: EmailFile, result: ClassificationResult) -> str:
    """Generate markdown body for a task file.

    Args:
        email: Source email.
        result: Classification result.

    Returns:
        Markdown body content.
    """
    title = result.action or f"Review email from {email.sender}"

    # Generate context from email subject and sender
    context = f"Email from {email.sender}"
    if email.subject:
        context += f' with subject "{email.subject}"'
    if result.reasoning:
        context += f". {result.reasoning}"

    # Action required
    action_required = result.action or "Review and respond to this email."

    return f"""
# {title}

## Context

{context}

## Action Required

{action_required}

## Source

- Email: {email.wikilink}
- From: {email.sender}
- Subject: {email.subject}
"""


# =============================================================================
# T047-T048: Write task file
# =============================================================================


def write_task_file(
    email: EmailFile,
    result: ClassificationResult,
    vault_path: Path,
    timestamp: Optional[datetime] = None,
) -> Path:
    """Write a task file for an actionable email.

    Creates the /Needs_Action/tasks/ directory if it doesn't exist.

    Args:
        email: Source email.
        result: Classification result.
        vault_path: Path to vault root.
        timestamp: Creation timestamp (default: now).

    Returns:
        Path to the created task file.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # T048: Create directory if missing
    tasks_dir = vault_path / "Needs_Action" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename and content
    action = result.action or f"review_email_{email.message_id[:8]}"
    filename = generate_task_filename(action, timestamp)
    frontmatter = generate_task_frontmatter(email, result, timestamp)
    body = generate_task_body(email, result)

    content = frontmatter + body

    # Write file
    task_path = tasks_dir / filename
    task_path.write_text(content, encoding="utf-8")

    logger.info(f"Created task file: {task_path}")
    return task_path


# =============================================================================
# T063-T068: Plan file generation (US3)
# =============================================================================


def generate_plan_filename(title: str, timestamp: Optional[datetime] = None) -> str:
    """Generate a filename for a plan file.

    Format: YYYYMMDD-HHMMSS_<slug>.md

    Args:
        title: Plan title to slugify.
        timestamp: Timestamp for filename (default: now).

    Returns:
        Filename string.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    time_str = timestamp.strftime("%Y%m%d-%H%M%S")
    slug = _slugify(title)[:50]
    return f"{time_str}_{slug}.md"


def generate_plan_frontmatter(
    email: EmailFile,
    result: ClassificationResult,
    task_path: str,
    timestamp: Optional[datetime] = None,
) -> str:
    """Generate YAML frontmatter for a plan file.

    Args:
        email: Source email.
        result: Classification result.
        task_path: Path to related task file (for wikilink).
        timestamp: Creation timestamp (default: now).

    Returns:
        YAML frontmatter string (including --- delimiters).
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    tags = '["plan", "email-derived"]'

    return f"""---
type: plan
created_at: "{timestamp.isoformat()}Z"
source_email: "{email.wikilink}"
related_task: "[[{task_path}]]"
status: pending
tags: {tags}
---"""


def generate_plan_body(email: EmailFile, result: ClassificationResult) -> str:
    """Generate markdown body for a plan file with checkbox steps.

    Args:
        email: Source email.
        result: Classification result with steps.

    Returns:
        Markdown body content.
    """
    title = result.action or f"Complete request from {email.sender}"
    overview = result.reasoning or f"Multi-step process from email: {email.subject}"

    # Generate checkbox steps
    steps = result.steps or []
    steps_md = "\n".join(f"- [ ] {step}" for step in steps)

    return f"""
# {title}

## Overview

{overview}

## Steps

{steps_md}

## Source

- Email: {email.wikilink}
"""


def write_plan_file(
    email: EmailFile,
    result: ClassificationResult,
    task_path: str,
    vault_path: Path,
    timestamp: Optional[datetime] = None,
) -> Path:
    """Write a plan file for a multi-step actionable email.

    Creates the /Plans/ directory if it doesn't exist.

    Args:
        email: Source email.
        result: Classification result with steps.
        task_path: Relative path to related task file.
        vault_path: Path to vault root.
        timestamp: Creation timestamp (default: now).

    Returns:
        Path to the created plan file.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # T067: Create directory if missing
    plans_dir = vault_path / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename and content
    title = result.action or f"plan_for_{email.message_id[:8]}"
    filename = generate_plan_filename(title, timestamp)
    frontmatter = generate_plan_frontmatter(email, result, task_path, timestamp)
    body = generate_plan_body(email, result)

    content = frontmatter + body

    # Write file
    plan_path = plans_dir / filename
    plan_path.write_text(content, encoding="utf-8")

    logger.info(f"Created plan file: {plan_path}")
    return plan_path
