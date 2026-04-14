"""Validation utilities for HITL approval files."""

import logging
from pathlib import Path
from typing import Optional

import yaml

from .exceptions import InvalidFrontmatterError

logger = logging.getLogger(__name__)

# Required frontmatter fields
REQUIRED_FIELDS = [
    "type",
    "action_type",
    "status",
    "created_at",
    "created_by",
    "target",
    "source",
    "rollback_strategy",
]


def parse_approval_file(path: Path) -> Optional[dict]:
    """Parse approval file and extract frontmatter and body.

    Args:
        path: Path to approval markdown file

    Returns:
        Dict with 'frontmatter' and 'body' keys, or None if parsing fails
    """
    path = Path(path)

    if not path.exists():
        logger.error(f"File not found: {path}")
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        return None

    # Split frontmatter and body
    if not content.startswith("---"):
        logger.error(f"File missing frontmatter: {path}")
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        logger.error(f"Invalid frontmatter format: {path}")
        return None

    frontmatter_str = parts[1].strip()
    body = parts[2].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML frontmatter in {path}: {e}")
        return None

    if frontmatter is None:
        frontmatter = {}

    return {
        "frontmatter": frontmatter,
        "body": body,
        "path": str(path),
        "filename": path.name,
    }


def validate_frontmatter(data: dict) -> bool:
    """Validate that frontmatter contains all required fields.

    Args:
        data: Frontmatter dict to validate

    Returns:
        True if valid, False otherwise
    """
    if not data:
        return False

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False

    # Validate type
    if data.get("type") != "approval_request":
        logger.warning(f"Invalid type: {data.get('type')}")
        return False

    # Validate action_type
    valid_action_types = {"send_email_reply", "send_email_followup", "publish_linkedin_post"}
    if data.get("action_type") not in valid_action_types:
        logger.warning(f"Invalid action_type: {data.get('action_type')}")
        return False

    # Validate status
    valid_statuses = {"pending", "approved", "rejected"}
    if data.get("status") not in valid_statuses:
        logger.warning(f"Invalid status: {data.get('status')}")
        return False

    # Validate rollback_strategy is not empty
    if not data.get("rollback_strategy"):
        logger.warning("Empty rollback_strategy")
        return False

    return True


def get_approval_summary(parsed: dict) -> dict:
    """Extract summary information from parsed approval file.

    Args:
        parsed: Result from parse_approval_file()

    Returns:
        Summary dict with key fields
    """
    fm = parsed.get("frontmatter", {})
    target = fm.get("target", {})

    return {
        "filename": parsed.get("filename", ""),
        "action_type": fm.get("action_type", ""),
        "status": fm.get("status", ""),
        "created_at": fm.get("created_at", ""),
        "created_by": fm.get("created_by", ""),
        "target": target.get("recipient", target.get("platform", "")),
        "subject": target.get("subject", ""),
    }
