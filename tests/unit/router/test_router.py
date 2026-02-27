"""Integration tests for the Inbox → Needs_Action Router."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from router.config import RouterConfig
from router.router import evaluate_file, route_inbox


def create_email_file(
    path: Path,
    subject: str = "Test Subject",
    urgency: str = "normal",
    starred: bool = False,
    important: bool = False,
    body: str = "Test body content",
    captured_at: str = None,
) -> Path:
    """Helper to create test email markdown files."""
    if captured_at is None:
        captured_at = datetime.now(timezone.utc).isoformat()

    content = f"""---
source: gmail
captured_at: "{captured_at}"
sender: "test@example.com"
subject: "{subject}"
urgency: {urgency}
starred: {str(starred).lower()}
important: {str(important).lower()}
status: unread
tags: [inbox, gmail]
---

# {subject}

{body}
"""
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def router_vault(tmp_path):
    """Create a temporary vault with canonical folders."""
    (tmp_path / "Inbox" / "email").mkdir(parents=True)
    (tmp_path / "Needs_Action" / "email").mkdir(parents=True)
    (tmp_path / "Logs").mkdir(parents=True)
    return tmp_path


# ============================================================
# T028: Integration test for flag:urgent routing
# ============================================================


class TestRouteFlagUrgent:
    """T028: Integration test for routing urgent emails."""

    def test_routes_urgent_email(self, router_vault):
        """Files with urgency=urgent are routed to Needs_Action."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        # Create an urgent email
        email_file = create_email_file(
            inbox_dir / "urgent-email.md",
            subject="URGENT: Action Required",
            urgency="urgent",
        )

        # Run the router
        report = route_inbox(router_vault)

        # Verify
        assert report.total_scanned == 1
        assert report.routed_count == 1
        assert report.skipped_count == 0
        assert report.error_count == 0

        # File should be in Needs_Action
        assert not (inbox_dir / "urgent-email.md").exists()
        assert (needs_action_dir / "urgent-email.md").exists()

        # Check matched rules
        assert len(report.routed_files) == 1
        assert "flag:urgent" in report.routed_files[0].matched_rules

    def test_routes_starred_email(self, router_vault):
        """Files with starred=true are routed to Needs_Action."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        email_file = create_email_file(
            inbox_dir / "starred-email.md",
            subject="Starred Email",
            starred=True,
        )

        report = route_inbox(router_vault)

        assert report.routed_count == 1
        assert not (inbox_dir / "starred-email.md").exists()
        assert (needs_action_dir / "starred-email.md").exists()
        assert "flag:starred" in report.routed_files[0].matched_rules

    def test_routes_important_email(self, router_vault):
        """Files with important=true are routed to Needs_Action."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        email_file = create_email_file(
            inbox_dir / "important-email.md",
            subject="Important Email",
            important=True,
        )

        report = route_inbox(router_vault)

        assert report.routed_count == 1
        assert "flag:important" in report.routed_files[0].matched_rules

    def test_skips_normal_email(self, router_vault):
        """Files without flags are skipped."""
        inbox_dir = router_vault / "Inbox" / "email"

        email_file = create_email_file(
            inbox_dir / "normal-email.md",
            subject="Normal Email",
            urgency="normal",
            starred=False,
            important=False,
        )

        report = route_inbox(router_vault)

        assert report.total_scanned == 1
        assert report.routed_count == 0
        assert report.skipped_count == 1

        # File should still be in Inbox
        assert (inbox_dir / "normal-email.md").exists()


# ============================================================
# T036: Integration test for keyword routing
# ============================================================


class TestRouteKeywordMatch:
    """T036: Integration test for routing by keyword match."""

    def test_routes_keyword_in_subject(self, router_vault):
        """Files with keyword in subject are routed."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        email_file = create_email_file(
            inbox_dir / "keyword-subject.md",
            subject="URGENT: Please review this document",
            body="Regular body text",
        )

        report = route_inbox(router_vault)

        assert report.routed_count == 1
        assert "keyword:urgent" in report.routed_files[0].matched_rules

    def test_routes_keyword_in_body(self, router_vault):
        """Files with keyword in body are routed."""
        inbox_dir = router_vault / "Inbox" / "email"

        email_file = create_email_file(
            inbox_dir / "keyword-body.md",
            subject="Normal Subject",
            body="This is CRITICAL and needs immediate attention.",
        )

        report = route_inbox(router_vault)

        assert report.routed_count == 1
        assert "keyword:critical" in report.routed_files[0].matched_rules


# ============================================================
# T045: Integration test for SLA breach routing
# ============================================================


class TestRouteSLABreach:
    """T045: Integration test for routing SLA-breaching emails."""

    def test_routes_old_email(self, router_vault):
        """Files older than SLA threshold are routed."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        email_file = create_email_file(
            inbox_dir / "old-email.md",
            subject="Old Email",
            captured_at=old_time.isoformat(),
        )

        report = route_inbox(router_vault)

        assert report.routed_count == 1
        assert "sla:24h" in report.routed_files[0].matched_rules

    def test_skips_recent_email(self, router_vault):
        """Files within SLA threshold are skipped (if no other rules match)."""
        inbox_dir = router_vault / "Inbox" / "email"

        recent_time = datetime.now(timezone.utc) - timedelta(hours=12)
        email_file = create_email_file(
            inbox_dir / "recent-email.md",
            subject="Recent Email",
            captured_at=recent_time.isoformat(),
        )

        report = route_inbox(router_vault)

        assert report.skipped_count == 1


