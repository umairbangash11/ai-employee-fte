"""Parser for approved X post files."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from x_publisher.exceptions import FrontmatterValidationError
from x_publisher.models import ApprovedPost
from x_publisher.utils import read_frontmatter

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["type", "action_type", "status", "platform", "char_count"]


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    """Validate frontmatter for an approved X post.

    Returns:
        List of error strings (empty if valid).
    """
    errors = []

    for f in REQUIRED_FIELDS:
        if f not in frontmatter:
            errors.append(f"Missing required field: {f}")

    if frontmatter.get("type") not in {"pending_action", "approval_request"}:
        errors.append(f"Invalid type: '{frontmatter.get('type')}'")

    if frontmatter.get("action_type") not in {"publish_post", "publish_x_post"}:
        errors.append(f"Invalid action_type: '{frontmatter.get('action_type')}'")

    if frontmatter.get("platform") != "x":
        errors.append(f"Invalid platform: expected 'x', got '{frontmatter.get('platform')}'")

    # char_count advisory logging
    char_count = frontmatter.get("char_count")
    if char_count is not None and char_count > 280:
        logger.warning(
            f"Post has char_count={char_count} which exceeds 280. "
            "Operator approved this post — proceeding as advisory only (FR-014)."
        )

    return errors


def extract_content(body: str) -> str:
    """Extract tweet text from the markdown body."""
    pattern = r"##\s*Content(?:\s*Preview)?\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        if content:
            return content
    lines = [l for l in body.strip().split("\n") if not l.startswith("#")]
    return "\n".join(lines).strip()


def parse_approved_post(file_path: Path) -> ApprovedPost:
    """Parse an approved X post file.

    Raises:
        FrontmatterValidationError: If frontmatter is invalid.
    """
    try:
        frontmatter, body = read_frontmatter(file_path)
    except ValueError as e:
        raise FrontmatterValidationError(str(e))

    errors = validate_frontmatter(frontmatter)
    if errors:
        raise FrontmatterValidationError(
            f"Invalid frontmatter in {file_path}: {'; '.join(errors)}",
            missing_fields=errors,
        )

    content = extract_content(body)
    if not content:
        raise FrontmatterValidationError(f"No content found in {file_path}", missing_fields=["content"])

    created_at_str = frontmatter.get("captured_at") or frontmatter.get("created_at")
    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")) if created_at_str else datetime.utcnow()
    except (ValueError, AttributeError):
        created_at = datetime.utcnow()

    return ApprovedPost(
        file_path=file_path,
        content=content,
        frontmatter=frontmatter,
        created_at=created_at,
        char_count=frontmatter.get("char_count"),
        image_path=frontmatter.get("image_path") or None,
    )
