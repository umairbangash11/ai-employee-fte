"""Parser for approved Instagram post files."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from instagram_publisher.exceptions import FrontmatterValidationError, ImageNotFoundError
from instagram_publisher.models import ApprovedPost
from instagram_publisher.utils import read_frontmatter

REQUIRED_FIELDS = ["type", "action_type", "status", "platform"]


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    """Validate frontmatter for an approved Instagram post.

    Returns:
        List of error strings (empty if valid).
    """
    errors = []

    for f in REQUIRED_FIELDS:
        if f not in frontmatter:
            errors.append(f"Missing required field: {f}")

    if frontmatter.get("type") not in {"pending_action", "approval_request"}:
        errors.append(f"Invalid type: '{frontmatter.get('type')}'")

    if frontmatter.get("action_type") not in {"publish_post", "publish_instagram_post"}:
        errors.append(f"Invalid action_type: '{frontmatter.get('action_type')}'")

    if frontmatter.get("platform") != "instagram":
        errors.append(f"Invalid platform: expected 'instagram', got '{frontmatter.get('platform')}'")

    return errors


def extract_content(body: str) -> str:
    """Extract caption from the markdown body (## Content heading)."""
    pattern = r"##\s*Content(?:\s*Preview)?\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)

    if match:
        content = match.group(1).strip()
        if content:
            return content

    # Fallback: strip markdown headers
    lines = [l for l in body.strip().split("\n") if not l.startswith("#")]
    return "\n".join(lines).strip()


def parse_approved_post(file_path: Path) -> ApprovedPost:
    """Parse an approved Instagram post file.

    Validates frontmatter and checks image_path existence if provided.

    Raises:
        FrontmatterValidationError: If frontmatter is missing required fields.
        ImageNotFoundError: If image_path is non-empty but file does not exist.
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

    # Image path validation (FR-013)
    image_path = frontmatter.get("image_path") or None
    if image_path and not Path(image_path).exists():
        raise ImageNotFoundError(image_path)

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
        image_path=image_path,
    )