# ============================================================
# T050: Multiple rules match test
# ============================================================


class TestMultipleRulesMatch:
    """T050: Test for file matching multiple rules."""

    def test_logs_all_matched_rules(self, router_vault):
        """When multiple rules match, all are logged but file is moved once."""
        inbox_dir = router_vault / "Inbox" / "email"
        needs_action_dir = router_vault / "Needs_Action" / "email"

        email_file = create_email_file(
            inbox_dir / "multi-match.md",
            subject="URGENT: Important message",
            urgency="urgent",
            starred=True,
            important=True,
        )

        report = route_inbox(router_vault)

        # Should only be routed once
        assert report.routed_count == 1
        assert len(report.routed_files) == 1

        # But should have multiple matched rules
        matched = report.routed_files[0].matched_rules
        assert "flag:urgent" in matched
        assert "flag:starred" in matched
        assert "flag:important" in matched
        assert "keyword:urgent" in matched


# ============================================================
# T051: Malformed frontmatter test
# ============================================================


class TestMalformedFrontmatterSkipped:
    """T051: Test for graceful handling of malformed files."""

    def test_skips_malformed_file(self, router_vault):
        """Files with malformed frontmatter are skipped and logged."""
        inbox_dir = router_vault / "Inbox" / "email"

        # Create malformed file
        malformed = inbox_dir / "malformed.md"
        malformed.write_text("""---
source: gmail
sender: [broken yaml
---

Body text.
""")

        # Also create a valid file
        create_email_file(
            inbox_dir / "valid.md",
            subject="Valid Email",
            urgency="urgent",
        )

        report = route_inbox(router_vault)

        # Valid file should be processed
        assert report.routed_count == 1

        # Malformed file should be recorded as error and skipped
        assert report.error_count == 1
        assert report.skipped_count == 1
        assert len(report.errors) == 1
        assert report.errors[0].error_type == "MalformedFrontmatter"


# ============================================================
# Dry run tests
# ============================================================


class TestDryRun:
    """Tests for dry_run mode."""

    def test_dry_run_does_not_move_files(self, router_vault):
        """In dry_run mode, files are not moved."""
        inbox_dir = router_vault / "Inbox" / "email"

        email_file = create_email_file(
            inbox_dir / "urgent.md",
            subject="Urgent Email",
            urgency="urgent",
        )

        report = route_inbox(router_vault, dry_run=True)

        # Report should show what would be routed
        assert report.routed_count == 1

        # But file should still be in Inbox
        assert (inbox_dir / "urgent.md").exists()


# ============================================================
# evaluate_file tests
# ============================================================


class TestEvaluateFile:
    """Tests for evaluate_file function."""

    def test_evaluates_single_file(self, router_vault):
        """evaluate_file correctly evaluates a single file."""
        inbox_dir = router_vault / "Inbox" / "email"

        email_file = create_email_file(
            inbox_dir / "test.md",
            subject="URGENT: Test",
            urgency="urgent",
        )

        result = evaluate_file(email_file)

        assert result.should_route is True
        assert "flag:urgent" in result.matched_rules

    def test_file_not_found_raises(self, router_vault):
        """evaluate_file raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            evaluate_file(router_vault / "nonexistent.md")

    def test_non_md_file_raises(self, router_vault):
        """evaluate_file raises ValueError for non-markdown files."""
        txt_file = router_vault / "test.txt"
        txt_file.write_text("Not markdown")

        with pytest.raises(ValueError, match="not a markdown file"):
            evaluate_file(txt_file)


# ============================================================
# Edge case tests
# ============================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_inbox(self, router_vault):
        """Router handles empty inbox gracefully."""
        report = route_inbox(router_vault)

        assert report.total_scanned == 0
        assert report.routed_count == 0
        assert report.skipped_count == 0
        assert report.error_count == 0

    def test_missing_inbox_directory(self, tmp_path):
        """Router handles missing inbox directory gracefully."""
        # Create vault without Inbox
        (tmp_path / "Needs_Action" / "email").mkdir(parents=True)

        report = route_inbox(tmp_path)

        assert report.total_scanned == 0

    def test_invalid_vault_path_raises(self):
        """Router raises ValueError for non-existent vault."""
        with pytest.raises(ValueError, match="does not exist"):
            route_inbox("/nonexistent/vault/path")

    def test_creates_needs_action_directory(self, tmp_path):
        """Router creates Needs_Action directory if it doesn't exist."""
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        (tmp_path / "Logs").mkdir(parents=True)
        # Don't create Needs_Action

        create_email_file(
            inbox_dir / "urgent.md",
            subject="Urgent",
            urgency="urgent",
        )

        report = route_inbox(tmp_path)

        assert report.routed_count == 1
        assert (tmp_path / "Needs_Action" / "email" / "urgent.md").exists()
