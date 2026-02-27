"""Email file parsing with YAML frontmatter extraction.

Parses markdown files with YAML frontmatter into InboxFile structures.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class MalformedFrontmatterError(Exception):
    """Raised when YAML frontmatter cannot be parsed."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Malformed frontmatter in {path}: {reason}")


@dataclass
class EmailFrontmatter:
    """YAML frontmatter structure for email files.

    Attributes:
        source: Origin of the email (gmail, whatsapp, filesystem)
        captured_at: When the email was captured (ISO 8601)
        sender: Email sender name or address
        subject: Email subject line
        urgency: Urgency level (normal or urgent)
        starred: Whether email was starred
        important: Whether email was marked important
        status: Processing status
        tags: Tags for organization
    """

    source: str = "gmail"
    captured_at: str = ""
    sender: str = ""
    subject: str = "(no subject)"
    urgency: str = "normal"
    starred: bool = False
    important: bool = False
    status: str = "unread"
    tags: list[str] = field(default_factory=lambda: ["inbox", "gmail"])


@dataclass
class InboxFile:
    """Parsed representation of an email markdown file.

    Attributes:
        path: Absolute path to the file
        frontmatter: Parsed YAML frontmatter metadata
        subject: Email subject extracted from frontmatter
        body: Markdown body content (after frontmatter)
        file_size: File size in bytes
    """

    path: Path
    frontmatter: EmailFrontmatter
    subject: str = "(no subject)"
    body: str = ""
    file_size: int = 0


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from markdown content.

    Args:
        content: Raw file content with potential frontmatter

    Returns:
        Tuple of (frontmatter_dict, body_content)

    Raises:
        ValueError: If frontmatter delimiters are malformed
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    end_index = -1

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = i
            break

    if end_index == -1:
        raise ValueError("Unclosed frontmatter block")

    frontmatter_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()

    try:
        frontmatter_dict = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

    return frontmatter_dict, body


def parse_email_file(file_path: str | Path) -> InboxFile:
    """Read and parse a markdown file with YAML frontmatter.

    Args:
        file_path: Path to the markdown file

    Returns:
        InboxFile with parsed frontmatter and body

    Raises:
        FileNotFoundError: If file does not exist
        MalformedFrontmatterError: If YAML parsing fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding="utf-8")
    file_size = path.stat().st_size

    try:
        fm_dict, body = extract_frontmatter(content)
    except ValueError as e:
        raise MalformedFrontmatterError(path, str(e))

    frontmatter = EmailFrontmatter(
        source=fm_dict.get("source", "gmail"),
        captured_at=fm_dict.get("captured_at", ""),
        sender=fm_dict.get("sender", ""),
        subject=fm_dict.get("subject", "(no subject)"),
        urgency=fm_dict.get("urgency", "normal"),
        starred=bool(fm_dict.get("starred", False)),
        important=bool(fm_dict.get("important", False)),
        status=fm_dict.get("status", "unread"),
        tags=fm_dict.get("tags", ["inbox", "gmail"]),
    )

    return InboxFile(
        path=path,
        frontmatter=frontmatter,
        subject=frontmatter.subject,
        body=body,
        file_size=file_size,
    )
