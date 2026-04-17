"""Canonical frontmatter builder for social post proposals."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_frontmatter(
    platform: str,
    content: str,
    dest_path: Path,
    *,
    source_path: str = "",
    image_path: str | None = None,
) -> dict[str, Any]:
    """Build the canonical frontmatter dict for a social post proposal.

    Produces type: pending_action schema required by FR-001 and data-model.md.

    Args:
        platform: One of 'facebook', 'instagram', 'x'
        content: Full post text
        dest_path: Absolute path where the draft file will be written
        source_path: Caller-provided source reference (defaults to empty string)
        image_path: Local image file path (Instagram/X only; omit for Facebook)

    Returns:
        Frontmatter dict ready for yaml.dump()
    """
    captured_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    fm: dict[str, Any] = {
        "type": "pending_action",
        "platform": platform,
        "action_type": "publish_post",
        "status": "awaiting_approval",
        "source_path": source_path,
        "dest_path": str(dest_path),
        "captured_at": captured_at,
        "content_preview": content[:100],
    }

    # Platform-specific fields
    if platform in ("instagram", "x") and image_path is not None:
        fm["image_path"] = image_path

    if platform == "x":
        char_count = len(content)
        fm["char_count"] = char_count
        if char_count > 280:
            fm["warning"] = "exceeds_char_limit"

    return fm
