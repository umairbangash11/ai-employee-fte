"""CEO Briefing Generator — Gold Phase 4.

Aggregates vault data (Business_Goals.md, Done/, Needs_Action/, Accounting/)
and generates executive markdown briefings to vault/Briefings/.

Public API:
    generate_briefing(vault_path, force_adhoc=False, dry_run=False) -> Path | str
"""

from datetime import datetime, timezone
from pathlib import Path

from briefing_generator.analyzers.bottleneck_analyzer import (
    filter_upcoming_deadlines,
    identify_bottlenecks,
)
from briefing_generator.analyzers.goal_progress import compute_goal_progress
from briefing_generator.analyzers.suggestion_generator import generate_suggestions
from briefing_generator.config import get_briefing_type, get_period_dates
from briefing_generator.logger import log_briefing_generation
from briefing_generator.models import BriefingData
from briefing_generator.readers.accounting_reader import read_accounting_data
from briefing_generator.readers.deadline_reader import read_deadlines
from briefing_generator.readers.done_reader import read_completed_items
from briefing_generator.readers.goals_reader import read_business_goals
from briefing_generator.readers.needs_action_reader import read_pending_items
from briefing_generator.vault_writer import write_briefing
from briefing_generator.writer import generate_briefing_markdown

__all__ = ["generate_briefing"]


def generate_briefing(
    vault_path: Path,
    force_adhoc: bool = False,
    dry_run: bool = False,
) -> "Path | str":
    """Generate a CEO briefing from vault data.

    Args:
        vault_path: Path to the vault directory.
        force_adhoc: If True, generate Adhoc briefing even on Monday.
        dry_run: If True, return markdown content without writing.

    Returns:
        Path to the generated briefing file, or markdown string if dry_run.
    """
    # Determine briefing type and period
    briefing_type = get_briefing_type(force_adhoc)
    period_start, period_end = get_period_dates()
    generated_at = datetime.now(timezone.utc)

    # Collect data gaps for audit
    data_gaps: list[str] = []

    # --- Phase 3: US1 - Read completed items from Done/ ---
    completed_items = read_completed_items(
        vault_path=vault_path,
        period_start=period_start,
        period_end=period_end,
        data_gaps=data_gaps,
    )

    # --- Phase 3: US1 - Read pending items from Needs_Action/ ---
    pending_items = read_pending_items(
        vault_path=vault_path,
        data_gaps=data_gaps,
    )

    # --- Phase 5: US3 - Read business goals ---
    goals = read_business_goals(
        vault_path=vault_path,
        data_gaps=data_gaps,
    )

    # --- Phase 5: US3 - Compute goal progress ---
    goal_progress = compute_goal_progress(
        goals=goals,
        completed_items=completed_items,
        pending_items=pending_items,
    )

    # --- Phase 6: US4 - Read accounting data ---
    accounting_summary = read_accounting_data(
        vault_path=vault_path,
        data_gaps=data_gaps,
    )

    # --- Phase 7: US5 - Read deadlines and identify bottlenecks ---
    all_deadlines = read_deadlines(
        vault_path=vault_path,
        data_gaps=data_gaps,
    )
    upcoming_deadlines, overdue_deadlines = filter_upcoming_deadlines(all_deadlines)

    bottlenecks = identify_bottlenecks(
        pending_items=pending_items,
        upcoming_deadlines=overdue_deadlines,  # Pass overdue for bottleneck inclusion
    )

    # --- Phase 8: US6 - Generate proactive suggestions ---
    suggestions = generate_suggestions(
        pending_items=pending_items,
        completed_items=completed_items,
        accounting_summary=accounting_summary,
    )

    # Build BriefingData with all components
    briefing_data = BriefingData(
        generated_at=generated_at,
        period_start=period_start,
        period_end=period_end,
        briefing_type=briefing_type,
        goals=goals,
        goal_progress=goal_progress,
        completed_items=completed_items,
        accounting_summary=accounting_summary,
        bottlenecks=bottlenecks,
        upcoming_deadlines=upcoming_deadlines,
        suggestions=suggestions,
        data_gaps=data_gaps,
    )

    # Generate markdown content
    content = generate_briefing_markdown(briefing_data)

    if dry_run:
        return content

    # Write to vault/Briefings/
    briefing_path = write_briefing(
        vault_path=vault_path,
        briefing_type=briefing_type,
        content=content,
    )

    # Log the generation
    details = (
        f"Generated {briefing_type} briefing with "
        f"{len(completed_items)} completed items, "
        f"{len(bottlenecks)} bottlenecks, "
        f"{len(suggestions)} suggestions"
    )
    log_briefing_generation(
        vault_path=vault_path,
        briefing_path=briefing_path,
        outcome="success",
        details=details,
    )

    return briefing_path
