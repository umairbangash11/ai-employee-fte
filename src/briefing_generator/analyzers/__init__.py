"""Data analyzers for CEO Briefing Generator.

Analyzers process reader output to compute derived data:
- Bottlenecks (stale items, overdue deadlines)
- Goal progress (alignment of completed work to goals)
- Proactive suggestions (rule-based recommendations)
"""

from briefing_generator.analyzers.bottleneck_analyzer import (
    filter_upcoming_deadlines,
    identify_bottlenecks,
)
from briefing_generator.analyzers.goal_progress import compute_goal_progress
from briefing_generator.analyzers.suggestion_generator import generate_suggestions

__all__ = [
    "identify_bottlenecks",
    "filter_upcoming_deadlines",
    "compute_goal_progress",
    "generate_suggestions",
]
