"""Markdown file generation for captured emails."""

import re
from datetime import datetime, timezone
from pathlib import Path

from gmail_watcher.models import EmailMessage


def generate_filename(message: EmailMessage) -> str:
    """Generate filename from timestamp and subject slug.

    Pattern: {YYYYMMDD-HHMMSS}_{subject_slug}.md

    Args:
        message: EmailMessage to generate filename for

    Returns:
        Generated filename string
    """
    # Format timestamp
    timestamp = message.date.strftime("%Y%m%d-%H%M%S")

    # Create slug from subject (lowercase, replace spaces with underscores, remove special chars)
    slug = message.subject.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"[\s_-]+", "_", slug)  # Normalize whitespace to underscores
    slug = slug.strip("_")[:50]  # Limit length

    if not slug:
        slug = "email"

    return f"{timestamp}_{slug}.md"


def generate_frontmatter(message: EmailMessage) -> str:
    """Generate YAML frontmatter for email.

    Args:
        message: EmailMessage to generate frontmatter for

    Returns:
        YAML frontmatter string (including --- delimiters)
    """
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Escape quotes in string values
    sender = message.sender.replace('"', '\\"')
    subject = message.subject.replace('"', '\\"')

    lines = [
        "---",
        "source: gmail-api",
        f'message_id: "{message.message_id}"',
        f'captured_at: "{captured_at}"',
        f'sender: "{sender}"',
        f'subject: "{subject}"',
        f"urgency: {message.urgency}",
        f"starred: {str(message.is_starred).lower()}",
        f"important: {str(message.is_important).lower()}",
        "status: unread",
        "tags: [inbox, gmail]",
        "---",
    ]

    return "\n".join(lines)


def generate_body(message: EmailMessage) -> str:
    """Generate Markdown body for email.

    Args:
        message: EmailMessage to generate body for

    Returns:
        Markdown body string
    """
    # Format date for display
    date_str = message.date.strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# {message.subject}",
        "",
        f"**From**: {message.sender}",
        f"**Date**: {date_str}",
        "",
        "---",
        "",
        message.body or message.snippet or "(no content)",
    ]

    # Add attachments section if present
    if message.attachments:
        lines.extend([
            "",
            "## Attachments",
            "",
        ])
        for att in message.attachments:
            lines.append(f"- [ ] attachment: {att.filename} ({att.mime_type}, {att.size_human})")

    return "\n".join(lines)


def determine_destination(message: EmailMessage, vault_path: Path) -> Path:
    """Determine destination directory based on urgency.

    Args:
        message: EmailMessage to route
        vault_path: Path to vault root

    Returns:
        Full path to destination directory
    """
    if message.urgency == "urgent":
        return vault_path / "Needs_Action" / "email"
    return vault_path / "Inbox" / "email"


def write_email_file(
    message: EmailMessage,
    vault_path: Path,
    dry_run: bool = False,
) -> Path | None:
    """Write email as Markdown file to vault.

    Args:
        message: EmailMessage to write
        vault_path: Path to vault root
        dry_run: If True, don't actually write file

    Returns:
        Path to created file, or None if dry_run
    """
    # Determine destination and filename
    dest_dir = determine_destination(message, vault_path)
    filename = generate_filename(message)
    filepath = dest_dir / filename

    if dry_run:
        print(f"Would capture: {message.subject}")
        print(f"  → {filepath}")
        return None

    # Ensure directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate content
    frontmatter = generate_frontmatter(message)
    body = generate_body(message)
    content = f"{frontmatter}\n\n{body}\n"

    # Write file
    filepath.write_text(content, encoding="utf-8")

    return filepath
