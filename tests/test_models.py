"""Tests for email_reasoner.models module."""

from datetime import datetime
from pathlib import Path

import pytest

from email_reasoner.models import (
    EmailFile,
    ClassificationResult,
    TaskFile,
    PlanFile,
    ProcessedEmail,
    ReasonerState,
)


class TestEmailFile:
    """Tests for EmailFile dataclass."""

    def test_email_file_creation(self):
        """Test creating an EmailFile with required fields."""
        email = EmailFile(
            message_id="test_123",
            sender="test@example.com",
            subject="Test Subject",
            body="Test body content",
        )

        assert email.message_id == "test_123"
        assert email.sender == "test@example.com"
        assert email.subject == "Test Subject"
        assert email.body == "Test body content"
        assert email.urgency == "normal"
        assert email.status == "unread"

    def test_wikilink_property(self):
        """Test wikilink generation from file path."""
        email = EmailFile(
            message_id="test_123",
            file_path=Path("/vault/Inbox/email/20260307_test.md")
        )

        assert "Inbox/email/20260307_test.md" in email.wikilink
        assert email.wikilink.startswith("[[")
        assert email.wikilink.endswith("]]")

    def test_relative_path_extraction(self):
        """Test relative path extraction from Inbox."""
        email = EmailFile(
            message_id="test_123",
            file_path=Path("/home/user/vault/Inbox/email/message.md")
        )

        assert email.relative_path == "Inbox/email/message.md"


class TestClassificationResult:
    """Tests for ClassificationResult Pydantic model."""

    def test_actionable_classification(self):
        """Test actionable classification creates task."""
        result = ClassificationResult(
            classification="actionable",
            confidence=0.95,
            reasoning="Interview request requires response",
            action="Respond to interview invitation",
            priority="high",
        )

        assert result.creates_task is True
        assert result.creates_plan is False

    def test_promotional_classification(self):
        """Test promotional classification does not create task."""
        result = ClassificationResult(
            classification="promotional",
            confidence=0.99,
            reasoning="Marketing email about sale",
        )

        assert result.creates_task is False
        assert result.creates_plan is False

    def test_multi_step_classification(self):
        """Test multi-step actionable creates plan."""
        result = ClassificationResult(
            classification="actionable",
            confidence=0.90,
            reasoning="Onboarding requires multiple steps",
            action="Complete onboarding process",
            priority="medium",
            is_multi_step=True,
            steps=["Sign documents", "Set up payroll", "Attend orientation"],
        )

        assert result.creates_task is True
        assert result.creates_plan is True

    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            ClassificationResult(
                classification="actionable",
                confidence=1.5,  # Invalid
                reasoning="Test",
            )

    def test_classification_enum_validation(self):
        """Test classification must be valid enum value."""
        with pytest.raises(ValueError):
            ClassificationResult(
                classification="unknown",  # Invalid
                confidence=0.5,
                reasoning="Test",
            )


class TestTaskFile:
    """Tests for TaskFile dataclass."""

    def test_task_file_creation(self):
        """Test creating a TaskFile with all fields."""
        task = TaskFile(
            source_email="[[Inbox/email/test.md]]",
            priority="high",
            due_date="2026-03-10",
            title="Respond to Interview",
            context="Interview invitation from Company X",
            action_required="Reply to confirm availability",
            email_from="recruiter@company.com",
            email_subject="Interview Invitation",
        )

        assert task.type == "task"
        assert task.status == "pending"
        assert "task" in task.tags
        assert "email-derived" in task.tags

    def test_filename_generation(self):
        """Test filename is generated correctly."""
        task = TaskFile(
            title="Respond to Interview Invitation",
            created_at=datetime(2026, 3, 7, 10, 30, 0),
        )

        filename = task.filename
        assert filename.startswith("20260307-103000_")
        assert filename.endswith(".md")
        assert "respond_to_interview" in filename.lower()

    def test_to_markdown(self):
        """Test markdown generation."""
        task = TaskFile(
            source_email="[[Inbox/email/test.md]]",
            priority="high",
            title="Test Task",
            context="Test context",
            action_required="Do something",
            email_from="test@example.com",
            email_subject="Test Subject",
        )

        markdown = task.to_markdown()

        assert "---" in markdown  # Frontmatter
        assert "type: task" in markdown
        assert "priority: high" in markdown
        assert "# Test Task" in markdown
        assert "Test context" in markdown
        assert "Do something" in markdown

    def test_slugify(self):
        """Test slug generation for filenames."""
        assert TaskFile._slugify("Hello World!") == "hello_world"
        assert TaskFile._slugify("Test 123 @#$") == "test_123"
        assert TaskFile._slugify("Multiple   Spaces") == "multiple_spaces"


class TestPlanFile:
    """Tests for PlanFile dataclass."""

    def test_plan_file_creation(self):
        """Test creating a PlanFile with steps."""
        plan = PlanFile(
            source_email="[[Inbox/email/onboarding.md]]",
            related_task="[[Needs_Action/tasks/onboarding.md]]",
            title="Complete Onboarding",
            overview="Multi-step onboarding process",
            steps=["Sign documents", "Set up payroll", "Attend orientation"],
        )

        assert plan.type == "plan"
        assert plan.status == "pending"
        assert len(plan.steps) == 3

    def test_to_markdown_with_steps(self):
        """Test markdown generation includes checkbox steps."""
        plan = PlanFile(
            source_email="[[Inbox/email/test.md]]",
            related_task="[[Needs_Action/tasks/task.md]]",
            title="Test Plan",
            overview="Test overview",
            steps=["Step 1", "Step 2", "Step 3"],
        )

        markdown = plan.to_markdown()

        assert "- [ ] Step 1" in markdown
        assert "- [ ] Step 2" in markdown
        assert "- [ ] Step 3" in markdown
        assert "related_task:" in markdown


class TestReasonerState:
    """Tests for ReasonerState dataclass."""

    def test_empty_state(self):
        """Test creating empty state."""
        state = ReasonerState()

        assert state.version == 1
        assert state.last_run is None
        assert len(state.processed) == 0

    def test_is_processed(self):
        """Test is_processed method."""
        state = ReasonerState()
        state.processed["msg_123"] = ProcessedEmail(
            classified_at="2026-03-07T10:00:00Z",
            classification="actionable",
        )

        assert state.is_processed("msg_123") is True
        assert state.is_processed("msg_456") is False

    def test_mark_processed(self):
        """Test mark_processed method."""
        state = ReasonerState()

        state.mark_processed("msg_new", "promotional", None)

        assert "msg_new" in state.processed
        assert state.processed["msg_new"].classification == "promotional"
        assert state.last_run is not None

    def test_to_dict_serialization(self):
        """Test serialization to dict."""
        state = ReasonerState()
        state.mark_processed("msg_1", "actionable", "task.md")

        data = state.to_dict()

        assert data["version"] == 1
        assert "msg_1" in data["processed"]
        assert data["processed"]["msg_1"]["classification"] == "actionable"
        assert data["processed"]["msg_1"]["task_file"] == "task.md"

    def test_from_dict_deserialization(self):
        """Test deserialization from dict."""
        data = {
            "version": 1,
            "last_run": "2026-03-07T10:00:00Z",
            "processed": {
                "msg_1": {
                    "classified_at": "2026-03-07T10:00:00Z",
                    "classification": "informational",
                    "task_file": None,
                }
            }
        }

        state = ReasonerState.from_dict(data)

        assert state.version == 1
        assert state.last_run == "2026-03-07T10:00:00Z"
        assert state.is_processed("msg_1")
        assert state.processed["msg_1"].classification == "informational"
