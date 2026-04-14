"""Tests for LinkedIn publisher models."""

import pytest
from datetime import datetime
from pathlib import Path

from linkedin_publisher.models import ApprovedPost, PublishResult, ExecutionState


class TestApprovedPost:
    """Tests for ApprovedPost dataclass."""

    def test_create_approved_post(self):
        """Test creating ApprovedPost with required fields."""
        post = ApprovedPost(
            file_path=Path("/vault/Approved/linkedin/test.md"),
            content="Test content",
            frontmatter={"type": "approval_request"},
            created_at=datetime(2026, 3, 12, 10, 0, 0),
        )

        assert post.file_path == Path("/vault/Approved/linkedin/test.md")
        assert post.content == "Test content"
        assert post.frontmatter == {"type": "approval_request"}
        assert post.created_at == datetime(2026, 3, 12, 10, 0, 0)
        assert post.source_path is None

    def test_approved_post_with_source_path(self):
        """Test ApprovedPost with optional source_path."""
        post = ApprovedPost(
            file_path="/vault/Approved/linkedin/test.md",
            content="Test content",
            frontmatter={},
            created_at=datetime.utcnow(),
            source_path="/vault/Inbox/email/source.md",
        )

        assert post.source_path == "/vault/Inbox/email/source.md"

    def test_file_path_converted_to_path(self):
        """Test that string file_path is converted to Path."""
        post = ApprovedPost(
            file_path="/vault/test.md",
            content="Test",
            frontmatter={},
            created_at=datetime.utcnow(),
        )

        assert isinstance(post.file_path, Path)


class TestPublishResult:
    """Tests for PublishResult dataclass."""

    def test_success_result(self):
        """Test successful publish result."""
        result = PublishResult(
            success=True,
            post_url="https://linkedin.com/post/123",
            retry_count=1,
            publish_duration_ms=5000,
        )

        assert result.success is True
        assert result.post_url == "https://linkedin.com/post/123"
        assert result.error is None
        assert result.retry_count == 1

    def test_failure_result(self):
        """Test failed publish result."""
        result = PublishResult(
            success=False,
            error="Network timeout",
            error_type="TimeoutError",
            retry_count=3,
        )

        assert result.success is False
        assert result.error == "Network timeout"
        assert result.error_type == "TimeoutError"

    def test_to_dict(self):
        """Test converting PublishResult to dict."""
        result = PublishResult(
            success=True,
            post_url="https://linkedin.com/post/123",
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["post_url"] == "https://linkedin.com/post/123"
        assert "timestamp" in data


class TestExecutionState:
    """Tests for ExecutionState dataclass."""

    def test_empty_state(self):
        """Test creating empty execution state."""
        state = ExecutionState()

        assert state.processed_hashes == set()
        assert state.last_run is None
        assert state.total_published == 0
        assert state.total_failed == 0

    def test_state_with_data(self):
        """Test creating state with data."""
        state = ExecutionState(
            processed_hashes={"abc123", "def456"},
            last_run=datetime(2026, 3, 12, 10, 0, 0),
            total_published=10,
            total_failed=2,
        )

        assert len(state.processed_hashes) == 2
        assert "abc123" in state.processed_hashes
        assert state.total_published == 10

    def test_to_dict(self):
        """Test converting state to dict."""
        state = ExecutionState(
            processed_hashes={"abc123"},
            total_published=5,
        )

        data = state.to_dict()

        assert "abc123" in data["processed_hashes"]
        assert data["total_published"] == 5

    def test_from_dict(self):
        """Test creating state from dict."""
        data = {
            "processed_hashes": ["abc123", "def456"],
            "last_run": "2026-03-12T10:00:00Z",
            "total_published": 10,
            "total_failed": 2,
        }

        state = ExecutionState.from_dict(data)

        assert len(state.processed_hashes) == 2
        assert state.last_run == datetime(2026, 3, 12, 10, 0, 0)
        assert state.total_published == 10

    def test_from_dict_empty(self):
        """Test creating state from empty dict."""
        state = ExecutionState.from_dict({})

        assert state.processed_hashes == set()
        assert state.total_published == 0
