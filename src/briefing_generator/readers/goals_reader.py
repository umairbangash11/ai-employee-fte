"""Reader for business goals from vault/Business_Goals.md.

Parses ## Goal: headings to extract BusinessGoal objects.
"""

import re
from pathlib import Path

from briefing_generator.config import VAULT_DIRS
from briefing_generator.models import BusinessGoal


def _make_slug(title: str) -> str:
    """Convert goal title to slug for matching.

    Example: "Increase Revenue" -> "increase-revenue"
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def read_business_goals(
    vault_path: Path,
    data_gaps: list[str] | None = None,
) -> list[BusinessGoal]:
    """Read business goals from vault/Business_Goals.md.

    Args:
        vault_path: Path to vault root.
        data_gaps: Optional list to append parse errors.

    Returns:
        List of BusinessGoal objects.
    """
    goals_file = vault_path / VAULT_DIRS["goals_file"]
    if not goals_file.exists():
        return []

    try:
        content = goals_file.read_text(encoding="utf-8")
    except Exception as e:
        if data_gaps is not None:
            data_gaps.append(f"{goals_file}: {e}")
        return []

    goals = []
    lines = content.split("\n")
    current_goal: dict | None = None

    for line in lines:
        # Check for goal heading
        match = re.match(r"^##\s*Goal:\s*(.+)$", line, re.IGNORECASE)
        if match:
            # Save previous goal
            if current_goal:
                goals.append(
                    BusinessGoal(
                        title=current_goal["title"],
                        slug=current_goal["slug"],
                        description=current_goal["description"].strip(),
                        target=current_goal.get("target"),
                    )
                )
            # Start new goal
            title = match.group(1).strip()
            current_goal = {
                "title": title,
                "slug": _make_slug(title),
                "description": "",
                "target": None,
            }
        elif current_goal:
            # Check for target line
            target_match = re.match(r"^Target:\s*(.+)$", line, re.IGNORECASE)
            if target_match:
                current_goal["target"] = target_match.group(1).strip()
            else:
                # Add to description
                current_goal["description"] += line + "\n"

    # Save last goal
    if current_goal:
        goals.append(
            BusinessGoal(
                title=current_goal["title"],
                slug=current_goal["slug"],
                description=current_goal["description"].strip(),
                target=current_goal.get("target"),
            )
        )

    return goals
