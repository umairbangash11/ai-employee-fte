"""Tests for email_reasoner.classifier module."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from email_reasoner.classifier import (
    classify_email,
    truncate_body,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from email_reasoner.models import EmailFile, ClassificationResult


class TestTruncateBody:
    """Tests for body truncation."""

    def test_short_body_unchanged(self):
        """Test that short bodies are not truncated."""
        body = "This is a short email body."
        result = truncate_body(body)
        assert result == body

    def test_long_body_truncated(self):
        """Test that long bodies are truncated."""
        body = "x" * 20000
        result = truncate_body(body, max_chars=1000)
        assert len(result) <= 1100  # Allow for truncation message
        assert "[... email truncated" in result

    def test_truncate_at_paragraph_break(self):
        """Test truncation at paragraph boundary."""
        body = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph." + "x" * 10000
        result = truncate_body(body, max_chars=100)
        assert "[... email truncated" in result


class TestClassifyEmail:
    """Tests for email classification with mocked OpenAI."""

    @pytest.fixture
    def sample_email(self):
        """Create a sample email for testing."""
        return EmailFile(
            message_id="test_123",
            sender="recruiter@company.com",
            subject="Interview Invitation for Software Engineer",
            body="We would like to invite you for an interview on March 10th.",
            captured_at=datetime(2026, 3, 7, 10, 0, 0),
            file_path=Path("/vault/Inbox/email/test.md"),
        )

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        return {
            "classification": "actionable",
            "confidence": 0.95,
            "reasoning": "Interview invitation requires response",
            "action": "Respond to interview invitation",
            "priority": "high",
            "due_date": "2026-03-10",
            "is_multi_step": False,
            "steps": None,
        }

    @patch("email_reasoner.classifier.get_openai_client")
    def test_classify_actionable_email(self, mock_get_client, sample_email, mock_openai_response):
        """Test classification of an actionable email."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_openai_response)))
        ]

        result = classify_email(sample_email, api_key="test-key")

        assert result.classification == "actionable"
        assert result.confidence == 0.95
        assert result.creates_task is True
        assert result.priority == "high"

    @patch("email_reasoner.classifier.get_openai_client")
    def test_classify_promotional_email(self, mock_get_client, sample_email):
        """Test classification of a promotional email."""
        promotional_response = {
            "classification": "promotional",
            "confidence": 0.98,
            "reasoning": "Marketing email about sale",
            "action": None,
            "priority": None,
            "due_date": None,
            "is_multi_step": False,
            "steps": None,
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(promotional_response)))
        ]

        sample_email.subject = "50% off sale today!"
        sample_email.sender = "marketing@store.com"
        sample_email.body = "Don't miss our biggest sale of the year!"

        result = classify_email(sample_email, api_key="test-key")

        assert result.classification == "promotional"
        assert result.creates_task is False

    @patch("email_reasoner.classifier.get_openai_client")
    def test_classify_multi_step_email(self, mock_get_client, sample_email):
        """Test classification of a multi-step actionable email."""
        multi_step_response = {
            "classification": "actionable",
            "confidence": 0.92,
            "reasoning": "Onboarding requires multiple steps",
            "action": "Complete onboarding process",
            "priority": "medium",
            "due_date": "2026-03-15",
            "is_multi_step": True,
            "steps": ["Sign documents", "Set up payroll", "Attend orientation"],
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(multi_step_response)))
        ]

        sample_email.subject = "Complete your onboarding"
        sample_email.body = "Please complete: 1) Sign docs 2) Setup payroll 3) Orientation"

        result = classify_email(sample_email, api_key="test-key")

        assert result.classification == "actionable"
        assert result.is_multi_step is True
        assert result.creates_plan is True
        assert len(result.steps) == 3

    @patch("email_reasoner.classifier.get_openai_client")
    def test_low_confidence_fallback(self, mock_get_client, sample_email):
        """Test that low confidence falls back to informational."""
        low_confidence_response = {
            "classification": "actionable",
            "confidence": 0.3,
            "reasoning": "Unclear if action needed",
            "action": "Maybe respond",
            "priority": "low",
            "due_date": None,
            "is_multi_step": False,
            "steps": None,
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(low_confidence_response)))
        ]

        result = classify_email(sample_email, api_key="test-key", confidence_threshold=0.6)

        assert result.classification == "informational"
        assert result.confidence == 0.3

    @patch("email_reasoner.classifier.get_openai_client")
    def test_api_error_fallback(self, mock_get_client, sample_email):
        """Test that API errors fall back to informational after retries."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # This should not raise, but return fallback
        result = classify_email(sample_email, api_key="test-key")

        assert result.classification == "informational"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()


class TestSystemPrompt:
    """Tests for system prompt content."""

    def test_prompt_contains_categories(self):
        """Test that system prompt defines all categories."""
        assert "actionable" in SYSTEM_PROMPT
        assert "informational" in SYSTEM_PROMPT
        assert "promotional" in SYSTEM_PROMPT
        assert "ignore" in SYSTEM_PROMPT

    def test_prompt_json_instruction(self):
        """Test that prompt requests JSON output."""
        assert "JSON" in SYSTEM_PROMPT or "json" in SYSTEM_PROMPT


class TestUserPromptTemplate:
    """Tests for user prompt template."""

    def test_template_has_placeholders(self):
        """Test that template has required placeholders."""
        assert "{sender}" in USER_PROMPT_TEMPLATE
        assert "{subject}" in USER_PROMPT_TEMPLATE
        assert "{body}" in USER_PROMPT_TEMPLATE
        assert "{date}" in USER_PROMPT_TEMPLATE
