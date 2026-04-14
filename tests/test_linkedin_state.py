"""Tests for LinkedIn publisher state management."""

import pytest
import json
from datetime import datetime
from pathlib import Path

from linkedin_publisher.state import (
    load_execution_state,
    save_execution_state,
    compute_content_hash,
    is_duplicate,
    add_processed_hash,
)
from linkedin_publisher.models import ExecutionState


class TestLoadExecutionState:
    """Tests for load_execution_state function."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty state."""
        state_path = tmp_path / "publisher.json"

        state = load_execution_state(state_path)

        assert state.processed_hashes == set()
        assert state.total_published == 0

    def test_load_valid_file(self, tmp_path):
        """Test loading from valid JSON file."""
        state_path = tmp_path / "publisher.json"
        state_path.write_text(json.dumps({
            "processed_hashes": ["abc123", "def456"],
            "last_run": "2026-03-12T10:00:00Z",
            "total_published": 10,
            "total_failed": 2,
        }))

        state = load_execution_state(state_path)

        assert len(state.processed_hashes) == 2
        assert "abc123" in state.processed_hashes
        assert state.total_published == 10

    def test_load_corrupted_file(self, tmp_path):
        """Test loading from corrupted file returns empty state."""
        state_path = tmp_path / "publisher.json"
        state_path.write_text("not valid json {{{")

        state = load_execution_state(state_path)

        assert state.processed_hashes == set()


class TestSaveExecutionState:
    """Tests for save_execution_state function."""

    def test_save_creates_file(self, tmp_path):
        """Test saving creates file with state."""
        state_path = tmp_path / "subdir" / "publisher.json"
        state = ExecutionState(
            processed_hashes={"abc123"},
            total_published=5,
        )

        save_execution_state(state, state_path)

        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert "abc123" in data["processed_hashes"]
        assert data["total_published"] == 5

    def test_save_updates_last_run(self, tmp_path):
        """Test saving updates last_run timestamp."""
        state_path = tmp_path / "publisher.json"
        state = ExecutionState()

        save_execution_state(state, state_path)

        data = json.loads(state_path.read_text())
        assert data["last_run"] is not None

    def test_save_creates_parent_dirs(self, tmp_path):
        """Test saving creates parent directories."""
        state_path = tmp_path / "deep" / "nested" / "publisher.json"
        state = ExecutionState()

        save_execution_state(state, state_path)

        assert state_path.exists()


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_hash_is_consistent(self):
        """Test same inputs produce same hash."""
        hash1 = compute_content_hash("publish_linkedin_post", "content", "/path")
        hash2 = compute_content_hash("publish_linkedin_post", "content", "/path")

        assert hash1 == hash2

    def test_hash_is_different_for_different_content(self):
        """Test different content produces different hash."""
        hash1 = compute_content_hash("publish_linkedin_post", "content1", "/path")
        hash2 = compute_content_hash("publish_linkedin_post", "content2", "/path")

        assert hash1 != hash2

    def test_hash_is_sha256(self):
        """Test hash is valid SHA256 hex string."""
        hash_value = compute_content_hash("publish_linkedin_post", "content", "/path")

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestIsDuplicate:
    """Tests for is_duplicate function."""

    def test_not_duplicate_empty_state(self):
        """Test hash not found in empty state."""
        state = ExecutionState()

        assert is_duplicate(state, "abc123") is False

    def test_is_duplicate(self):
        """Test hash found in state."""
        state = ExecutionState(processed_hashes={"abc123", "def456"})

        assert is_duplicate(state, "abc123") is True

    def test_not_duplicate(self):
        """Test hash not found in state."""
        state = ExecutionState(processed_hashes={"abc123"})

        assert is_duplicate(state, "xyz789") is False


class TestAddProcessedHash:
    """Tests for add_processed_hash function."""

    def test_add_hash_success(self):
        """Test adding hash with success increments published count."""
        state = ExecutionState()

        add_processed_hash(state, "abc123", success=True)

        assert "abc123" in state.processed_hashes
        assert state.total_published == 1
        assert state.total_failed == 0

    def test_add_hash_failure(self):
        """Test adding hash with failure increments failed count."""
        state = ExecutionState()

        add_processed_hash(state, "abc123", success=False)

        assert "abc123" in state.processed_hashes
        assert state.total_published == 0
        assert state.total_failed == 1

    def test_add_multiple_hashes(self):
        """Test adding multiple hashes."""
        state = ExecutionState()

        add_processed_hash(state, "hash1", success=True)
        add_processed_hash(state, "hash2", success=True)
        add_processed_hash(state, "hash3", success=False)

        assert len(state.processed_hashes) == 3
        assert state.total_published == 2
        assert state.total_failed == 1
