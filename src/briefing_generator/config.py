"""Configuration for CEO Briefing Generator."""

import os
from datetime import date, datetime, timedelta
from pathlib import Path


def get_vault_path() -> Path:
    """Get vault path from environment variable.

    Returns:
        Path to vault directory.

    Raises:
        ValueError: If VAULT_PATH is not set.
    """
    vault_path = os.environ.get("VAULT_PATH")
    if not vault_path:
        raise ValueError("VAULT_PATH environment variable is not set")
    return Path(vault_path)


def get_briefing_type(force_adhoc: bool = False) -> str:
    """Determine briefing type based on day of week.

    Args:
        force_adhoc: If True, return "Adhoc" regardless of day.

    Returns:
        "Monday" if today is Monday and not force_adhoc, else "Adhoc".
    """
    if force_adhoc:
        return "Adhoc"
    today = date.today()
    return "Monday" if today.weekday() == 0 else "Adhoc"


def get_period_dates() -> tuple[date, date]:
    """Get the briefing period (past 7 days).

    Returns:
        Tuple of (period_start, period_end) dates.
    """
    today = date.today()
    period_start = today - timedelta(days=7)
    return period_start, today


# Thresholds for proactive suggestions
THRESHOLDS = {
    "email_backlog": 5,          # >5 items in Needs_Action/email/
    "whatsapp_backlog": 3,       # >3 items in Needs_Action/whatsapp/
    "social_activity": 10,       # >10 posts in Done/facebook/+instagram/+x/
    "stale_plans": 3,            # >3 items in Needs_Action/plans/ >7 days
    "stale_days": 7,             # Items older than 7 days are stale
    "deadline_window": 7,        # Show deadlines within 7 days
}

# Vault directory names
VAULT_DIRS = {
    "briefings": "Briefings",
    "logs": "Logs",
    "done": "Done",
    "needs_action": "Needs_Action",
    "accounting": "Accounting",
    "goals_file": "Business_Goals.md",
}
