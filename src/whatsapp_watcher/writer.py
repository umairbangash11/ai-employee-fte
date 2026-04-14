"""Markdown file generation for WhatsApp messages.

Converts WhatsAppMessage instances to Obsidian-compatible Markdown files with YAML frontmatter.
"""

import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from .config import WatcherConfig
from .models import WhatsAppMessage


def determine_urgency(body: str, keywords: list[str]) -> str:
    """Check if message body contains urgency keywords.

    Case-insensitive matching.

    Args:
        body: Message body text
        keywords: List of urgency keywords

    Returns:
        "urgent" if any keyword found, else "normal"
    """
    body_lower = body.lower()
    for keyword in keywords:
        if keyword.lower() in body_lower:
            return "urgent"
    return "normal"


def generate_filename(message: WhatsAppMessage, urgency: str) -> str:
    """Generate filesystem-safe filename for message.

    Format:
        {YYYYMMDD}-{HHMMSS}-{chat-slug}-{sender-slug}.md

    For urgent messages:
        {YYYYMMDD}-{HHMMSS}-URGENT-{chat-slug}.md

    Args:
        message: WhatsAppMessage to generate filename for
        urgency: "urgent" or "normal"

    Returns:
        Filename string (not path)
    """
    # Format timestamp
    timestamp_str = message.timestamp.strftime("%Y%m%d-%H%M%S")

    # Sanitize chat name and sender
    def sanitize(text: str) -> str:
        # Convert to lowercase
        text = text.lower()
        # Replace spaces with hyphens
        text = text.replace(' ', '-')
        # Remove special characters except hyphens and underscores
        text = re.sub(r'[^a-z0-9\-_]', '', text)
        # Truncate to reasonable length
        return text[:50]

    chat_slug = sanitize(message.chat_name)
    sender_slug = sanitize(message.sender)

    if urgency == "urgent":
        # Urgent messages: include URGENT marker
        filename = f"{timestamp_str}-URGENT-{chat_slug}.md"
    else:
        # Normal messages: include sender
        if message.chat_type == "group":
            filename = f"{timestamp_str}-{chat_slug}-{sender_slug}.md"
        else:
            filename = f"{timestamp_str}-{chat_slug}.md"

    return filename


def build_frontmatter(message: WhatsAppMessage, urgency: str, captured_at: datetime) -> dict:
    """Build frontmatter dict from message.

    Args:
        message: WhatsAppMessage to build frontmatter for
        urgency: "urgent" or "normal"
        captured_at: Timestamp when message was captured

    Returns:
        Dict with all frontmatter fields
    """
    return {
        "source": "whatsapp",
        "captured_at": captured_at.isoformat(),
        "sender": message.sender,
        "chat_name": message.chat_name,
        "chat_type": message.chat_type,
        "message_timestamp": message.timestamp.isoformat(),
        "urgency": urgency,
        "status": "unread",
        "has_media": message.has_media,
        "media_type": message.media_type,
        "tags": ["inbox", "whatsapp"],
        "hash": message.hash
    }


def format_frontmatter(frontmatter: dict) -> str:
    """Format frontmatter dict as YAML block.

    Args:
        frontmatter: Dict with frontmatter data

    Returns:
        Complete YAML frontmatter block as string
    """
    yaml_content = yaml.safe_dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_content}---"


def format_body(message: WhatsAppMessage) -> str:
    """Format message body as Markdown.

    Structure:
        # {chat_name}

        **Sender**: {sender}
        **Timestamp**: {timestamp}

        {body}

        [Media: {media_type}] (if has_media)

    Args:
        message: WhatsAppMessage to format

    Returns:
        Markdown body string
    """
    lines = [
        f"# {message.chat_name}",
        "",
        f"**Sender**: {message.sender}",
        f"**Timestamp**: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    # Add chat type for groups
    if message.chat_type == "group":
        lines.append(f"**Chat Type**: Group")
        lines.append("")

    # Add message body
    lines.append(message.body)
    lines.append("")

    # Add media indicator
    if message.has_media and message.media_type:
        lines.append(f"[Media: {message.media_type}]")
        lines.append("")

    return "\n".join(lines)


def determine_output_directory(vault_path: Path, urgency: str) -> Path:
    """Determine output directory based on urgency.

    Args:
        vault_path: Path to vault root
        urgency: "urgent" or "normal"

    Returns:
        Path to output directory
    """
    if urgency == "urgent":
        return vault_path / "Needs_Action" / "whatsapp"
    else:
        return vault_path / "Inbox" / "whatsapp"


def write_file_atomic(content: str, filepath: Path) -> None:
    """Write file atomically using temp file + rename.

    Ensures no partial writes on crash.

    Args:
        content: File content to write
        filepath: Target file path
    """
    # Write to temp file in same directory
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=".tmp_",
        suffix=".md"
    )

    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)

        # Atomic rename
        os.rename(temp_path, filepath)
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise e


def write_message_file(
    message: WhatsAppMessage,
    config: WatcherConfig,
    captured_at: datetime
) -> Path:
    """Write WhatsApp message to Markdown file in vault.

    Algorithm:
        1. Determine urgency by checking body for keywords
        2. Generate filename from timestamp, chat, sender
        3. Build frontmatter dict
        4. Format frontmatter as YAML
        5. Format body as Markdown
        6. Determine output directory (Inbox vs Needs_Action)
        7. Write file atomically
        8. Return Path to created file

    Args:
        message: WhatsAppMessage to write
        config: WatcherConfig with vault_path and urgency_keywords
        captured_at: Timestamp when message was captured

    Returns:
        Path to created markdown file (or None if dry-run)
    """
    # Determine urgency
    urgency = determine_urgency(message.body, config.urgency_keywords)

    # Generate filename
    filename = generate_filename(message, urgency)

    # Build frontmatter
    frontmatter_dict = build_frontmatter(message, urgency, captured_at)
    frontmatter_str = format_frontmatter(frontmatter_dict)

    # Format body
    body_str = format_body(message)

    # Combine into full content
    full_content = f"{frontmatter_str}\n\n{body_str}\n"

    # Determine output directory
    output_dir = determine_output_directory(config.vault_path, urgency)

    # Dry-run mode
    if config.dry_run:
        filepath = output_dir / filename
        print(f"[Dry Run] Would write: {filepath}", file=sys.stderr)
        return None

    # Ensure directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write file atomically
    filepath = output_dir / filename
    write_file_atomic(full_content, filepath)

    print(f"Written: {filepath}", file=sys.stderr)
    return filepath
