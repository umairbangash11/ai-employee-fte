"""Briefing markdown generator.

Renders BriefingData into a complete markdown document with all sections.
"""

from datetime import datetime, timezone

from briefing_generator.models import (
    AccountingSummary,
    Bottleneck,
    BriefingData,
    CompletedItem,
    GoalProgress,
    ProactiveSuggestion,
    UpcomingDeadline,
)


def _format_datetime(dt: datetime) -> str:
    """Format datetime as ISO 8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_date(d) -> str:
    """Format date as YYYY-MM-DD string."""
    return d.strftime("%Y-%m-%d")


def _render_frontmatter(data: BriefingData) -> str:
    """Render YAML frontmatter block."""
    return f"""---
type: ceo_briefing
generated_at: "{_format_datetime(data.generated_at)}"
period_start: "{_format_date(data.period_start)}"
period_end: "{_format_date(data.period_end)}"
status: generated
---"""


def _render_executive_summary(data: BriefingData) -> str:
    """Render Executive Summary section."""
    lines = ["## Executive Summary", ""]

    # Task completion summary
    completed_count = len(data.completed_items)
    if completed_count > 0:
        lines.append(f"- {completed_count} tasks completed this week")
    else:
        lines.append("- No tasks completed this week")

    # Accounting summary
    if data.accounting_summary.has_data:
        paid = data.accounting_summary.total_paid
        invoiced = data.accounting_summary.total_invoiced
        lines.append(f"- Revenue: ${paid:,.2f} received, ${invoiced:,.2f} invoiced")
    else:
        lines.append("- No accounting data available")

    # Bottlenecks summary
    bottleneck_count = len(data.bottlenecks)
    if bottleneck_count > 0:
        lines.append(f"- {bottleneck_count} items require attention")
    else:
        lines.append("- No bottlenecks identified")

    # Deadlines summary
    deadline_count = len(data.upcoming_deadlines)
    if deadline_count > 0:
        lines.append(f"- {deadline_count} deadlines upcoming in next 7 days")
    else:
        lines.append("- No upcoming deadlines")

    return "\n".join(lines)


def _render_goals_progress(data: BriefingData) -> str:
    """Render Goals Progress section."""
    lines = ["## Goals Progress", ""]

    if not data.goals:
        lines.append("*No business goals defined.*")
        return "\n".join(lines)

    # Table header
    lines.append("| Goal | Status | Completed | Pending |")
    lines.append("|------|--------|-----------|---------|")

    status_icons = {
        "on_track": "✅ On Track",
        "at_risk": "⚠️ At Risk",
        "blocked": "🚫 Blocked",
        "no_activity": "⏸️ No Activity",
    }

    for progress in data.goal_progress:
        status_str = status_icons.get(progress.status, progress.status)
        lines.append(
            f"| {progress.goal_title} | {status_str} | "
            f"{progress.completed_count} | {progress.pending_count} |"
        )

    return "\n".join(lines)


def _render_accounting_summary(data: BriefingData) -> str:
    """Render Revenue/Business Summary section."""
    lines = ["## Revenue/Business Summary", ""]

    summary = data.accounting_summary
    if not summary.has_data:
        lines.append("*No accounting data available.*")
        return "\n".join(lines)

    lines.append(f"- **Invoiced**: ${summary.total_invoiced:,.2f} ({summary.invoice_count} invoices)")
    lines.append(f"- **Received**: ${summary.total_paid:,.2f} ({summary.payment_count} payments)")

    outstanding = summary.total_invoiced - summary.total_paid
    if outstanding > 0:
        lines.append(f"- **Outstanding**: ${outstanding:,.2f}")

    if summary.overdue_invoices:
        lines.append("")
        lines.append("### Overdue Invoices")
        for inv in summary.overdue_invoices:
            lines.append(f"- {inv.partner}: ${inv.amount:,.2f} (overdue {inv.days_overdue} days)")

    return "\n".join(lines)


def _render_completed_tasks(data: BriefingData) -> str:
    """Render Completed Tasks section."""
    lines = ["## Completed Tasks", ""]

    if not data.completed_items:
        lines.append("*No items completed this period.*")
        return "\n".join(lines)

    # Group by source type
    by_source: dict[str, list[CompletedItem]] = {}
    for item in data.completed_items:
        source = item.source_type
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(item)

    for source, items in sorted(by_source.items()):
        lines.append(f"### {source.title()}")
        for item in items:
            date_str = item.completed_at.strftime("%b %d")
            lines.append(f"- {item.subject} ({date_str})")
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_bottlenecks(data: BriefingData) -> str:
    """Render Bottlenecks section."""
    lines = ["## Bottlenecks", ""]

    if not data.bottlenecks:
        lines.append("*No bottlenecks identified.*")
        return "\n".join(lines)

    # Table header
    lines.append("| Item | Days | Category | Reason |")
    lines.append("|------|------|----------|--------|")

    for b in data.bottlenecks:
        if b.reason == "overdue":
            days_str = f"overdue {b.days_stale}d"
        else:
            days_str = f"{b.days_stale} days"
        lines.append(f"| {b.subject[:40]} | {days_str} | {b.category} | {b.reason} |")

    return "\n".join(lines)


def _render_suggestions(data: BriefingData) -> str:
    """Render Proactive Suggestions section."""
    lines = ["## Proactive Suggestions", ""]

    if not data.suggestions:
        lines.append("*No suggestions this period.*")
        return "\n".join(lines)

    severity_icons = {"warning": "⚠️", "info": "ℹ️"}

    for s in data.suggestions:
        icon = severity_icons.get(s.severity, "•")
        lines.append(f"- {icon} **{s.category.replace('_', ' ').title()}**: {s.message}")

    return "\n".join(lines)


def _render_upcoming_deadlines(data: BriefingData) -> str:
    """Render Upcoming Deadlines section."""
    lines = ["## Upcoming Deadlines", ""]

    if not data.upcoming_deadlines:
        lines.append("*No upcoming deadlines.*")
        return "\n".join(lines)

    # Table header
    lines.append("| Item | Due | Days |")
    lines.append("|------|-----|------|")

    for d in data.upcoming_deadlines:
        due_str = d.deadline.strftime("%b %d")
        lines.append(f"| {d.subject[:40]} | {due_str} | {d.days_until} |")

    return "\n".join(lines)


def _render_data_gaps(data: BriefingData) -> str:
    """Render Data Gaps footer if any files couldn't be parsed."""
    if not data.data_gaps:
        return ""

    lines = ["", "---", "", "### Data Gaps", ""]
    lines.append("The following files could not be fully parsed:")
    for gap in data.data_gaps[:10]:  # Limit to 10
        lines.append(f"- {gap}")
    if len(data.data_gaps) > 10:
        lines.append(f"- ... and {len(data.data_gaps) - 10} more")

    return "\n".join(lines)


def generate_briefing_markdown(data: BriefingData) -> str:
    """Generate complete briefing markdown from BriefingData.

    Args:
        data: Aggregated briefing data.

    Returns:
        Complete markdown content for the briefing file.
    """
    period_str = f"{_format_date(data.period_start)} to {_format_date(data.period_end)}"

    sections = [
        _render_frontmatter(data),
        "",
        f"# CEO Briefing: Week of {period_str}",
        "",
        _render_executive_summary(data),
        "",
        _render_goals_progress(data),
        "",
        _render_accounting_summary(data),
        "",
        _render_completed_tasks(data),
        "",
        _render_bottlenecks(data),
        "",
        _render_suggestions(data),
        "",
        _render_upcoming_deadlines(data),
        _render_data_gaps(data),
    ]

    return "\n".join(sections)
