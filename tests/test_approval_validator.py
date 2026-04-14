"""Tests for hitl_approval.validator module."""

from pathlib import Path

import pytest

from hitl_approval.validator import (
    parse_approval_file,
    validate_frontmatter,
    get_approval_summary,
)


class TestParseApprovalFile:
    """Tests for approval file parsing."""

    def test_parses_valid_file(self, tmp_path):
        """Test parsing a valid approval file."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
type: approval_request
action_type: send_email_reply
status: pending
created_at: "2026-03-08T14:30:00Z"
created_by: email_reasoner
target:
  recipient: "test@example.com"
  subject: "Re: Test"
source:
  type: email
  path: "[[Inbox/email/test.md]]"
rollback_strategy: "Cannot unsend"
---

# Action: Re: Test

This is the body.
""")

        result = parse_approval_file(file_path)

        assert result is not None
        assert result["frontmatter"]["type"] == "approval_request"
        assert result["frontmatter"]["action_type"] == "send_email_reply"
        assert "This is the body" in result["body"]

    def test_returns_none_for_missing_file(self, tmp_path):
        """Test that missing file returns None."""
        file_path = tmp_path / "missing.md"
        result = parse_approval_file(file_path)
        assert result is None

    def test_returns_none_for_missing_frontmatter(self, tmp_path):
        """Test that file without frontmatter returns None."""
        file_path = tmp_path / "no_frontmatter.md"
        file_path.write_text("Just some text without frontmatter")

        result = parse_approval_file(file_path)
        assert result is None

    def test_returns_none_for_invalid_yaml(self, tmp_path):
        """Test that invalid YAML returns None."""
        file_path = tmp_path / "invalid.md"
        file_path.write_text("""---
this is not: valid: yaml: at: all
  - broken indent
---
Body
""")

        result = parse_approval_file(file_path)
        assert result is None


class TestValidateFrontmatter:
    """Tests for frontmatter validation."""

    def test_valid_frontmatter(self):
        """Test validation passes for valid frontmatter."""
        data = {
            "type": "approval_request",
            "action_type": "send_email_reply",
            "status": "pending",
            "created_at": "2026-03-08T14:30:00Z",
            "created_by": "email_reasoner",
            "target": {"recipient": "test@example.com"},
            "source": {"type": "email", "path": "test.md"},
            "rollback_strategy": "Cannot unsend",
        }
        assert validate_frontmatter(data) is True

    def test_invalid_type(self):
        """Test validation fails for wrong type."""
        data = {
            "type": "wrong_type",
            "action_type": "send_email_reply",
            "status": "pending",
            "created_at": "2026-03-08T14:30:00Z",
            "created_by": "email_reasoner",
            "target": {"recipient": "test@example.com"},
            "source": {"type": "email"},
            "rollback_strategy": "Cannot unsend",
        }
        assert validate_frontmatter(data) is False

    def test_invalid_action_type(self):
        """Test validation fails for invalid action_type."""
        data = {
            "type": "approval_request",
            "action_type": "invalid_action",
            "status": "pending",
            "created_at": "2026-03-08T14:30:00Z",
            "created_by": "email_reasoner",
            "target": {"recipient": "test@example.com"},
            "source": {"type": "email"},
            "rollback_strategy": "Cannot unsend",
        }
        assert validate_frontmatter(data) is False

    def test_missing_required_field(self):
        """Test validation fails for missing required field."""
        data = {
            "type": "approval_request",
            "action_type": "send_email_reply",
            # Missing: status, created_at, etc.
        }
        assert validate_frontmatter(data) is False

    def test_empty_rollback_strategy(self):
        """Test validation fails for empty rollback_strategy."""
        data = {
            "type": "approval_request",
            "action_type": "send_email_reply",
            "status": "pending",
            "created_at": "2026-03-08T14:30:00Z",
            "created_by": "email_reasoner",
            "target": {"recipient": "test@example.com"},
            "source": {"type": "email"},
            "rollback_strategy": "",  # Empty
        }
        assert validate_frontmatter(data) is False


class TestGetApprovalSummary:
    """Tests for summary extraction."""

    def test_extracts_summary(self):
        """Test summary extraction from parsed file."""
        parsed = {
            "filename": "test.md",
            "frontmatter": {
                "action_type": "send_email_reply",
                "status": "pending",
                "created_at": "2026-03-08T14:30:00Z",
                "created_by": "email_reasoner",
                "target": {
                    "recipient": "test@example.com",
                    "subject": "Re: Test",
                },
            },
            "body": "Body content",
        }

        summary = get_approval_summary(parsed)

        assert summary["filename"] == "test.md"
        assert summary["action_type"] == "send_email_reply"
        assert summary["target"] == "test@example.com"
        assert summary["subject"] == "Re: Test"

    def test_handles_linkedin_target(self):
        """Test summary extraction for LinkedIn target."""
        parsed = {
            "filename": "linkedin.md",
            "frontmatter": {
                "action_type": "publish_linkedin_post",
                "status": "pending",
                "target": {
                    "platform": "linkedin",
                },
            },
            "body": "",
        }

        summary = get_approval_summary(parsed)
        assert summary["target"] == "linkedin"
