"""Tests for email file parsing."""

from pathlib import Path
import tempfile

import pytest

from router.parser import (
    EmailFrontmatter,
    InboxFile,
    MalformedFrontmatterError,
    extract_frontmatter,
    parse_email_file,
)


class TestExtractFrontmatter:
    """Tests for extract_frontmatter helper."""

    def test_valid_frontmatter(self):
        """Extracts valid YAML frontmatter."""
        content = """---
source: gmail
sender: "John Doe"
subject: "Test Email"
---

This is the body."""

        fm, body = extract_frontmatter(content)
        assert fm["source"] == "gmail"
        assert fm["sender"] == "John Doe"
        assert fm["subject"] == "Test Email"
        assert body == "This is the body."

    def test_no_frontmatter(self):
        """Returns empty dict when no frontmatter present."""
        content = "Just a plain markdown file."
        fm, body = extract_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_unclosed_frontmatter(self):
        """Raises ValueError for unclosed frontmatter."""
        content = """---
source: gmail
sender: "John Doe"

Body without closing delimiter."""

        with pytest.raises(ValueError, match="Unclosed frontmatter"):
            extract_frontmatter(content)

    def test_invalid_yaml(self):
        """Raises ValueError for invalid YAML."""
        content = """---
source: gmail
sender: [unclosed bracket
---

Body."""

        with pytest.raises(ValueError, match="Invalid YAML"):
            extract_frontmatter(content)

    def test_empty_frontmatter(self):
        """Handles empty frontmatter block."""
        content = """---
---

Body after empty frontmatter."""

        fm, body = extract_frontmatter(content)
        assert fm == {}
        assert body == "Body after empty frontmatter."


class TestEmailFrontmatter:
    """Tests for EmailFrontmatter dataclass."""

    def test_defaults(self):
        """EmailFrontmatter has sensible defaults."""
        fm = EmailFrontmatter()
        assert fm.source == "gmail"
        assert fm.urgency == "normal"
        assert fm.starred is False
        assert fm.important is False
        assert fm.status == "unread"

    def test_custom_values(self):
        """EmailFrontmatter accepts custom values."""
        fm = EmailFrontmatter(
            source="whatsapp",
            captured_at="2026-02-27T14:30:00Z",
            sender="Jane",
            subject="Hello",
            urgency="urgent",
            starred=True,
            important=True,
        )
        assert fm.source == "whatsapp"
        assert fm.urgency == "urgent"
        assert fm.starred is True


class TestParseEmailFile:
    """Tests for parse_email_file function."""

    def test_parse_valid_file(self, tmp_path):
        """Parses a valid email file."""
        email_file = tmp_path / "test-email.md"
        email_file.write_text("""---
source: gmail
captured_at: "2026-02-27T14:30:00Z"
sender: "John Doe"
subject: "Important Meeting"
urgency: urgent
starred: true
important: false
status: unread
tags: [inbox, gmail]
---

# Important Meeting

Hi team,

Please join the meeting at 3 PM.

Best,
John
""")

        result = parse_email_file(email_file)

        assert isinstance(result, InboxFile)
        assert result.path == email_file
        assert result.frontmatter.source == "gmail"
        assert result.frontmatter.sender == "John Doe"
        assert result.frontmatter.subject == "Important Meeting"
        assert result.frontmatter.urgency == "urgent"
        assert result.frontmatter.starred is True
        assert result.frontmatter.important is False
        assert result.subject == "Important Meeting"
        assert "Please join the meeting" in result.body
        assert result.file_size > 0

    def test_parse_minimal_file(self, tmp_path):
        """Parses file with minimal frontmatter."""
        email_file = tmp_path / "minimal.md"
        email_file.write_text("""---
source: gmail
captured_at: "2026-02-27T14:30:00Z"
sender: "Jane"
---

Short message.""")

        result = parse_email_file(email_file)

        assert result.frontmatter.subject == "(no subject)"
        assert result.frontmatter.urgency == "normal"
        assert result.frontmatter.starred is False

    def test_parse_file_not_found(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_email_file("/nonexistent/path/email.md")

    def test_parse_malformed_yaml(self, tmp_path):
        """Raises MalformedFrontmatterError for invalid YAML."""
        email_file = tmp_path / "malformed.md"
        email_file.write_text("""---
source: gmail
sender: [broken yaml
---

Body.""")

        with pytest.raises(MalformedFrontmatterError) as exc_info:
            parse_email_file(email_file)

        assert exc_info.value.path == email_file
        assert "Invalid YAML" in exc_info.value.reason

    def test_parse_unclosed_frontmatter(self, tmp_path):
        """Raises MalformedFrontmatterError for unclosed frontmatter."""
        email_file = tmp_path / "unclosed.md"
        email_file.write_text("""---
source: gmail
sender: "John"

Missing closing delimiter.""")

        with pytest.raises(MalformedFrontmatterError) as exc_info:
            parse_email_file(email_file)

        assert "Unclosed frontmatter" in exc_info.value.reason

    def test_parse_no_frontmatter(self, tmp_path):
        """Handles file without frontmatter gracefully."""
        email_file = tmp_path / "no-frontmatter.md"
        email_file.write_text("Just plain text, no YAML.")

        result = parse_email_file(email_file)

        assert result.frontmatter.source == "gmail"
        assert result.frontmatter.subject == "(no subject)"
        assert result.body == "Just plain text, no YAML."

    def test_parse_string_path(self, tmp_path):
        """Accepts string path argument."""
        email_file = tmp_path / "string-path.md"
        email_file.write_text("""---
source: gmail
sender: "Test"
---

Content.""")

        result = parse_email_file(str(email_file))
        assert result.path == email_file
