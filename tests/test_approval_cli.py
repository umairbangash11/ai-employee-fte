"""Tests for hitl_approval CLI."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from hitl_approval.__main__ import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def vault_with_approvals(tmp_path):
    """Create vault with sample approval files."""
    vault = tmp_path / "vault"

    # Create directories
    (vault / "Pending_Approval" / "email").mkdir(parents=True)
    (vault / "Pending_Approval" / "linkedin").mkdir(parents=True)
    (vault / "Approved" / "email").mkdir(parents=True)
    (vault / "Rejected" / "email").mkdir(parents=True)
    (vault / "Logs" / "approvals").mkdir(parents=True)

    # Create sample pending email
    pending_email = vault / "Pending_Approval" / "email" / "20260308-143000_send_email_reply_test.md"
    pending_email.write_text("""---
type: approval_request
action_type: send_email_reply
status: pending
created_at: "2026-03-08T14:30:00Z"
created_by: email_reasoner
target:
  recipient: "test@example.com"
  subject: "Re: Test Subject"
source:
  type: email
  path: "[[Inbox/email/test.md]]"
rollback_strategy: "Cannot unsend"
---

# Action: Re: Test Subject

Test body content.
""")

    # Create sample pending linkedin
    pending_linkedin = vault / "Pending_Approval" / "linkedin" / "20260308-150000_publish_linkedin_post_update.md"
    pending_linkedin.write_text("""---
type: approval_request
action_type: publish_linkedin_post
status: pending
created_at: "2026-03-08T15:00:00Z"
created_by: orchestrator
target:
  platform: linkedin
  post_type: text
source:
  type: task
  path: "[[Needs_Action/tasks/post.md]]"
rollback_strategy: "Delete post manually"
---

# Action: LinkedIn Post

LinkedIn post content.
""")

    return vault


class TestListCommand:
    """Tests for list command."""

    def test_list_shows_pending_approvals(self, runner, vault_with_approvals):
        """Test that list shows pending approvals."""
        result = runner.invoke(cli, ["--vault-path", str(vault_with_approvals), "list"])

        assert result.exit_code == 0
        assert "Pending approvals (2)" in result.output
        assert "send_email_reply" in result.output
        assert "publish_linkedin_post" in result.output

    def test_list_empty_state(self, runner, tmp_path):
        """Test list with no pending approvals."""
        vault = tmp_path / "empty_vault"
        vault.mkdir()
        (vault / "Pending_Approval" / "email").mkdir(parents=True)
        (vault / "Pending_Approval" / "linkedin").mkdir(parents=True)

        result = runner.invoke(cli, ["--vault-path", str(vault), "list"])

        assert result.exit_code == 0
        assert "No pending approvals" in result.output


class TestShowCommand:
    """Tests for show command."""

    def test_show_displays_approval_details(self, runner, vault_with_approvals):
        """Test that show displays approval details."""
        result = runner.invoke(
            cli,
            ["--vault-path", str(vault_with_approvals), "show", "send_email_reply_test"],
        )

        assert result.exit_code == 0
        assert "send_email_reply" in result.output
        assert "pending" in result.output
        assert "email_reasoner" in result.output

    def test_show_not_found(self, runner, vault_with_approvals):
        """Test show with non-existent approval."""
        result = runner.invoke(
            cli,
            ["--vault-path", str(vault_with_approvals), "show", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "No approval found" in result.output


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_shows_counts(self, runner, vault_with_approvals):
        """Test that stats shows correct counts."""
        result = runner.invoke(cli, ["--vault-path", str(vault_with_approvals), "stats"])

        assert result.exit_code == 0
        assert "Pending:   2" in result.output
        assert "Approved:  0" in result.output
        assert "Rejected:  0" in result.output

    def test_stats_shows_type_breakdown(self, runner, vault_with_approvals):
        """Test that stats shows type breakdown."""
        result = runner.invoke(cli, ["--vault-path", str(vault_with_approvals), "stats"])

        assert result.exit_code == 0
        assert "Email:" in result.output
        assert "LinkedIn:" in result.output


class TestVersionOption:
    """Tests for version option."""

    def test_version_displays(self, runner):
        """Test that --version displays version."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
