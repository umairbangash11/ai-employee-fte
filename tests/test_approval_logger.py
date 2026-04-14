"""Tests for hitl_approval.logger module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from hitl_approval.logger import ApprovalLogger, get_log_path


class TestGetLogPath:
    """Tests for log path generation."""

    def test_creates_approvals_directory(self, tmp_path):
        """Test that approvals directory is created."""
        logs_path = tmp_path / "Logs"
        logs_path.mkdir()

        log_path = get_log_path(logs_path)

        assert (logs_path / "approvals").exists()

    def test_returns_dated_log_file(self, tmp_path):
        """Test that log file has correct date format."""
        logs_path = tmp_path / "Logs"
        logs_path.mkdir()

        log_path = get_log_path(logs_path)

        assert log_path.name.startswith("approval-")
        assert log_path.name.endswith(".log")
        # Format: approval-YYYYMMDD.log
        assert len(log_path.name) == len("approval-20260308.log")


class TestApprovalLogger:
    """Tests for ApprovalLogger class."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp path."""
        logs_path = tmp_path / "Logs"
        logs_path.mkdir()
        return ApprovalLogger(logs_path)

    def test_log_event_creates_file(self, logger, tmp_path):
        """Test that log_event creates log file."""
        logger.log_event(
            event="created",
            file_path="Pending_Approval/email/test.md",
            actor="email_reasoner",
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        assert len(log_files) == 1

    def test_log_event_json_format(self, logger, tmp_path):
        """Test that log entries are valid JSON."""
        logger.log_event(
            event="created",
            file_path="Pending_Approval/email/test.md",
            actor="email_reasoner",
            action_type="send_email_reply",
            details={"target": "test@example.com"},
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()

        # Should be valid JSON
        entry = json.loads(content.strip())
        assert entry["event"] == "created"
        assert entry["file_path"] == "Pending_Approval/email/test.md"
        assert entry["actor"] == "email_reasoner"

    def test_log_event_has_timestamp(self, logger, tmp_path):
        """Test that log entries have timestamp."""
        logger.log_event(
            event="approved",
            file_path="Approved/email/test.md",
            actor="human",
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert "timestamp" in entry
        assert entry["timestamp"].endswith("Z")

    def test_log_approved(self, logger, tmp_path):
        """Test log_approved convenience method."""
        logger.log_approved(
            file_path="Approved/email/test.md",
            original_path="Pending_Approval/email/test.md",
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "approved"
        assert entry["actor"] == "human"
        assert entry["details"]["original_path"] == "Pending_Approval/email/test.md"

    def test_log_rejected(self, logger, tmp_path):
        """Test log_rejected convenience method."""
        logger.log_rejected(
            file_path="Rejected/email/test.md",
            original_path="Pending_Approval/email/test.md",
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "rejected"
        assert entry["actor"] == "human"

    def test_log_created(self, logger, tmp_path):
        """Test log_created convenience method."""
        logger.log_created(
            file_path="Pending_Approval/email/test.md",
            action_type="send_email_reply",
            actor="email_reasoner",
            target="test@example.com",
            subject="Re: Test",
        )

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "created"
        assert entry["action_type"] == "send_email_reply"
        assert entry["details"]["target"] == "test@example.com"

    def test_multiple_entries_appended(self, logger, tmp_path):
        """Test that multiple entries are appended to same file."""
        logger.log_event(event="created", file_path="test1.md", actor="system")
        logger.log_event(event="approved", file_path="test2.md", actor="human")
        logger.log_event(event="rejected", file_path="test3.md", actor="human")

        log_files = list((tmp_path / "Logs" / "approvals").glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3
        # Each line should be valid JSON
        for line in lines:
            json.loads(line)
