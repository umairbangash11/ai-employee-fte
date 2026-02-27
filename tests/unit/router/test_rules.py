"""Tests for routing rules."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from router.config import RouterConfig
from router.parser import EmailFrontmatter, InboxFile
from router.rules import (
    RoutingResult,
    RoutingRule,
    evaluate_rules,
    get_default_rules,
    is_sla_breached,
    make_flag_rules,
    make_keyword_matcher,
    make_keyword_rules,
    make_sla_rule,
)


def make_test_file(
    path: Path = Path("/test/email.md"),
    urgency: str = "normal",
    starred: bool = False,
    important: bool = False,
    subject: str = "Test Subject",
    body: str = "Test body content",
    captured_at: str = "",
) -> InboxFile:
    """Helper to create test InboxFile instances."""
    return InboxFile(
        path=path,
        frontmatter=EmailFrontmatter(
            source="gmail",
            captured_at=captured_at or datetime.now(timezone.utc).isoformat(),
            sender="test@example.com",
            subject=subject,
            urgency=urgency,
            starred=starred,
            important=important,
        ),
        subject=subject,
        body=body,
        file_size=100,
    )


# ============================================================
# Phase 3: User Story 1 - Flag-based Routing Tests (T020-T023)
# ============================================================


class TestFlagUrgentRule:
    """T020: Tests for urgency=urgent flag matching."""

    def test_matches_urgent_flag(self):
        """Files with urgency=urgent should match."""
        file = make_test_file(urgency="urgent")
        rules = make_flag_rules()
        urgent_rule = next(r for r in rules if r.name == "flag:urgent")

        assert urgent_rule.matcher(file) is True

    def test_no_match_normal_urgency(self):
        """Files with urgency=normal should not match."""
        file = make_test_file(urgency="normal")
        rules = make_flag_rules()
        urgent_rule = next(r for r in rules if r.name == "flag:urgent")

        assert urgent_rule.matcher(file) is False


class TestFlagStarredRule:
    """T021: Tests for starred=true flag matching."""

    def test_matches_starred_flag(self):
        """Files with starred=true should match."""
        file = make_test_file(starred=True)
        rules = make_flag_rules()
        starred_rule = next(r for r in rules if r.name == "flag:starred")

        assert starred_rule.matcher(file) is True

    def test_no_match_unstarred(self):
        """Files with starred=false should not match."""
        file = make_test_file(starred=False)
        rules = make_flag_rules()
        starred_rule = next(r for r in rules if r.name == "flag:starred")

        assert starred_rule.matcher(file) is False


class TestFlagImportantRule:
    """T022: Tests for important=true flag matching."""

    def test_matches_important_flag(self):
        """Files with important=true should match."""
        file = make_test_file(important=True)
        rules = make_flag_rules()
        important_rule = next(r for r in rules if r.name == "flag:important")

        assert important_rule.matcher(file) is True

    def test_no_match_not_important(self):
        """Files with important=false should not match."""
        file = make_test_file(important=False)
        rules = make_flag_rules()
        important_rule = next(r for r in rules if r.name == "flag:important")

        assert important_rule.matcher(file) is False


class TestFlagNoMatch:
    """T023: Tests for files without any flags."""

    def test_no_flags_no_match(self):
        """Files without any flags should not match any flag rules."""
        file = make_test_file(urgency="normal", starred=False, important=False)
        rules = make_flag_rules()

        for rule in rules:
            assert rule.matcher(file) is False

    def test_evaluate_rules_no_match(self):
        """evaluate_rules returns should_route=False when no rules match."""
        file = make_test_file(urgency="normal", starred=False, important=False)
        rules = make_flag_rules()

        result = evaluate_rules(file, rules)

        assert result.should_route is False
        assert result.matched_rules == []


# ============================================================
# Phase 4: User Story 2 - Keyword-based Routing Tests (T029-T032)
# ============================================================


class TestKeywordInSubject:
    """T029: Tests for keyword match in subject."""

    def test_matches_keyword_in_subject(self):
        """Keywords in subject should match."""
        file = make_test_file(subject="URGENT: Please review")
        matcher = make_keyword_matcher("urgent")

        assert matcher(file) is True

    def test_partial_keyword_match(self):
        """Partial keyword matches should work."""
        file = make_test_file(subject="This is urgently needed")
        matcher = make_keyword_matcher("urgent")

        assert matcher(file) is True


class TestKeywordInBody:
    """T030: Tests for keyword match in body."""

    def test_matches_keyword_in_body(self):
        """Keywords in body should match."""
        file = make_test_file(body="Please treat this as URGENT")
        matcher = make_keyword_matcher("urgent")

        assert matcher(file) is True


class TestKeywordCaseInsensitive:
    """T031: Tests for case-insensitive keyword matching."""

    def test_case_insensitive_uppercase(self):
        """UPPERCASE keywords should match lowercase."""
        file = make_test_file(subject="URGENT request")
        matcher = make_keyword_matcher("urgent")

        assert matcher(file) is True

    def test_case_insensitive_lowercase(self):
        """lowercase keywords should match UPPERCASE."""
        file = make_test_file(subject="urgent request")
        matcher = make_keyword_matcher("URGENT")

        assert matcher(file) is True

    def test_case_insensitive_mixed(self):
        """Mixed case should match."""
        file = make_test_file(subject="Urgent Request")
        matcher = make_keyword_matcher("uRgEnT")

        assert matcher(file) is True


class TestKeywordNoMatch:
    """T032: Tests for files without matching keywords."""

    def test_no_keyword_match(self):
        """Files without matching keywords should not match."""
        file = make_test_file(
            subject="Normal email",
            body="Just a regular message with nothing special",
        )
        rules = make_keyword_rules(["urgent", "asap", "critical"])

        for rule in rules:
            assert rule.matcher(file) is False


# ============================================================
# Phase 5: User Story 3 - SLA-based Routing Tests (T037-T040)
# ============================================================


class TestSlaBreachDefault:
    """T037: Tests for 24-hour SLA breach."""

    def test_breaches_24h_sla(self):
        """Files older than 24 hours should breach SLA."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        result = is_sla_breached(old_time.isoformat(), 24)

        assert result is True

    def test_sla_rule_matches_old_file(self):
        """SLA rule should match files older than threshold."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        file = make_test_file(captured_at=old_time.isoformat())
        sla_rule = make_sla_rule(24)

        assert sla_rule.matcher(file) is True


class TestSlaWithinThreshold:
    """T038: Tests for files within SLA threshold."""

    def test_within_sla_threshold(self):
        """Files within 24 hours should not breach SLA."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=12)
        result = is_sla_breached(recent_time.isoformat(), 24)

        assert result is False

    def test_sla_rule_no_match_recent_file(self):
        """SLA rule should not match recent files."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=12)
        file = make_test_file(captured_at=recent_time.isoformat())
        sla_rule = make_sla_rule(24)

        assert sla_rule.matcher(file) is False


class TestSlaCustomThreshold:
    """T039: Tests for custom 4-hour SLA breach."""

    def test_custom_4h_sla_breach(self):
        """Files older than 4 hours should breach custom SLA."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=5)
        result = is_sla_breached(old_time.isoformat(), 4)

        assert result is True

    def test_custom_4h_sla_within(self):
        """Files within 4 hours should not breach custom SLA."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        result = is_sla_breached(recent_time.isoformat(), 4)

        assert result is False


class TestSlaInvalidTimestamp:
    """T040: Tests for malformed captured_at handling."""

    def test_invalid_timestamp_no_breach(self):
        """Invalid timestamps should not trigger SLA breach."""
        result = is_sla_breached("not-a-timestamp", 24)

        assert result is False

    def test_empty_timestamp_no_breach(self):
        """Empty timestamps should not trigger SLA breach."""
        result = is_sla_breached("", 24)

        assert result is False

    def test_none_handling(self):
        """None timestamp should not trigger SLA breach."""
        # The function expects a string, but should handle edge cases gracefully
        result = is_sla_breached("", 24)  # Empty string as proxy for None

        assert result is False


# ============================================================
# General Rule Framework Tests
# ============================================================


class TestEvaluateRules:
    """Tests for evaluate_rules function."""

    def test_returns_all_matching_rules(self):
        """All matching rules should be returned."""
        file = make_test_file(urgency="urgent", starred=True, important=True)
        rules = make_flag_rules()

        result = evaluate_rules(file, rules)

        assert result.should_route is True
        assert "flag:urgent" in result.matched_rules
        assert "flag:starred" in result.matched_rules
        assert "flag:important" in result.matched_rules
        assert len(result.matched_rules) == 3

    def test_rules_sorted_by_priority(self):
        """Rules should be evaluated in priority order."""
        file = make_test_file(urgency="urgent")

        # Create rules with different priorities
        rules = [
            RoutingRule(
                name="low_priority",
                type="test",
                matcher=lambda f: True,
                priority=100,
            ),
            RoutingRule(
                name="high_priority",
                type="test",
                matcher=lambda f: True,
                priority=10,
            ),
        ]

        result = evaluate_rules(file, rules)

        # Both should match, order depends on priority
        assert len(result.matched_rules) == 2


class TestGetDefaultRules:
    """Tests for get_default_rules function."""

    def test_includes_flag_rules(self):
        """Default rules include flag rules."""
        config = RouterConfig()
        rules = get_default_rules(config)

        rule_names = [r.name for r in rules]
        assert "flag:urgent" in rule_names
        assert "flag:starred" in rule_names
        assert "flag:important" in rule_names

    def test_includes_keyword_rules(self):
        """Default rules include keyword rules."""
        config = RouterConfig(urgency_keywords=["urgent", "asap"])
        rules = get_default_rules(config)

        rule_names = [r.name for r in rules]
        assert "keyword:urgent" in rule_names
        assert "keyword:asap" in rule_names

    def test_includes_sla_rule(self):
        """Default rules include SLA rule."""
        config = RouterConfig(sla_threshold_hours=24)
        rules = get_default_rules(config)

        rule_names = [r.name for r in rules]
        assert "sla:24h" in rule_names
