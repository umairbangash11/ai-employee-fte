"""Tests for hitl_approval.writer module."""

from datetime import datetime
from pathlib import Path

import pytest

from hitl_approval.models import ApprovalRequest
from hitl_approval.writer import (
    compute_approval_hash,
    generate_frontmatter,
    generate_body,
    create_approval_request,
)
from hitl_approval.exceptions import DuplicateApprovalError


class TestComputeApprovalHash:
    """Tests for approval hash computation."""

    def test_hash_is_deterministic(self):
        """Test that same inputs produce same hash."""
        request = ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="test@example.com",
            target_subject="Re: Test",
            content="Test content",
            source_path="/Inbox/email/test.md",
            source_type="email",
            reasoning="Test reasoning",
            expected_outcome="Email sent",
            rollback_strategy="Cannot unsend",
            created_by="email_reasoner",
        )
        hash1 = compute_approval_hash(request)
        hash2 = compute_approval_hash(request)
        assert hash1 == hash2

    def test_different_inputs_different_hash(self):
        """Test that different inputs produce different hashes."""
        request1 = ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="test1@example.com",
            target_subject="Re: Test",
            content="Test content",
            source_path="/Inbox/email/test.md",
            source_type="email",
            reasoning="Test reasoning",
            expected_outcome="Email sent",
            rollback_strategy="Cannot unsend",
            created_by="email_reasoner",
        )
        request2 = ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="test2@example.com",
            target_subject="Re: Test",
            content="Test content",
            source_path="/Inbox/email/test.md",
            source_type="email",
            reasoning="Test reasoning",
            expected_outcome="Email sent",
            rollback_strategy="Cannot unsend",
            created_by="email_reasoner",
        )
        assert compute_approval_hash(request1) != compute_approval_hash(request2)


class TestGenerateFrontmatter:
    """Tests for frontmatter generation."""

    @pytest.fixture
    def sample_request(self):
        """Create sample approval request."""
        return ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="recruiter@company.com",
            target_subject="Re: Interview Invitation",
            content="Thank you for the interview invitation.",
            source_path="Inbox/email/interview.md",
            source_type="email",
            reasoning="Interview invitation requires response",
            expected_outcome="Email reply sent confirming attendance",
            rollback_strategy="Email cannot be unsent once sent",
            created_by="email_reasoner",
            tags=["email", "interview"],
        )

    def test_frontmatter_has_required_fields(self, sample_request):
        """Test that frontmatter contains all required fields."""
        timestamp = datetime(2026, 3, 8, 14, 30, 0)
        frontmatter = generate_frontmatter(sample_request, timestamp)

        assert "type: approval_request" in frontmatter
        assert "action_type: send_email_reply" in frontmatter
        assert "status: pending" in frontmatter
        assert 'created_at: "2026-03-08T14:30:00Z"' in frontmatter
        assert "created_by: email_reasoner" in frontmatter
        assert 'recipient: "recruiter@company.com"' in frontmatter
        assert 'rollback_strategy: "Email cannot be unsent once sent"' in frontmatter

    def test_frontmatter_has_yaml_delimiters(self, sample_request):
        """Test that frontmatter has proper YAML delimiters."""
        timestamp = datetime(2026, 3, 8, 14, 30, 0)
        frontmatter = generate_frontmatter(sample_request, timestamp)

        assert frontmatter.startswith("---")
        assert frontmatter.endswith("---")


class TestGenerateBody:
    """Tests for body generation."""

    @pytest.fixture
    def sample_request(self):
        """Create sample approval request."""
        return ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="recruiter@company.com",
            target_subject="Re: Interview Invitation",
            content="Thank you for the interview invitation. I would be happy to attend.",
            source_path="Inbox/email/interview.md",
            source_type="email",
            reasoning="Interview invitation requires response",
            expected_outcome="Email reply sent",
            rollback_strategy="Email cannot be unsent",
            created_by="email_reasoner",
        )

    def test_body_has_title(self, sample_request):
        """Test that body has action title."""
        body = generate_body(sample_request)
        assert "# Action: Re: Interview Invitation" in body

    def test_body_has_content_preview(self, sample_request):
        """Test that body has content preview."""
        body = generate_body(sample_request)
        assert "Thank you for the interview invitation" in body
        assert "**To**: recruiter@company.com" in body

    def test_body_has_approval_instructions(self, sample_request):
        """Test that body has approval instructions."""
        body = generate_body(sample_request)
        assert "To approve: Move this file to `/Approved/email/`" in body
        assert "To reject: Move this file to `/Rejected/email/`" in body

    def test_body_has_risk_assessment(self, sample_request):
        """Test that body has risk assessment section."""
        body = generate_body(sample_request)
        assert "## Risk Assessment" in body
        assert "Impact:" in body
        assert "Rollback:" in body


class TestCreateApprovalRequest:
    """Tests for approval request creation."""

    @pytest.fixture
    def sample_request(self):
        """Create sample approval request."""
        return ApprovalRequest(
            action_type="send_email_reply",
            target_recipient="test@example.com",
            target_subject="Re: Test Subject",
            content="Test email content",
            source_path="Inbox/email/test.md",
            source_type="email",
            reasoning="Test reasoning",
            expected_outcome="Email sent",
            rollback_strategy="Cannot unsend email",
            created_by="email_reasoner",
        )

    def test_creates_file_in_pending_approval(self, tmp_path, sample_request):
        """Test that file is created in correct directory."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        file_path = create_approval_request(sample_request, vault_path)

        assert file_path.exists()
        assert "Pending_Approval" in str(file_path)
        assert "email" in str(file_path)

    def test_file_has_correct_content(self, tmp_path, sample_request):
        """Test that created file has correct content."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        file_path = create_approval_request(sample_request, vault_path)
        content = file_path.read_text()

        assert "type: approval_request" in content
        assert "action_type: send_email_reply" in content
        assert "Test email content" in content

    def test_duplicate_raises_error(self, tmp_path, sample_request):
        """Test that duplicate request raises DuplicateApprovalError."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # First request should succeed
        create_approval_request(sample_request, vault_path)

        # Second identical request should fail
        with pytest.raises(DuplicateApprovalError):
            create_approval_request(sample_request, vault_path)

    def test_creates_directories_if_missing(self, tmp_path, sample_request):
        """Test that directories are created if they don't exist."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        file_path = create_approval_request(sample_request, vault_path)

        assert (vault_path / "Pending_Approval" / "email").exists()
        assert file_path.exists()
