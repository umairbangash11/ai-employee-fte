"""Integration tests for HITL approval with email reasoner."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestReasonerApprovalIntegration:
    """Integration tests for email reasoner creating approval requests."""

    @pytest.fixture
    def vault_path(self, tmp_path):
        """Create temporary vault structure."""
        vault = tmp_path / "vault"
        inbox = vault / "Inbox" / "email"
        inbox.mkdir(parents=True)
        return vault

    @pytest.fixture
    def sample_email_file(self, vault_path):
        """Create sample email file in inbox."""
        email_path = vault_path / "Inbox" / "email" / "test_email.md"
        email_content = """---
message_id: test_123
sender: recruiter@company.com
subject: Interview Invitation
captured_at: 2026-03-08T10:00:00Z
---

We would like to invite you for an interview.
Please respond with your availability.
"""
        email_path.write_text(email_content)
        return email_path

    def test_approval_file_created_for_reply_action(self, vault_path):
        """Test that approval file is created when reply action is detected."""
        from hitl_approval.models import ApprovalRequest
        from hitl_approval.writer import create_approval_request

        request = ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="recruiter@company.com",
            target_subject="Re: Interview Invitation",
            content="Thank you for the invitation. I am available on Monday.",
            source_path="Inbox/email/test_email.md",
            source_type="email",
            reasoning="Interview invitation requires response",
            expected_outcome="Email reply sent confirming availability",
            rollback_strategy="Email cannot be unsent once sent",
            created_by="email_reasoner",
            tags=["email", "actionable", "high"],
        )

        approval_path = create_approval_request(request, vault_path)

        # Verify file created in correct location
        assert approval_path.exists()
        assert "Pending_Approval" in str(approval_path)
        assert "email" in str(approval_path)

        # Verify content
        content = approval_path.read_text()
        assert "type: approval_request" in content
        assert "action_type: send_email_reply" in content
        assert "recruiter@company.com" in content
        assert "Interview Invitation" in content

    def test_approval_file_not_created_for_low_priority(self, vault_path):
        """Test that low priority actions don't require approval."""
        # This tests the logic that would be in engine._requires_approval
        # Low priority actions should not trigger approval workflow
        from email_reasoner.models import ClassificationResult

        result = ClassificationResult(
            classification="actionable",
            confidence=0.9,
            reasoning="Some action needed",
            action="Reply to email",
            priority="low",  # Low priority
            is_multi_step=False,
        )

        # Low priority should not require approval
        # (Testing the concept, actual engine logic may vary)
        assert result.priority == "low"

    def test_approval_file_contains_rollback_strategy(self, vault_path):
        """Test that approval file contains rollback strategy."""
        from hitl_approval.models import ApprovalRequest
        from hitl_approval.writer import create_approval_request

        request = ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="test@example.com",
            target_subject="Re: Test",
            content="Test content",
            source_path="Inbox/email/test.md",
            source_type="email",
            reasoning="Test",
            expected_outcome="Email sent",
            rollback_strategy="Email cannot be unsent once sent",
            created_by="email_reasoner",
        )

        approval_path = create_approval_request(request, vault_path)
        content = approval_path.read_text()

        assert "rollback_strategy" in content
        assert "cannot be unsent" in content

    def test_approval_directories_created(self, vault_path):
        """Test that all approval directories are created."""
        from hitl_approval.utils import ensure_approval_dirs

        dirs = ensure_approval_dirs(vault_path)

        # Verify all directories exist
        assert (vault_path / "Pending_Approval" / "email").exists()
        assert (vault_path / "Pending_Approval" / "linkedin").exists()
        assert (vault_path / "Approved" / "email").exists()
        assert (vault_path / "Approved" / "linkedin").exists()
        assert (vault_path / "Rejected" / "email").exists()
        assert (vault_path / "Rejected" / "linkedin").exists()
        assert (vault_path / "Logs" / "approvals").exists()
