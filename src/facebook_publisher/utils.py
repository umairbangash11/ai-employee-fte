"""Utility functions for Facebook Publisher."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        The path that was created or verified
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def move_file(source: Path, destination_dir: Path, preserve_name: bool = True) -> Path:
    """Move a file to a destination directory.

    Args:
        source: Source file path
        destination_dir: Destination directory
        preserve_name: If True, keep original filename; if False, generate timestamp-based name

    Returns:
        Path to the moved file
    """
    ensure_directory(destination_dir)

    if preserve_name:
        dest_path = destination_dir / source.name
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        dest_path = destination_dir / f"{timestamp}_{source.name}"

    # Handle case where destination already exists
    if dest_path.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        dest_path = destination_dir / f"{timestamp}_{source.name}"

    shutil.move(str(source), str(dest_path))
    return dest_path


def compute_content_hash(action_type: str, content: str, source_path: str) -> str:
    """Compute a deterministic hash for content deduplication.

    Hash is computed from: action_type + content + source_path
    Returns first 16 characters of SHA-256 hash.

    Args:
        action_type: The action type (e.g., 'publish_facebook_post')
        content: The post content
        source_path: The source file path

    Returns:
        16-character hex hash string
    """
    combined = f"{action_type}{content}{source_path}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def read_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
    """Read YAML frontmatter and body from a markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (frontmatter dict, body string)

    Raises:
        ValueError: If frontmatter is invalid or missing
    """
    content = file_path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError(f"No frontmatter found in {file_path}")

    # Find the end of frontmatter
    end_marker = content.find("---", 3)
    if end_marker == -1:
        raise ValueError(f"Invalid frontmatter format in {file_path}")

    frontmatter_str = content[3:end_marker].strip()
    body = content[end_marker + 3 :].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")

    return frontmatter, body


def write_frontmatter(file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Write YAML frontmatter and body to a markdown file.

    Args:
        file_path: Path to the markdown file
        frontmatter: Frontmatter dictionary
        body: Body content
    """
    # Use default_flow_style=False for readable YAML
    frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)

    content = f"---\n{frontmatter_str}---\n\n{body}"
    file_path.write_text(content, encoding="utf-8")


def update_frontmatter(file_path: Path, updates: dict[str, Any]) -> None:
    """Update specific fields in a file's frontmatter.

    Args:
        file_path: Path to the markdown file
        updates: Dictionary of fields to update
    """
    frontmatter, body = read_frontmatter(file_path)
    frontmatter.update(updates)
    write_frontmatter(file_path, frontmatter, body)


def format_timestamp(dt: datetime | None = None) -> str:
    """Format a datetime as ISO 8601 string.

    Args:
        dt: Datetime to format (defaults to UTC now)

    Returns:
        ISO 8601 formatted string
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
