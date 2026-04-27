"""Reader for completed items from vault/Done/.

Scans Done/ directory and parses YAML frontmatter to extract
CompletedItem data for the briefing period.
"""

from datetime import date, datetime
from pathlib import Path

import frontmatter

from briefing_generator.config import VAULT_DIRS
from briefing_generator.models import CompletedItem
from briefing_generator.retry import with_retry


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime from frontmatter value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Try ISO 8601 format
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _infer_source_type(file_path: Path) -> str:
    """Infer source type from file path.

    Examples:
        Done/email/foo.md -> "email"
        Done/facebook/bar.md -> "facebook"
        Done/general.md -> "other"
    """
    parts = file_path.parts
    # Find "Done" in path and get the next part
    try:
        done_idx = parts.index("Done")
        if done_idx + 1 < len(parts) - 1:
            return parts[done_idx + 1]
    except ValueError:
        pass
    return "other"


def read_completed_items(
    vault_path: Path,
    period_start: date,
    period_end: date,
    data_gaps: list[str] | None = None,
) -> list[CompletedItem]:
    """Read completed items from vault/Done/.

    Args:
        vault_path: Path to vault root.
        period_start: Start of briefing period.
        period_end: End of briefing period.
        data_gaps: Optional list to append skipped file paths.

    Returns:
        List of CompletedItem objects within the period.
    """
    done_dir = vault_path / VAULT_DIRS["done"]
    if not done_dir.is_dir():
        return []

    items = []
    for md_file in done_dir.rglob("*.md"):
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

            # Parse completion date
            completed_at = (
                _parse_datetime(metadata.get("published_at"))
                or _parse_datetime(metadata.get("completed_at"))
                or _parse_datetime(metadata.get("captured_at"))
            )

            if completed_at is None:
                if data_gaps is not None:
                    data_gaps.append(f"{md_file}: missing completion date")
                continue

            # Filter by period
            completed_date = completed_at.date()
            if not (period_start <= completed_date <= period_end):
                continue

            # Extract subject
            subject = metadata.get("subject") or metadata.get("title") or md_file.stem

            # Extract source type
            source_type = (
                metadata.get("platform")
                or metadata.get("source")
                or _infer_source_type(md_file)
            )

            # Extract goal slug (optional)
            goal_slug = metadata.get("goal")

            items.append(
                CompletedItem(
                    file_path=md_file,
                    subject=subject,
                    completed_at=completed_at,
                    source_type=source_type,
                    goal_slug=goal_slug,
                )
            )

        except Exception as e:
            if data_gaps is not None:
                data_gaps.append(f"{md_file}: {e}")
            continue

    # Sort by completion date descending
    items.sort(key=lambda x: x.completed_at, reverse=True)
    return items
