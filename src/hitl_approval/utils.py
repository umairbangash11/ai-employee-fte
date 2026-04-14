"""Utility functions for HITL approval system."""

import re
from datetime import datetime
from pathlib import Path


def ensure_approval_dirs(vault_path: Path) -> dict[str, Path]:
    """Create all approval-related directories if they don't exist.

    Creates:
    - /Pending_Approval/email/
    - /Pending_Approval/linkedin/
    - /Approved/email/
    - /Approved/linkedin/
    - /Rejected/email/
    - /Rejected/linkedin/
    - /Logs/approvals/

    Args:
        vault_path: Path to Obsidian vault root

    Returns:
        Dict mapping directory names to their paths
    """
    vault_path = Path(vault_path)
    dirs = {}

    # Pending approval directories
    dirs["pending_email"] = vault_path / "Pending_Approval" / "email"
    dirs["pending_linkedin"] = vault_path / "Pending_Approval" / "linkedin"

    # Approved directories
    dirs["approved_email"] = vault_path / "Approved" / "email"
    dirs["approved_linkedin"] = vault_path / "Approved" / "linkedin"

    # Rejected directories
    dirs["rejected_email"] = vault_path / "Rejected" / "email"
    dirs["rejected_linkedin"] = vault_path / "Rejected" / "linkedin"

    # Logs directory
    dirs["logs_approvals"] = vault_path / "Logs" / "approvals"

    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


def generate_slug(text: str, max_len: int = 50) -> str:
    """Generate a URL-safe slug from text.

    Rules:
    - Lowercase
    - Spaces → underscores
    - Strip special characters except underscore
    - Max length enforced

    Args:
        text: Input text to slugify
        max_len: Maximum length of output (default 50)

    Returns:
        Slugified string

    Examples:
        >>> generate_slug("Interview Response")
        'interview_response'
        >>> generate_slug("Re: Hello @#$ World!")
        're_hello_world'
    """
    # Lowercase
    slug = text.lower()

    # Replace spaces with underscores
    slug = slug.replace(" ", "_")

    # Remove special characters except underscore and alphanumeric
    slug = re.sub(r"[^a-z0-9_]", "", slug)

    # Collapse multiple underscores
    slug = re.sub(r"_+", "_", slug)

    # Strip leading/trailing underscores
    slug = slug.strip("_")

    # Truncate to max length
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("_")

    return slug


def generate_approval_filename(
    action_type: str,
    slug: str,
    timestamp: datetime | None = None,
) -> str:
    """Generate approval request filename.

    Format: YYYYMMDD-HHMMSS_<action_type>_<slug>.md

    Args:
        action_type: Type of action (e.g., send_email_reply)
        slug: Slugified description
        timestamp: Optional timestamp (defaults to now)

    Returns:
        Filename string

    Example:
        >>> generate_approval_filename("send_email_reply", "interview_response")
        '20260308-143000_send_email_reply_interview_response.md'
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    date_str = timestamp.strftime("%Y%m%d-%H%M%S")
    return f"{date_str}_{action_type}_{slug}.md"


def get_action_type_dir(action_type: str) -> str:
    """Get directory name for action type.

    Args:
        action_type: Type of action

    Returns:
        Directory name ('email' or 'linkedin')
    """
    if action_type in ("send_email_reply", "send_email_followup"):
        return "email"
    elif action_type == "publish_linkedin_post":
        return "linkedin"
    else:
        raise ValueError(f"Unknown action type: {action_type}")
