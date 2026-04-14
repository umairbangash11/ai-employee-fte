"""Unit tests for facebook_publisher models."""

from datetime import datetime
from pathlib import Path

import pytest

from facebook_publisher.models import ApprovedPost, ExecutionState, PublishResult


class TestApprovedPost:
    """Tests for ApprovedPost dataclass."""

    def test_create_approved_post(self):
        """Test creating an ApprovedPost with required fields."""
        post = ApprovedPost(
            file_path=Path("/vault/Approved/facebook/test.md"),
            content="Hello, Facebook!",
            frontmatter={"type": "approval_request"},
            created_at=datetime(2026, 3, 22, 10, 0, 0),
            visibility="public",
        )

        assert post.file_path == Path("/vault/Approved/facebook/test.md")
        assert post.content == "Hello, Facebook!"
        assert post.frontmatter == {"type": "approval_request"}
        assert post.visibility == "public"

    def test_approved_post_default_visibility(self):
        """Test ApprovedPost defaults to public visibility."""
        post = ApprovedPost(
            file_path=Path("/vault/Approved/facebook/test.md"),
            content="Test content",
            frontmatter={},
            created_at=datetime.utcnow(),
        )

        assert post.visibility == "public"


class TestPublishResult:
    """Tests for PublishResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful PublishResult."""
        result = PublishResult(
            success=True,
            post_url="https://facebook.com/posts/123",
            timestamp=datetime(2026, 3, 22, 10, 0, 0),
            duration_ms=5000,
        )

        assert result.success is True
        assert result.post_url == "https://facebook.com/posts/123"
        assert result.error is None
        assert result.duration_ms == 5000

    def test_create_failure_result(self):
        """Test creating a failed PublishResult."""
        result = PublishResult(
            success=False,
            error="Network timeout",
            error_type="TimeoutError",
            retry_count=3,
            timestamp=datetime.utcnow(),
        )

        assert result.success is False
        assert result.error == "Network timeout"
        assert result.error_type == "TimeoutError"
        assert result.retry_count == 3
        assert result.post_url is None

    def test_publish_result_defaults(self):
        """Test PublishResult defaults."""
        result = PublishResult(
            success=True,
            timestamp=datetime.utcnow(),
        )

        assert result.post_url is None
        assert result.error is None
        assert result.error_type is None
        assert result.retry_count is None
        assert result.duration_ms is None


class TestExecutionState:
    """Tests for ExecutionState dataclass."""

    def test_create_execution_state(self):
        """Test creating ExecutionState with all fields."""
        state = ExecutionState(
            processed_hashes={"hash1", "hash2"},
            last_run=datetime(2026, 3, 22, 10, 0, 0),
            stats={"published": 5, "failed": 1, "skipped": 2},
        )

        assert len(state.processed_hashes) == 2
        assert "hash1" in state.processed_hashes
        assert state.stats["published"] == 5

    def test_execution_state_to_dict(self):
        """Test ExecutionState serialization to dictionary."""
        state = ExecutionState(
            processed_hashes={"hash1", "hash2"},
            last_run=datetime(2026, 3, 22, 10, 0, 0),
            stats={"published": 5, "failed": 1, "skipped": 2},
        )

        data = state.to_dict()

        assert "hash1" in data["processed_hashes"]
        assert "hash2" in data["processed_hashes"]
        assert data["last_run"] == "2026-03-22T10:00:00"
        assert data["stats"]["published"] == 5

    def test_execution_state_from_dict(self):
        """Test ExecutionState deserialization from dictionary."""
        data = {
            "processed_hashes": ["hash1", "hash2"],
            "last_run": "2026-03-22T10:00:00",
            "stats": {"published": 5, "failed": 1, "skipped": 2},
        }

        state = ExecutionState.from_dict(data)

        assert len(state.processed_hashes) == 2
        assert state.last_run == datetime(2026, 3, 22, 10, 0, 0)
        assert state.stats["published"] == 5

    def test_execution_state_from_empty_dict(self):
        """Test ExecutionState deserialization from empty dictionary."""
        state = ExecutionState.from_dict({})

        assert len(state.processed_hashes) == 0
        assert state.last_run is None
        assert state.stats == {"published": 0, "failed": 0, "skipped": 0}

    def test_execution_state_defaults(self):
        """Test ExecutionState defaults."""
        state = ExecutionState()

        assert len(state.processed_hashes) == 0
        assert state.last_run is None
        assert state.stats == {"published": 0, "failed": 0, "skipped": 0}
