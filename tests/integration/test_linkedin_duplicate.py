"""Integration tests for LinkedIn duplicate detection."""

import pytest
from pathlib import Path

from linkedin_publisher.state import (
    compute_content_hash,
    is_duplicate,
    add_processed_hash,
    load_execution_state,
    save_execution_state,
)
from linkedin_publisher.models import ExecutionState


class TestLinkedInDuplicateDetection:
    """Integration tests for duplicate content detection."""

    def test_duplicate_detection_across_files(self, tmp_path):
        """Test that same content from different files is detected as duplicate."""
        state_path = tmp_path / "publisher.json"

        # First file
        hash1 = compute_content_hash(
            "publish_linkedin_post",
            "Same content here",
            "/source1.md",
        )

        state = load_execution_state(state_path)
        assert is_duplicate(state, hash1) is False

        add_processed_hash(state, hash1, success=True)
        save_execution_state(state, state_path)

        # Second file with same content and source
        hash2 = compute_content_hash(
            "publish_linkedin_post",
            "Same content here",
            "/source1.md",
        )

        state = load_execution_state(state_path)
        assert is_duplicate(state, hash2) is True

    def test_different_content_not_duplicate(self, tmp_path):
        """Test that different content is not detected as duplicate."""
        state_path = tmp_path / "publisher.json"

        # First post
        hash1 = compute_content_hash(
            "publish_linkedin_post",
            "First post content",
            "/source.md",
        )

        state = load_execution_state(state_path)
        add_processed_hash(state, hash1, success=True)
        save_execution_state(state, state_path)

        # Different content
        hash2 = compute_content_hash(
            "publish_linkedin_post",
            "Second post content",
            "/source.md",
        )

        state = load_execution_state(state_path)
        assert is_duplicate(state, hash2) is False

    def test_state_persists_across_sessions(self, tmp_path):
        """Test that duplicate detection state persists across sessions."""
        state_path = tmp_path / "publisher.json"

        # Session 1: Add a hash
        hash_value = compute_content_hash(
            "publish_linkedin_post",
            "Persistent content",
            "/source.md",
        )

        state1 = load_execution_state(state_path)
        add_processed_hash(state1, hash_value, success=True)
        save_execution_state(state1, state_path)

        # Session 2: Load fresh state
        state2 = load_execution_state(state_path)

        # Should still detect as duplicate
        assert is_duplicate(state2, hash_value) is True
        assert state2.total_published == 1

    def test_statistics_tracked(self, tmp_path):
        """Test that success/failure statistics are tracked."""
        state_path = tmp_path / "publisher.json"

        state = load_execution_state(state_path)

        # Add successful publishes
        add_processed_hash(state, "hash1", success=True)
        add_processed_hash(state, "hash2", success=True)
        add_processed_hash(state, "hash3", success=True)

        # Add failed publishes
        add_processed_hash(state, "hash4", success=False)
        add_processed_hash(state, "hash5", success=False)

        save_execution_state(state, state_path)

        # Reload and verify
        loaded_state = load_execution_state(state_path)

        assert loaded_state.total_published == 3
        assert loaded_state.total_failed == 2
        assert len(loaded_state.processed_hashes) == 5
