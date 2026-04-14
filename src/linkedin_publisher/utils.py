"""Utility functions for LinkedIn publisher."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


def ensure_directories(vault_path: Path) -> dict[str, Path]:
    """Create all LinkedIn publisher directories if they don't exist.

    Creates:
    - /Approved/linkedin/
    - /Done/linkedin/
    - /Needs_Action/linkedin/
    - /Logs/linkedin/

    Args:
        vault_path: Path to Obsidian vault root

    Returns:
        Dict mapping directory names to their paths
    """
    vault_path = Path(vault_path)
    dirs = {}

    # LinkedIn directories
    dirs["approved_linkedin"] = vault_path / "Approved" / "linkedin"
    dirs["done_linkedin"] = vault_path / "Done" / "linkedin"
    dirs["needs_action_linkedin"] = vault_path / "Needs_Action" / "linkedin"
    dirs["logs_linkedin"] = vault_path / "Logs" / "linkedin"

    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


def move_file_to_done(file_path: Path, done_path: Path) -> Path:
    """Move file from /Approved/linkedin/ to /Done/linkedin/.

    Args:
        file_path: Source file path
        done_path: Path to /Done/linkedin/ directory

    Returns:
        New file path in /Done/linkedin/
    """
    done_path = Path(done_path)
    done_path.mkdir(parents=True, exist_ok=True)

    dest_path = done_path / file_path.name
    shutil.move(str(file_path), str(dest_path))
    return dest_path


def move_file_to_needs_action(file_path: Path, needs_action_path: Path) -> Path:
    """Move file from /Approved/linkedin/ to /Needs_Action/linkedin/.

    Used for unrecoverable errors (auth failure, invalid frontmatter).

    Args:
        file_path: Source file path
        needs_action_path: Path to /Needs_Action/linkedin/ directory

    Returns:
        New file path in /Needs_Action/linkedin/
    """
    needs_action_path = Path(needs_action_path)
    needs_action_path.mkdir(parents=True, exist_ok=True)

    dest_path = needs_action_path / file_path.name
    shutil.move(str(file_path), str(dest_path))
    return dest_path


def update_frontmatter(file_path: Path, updates: dict) -> None:
    """Update YAML frontmatter in a Markdown file.

    Reads file, updates frontmatter fields, writes back.

    Args:
        file_path: Path to Markdown file
        updates: Dict of fields to update/add to frontmatter
    """
    file_path = Path(file_path)
    content = file_path.read_text(encoding="utf-8")

    # Parse frontmatter
    if not content.startswith("---"):
        raise ValueError(f"File has no frontmatter: {file_path}")

    # Find end of frontmatter
    end_idx = content.find("---", 3)
    if end_idx == -1:
        raise ValueError(f"Invalid frontmatter format: {file_path}")

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3:]

    # Parse and update frontmatter
    frontmatter = yaml.safe_load(frontmatter_str) or {}
    frontmatter.update(updates)

    # Write back
    new_frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    new_content = f"---\n{new_frontmatter_str}---{body}"

    file_path.write_text(new_content, encoding="utf-8")


def update_file_with_success(
    file_path: Path,
    post_url: Optional[str] = None,
    log_path: Optional[str] = None,
) -> None:
    """Update frontmatter after successful publish.

    Updates:
    - status: published
    - published_at: ISO timestamp
    - executed_by: linkedin_publisher
    - linkedin_post_url: URL (if provided)
    - execution_log: log path (if provided)

    Args:
        file_path: Path to approval file
        post_url: URL of published post (optional)
        log_path: Path to execution log (optional)
    """
    updates = {
        "status": "published",
        "published_at": datetime.utcnow().isoformat() + "Z",
        "executed_by": "linkedin_publisher",
    }

    if post_url:
        updates["linkedin_post_url"] = post_url

    if log_path:
        updates["execution_log"] = f"[[{log_path}]]"

    update_frontmatter(file_path, updates)


def update_file_with_failure(
    file_path: Path,
    error_message: str,
    retry_count: int,
) -> None:
    """Update frontmatter after failed publish attempt.

    File remains in /Approved/linkedin/ for manual review.

    Updates:
    - status: failed
    - last_error: error message
    - last_error_at: ISO timestamp
    - retry_count: number of attempts

    Args:
        file_path: Path to approval file
        error_message: Error description
        retry_count: Number of attempts made
    """
    updates = {
        "status": "failed",
        "last_error": error_message,
        "last_error_at": datetime.utcnow().isoformat() + "Z",
        "retry_count": retry_count,
    }

    update_frontmatter(file_path, updates)


def handle_publish_success(
    file_path: Path,
    done_path: Path,
    post_url: Optional[str] = None,
    log_path: Optional[str] = None,
) -> Path:
    """Handle successful publish: update frontmatter and move to Done.

    Args:
        file_path: Path to approval file
        done_path: Path to /Done/linkedin/ directory
        post_url: URL of published post (optional)
        log_path: Path to execution log (optional)

    Returns:
        New file path in /Done/linkedin/
    """
    # Update frontmatter with success
    update_file_with_success(file_path, post_url, log_path)

    # Move to Done
    return move_file_to_done(file_path, done_path)
