"""Goal progress analyzer.

Computes progress status for each business goal by aligning
completed items and pending items to goals via goal_slug matching.
"""

from briefing_generator.models import (
    BusinessGoal,
    CompletedItem,
    GoalProgress,
    PendingItem,
)


def compute_goal_progress(
    goals: list[BusinessGoal],
    completed_items: list[CompletedItem],
    pending_items: list[PendingItem],
) -> list[GoalProgress]:
    """Compute progress status for each business goal.

    Args:
        goals: List of business goals.
        completed_items: Completed items in the period.
        pending_items: Items in Needs_Action/.

    Returns:
        List of GoalProgress objects.
    """
    progress_list = []

    for goal in goals:
        # Count items aligned to this goal
        completed_count = sum(
            1 for item in completed_items if item.goal_slug == goal.slug
        )
        pending_count = sum(
            1 for item in pending_items if item.goal_slug == goal.slug
        )

        # Determine status
        if completed_count > 0 and pending_count <= 2:
            status = "on_track"
            reason = f"{completed_count} completed, {pending_count} pending"
        elif completed_count > 0 and pending_count > 2:
            status = "at_risk"
            reason = f"{completed_count} completed but {pending_count} pending items"
        elif completed_count == 0 and pending_count > 0:
            status = "blocked"
            reason = f"No progress, {pending_count} items pending"
        else:
            status = "no_activity"
            reason = "No activity this period"

        progress_list.append(
            GoalProgress(
                goal_slug=goal.slug,
                goal_title=goal.title,
                status=status,
                completed_count=completed_count,
                pending_count=pending_count,
                reason=reason,
            )
        )

    return progress_list
