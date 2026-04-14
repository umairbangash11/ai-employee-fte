"""Tests for hitl_approval.models module."""

import pytest
from datetime import datetime

from hitl_approval.models import (
    ApprovalRequest,
    ApprovalState,
    ACTION_TYPE_EMAIL_REPLY,
    ACTION_TYPE_EMAIL_FOLLOWUP,
    ACTION_TYPE_LINKEDIN_POST,
    VALID_ACTION_TYPES,
)


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_valid_email_reply_request(self):
        """Test creating a valid email reply request."""
        request = ApprovalRequest(
            action_type=ACTION_TYPE_EMAIL_REPLY,
            target_recipient="test@example.com",
            target_subject="Re: Test Subject",
            content="Test email body",
            source_path="Inbox/email/test.md",
            source_type="email",
            reasoning="Customer needs response",
            expected_outcome="Reply sent",
            rollback_strategy="Cannot unsend email",
            created_by="email_reasoner",
        )

        assert request.action_type == ACTION_TYPE_EMAIL_REPLY
        assert request.target_recipient == "test@example.com"
        assert request.rollback_strategy == "Cannot unsend email"

    def test_valid_linkedin_post_request(self):
        """Test creating a valid LinkedIn post request."""
        request = ApprovalRequest(
            action_type=ACTION_TYPE_LINKEDIN_POST,
            target_recipient="linkedin",
            target_subject="LinkedIn Post",
            content="Post content here",
            source_path="Needs_Action/tasks/post.md",
            source_type="task",
            reasoning="Weekly update needed",
            expected_outcome="Post published",
            rollback_strategy="Delete post manually",
            created_by="orchestrator",
        )

        assert request.action_type == ACTION_TYPE_LINKEDIN_POST
        assert request.created_by == "orchestrator"

    def test_invalid_action_type_raises_error(self):
        """Test that invalid action_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid action_type"):
            ApprovalRequest(
                action_type="invalid_action",
                target_recipient="test@example.com",
                target_subject="Test",
                content="Content",
                source_path="test.md",
                source_type="email",
                reasoning="Test",
                expected_outcome="Test",
                rollback_strategy="Test rollback",
                created_by="test",
            )

    def test_missing_rollback_strategy_raises_error(self):
        """Test that empty rollback_strategy raises ValueError."""
        with pytest.raises(ValueError, match="rollback_strategy is required"):
            ApprovalRequest(
                action_type=ACTION_TYPE_EMAIL_REPLY,
                target_recipient="test@example.com",
                target_subject="Test",
                content="Content",
                source_path="test.md",
                source_type="email",
                reasoning="Test",
                expected_outcome="Test",
                rollback_strategy="",  # Empty - should fail
                created_by="test",
            )

    def test_missing_target_recipient_raises_error(self):
        """Test that empty target_recipient raises ValueError."""
        with pytest.raises(ValueError, match="target_recipient is required"):
            ApprovalRequest(
                action_type=ACTION_TYPE_EMAIL_REPLY,
                target_recipient="",  # Empty - should fail
                target_subject="Test",
                content="Content",
                source_path="test.md",
                source_type="email",
                reasoning="Test",
                expected_outcome="Test",
                rollback_strategy="Cannot unsend",
                created_by="test",
            )

    def test_missing_source_path_raises_error(self):
        """Test that empty source_path raises ValueError."""
        with pytest.raises(ValueError, match="source_path is required"):
            ApprovalRequest(
                action_type=ACTION_TYPE_EMAIL_REPLY,
                target_recipient="test@example.com",
                target_subject="Test",
                content="Content",
                source_path="",  # Empty - should fail
                source_type="email",
                reasoning="Test",
                expected_outcome="Test",
                rollback_strategy="Cannot unsend",
                created_by="test",
            )

    def test_optional_expires_at(self):
        """Test that expires_at is optional."""
        request = ApprovalRequest(
            action_type=ACTION_TYPE_EMAIL_REPLY,
            target_recipient="test@example.com",
            target_subject="Test",
            content="Content",
            source_path="test.md",
            source_type="email",
            reasoning="Test",
            expected_outcome="Test",
            rollback_strategy="Cannot unsend",
            created_by="test",
        )
        assert request.expires_at is None

        # With expires_at
        expiry = datetime(2026, 3, 10, 14, 30, 0)
        request_with_expiry = ApprovalRequest(
            action_type=ACTION_TYPE_EMAIL_REPLY,
            target_recipient="test@example.com",
            target_subject="Test",
            content="Content",
            source_path="test.md",
            source_type="email",
            reasoning="Test",
            expected_outcome="Test",
            rollback_strategy="Cannot unsend",
            created_by="test",
            expires_at=expiry,
        )
        assert request_with_expiry.expires_at == expiry

    def test_default_tags(self):
        """Test that tags defaults to empty list."""
        request = ApprovalRequest(
            action_type=ACTION_TYPE_EMAIL_REPLY,
            target_recipient="test@example.com",
            target_subject="Test",
            content="Content",
            source_path="test.md",
            source_type="email",
            reasoning="Test",
            expected_outcome="Test",
            rollback_strategy="Cannot unsend",
            created_by="test",
        )
        assert request.tags == []

    def test_custom_tags(self):
        """Test that custom tags are preserved."""
        request = ApprovalRequest(
            action_type=ACTION_TYPE_EMAIL_REPLY,
            target_recipient="test@example.com",
            target_subject="Test",
            content="Content",
            source_path="test.md",
            source_type="email",
            reasoning="Test",
            expected_outcome="Test",
            rollback_strategy="Cannot unsend",
            created_by="test",
            tags=["urgent", "interview"],
        )
        assert request.tags == ["urgent", "interview"]


class TestApprovalState:
    """Tests for ApprovalState dataclass."""

    def test_default_state(self):
        """Test default state initialization."""
        state = ApprovalState()
        assert state.created_hashes == set()
        assert state.last_updated is None

    def test_to_dict(self):
        """Test conversion to dict."""
        now = datetime(2026, 3, 8, 14, 30, 0)
        state = ApprovalState(
            created_hashes={"hash1", "hash2"},
            last_updated=now,
        )

        result = state.to_dict()

        assert set(result["created_hashes"]) == {"hash1", "hash2"}
        assert result["last_updated"] == now.isoformat()

    def test_to_dict_without_last_updated(self):
        """Test to_dict when last_updated is None."""
        state = ApprovalState(created_hashes={"hash1"})
        result = state.to_dict()

        assert result["last_updated"] is None

    def test_from_dict(self):
        """Test creation from dict."""
        data = {
            "created_hashes": ["hash1", "hash2"],
            "last_updated": "2026-03-08T14:30:00",
        }

        state = ApprovalState.from_dict(data)

        assert state.created_hashes == {"hash1", "hash2"}
        assert state.last_updated == datetime(2026, 3, 8, 14, 30, 0)

    def test_from_dict_empty(self):
        """Test from_dict with empty data."""
        state = ApprovalState.from_dict({})

        assert state.created_hashes == set()
        assert state.last_updated is None

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        now = datetime(2026, 3, 8, 14, 30, 0)
        original = ApprovalState(
            created_hashes={"hash1", "hash2", "hash3"},
            last_updated=now,
        )

        data = original.to_dict()
        restored = ApprovalState.from_dict(data)

        assert restored.created_hashes == original.created_hashes
        assert restored.last_updated == original.last_updated


class TestActionTypeConstants:
    """Tests for action type constants."""

    def test_valid_action_types_contains_all(self):
        """Test that VALID_ACTION_TYPES contains all constants."""
        assert ACTION_TYPE_EMAIL_REPLY in VALID_ACTION_TYPES
        assert ACTION_TYPE_EMAIL_FOLLOWUP in VALID_ACTION_TYPES
        assert ACTION_TYPE_LINKEDIN_POST in VALID_ACTION_TYPES

    def test_action_type_values(self):
        """Test action type constant values."""
        assert ACTION_TYPE_EMAIL_REPLY == "send_email_reply"
        assert ACTION_TYPE_EMAIL_FOLLOWUP == "send_email_followup"
        assert ACTION_TYPE_LINKEDIN_POST == "publish_linkedin_post"
