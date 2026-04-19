"""Proactive suggestion generator.

Generates rule-based suggestions based on observed patterns
in vault data.
"""

from briefing_generator.config import THRESHOLDS
from briefing_generator.models import (
    AccountingSummary,
    CompletedItem,
    PendingItem,
    ProactiveSuggestion,
)


def _count_by_category(items: list, category_attr: str, target: str) -> int:
    """Count items matching a category."""
    return sum(1 for item in items if getattr(item, category_attr, "").lower() == target.lower())


def _count_stale_items(items: list[PendingItem], stale_days: int) -> int:
    """Count items older than stale_days."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    count = 0
    for item in items:
        if item.captured_at.tzinfo is None:
            days = (now.replace(tzinfo=None) - item.captured_at).days
        else:
            days = (now - item.captured_at).days
        if days > stale_days:
            count += 1
    return count


def generate_suggestions(
    pending_items: list[PendingItem],
    completed_items: list[CompletedItem],
    accounting_summary: AccountingSummary,
) -> list[ProactiveSuggestion]:
    """Generate proactive suggestions based on observed patterns.

    Args:
        pending_items: Items in Needs_Action/.
        completed_items: Completed items in the period.
        accounting_summary: Accounting data summary.

    Returns:
        List of ProactiveSuggestion objects.
    """
    suggestions = []

    # Rule 1: Email backlog
    email_count = _count_by_category(pending_items, "category", "email")
    if email_count > THRESHOLDS["email_backlog"]:
        suggestions.append(
            ProactiveSuggestion(
                category="email_backlog",
                message="Consider scheduling time to process email backlog.",
                severity="warning",
                threshold_met=f">{THRESHOLDS['email_backlog']} items in Needs_Action/email/",
            )
        )

    # Rule 2: WhatsApp backlog
    whatsapp_count = _count_by_category(pending_items, "category", "whatsapp")
    if whatsapp_count > THRESHOLDS["whatsapp_backlog"]:
        suggestions.append(
            ProactiveSuggestion(
                category="whatsapp_backlog",
                message="WhatsApp messages need attention.",
                severity="warning",
                threshold_met=f">{THRESHOLDS['whatsapp_backlog']} items in Needs_Action/whatsapp/",
            )
        )

    # Rule 3: High social activity
    social_count = (
        _count_by_category(completed_items, "source_type", "facebook")
        + _count_by_category(completed_items, "source_type", "instagram")
        + _count_by_category(completed_items, "source_type", "x")
    )
    if social_count > THRESHOLDS["social_activity"]:
        suggestions.append(
            ProactiveSuggestion(
                category="social_activity",
                message="Strong social media week; consider content calendar review.",
                severity="info",
                threshold_met=f">{THRESHOLDS['social_activity']} posts in Done/",
            )
        )

    # Rule 4: Overdue invoices
    if accounting_summary.overdue_invoices:
        overdue_count = len(accounting_summary.overdue_invoices)
        total_overdue = sum(inv.amount for inv in accounting_summary.overdue_invoices)
        suggestions.append(
            ProactiveSuggestion(
                category="overdue_invoices",
                message=f"Outstanding invoices require follow-up (${total_overdue:,.2f} overdue).",
                severity="warning",
                threshold_met=f"{overdue_count} overdue invoices",
            )
        )

    # Rule 5: Stale plans
    plans_count = _count_by_category(pending_items, "category", "plans")
    stale_plans = 0
    for item in pending_items:
        if item.category.lower() == "plans":
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if item.captured_at.tzinfo is None:
                days = (now.replace(tzinfo=None) - item.captured_at).days
            else:
                days = (now - item.captured_at).days
            if days > THRESHOLDS["stale_days"]:
                stale_plans += 1

    if stale_plans > THRESHOLDS["stale_plans"]:
        suggestions.append(
            ProactiveSuggestion(
                category="stale_plans",
                message="Triage backlog accumulating in plans.",
                severity="warning",
                threshold_met=f">{THRESHOLDS['stale_plans']} stale items in Needs_Action/plans/",
            )
        )

    return suggestions
