"""Tests for email_reasoner.state module."""

import json
from pathlib import Path

import pytest

from email_reasoner.state import (
    load_state,
    save_state,
    is_processed,
    mark_processed,
    ensure_state_directory,
)
from email_reasoner.models import ReasonerState


class TestLoadState:
    """Tests for load_state function."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty state."""
        state_path = tmp_path / ".watcher-state" / "reasoner.json"

        result = load_state(state_path)

        assert isinstance(result, ReasonerState)
        assert result.version == 1
        assert result.last_run is None
        assert len(result.processed) == 0

    def test_load_valid_state_file(self, tmp_path):
        """Test loading from a valid state file."""
        state_dir = tmp_path / ".watcher-state"
        state_dir.mkdir(parents=True)
        state_path = state_dir / "reasoner.json"

        state_data = {
            "version": 1,
            "last_run": "2026-03-07T10:00:00Z",
            "processed": {
                "msg_123": {
                    "classified_at": "2026-03-07T10:00:00Z",
                    "classification": "actionable",
                    "task_file": "Needs_Action/tasks/task_123.md"
                }
            }
        }
        state_path.write_text(json.dumps(state_data))

        result = load_state(state_path)

        assert result.version == 1
        assert result.last_run == "2026-03-07T10:00:00Z"
        assert len(result.processed) == 1
        assert "msg_123" in result.processed

    def test_load_corrupt_file(self, tmp_path):
        """Test loading from corrupt file returns empty state."""
        state_dir = tmp_path / ".watcher-state"
        state_dir.mkdir(parents=True)
        state_path = state_dir / "reasoner.json"
        state_path.write_text("not valid json {{{")

        result = load_state(state_path)

        assert isinstance(result, ReasonerState)
        assert len(result.processed) == 0


class TestSaveState:
    """Tests for save_state function."""

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory if missing."""
        state_path = tmp_path / ".watcher-state" / "reasoner.json"
        state = ReasonerState()

        save_state(state, state_path)

        assert state_path.parent.exists()
        assert state_path.exists()

    def test_save_state_content(self, tmp_path):
        """Test that saved state contains correct data."""
        state_dir = tmp_path / ".watcher-state"
        state_dir.mkdir(parents=True)
        state_path = state_dir / "reasoner.json"

        state = ReasonerState()
        state.mark_processed("msg_abc", "promotional", None)

        save_state(state, state_path)

        saved_data = json.loads(state_path.read_text())
        assert saved_data["version"] == 1
        assert "msg_abc" in saved_data["processed"]
        assert saved_data["processed"]["msg_abc"]["classification"] == "promotional"


class TestIsProcessed:
    """Tests for is_processed function."""

    def test_is_processed_true(self):
        """Test is_processed returns True for processed email."""
        state = ReasonerState()
        state.mark_processed("existing_msg", "actionable", "task.md")

        result = is_processed(state, "existing_msg")

        assert result is True

    def test_is_processed_false(self):
        """Test is_processed returns False for new email."""
        state = ReasonerState()

        result = is_processed(state, "new_msg")

        assert result is False


class TestMarkProcessed:
    """Tests for mark_processed function."""

    def test_mark_processed_with_task(self):
        """Test marking email as processed with task file."""
        state = ReasonerState()

        mark_processed(state, "msg_123", "actionable", "Needs_Action/tasks/task.md")

        assert "msg_123" in state.processed
        assert state.processed["msg_123"].classification == "actionable"
        assert state.processed["msg_123"].task_file == "Needs_Action/tasks/task.md"

    def test_mark_processed_without_task(self):
        """Test marking email as processed without task file."""
        state = ReasonerState()

        mark_processed(state, "msg_456", "promotional", None)

        assert "msg_456" in state.processed
        assert state.processed["msg_456"].classification == "promotional"
        assert state.processed["msg_456"].task_file is None

    def test_mark_processed_updates_last_run(self):
        """Test that marking updates last_run timestamp."""
        state = ReasonerState()
        assert state.last_run is None

        mark_processed(state, "msg_789", "informational", None)

        assert state.last_run is not None


class TestEnsureStateDirectory:
    """Tests for ensure_state_directory function."""

    def test_creates_directory(self, tmp_path):
        """Test that directory is created if missing."""
        state_dir = tmp_path / ".watcher-state"
        assert not state_dir.exists()

        ensure_state_directory(state_dir)

        assert state_dir.exists()
        assert state_dir.is_dir()

    def test_existing_directory_no_error(self, tmp_path):
        """Test that existing directory doesn't cause error."""
        state_dir = tmp_path / ".watcher-state"
        state_dir.mkdir(parents=True)

        # Should not raise
        ensure_state_directory(state_dir)

        assert state_dir.exists()
