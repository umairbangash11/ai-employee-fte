"""Utility functions for X Publisher (mirrors facebook_publisher/utils.py)."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def move_file(source: Path, destination_dir: Path, preserve_name: bool = True) -> Path:
    ensure_directory(destination_dir)
    if preserve_name:
        dest_path = destination_dir / source.name
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        dest_path = destination_dir / f"{timestamp}_{source.name}"
    if dest_path.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        dest_path = destination_dir / f"{timestamp}_{source.name}"
    shutil.move(str(source), str(dest_path))
    return dest_path


def compute_content_hash(action_type: str, content: str, source_path: str) -> str:
    combined = f"{action_type}{content}{source_path}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def read_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError(f"No frontmatter found in {file_path}")
    end_marker = content.find("---", 3)
    if end_marker == -1:
        raise ValueError(f"Invalid frontmatter format in {file_path}")
    frontmatter_str = content[3:end_marker].strip()
    body = content[end_marker + 3:].strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")
    return frontmatter, body


def write_frontmatter(file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    content = f"---\n{frontmatter_str}---\n\n{body}"
    file_path.write_text(content, encoding="utf-8")


def format_timestamp(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
