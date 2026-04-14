"""Parser for approved Facebook post files.

Parses YAML frontmatter and extracts post content from markdown files.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from facebook_publisher.exceptions import FrontmatterValidationError
from facebook_publisher.models import ApprovedPost
from facebook_publisher.utils import read_frontmatter

# Required frontmatter fields
REQUIRED_FIELDS = [
    "type",
    "action_type",
    "status",
    "target",
]

# Required nested fields
REQUIRED_TARGET_FIELDS = ["platform", "visibility"]


def parse_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
    """Parse frontmatter from an approved post file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (frontmatter dict, body string)

    Raises:
        FrontmatterValidationError: If frontmatter is invalid
    """
    try:
        frontmatter, body = read_frontmatter(file_path)
    except ValueError as e:
        raise FrontmatterValidationError(str(e))

    return frontmatter, body


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    """Validate frontmatter has all required fields.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        List of missing or invalid fields (empty if valid)
    """
    errors = []

    # Check required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")

    # Check type value
    if frontmatter.get("type") != "approval_request":
        errors.append(f"Invalid type: expected 'approval_request', got '{frontmatter.get('type')}'")

    # Check action_type value
    if frontmatter.get("action_type") != "publish_facebook_post":
        errors.append(
            f"Invalid action_type: expected 'publish_facebook_post', got '{frontmatter.get('action_type')}'"
        )

    # Check target nested fields
    target = frontmatter.get("target", {})
    if not isinstance(target, dict):
        errors.append("'target' must be a dictionary")
    else:
        for field in REQUIRED_TARGET_FIELDS:
            if field not in target:
                errors.append(f"Missing required target field: {field}")

        # Validate platform
        if target.get("platform") != "facebook":
            errors.append(f"Invalid platform: expected 'facebook', got '{target.get('platform')}'")

        # Validate visibility
        valid_visibility = ["public", "friends", "only_me"]
        if target.get("visibility") not in valid_visibility:
            errors.append(
                f"Invalid visibility: expected one of {valid_visibility}, got '{target.get('visibility')}'"
            )

    return errors


def extract_content(body: str) -> str:
    """Extract post content from the markdown body.

    Looks for content under '## Content Preview' heading.
    Falls back to entire body if section not found.

    Args:
        body: Markdown body text

    Returns:
        Extracted content string
    """
    # Try to find ## Content Preview section
    pattern = r"##\s*Content\s*Preview\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)

    if match:
        content = match.group(1).strip()
        if content:
            return content

    # Fallback: use entire body (stripped of any markdown headers)
    # Remove markdown headers for cleaner content
    lines = body.strip().split("\n")
    content_lines = []
    for line in lines:
        # Skip markdown headers
        if line.startswith("#"):
            continue
        content_lines.append(line)

    return "\n".join(content_lines).strip()


def parse_approved_post(file_path: Path) -> ApprovedPost:
    """Parse an approved post file into an ApprovedPost object.

    Args:
        file_path: Path to the markdown file

    Returns:
        ApprovedPost object

    Raises:
        FrontmatterValidationError: If frontmatter is invalid or missing required fields
    """
    frontmatter, body = parse_frontmatter(file_path)

    # Validate frontmatter
    errors = validate_frontmatter(frontmatter)
    if errors:
        raise FrontmatterValidationError(
            f"Invalid frontmatter in {file_path}: {'; '.join(errors)}",
            missing_fields=errors,
        )

    # Extract content
    content = extract_content(body)
    if not content:
        raise FrontmatterValidationError(
            f"No content found in {file_path}",
            missing_fields=["content"],
        )

    # Get created_at timestamp
    created_at_str = frontmatter.get("created_at")
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_at = datetime.utcnow()
    else:
        created_at = datetime.utcnow()

    # Get visibility
    visibility = frontmatter.get("target", {}).get("visibility", "public")

    return ApprovedPost(
        file_path=file_path,
        content=content,
        frontmatter=frontmatter,
        created_at=created_at,
        visibility=visibility,
    )
