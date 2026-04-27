"""Reader for pending items from vault/Needs_Action/.

Scans Needs_Action/ directory and parses YAML frontmatter to extract
PendingItem data for bottleneck analysis.
"""

from datetime import date, datetime
from pathlib import Path

import frontmatter

from briefing_generator.config import VAULT_DIRS
from briefing_generator.models import PendingItem
from briefing_generator.retry import with_retry


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime from frontmatter value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_date(value: str | date | None) -> date | None:
    """Parse a date from frontmatter value."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


def _infer_category(file_path: Path) -> str:
    """Infer category from file path.

    Examples:
        Needs_Action/email/foo.md -> "email"
        Needs_Action/plans/bar.md -> "plans"
        Needs_Action/general.md -> "other"
    """
    parts = file_path.parts
    try:
        na_idx = parts.index("Needs_Action")
        if na_idx + 1 < len(parts) - 1:
            return parts[na_idx + 1]
    except ValueError:
        pass
    return "other"


def read_pending_items(
    vault_path: Path,
    data_gaps: list[str] | None = None,
) -> list[PendingItem]:
    """Read pending items from vault/Needs_Action/.

    Args:
        vault_path: Path to vault root.
        data_gaps: Optional list to append skipped file paths.

    Returns:
        List of PendingItem objects.
    """
    needs_action_dir = vault_path / VAULT_DIRS["needs_action"]
    if not needs_action_dir.is_dir():
        return []

    items = []
    for md_file in needs_action_dir.rglob("*.md"):
        # Ralph Wiggum Loop: retry up to 3 times for file read failures
        def load_file():
            return frontmatter.load(md_file)

        post = with_retry(
            load_file,
            on_failure=lambda e: data_gaps.append(f"{md_file}: {e}") if data_gaps else None,
        )

        if post is None:
            continue

        try:
            metadata = post.metadata

            # Parse captured_at (required for bottleneck detection)
            captured_at = _parse_datetime(metadata.get("captured_at"))
            if captured_at is None:
                # Use file modification time as fallback
                captured_at = datetime.fromtimestamp(md_file.stat().st_mtime)

            # Extract subject
            subject = metadata.get("subject") or metadata.get("title") or md_file.stem

            # Infer category
            category = metadata.get("source") or _infer_category(md_file)

            # Extract optional fields
            goal_slug = metadata.get("goal")
            deadline = _parse_date(metadata.get("deadline"))

            items.append(
                PendingItem(
                    file_path=md_file,
                    subject=subject,
                    captured_at=captured_at,
                    category=category,
                    goal_slug=goal_slug,
                    deadline=deadline,
                )
            )

        except Exception as e:
            if data_gaps is not None:
                data_gaps.append(f"{md_file}: {e}")
            continue

    # Sort by captured_at ascending (oldest first)
    items.sort(key=lambda x: x.captured_at)
    return items
