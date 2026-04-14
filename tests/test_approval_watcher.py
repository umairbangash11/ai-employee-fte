"""Tests for hitl_approval.watcher module."""

import json
import time
from pathlib import Path

import pytest

from hitl_approval.watcher import ApprovalWatcher, ApprovalEventHandler
from hitl_approval.logger import ApprovalLogger


class TestApprovalEventHandler:
    """Tests for ApprovalEventHandler class."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with temp vault."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        logs_path = vault_path / "Logs"
        logs_path.mkdir()
        logger = ApprovalLogger(logs_path)
        return ApprovalEventHandler(vault_path, logger)

    def test_is_approved_path_positive(self, handler):
        """Test _is_approved_path returns True for Approved paths."""
        assert handler._is_approved_path("/vault/Approved/email/test.md") is True
        assert handler._is_approved_path("/vault/Approved/linkedin/test.md") is True

    def test_is_approved_path_negative(self, handler):
        """Test _is_approved_path returns False for non-Approved paths."""
        assert handler._is_approved_path("/vault/Pending_Approval/email/test.md") is False
        assert handler._is_approved_path("/vault/Inbox/email/test.md") is False

    def test_is_rejected_path_positive(self, handler):
        """Test _is_rejected_path returns True for Rejected paths."""
        assert handler._is_rejected_path("/vault/Rejected/email/test.md") is True
        assert handler._is_rejected_path("/vault/Rejected/linkedin/test.md") is True

    def test_is_rejected_path_negative(self, handler):
        """Test _is_rejected_path returns False for non-Rejected paths."""
        assert handler._is_rejected_path("/vault/Approved/email/test.md") is False
        assert handler._is_rejected_path("/vault/Pending_Approval/email/test.md") is False

    def test_is_pending_approval_path_positive(self, handler):
        """Test _is_pending_approval_path returns True for Pending paths."""
        assert handler._is_pending_approval_path("/vault/Pending_Approval/email/test.md") is True

    def test_is_pending_approval_path_negative(self, handler):
        """Test _is_pending_approval_path returns False for non-Pending paths."""
        assert handler._is_pending_approval_path("/vault/Approved/email/test.md") is False


class TestApprovalWatcher:
    """Tests for ApprovalWatcher class."""

    @pytest.fixture
    def vault_path(self, tmp_path):
        """Create temp vault structure."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Logs").mkdir()
        return vault

    def test_start_creates_directories(self, vault_path):
        """Test that start() creates watch directories."""
        watcher = ApprovalWatcher(vault_path)
        watcher.start()

        try:
            assert (vault_path / "Pending_Approval" / "email").exists()
            assert (vault_path / "Pending_Approval" / "linkedin").exists()
            assert (vault_path / "Approved" / "email").exists()
            assert (vault_path / "Approved" / "linkedin").exists()
            assert (vault_path / "Rejected" / "email").exists()
            assert (vault_path / "Rejected" / "linkedin").exists()
        finally:
            watcher.stop()

    def test_is_running(self, vault_path):
        """Test is_running property."""
        watcher = ApprovalWatcher(vault_path)

        assert watcher.is_running is False

        watcher.start()
        assert watcher.is_running is True

        watcher.stop()
        assert watcher.is_running is False

    def test_stop_is_idempotent(self, vault_path):
        """Test that stop() can be called multiple times."""
        watcher = ApprovalWatcher(vault_path)
        watcher.start()
        watcher.stop()
        watcher.stop()  # Should not raise

    def test_start_is_idempotent(self, vault_path):
        """Test that start() can be called multiple times."""
        watcher = ApprovalWatcher(vault_path)
        watcher.start()
        watcher.start()  # Should not raise or start second observer

        try:
            assert watcher.is_running is True
        finally:
            watcher.stop()


class TestApprovalWatcherIntegration:
    """Integration tests for watcher detecting file moves."""

    @pytest.fixture
    def vault_path(self, tmp_path):
        """Create temp vault structure."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Logs").mkdir()
        return vault

    def test_detects_file_move_to_approved(self, vault_path):
        """Test that moving file to Approved creates log entry."""
        watcher = ApprovalWatcher(vault_path)
        watcher.start()

        try:
            # Create directories
            pending_dir = vault_path / "Pending_Approval" / "email"
            approved_dir = vault_path / "Approved" / "email"
            pending_dir.mkdir(parents=True, exist_ok=True)
            approved_dir.mkdir(parents=True, exist_ok=True)

            # Simulate file move by creating in Approved
            test_file = approved_dir / "test_approval.md"
            test_file.write_text("---\ntype: approval_request\n---\n")

            # Give watcher time to process
            time.sleep(0.5)

            # Check log
            log_files = list((vault_path / "Logs" / "approvals").glob("*.log"))
            assert len(log_files) == 1

            content = log_files[0].read_text()
            entry = json.loads(content.strip())
            assert entry["event"] == "approved"
        finally:
            watcher.stop()

    def test_detects_file_move_to_rejected(self, vault_path):
        """Test that moving file to Rejected creates log entry."""
        watcher = ApprovalWatcher(vault_path)
        watcher.start()

        try:
            # Create directories
            rejected_dir = vault_path / "Rejected" / "linkedin"
            rejected_dir.mkdir(parents=True, exist_ok=True)

            # Simulate file move by creating in Rejected
            test_file = rejected_dir / "test_rejection.md"
            test_file.write_text("---\ntype: approval_request\n---\n")

            # Give watcher time to process
            time.sleep(0.5)

            # Check log
            log_files = list((vault_path / "Logs" / "approvals").glob("*.log"))
            assert len(log_files) == 1

            content = log_files[0].read_text()
            entry = json.loads(content.strip())
            assert entry["event"] == "rejected"
        finally:
            watcher.stop()
