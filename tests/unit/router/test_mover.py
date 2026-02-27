"""Tests for file mover with claim-by-move pattern."""

from pathlib import Path
import os
import tempfile

import pytest

from router.router import MoveResult, move_file_to_needs_action


class TestMoveFileToNeedsAction:
    """Tests for move_file_to_needs_action function."""

    def test_successful_move(self, tmp_path):
        """Moves file successfully to destination."""
        # Setup
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        needs_action_dir = tmp_path / "Needs_Action" / "email"
        needs_action_dir.mkdir(parents=True)
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir(parents=True)

        source_file = inbox_dir / "test-email.md"
        source_file.write_text("Test content")

        # Execute
        result = move_file_to_needs_action(source_file, needs_action_dir, logs_dir)

        # Verify
        assert result.success is True
        assert result.claimed is False
        assert result.source == source_file
        assert result.destination is not None
        assert result.destination.exists()
        assert not source_file.exists()
        assert result.destination.read_text() == "Test content"

    def test_already_claimed(self, tmp_path):
        """Returns claimed=True when file already moved."""
        # Setup
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        needs_action_dir = tmp_path / "Needs_Action" / "email"
        needs_action_dir.mkdir(parents=True)
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir(parents=True)

        # Source file doesn't exist (already moved)
        source_file = inbox_dir / "already-moved.md"

        # Execute
        result = move_file_to_needs_action(source_file, needs_action_dir, logs_dir)

        # Verify
        assert result.success is False
        assert result.claimed is True
        assert result.destination is None

    def test_creates_destination_directory(self, tmp_path):
        """Creates destination directory if it doesn't exist."""
        # Setup
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        needs_action_dir = tmp_path / "Needs_Action" / "email"
        # Don't create needs_action_dir - it should be auto-created
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir(parents=True)

        source_file = inbox_dir / "test-email.md"
        source_file.write_text("Test content")

        # Execute
        result = move_file_to_needs_action(source_file, needs_action_dir, logs_dir)

        # Verify
        assert result.success is True
        assert needs_action_dir.exists()
        assert result.destination.exists()

    def test_handles_duplicate_filename(self, tmp_path):
        """Handles case when destination file already exists."""
        # Setup
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        needs_action_dir = tmp_path / "Needs_Action" / "email"
        needs_action_dir.mkdir(parents=True)
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir(parents=True)

        # Create file with same name in destination
        existing_file = needs_action_dir / "duplicate.md"
        existing_file.write_text("Existing content")

        source_file = inbox_dir / "duplicate.md"
        source_file.write_text("New content")

        # Execute
        result = move_file_to_needs_action(source_file, needs_action_dir, logs_dir)

        # Verify - should succeed with a different filename
        assert result.success is True
        assert result.destination is not None
        assert result.destination.exists()
        # Original file should still exist with original content
        assert existing_file.read_text() == "Existing content"
        # New file should have new content with modified name
        assert result.destination.name != "duplicate.md" or result.destination == existing_file

    def test_preserves_file_content(self, tmp_path):
        """File content is preserved after move."""
        # Setup
        inbox_dir = tmp_path / "Inbox" / "email"
        inbox_dir.mkdir(parents=True)
        needs_action_dir = tmp_path / "Needs_Action" / "email"
        needs_action_dir.mkdir(parents=True)
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir(parents=True)

        content = """---
source: gmail
captured_at: "2026-02-27T14:30:00Z"
sender: "Test User"
subject: "Test Subject"
---

This is the email body with special characters: é, ñ, 中文
"""
        source_file = inbox_dir / "test-email.md"
        source_file.write_text(content, encoding="utf-8")

        # Execute
        result = move_file_to_needs_action(source_file, needs_action_dir, logs_dir)

        # Verify
        assert result.success is True
        assert result.destination.read_text(encoding="utf-8") == content
