"""Bottleneck analyzer.

Identifies stale items (>7 days in Needs_Action) and overdue deadlines.
"""

from datetime import date, datetime, timezone

from briefing_generator.config import THRESHOLDS
from briefing_generator.models import Bottleneck, PendingItem, UpcomingDeadline


def identify_bottlenecks(
    pending_items: list[PendingItem],
    upcoming_deadlines: list[UpcomingDeadline],
) -> list[Bottleneck]:
    """Identify bottlenecks from pending items and overdue deadlines.

    Args:
        pending_items: Items in Needs_Action/.
        upcoming_deadlines: Items with deadline: frontmatter (may include overdue).

    Returns:
        List of Bottleneck objects.
    """
    bottlenecks = []
    today = date.today()
    now = datetime.now(timezone.utc)
    stale_threshold = THRESHOLDS["stale_days"]

    # Find stale items in Needs_Action/
    for item in pending_items:
        # Calculate days stale
        if item.captured_at.tzinfo is None:
            captured_naive = item.captured_at
            days_stale = (now.replace(tzinfo=None) - captured_naive).days
        else:
            days_stale = (now - item.captured_at).days

        if days_stale > stale_threshold:
            bottlenecks.append(
                Bottleneck(
                    file_path=item.file_path,
                    subject=item.subject,
                    days_stale=days_stale,
                    reason="stale",
                    category=item.category,
                    captured_at=item.captured_at,
                    deadline=item.deadline,
                )
            )

    # Find overdue deadlines (from deadline reader)
    for deadline in upcoming_deadlines:
        if deadline.days_until < 0:
            # This is overdue - should be in bottlenecks, not upcoming
            # Note: The deadline reader should exclude these, but handle here as fallback
            days_overdue = abs(deadline.days_until)
            bottlenecks.append(
                Bottleneck(
                    file_path=deadline.file_path,
                    subject=deadline.subject,
                    days_stale=days_overdue,
                    reason="overdue",
                    category=deadline.category,
                    captured_at=datetime.combine(deadline.deadline, datetime.min.time()),
                    deadline=deadline.deadline,
                )
            )

    # Sort by days_stale descending
    bottlenecks.sort(key=lambda x: x.days_stale, reverse=True)
    return bottlenecks


def filter_upcoming_deadlines(
    all_deadlines: list[UpcomingDeadline],
) -> tuple[list[UpcomingDeadline], list[UpcomingDeadline]]:
    """Split deadlines into upcoming and overdue.

    Args:
        all_deadlines: All items with deadline: frontmatter.

    Returns:
        Tuple of (upcoming, overdue) deadline lists.
    """
    upcoming = []
    overdue = []

    for d in all_deadlines:
        if d.days_until < 0:
            overdue.append(d)
        else:
            upcoming.append(d)

    # Sort upcoming by date ascending
    upcoming.sort(key=lambda x: x.deadline)
    return upcoming, overdue
