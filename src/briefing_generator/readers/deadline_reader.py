"""Reader for items with deadline: frontmatter.

Scans the entire vault for files with deadline: frontmatter
to identify upcoming deadlines and overdue items.
"""

from datetime import date
from pathlib import Path

import frontmatter

from briefing_generator.config import THRESHOLDS
from briefing_generator.models import UpcomingDeadline


def _parse_date(value) -> date | None:
    """Parse date from frontmatter value."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, AttributeError):
        return None


def _infer_category(file_path: Path) -> str:
    """Infer category from file path."""
    parts = file_path.parts
    # Look for known directory names
    known_dirs = ["email", "whatsapp", "plans", "odoo", "facebook", "instagram", "x"]
    for part in parts:
        if part.lower() in known_dirs:
            return part.lower()
    return "other"


def read_deadlines(
    vault_path: Path,
    data_gaps: list[str] | None = None,
) -> list[UpcomingDeadline]:
    """Read items with deadline: frontmatter from vault.

    Args:
        vault_path: Path to vault root.
        data_gaps: Optional list to append parse errors.

    Returns:
        List of UpcomingDeadline objects (includes both upcoming and overdue).
    """
    today = date.today()
    deadline_window = THRESHOLDS["deadline_window"]
    deadlines = []

    # Scan all markdown files in vault
    for md_file in vault_path.rglob("*.md"):
        # Skip certain directories
        if any(
            part.startswith(".")
            for part in md_file.relative_to(vault_path).parts
        ):
            continue

        try:
            post = frontmatter.load(md_file)
            metadata = post.metadata

            deadline = _parse_date(metadata.get("deadline"))
            if deadline is None:
                continue

            # Calculate days until deadline
            days_until = (deadline - today).days

            # Include if within window OR overdue (negative days_until)
            if days_until <= deadline_window:
                subject = metadata.get("subject") or metadata.get("title") or md_file.stem
                category = _infer_category(md_file)

                deadlines.append(
                    UpcomingDeadline(
                        file_path=md_file,
                        subject=subject,
                        deadline=deadline,
                        days_until=days_until,
                        category=category,
                    )
                )

        except Exception as e:
            if data_gaps is not None:
                data_gaps.append(f"{md_file}: {e}")
            continue

    # Sort by deadline ascending (soonest first)
    deadlines.sort(key=lambda x: x.deadline)
    return deadlines
