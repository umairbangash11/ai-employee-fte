"""Tests for hitl_approval.state module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from hitl_approval.models import ApprovalState
from hitl_approval.state import (
    load_approval_state,
    save_approval_state,
    is_duplicate,
    add_hash,
)


class TestLoadApprovalState:
    """Tests for state loading."""

    def test_returns_empty_state_if_file_missing(self, tmp_path):
        """Test that missing file returns empty state."""
        state_path = tmp_path / "missing.json"
        state = load_approval_state(state_path)

        assert len(state.created_hashes) == 0
        assert state.last_updated is None

    def test_loads_existing_state(self, tmp_path):
        """Test that existing state is loaded correctly."""
        state_path = tmp_path / "state.json"
        state_data = {
            "created_hashes": ["abc123", "def456"],
            "last_updated": "2026-03-08T14:30:00",
        }
        with open(state_path, "w") as f:
            json.dump(state_data, f)

        state = load_approval_state(state_path)

        assert "abc123" in state.created_hashes
        assert "def456" in state.created_hashes
        assert state.last_updated is not None

    def test_handles_corrupted_json(self, tmp_path):
        """Test that corrupted JSON returns empty state."""
        state_path = tmp_path / "corrupt.json"
        with open(state_path, "w") as f:
            f.write("not valid json {{{")

        state = load_approval_state(state_path)

        assert len(state.created_hashes) == 0


class TestSaveApprovalState:
    """Tests for state saving."""

    def test_saves_state_to_file(self, tmp_path):
        """Test that state is saved correctly."""
        state_path = tmp_path / "state.json"
        state = ApprovalState(
            created_hashes={"abc123", "def456"},
        )

        save_approval_state(state, state_path)

        assert state_path.exists()
        with open(state_path) as f:
            data = json.load(f)
        assert "abc123" in data["created_hashes"]
        assert "def456" in data["created_hashes"]

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created if missing."""
        state_path = tmp_path / "subdir" / "state.json"
        state = ApprovalState()

        save_approval_state(state, state_path)

        assert state_path.exists()
        assert (tmp_path / "subdir").is_dir()

    def test_updates_last_updated(self, tmp_path):
        """Test that last_updated is set on save."""
        state_path = tmp_path / "state.json"
        state = ApprovalState()
        assert state.last_updated is None

        save_approval_state(state, state_path)

        assert state.last_updated is not None


class TestIsDuplicate:
    """Tests for duplicate detection."""

    def test_returns_false_for_new_hash(self):
        """Test that new hash is not a duplicate."""
        state = ApprovalState()
        assert is_duplicate(state, "new_hash") is False

    def test_returns_true_for_existing_hash(self):
        """Test that existing hash is a duplicate."""
        state = ApprovalState(created_hashes={"existing_hash"})
        assert is_duplicate(state, "existing_hash") is True

    def test_returns_false_after_different_hash_added(self):
        """Test that different hash is not a duplicate."""
        state = ApprovalState(created_hashes={"hash1"})
        assert is_duplicate(state, "hash2") is False


class TestAddHash:
    """Tests for adding hashes to state."""

    def test_adds_hash_to_state(self):
        """Test that hash is added to state."""
        state = ApprovalState()
        add_hash(state, "new_hash")

        assert "new_hash" in state.created_hashes

    def test_adding_duplicate_is_idempotent(self):
        """Test that adding same hash twice doesn't create duplicates."""
        state = ApprovalState()
        add_hash(state, "hash1")
        add_hash(state, "hash1")

        assert len(state.created_hashes) == 1
