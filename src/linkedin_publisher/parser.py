"""Parser for approved LinkedIn post files."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .exceptions import InvalidFrontmatterError
from .models import ApprovedPost


def parse_approved_file(file_path: Path) -> ApprovedPost:
    """Parse an approved LinkedIn post file.

    Reads Markdown file, extracts YAML frontmatter and content.

    Args:
        file_path: Path to approval file

    Returns:
        ApprovedPost with parsed data

    Raises:
        InvalidFrontmatterError: If frontmatter is missing or invalid
    """
    file_path = Path(file_path)
    content = file_path.read_text(encoding="utf-8")

    # Check for frontmatter
    if not content.startswith("---"):
        raise InvalidFrontmatterError("File has no frontmatter", str(file_path))

    # Find end of frontmatter
    end_idx = content.find("---", 3)
    if end_idx == -1:
        raise InvalidFrontmatterError("Invalid frontmatter format", str(file_path))

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    # Parse frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise InvalidFrontmatterError(f"YAML parse error: {e}", str(file_path))

    # Validate required fields
    validate_frontmatter(frontmatter, str(file_path))

    # Extract post content
    post_content = extract_post_content(body, frontmatter)

    # Parse created_at
    created_at_str = frontmatter.get("created_at", "")
    try:
        if created_at_str.endswith("Z"):
            created_at_str = created_at_str[:-1]
        created_at = datetime.fromisoformat(created_at_str)
    except (ValueError, AttributeError):
        created_at = datetime.utcnow()

    # Get source path
    source = frontmatter.get("source", {})
    source_path = source.get("path") if isinstance(source, dict) else None

    return ApprovedPost(
        file_path=file_path,
        content=post_content,
        frontmatter=frontmatter,
        created_at=created_at,
        source_path=source_path,
    )


def extract_post_content(body: str, frontmatter: dict) -> str:
    """Extract post content from file body.

    Looks for content in this order:
    1. ## Content Preview section
    2. ## Content section
    3. Full body text (excluding other sections)

    Args:
        body: Markdown body (after frontmatter)
        frontmatter: Parsed frontmatter dict

    Returns:
        Post content string
    """
    # Try to find ## Content Preview section
    content_preview_match = re.search(
        r"##\s*Content\s*Preview\s*\n+(.*?)(?=\n##|\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if content_preview_match:
        return content_preview_match.group(1).strip()

    # Try to find ## Content section
    content_match = re.search(
        r"##\s*Content\s*\n+(.*?)(?=\n##|\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if content_match:
        return content_match.group(1).strip()

    # Fall back to content in frontmatter if available
    if frontmatter.get("content"):
        return frontmatter["content"].strip()

    # Fall back to full body, excluding common sections
    # Remove known sections
    cleaned = body
    for section in ["## Reasoning", "## Expected Outcome", "## Rollback Strategy", "## Source"]:
        pattern = rf"{re.escape(section)}\s*\n+.*?(?=\n##|\Z)"
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    return cleaned.strip()


def validate_frontmatter(frontmatter: dict, file_path: str = "") -> None:
    """Validate required frontmatter fields for LinkedIn posts.

    Required:
    - type: approval_request
    - action_type: publish_linkedin_post
    - target.platform: linkedin

    Args:
        frontmatter: Parsed frontmatter dict
        file_path: File path for error messages

    Raises:
        InvalidFrontmatterError: If validation fails
    """
    # Check type
    if frontmatter.get("type") != "approval_request":
        raise InvalidFrontmatterError(
            f"Expected type=approval_request, got {frontmatter.get('type')}",
            file_path,
        )

    # Check action_type
    if frontmatter.get("action_type") != "publish_linkedin_post":
        raise InvalidFrontmatterError(
            f"Expected action_type=publish_linkedin_post, got {frontmatter.get('action_type')}",
            file_path,
        )

    # Check target.platform
    target = frontmatter.get("target", {})
    if not isinstance(target, dict):
        raise InvalidFrontmatterError("target must be a dict", file_path)

    if target.get("platform") != "linkedin":
        raise InvalidFrontmatterError(
            f"Expected target.platform=linkedin, got {target.get('platform')}",
            file_path,
        )
