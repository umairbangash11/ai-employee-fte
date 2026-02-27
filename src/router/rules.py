"""Routing rules for email triage.

Defines rule types and evaluation logic for determining which files
should be routed from /Inbox/email/ to /Needs_Action/email/.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from router.config import RouterConfig
from router.parser import InboxFile


@dataclass
class RoutingRule:
    """A rule that determines if a file should be routed.

    Attributes:
        name: Human-readable rule identifier (e.g., "flag:urgent")
        type: Category of rule (flag, keyword, sla)
        matcher: Function (InboxFile) -> bool
        priority: Rule evaluation order (lower = earlier)
    """

    name: str
    type: str  # "flag", "keyword", "sla"
    matcher: Callable[[InboxFile], bool]
    priority: int = 100


@dataclass
class RoutingResult:
    """Result of routing evaluation for a single file.

    Attributes:
        file: The evaluated file
        should_route: True if file matches any routing rule
        matched_rules: Names of rules that matched
        destination: Target path in /Needs_Action/email/
    """

    file: InboxFile
    should_route: bool
    matched_rules: list[str] = field(default_factory=list)
    destination: Path | None = None


def evaluate_rules(file: InboxFile, rules: list[RoutingRule]) -> RoutingResult:
    """Evaluate a file against all routing rules.

    All rules are evaluated (not short-circuit) to capture all matches for logging.

    Args:
        file: The InboxFile to evaluate
        rules: List of routing rules to check

    Returns:
        RoutingResult with all matched rules
    """
    matched_rules: list[str] = []

    # Sort rules by priority
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        try:
            if rule.matcher(file):
                matched_rules.append(rule.name)
        except Exception:
            # Rule evaluation failed - skip this rule
            # Could log this for debugging
            pass

    should_route = len(matched_rules) > 0

    return RoutingResult(
        file=file,
        should_route=should_route,
        matched_rules=matched_rules,
        destination=None,  # Set by caller if routing
    )


def get_default_rules(config: RouterConfig) -> list[RoutingRule]:
    """Build the default routing rule set.

    Rules (in evaluation order):
    1. Flag rules (urgency=urgent, starred=true, important=true)
    2. Keyword rules (configurable keyword list)
    3. SLA rule (captured_at exceeds threshold)

    Args:
        config: RouterConfig with keywords and SLA threshold

    Returns:
        List of RoutingRule objects
    """
    rules: list[RoutingRule] = []

    # Add flag rules (priority 10)
    rules.extend(make_flag_rules())

    # Add keyword rules (priority 50)
    rules.extend(make_keyword_rules(config.urgency_keywords))

    # Add SLA rule (priority 100)
    rules.append(make_sla_rule(config.sla_threshold_hours))

    return rules


def make_flag_rules() -> list[RoutingRule]:
    """Create rules for flag-based routing.

    Returns:
        List of flag rules for urgency, starred, important
    """
    return [
        RoutingRule(
            name="flag:urgent",
            type="flag",
            matcher=lambda f: f.frontmatter.urgency == "urgent",
            priority=10,
        ),
        RoutingRule(
            name="flag:starred",
            type="flag",
            matcher=lambda f: f.frontmatter.starred is True,
            priority=10,
        ),
        RoutingRule(
            name="flag:important",
            type="flag",
            matcher=lambda f: f.frontmatter.important is True,
            priority=10,
        ),
    ]


def make_keyword_matcher(keyword: str) -> Callable[[InboxFile], bool]:
    """Create a matcher function for a keyword.

    Case-insensitive search in subject and body.

    Args:
        keyword: The keyword to search for

    Returns:
        Matcher function (InboxFile) -> bool
    """
    kw_lower = keyword.lower()

    def matcher(file: InboxFile) -> bool:
        text = f"{file.subject} {file.body}".lower()
        return kw_lower in text

    return matcher


def make_keyword_rules(keywords: list[str]) -> list[RoutingRule]:
    """Create rules for keyword-based routing.

    Args:
        keywords: List of keywords to match

    Returns:
        List of keyword rules
    """
    return [
        RoutingRule(
            name=f"keyword:{kw}",
            type="keyword",
            matcher=make_keyword_matcher(kw),
            priority=50,
        )
        for kw in keywords
    ]


def is_sla_breached(captured_at: str, threshold_hours: int) -> bool:
    """Check if captured_at timestamp exceeds SLA threshold.

    Args:
        captured_at: ISO 8601 datetime string
        threshold_hours: Hours before SLA breach

    Returns:
        True if SLA is breached, False otherwise
    """
    from datetime import datetime, timezone

    if not captured_at:
        return False

    try:
        # Parse ISO 8601 timestamp
        captured_dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))

        # Get current time in UTC
        now = datetime.now(timezone.utc)

        # Calculate age in hours
        age = now - captured_dt
        age_hours = age.total_seconds() / 3600

        return age_hours > threshold_hours
    except (ValueError, TypeError):
        # Invalid timestamp format - don't trigger SLA
        return False


def make_sla_matcher(threshold_hours: int) -> Callable[[InboxFile], bool]:
    """Create a matcher function for SLA breach.

    Args:
        threshold_hours: Hours before SLA breach

    Returns:
        Matcher function (InboxFile) -> bool
    """

    def matcher(file: InboxFile) -> bool:
        return is_sla_breached(file.frontmatter.captured_at, threshold_hours)

    return matcher


def make_sla_rule(threshold_hours: int) -> RoutingRule:
    """Create rule for SLA-based routing.

    Args:
        threshold_hours: Hours before SLA breach

    Returns:
        SLA routing rule
    """
    return RoutingRule(
        name=f"sla:{threshold_hours}h",
        type="sla",
        matcher=make_sla_matcher(threshold_hours),
        priority=100,
    )
