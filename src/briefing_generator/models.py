"""Data models for CEO Briefing Generator.

All models are dataclasses used internally for data aggregation.
No external persistence required.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal


@dataclass
class BusinessGoal:
    """A business goal extracted from Business_Goals.md."""

    title: str
    slug: str
    description: str
    target: str | None = None


@dataclass
class GoalProgress:
    """Progress status for a business goal."""

    goal_slug: str
    goal_title: str
    status: Literal["on_track", "at_risk", "blocked", "no_activity"]
    completed_count: int
    pending_count: int
    reason: str


@dataclass
class CompletedItem:
    """A completed item from Done/."""

    file_path: Path
    subject: str
    completed_at: datetime
    source_type: str
    goal_slug: str | None = None


@dataclass
class Bottleneck:
    """An item identified as a bottleneck."""

    file_path: Path
    subject: str
    days_stale: int
    reason: str  # "stale" or "overdue"
    category: str
    captured_at: datetime
    deadline: date | None = None


@dataclass
class OverdueInvoice:
    """An overdue invoice flagged in Bottlenecks."""

    file_path: Path
    partner: str
    amount: Decimal
    due_date: date
    days_overdue: int


@dataclass
class AccountingSummary:
    """Summary of accounting activity in the period."""

    total_invoiced: Decimal = Decimal("0")
    invoice_count: int = 0
    total_paid: Decimal = Decimal("0")
    payment_count: int = 0
    overdue_invoices: list[OverdueInvoice] = field(default_factory=list)
    has_data: bool = False


@dataclass
class UpcomingDeadline:
    """An item with an upcoming deadline."""

    file_path: Path
    subject: str
    deadline: date
    days_until: int
    category: str


@dataclass
class ProactiveSuggestion:
    """A proactive suggestion based on observed patterns."""

    category: str
    message: str
    severity: Literal["info", "warning"]
    threshold_met: str


@dataclass
class PendingItem:
    """An item in Needs_Action/ for bottleneck analysis."""

    file_path: Path
    subject: str
    captured_at: datetime
    category: str
    goal_slug: str | None = None
    deadline: date | None = None


@dataclass
class BriefingData:
    """Aggregated data for CEO Briefing generation."""

    # Metadata
    generated_at: datetime
    period_start: date
    period_end: date
    briefing_type: str

    # Business goals
    goals: list[BusinessGoal] = field(default_factory=list)
    goal_progress: list[GoalProgress] = field(default_factory=list)

    # Completed work
    completed_items: list[CompletedItem] = field(default_factory=list)

    # Accounting
    accounting_summary: AccountingSummary = field(default_factory=AccountingSummary)

    # Issues
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    upcoming_deadlines: list[UpcomingDeadline] = field(default_factory=list)

    # Intelligence
    suggestions: list[ProactiveSuggestion] = field(default_factory=list)

    # Audit metadata
    data_gaps: list[str] = field(default_factory=list)
