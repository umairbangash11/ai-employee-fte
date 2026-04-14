"""Tests for email_reasoner.writer module."""

from datetime import datetime
from pathlib import Path

import pytest

from email_reasoner.writer import (
    generate_task_filename,
    generate_task_frontmatter,
    generate_task_body,
    write_task_file,
    generate_plan_filename,
    generate_plan_body,
    write_plan_file,
    _slugify,
)
from email_reasoner.models import EmailFile, ClassificationResult


class TestSlugify:
    """Tests for slug generation."""

    def test_basic_slugify(self):
        """Test basic text slugification."""
        assert _slugify("Hello World") == "hello_world"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert _slugify("Test @#$ 123") == "test_123"

    def test_multiple_spaces_collapsed(self):
        """Test that multiple spaces become single underscore."""
        assert _slugify("Multiple   Spaces") == "multiple_spaces"

    def test_leading_trailing_stripped(self):
        """Test that leading/trailing underscores are stripped."""
        assert _slugify("  Test  ") == "test"


class TestGenerateTaskFilename:
    """Tests for task filename generation."""

    def test_filename_format(self):
        """Test filename has correct format."""
        timestamp = datetime(2026, 3, 7, 10, 30, 0)
        filename = generate_task_filename("Respond to Interview", timestamp)

        assert filename.startswith("20260307-103000_")
        assert filename.endswith(".md")
        assert "respond_to_interview" in filename

    def test_filename_truncation(self):
        """Test that long actions are truncated in filename."""
        timestamp = datetime(2026, 3, 7, 10, 30, 0)
        long_action = "This is a very long action description " * 5
        filename = generate_task_filename(long_action, timestamp)

        # 50 char slug + timestamp + underscore + .md
        assert len(filename) <= 75


class TestGenerateTaskFrontmatter:
    """Tests for task frontmatter generation."""

    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return EmailFile(
            message_id="test_123",
            sender="test@example.com",
            subject="Test Subject",
            file_path=Path("/vault/Inbox/email/test.md"),
        )

    @pytest.fixture
    def sample_result(self):
        """Create sample classification result."""
        return ClassificationResult(
            classification="actionable",
            confidence=0.95,
            reasoning="Test",
            action="Test action",
            priority="high",
            due_date="2026-03-10",
        )

    def test_frontmatter_contains_required_fields(self, sample_email, sample_result):
        """Test that frontmatter has all required fields."""
        frontmatter = generate_task_frontmatter(sample_email, sample_result)

        assert "type: task" in frontmatter
        assert "priority: high" in frontmatter
        assert 'due_date: "2026-03-10"' in frontmatter
        assert "status: pending" in frontmatter
        assert "source_email:" in frontmatter

    def test_frontmatter_null_due_date(self, sample_email):
        """Test frontmatter with null due date."""
        result = ClassificationResult(
            classification="actionable",
            confidence=0.9,
            reasoning="Test",
            action="Test",
            priority="medium",
            due_date=None,
        )
        frontmatter = generate_task_frontmatter(sample_email, result)

        assert "due_date: null" in frontmatter


class TestGenerateTaskBody:
    """Tests for task body generation."""

    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return EmailFile(
            message_id="test_123",
            sender="recruiter@company.com",
            subject="Interview Invitation",
            file_path=Path("/vault/Inbox/email/test.md"),
        )

    @pytest.fixture
    def sample_result(self):
        """Create sample classification result."""
        return ClassificationResult(
            classification="actionable",
            confidence=0.95,
            reasoning="Interview invitation requires response",
            action="Respond to interview invitation",
            priority="high",
        )

    def test_body_contains_title(self, sample_email, sample_result):
        """Test that body contains action as title."""
        body = generate_task_body(sample_email, sample_result)

        assert "# Respond to interview invitation" in body

    def test_body_contains_source_info(self, sample_email, sample_result):
        """Test that body contains source email info."""
        body = generate_task_body(sample_email, sample_result)

        assert "recruiter@company.com" in body
        assert "Interview Invitation" in body


class TestWriteTaskFile:
    """Tests for task file writing."""

    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return EmailFile(
            message_id="test_123",
            sender="test@example.com",
            subject="Test Subject",
            file_path=Path("/vault/Inbox/email/test.md"),
        )

    @pytest.fixture
    def sample_result(self):
        """Create sample classification result."""
        return ClassificationResult(
            classification="actionable",
            confidence=0.95,
            reasoning="Test",
            action="Test action",
            priority="medium",
        )

    def test_creates_task_file(self, tmp_path, sample_email, sample_result):
        """Test that task file is created."""
        task_path = write_task_file(sample_email, sample_result, tmp_path)

        assert task_path.exists()
        assert task_path.suffix == ".md"

    def test_creates_directory(self, tmp_path, sample_email, sample_result):
        """Test that /Needs_Action/tasks/ directory is created."""
        write_task_file(sample_email, sample_result, tmp_path)

        tasks_dir = tmp_path / "Needs_Action" / "tasks"
        assert tasks_dir.exists()
        assert tasks_dir.is_dir()

    def test_file_content(self, tmp_path, sample_email, sample_result):
        """Test that file has correct content."""
        task_path = write_task_file(sample_email, sample_result, tmp_path)

        content = task_path.read_text()
        assert "---" in content  # Frontmatter
        assert "type: task" in content
        assert "Test action" in content


class TestPlanFileGeneration:
    """Tests for plan file generation."""

    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return EmailFile(
            message_id="onboard_123",
            sender="hr@company.com",
            subject="Complete your onboarding",
            file_path=Path("/vault/Inbox/email/onboard.md"),
        )

    @pytest.fixture
    def multi_step_result(self):
        """Create multi-step classification result."""
        return ClassificationResult(
            classification="actionable",
            confidence=0.92,
            reasoning="Onboarding requires multiple steps",
            action="Complete onboarding process",
            priority="medium",
            is_multi_step=True,
            steps=["Sign documents", "Set up payroll", "Attend orientation"],
        )

    def test_plan_filename_format(self):
        """Test plan filename has correct format."""
        timestamp = datetime(2026, 3, 7, 10, 30, 0)
        filename = generate_plan_filename("Complete Onboarding", timestamp)

        assert filename.startswith("20260307-103000_")
        assert filename.endswith(".md")

    def test_plan_body_has_checkboxes(self, sample_email, multi_step_result):
        """Test that plan body has checkbox steps."""
        body = generate_plan_body(sample_email, multi_step_result)

        assert "- [ ] Sign documents" in body
        assert "- [ ] Set up payroll" in body
        assert "- [ ] Attend orientation" in body

    def test_write_plan_file(self, tmp_path, sample_email, multi_step_result):
        """Test that plan file is created."""
        plan_path = write_plan_file(
            sample_email,
            multi_step_result,
            "Needs_Action/tasks/test_task.md",
            tmp_path,
        )

        assert plan_path.exists()
        assert plan_path.parent.name == "Plans"

        content = plan_path.read_text()
        assert "type: plan" in content
        assert "related_task:" in content
        assert "- [ ] Sign documents" in content

    def test_plan_directory_created(self, tmp_path, sample_email, multi_step_result):
        """Test that /Plans/ directory is created."""
        write_plan_file(
            sample_email,
            multi_step_result,
            "Needs_Action/tasks/test_task.md",
            tmp_path,
        )

        plans_dir = tmp_path / "Plans"
        assert plans_dir.exists()
        assert plans_dir.is_dir()
