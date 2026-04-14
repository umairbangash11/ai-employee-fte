"""Email file scanner for Email Reasoning Layer.

This module discovers and parses email markdown files from the Inbox.
All operations are READ-ONLY - no modification of source files.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from .models import EmailFile


logger = logging.getLogger(__name__)


# =============================================================================
# T016-T022: Scanner module implementation
# =============================================================================


def scan_inbox(inbox_path: Path) -> list[Path]:
    """Find all markdown files in the inbox directory.

    Args:
        inbox_path: Path to Inbox/email directory.

    Returns:
        List of paths to .md files, sorted by modification time (oldest first).

    Note:
        This function only reads directory contents. It does NOT modify files.
    """
    if not inbox_path.exists():
        logger.warning(f"Inbox path does not exist: {inbox_path}")
        return []

    if not inbox_path.is_dir():
        logger.warning(f"Inbox path is not a directory: {inbox_path}")
        return []

    # Find all .md files
    md_files = list(inbox_path.glob("*.md"))

    # Sort by modification time (oldest first for chronological processing)
    md_files.sort(key=lambda p: p.stat().st_mtime)

    logger.debug(f"Found {len(md_files)} email files in {inbox_path}")
    return md_files


def parse_email_file(path: Path) -> Optional[EmailFile]:
    """Parse an email markdown file with YAML frontmatter.

    Args:
        path: Path to the email .md file.

    Returns:
        EmailFile object if parsing succeeds, None if the file is invalid.

    Note:
        This function only reads the file. It does NOT modify it.

    Handles:
        - T019: Missing frontmatter → return None + warning
        - T020: Missing message_id → return None + warning
        - T021: Empty body → return EmailFile with empty body
    """
    try:
        # Read and parse frontmatter
        post = frontmatter.load(path)
    except Exception as e:
        # T019: Handle missing/invalid frontmatter
        logger.warning(f"Failed to parse frontmatter in {path}: {e}")
        return None

    # Extract metadata from frontmatter
    metadata = post.metadata

    # T020: Check for required message_id
    message_id = metadata.get("message_id")
    if not message_id:
        logger.warning(f"Missing message_id in {path}, skipping")
        return None

    # Parse captured_at timestamp
    captured_at_str = metadata.get("captured_at")
    if captured_at_str:
        try:
            # Handle ISO format with or without Z suffix
            if captured_at_str.endswith("Z"):
                captured_at_str = captured_at_str[:-1]
            captured_at = datetime.fromisoformat(captured_at_str)
        except ValueError:
            captured_at = datetime.utcnow()
    else:
        captured_at = datetime.utcnow()

    # T021: Body may be empty - that's OK
    body = post.content.strip()

    # Build EmailFile object
    email = EmailFile(
        message_id=message_id,
        thread_id=metadata.get("thread_id"),
        sender=metadata.get("sender", ""),
        subject=metadata.get("subject", ""),
        captured_at=captured_at,
        urgency=metadata.get("urgency", "normal"),
        status=metadata.get("status", "unread"),
        tags=metadata.get("tags", []),
        attachments=metadata.get("attachments", []),
        body=body,
        file_path=path
    )

    # Log warning if sender/subject missing but continue
    if not email.sender:
        logger.warning(f"Missing sender in {path}")
    if not email.subject:
        logger.warning(f"Missing subject in {path}")

    return email


def scan_and_parse_inbox(inbox_path: Path) -> list[EmailFile]:
    """Convenience function to scan and parse all emails in inbox.

    Args:
        inbox_path: Path to Inbox/email directory.

    Returns:
        List of successfully parsed EmailFile objects.
    """
    email_files = []

    for path in scan_inbox(inbox_path):
        email = parse_email_file(path)
        if email:
            email_files.append(email)

    logger.info(f"Parsed {len(email_files)} valid email files from {inbox_path}")
    return email_files
