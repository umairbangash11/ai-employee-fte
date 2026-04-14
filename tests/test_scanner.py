"""Tests for email_reasoner.scanner module."""

import tempfile
from pathlib import Path

import pytest

from email_reasoner.scanner import scan_inbox, parse_email_file, scan_and_parse_inbox


class TestScanInbox:
    """Tests for scan_inbox function."""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning an empty inbox directory."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        result = scan_inbox(inbox)
        assert result == []

    def test_scan_nonexistent_directory(self, tmp_path):
        """Test scanning a non-existent directory returns empty list."""
        inbox = tmp_path / "does_not_exist"

        result = scan_inbox(inbox)
        assert result == []

    def test_scan_finds_md_files(self, tmp_path):
        """Test that scan finds all .md files."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        # Create some .md files
        (inbox / "email1.md").write_text("# Email 1")
        (inbox / "email2.md").write_text("# Email 2")
        (inbox / "email3.md").write_text("# Email 3")

        result = scan_inbox(inbox)
        assert len(result) == 3
        assert all(p.suffix == ".md" for p in result)

    def test_scan_ignores_non_md_files(self, tmp_path):
        """Test that scan ignores non-.md files."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        # Create mixed files
        (inbox / "email1.md").write_text("# Email 1")
        (inbox / "notes.txt").write_text("notes")
        (inbox / "data.json").write_text("{}")

        result = scan_inbox(inbox)
        assert len(result) == 1
        assert result[0].name == "email1.md"


class TestParseEmailFile:
    """Tests for parse_email_file function."""

    def test_parse_valid_email(self, tmp_path):
        """Test parsing a valid email file with frontmatter."""
        email_content = """---
message_id: "abc123"
thread_id: "xyz789"
sender: "test@example.com"
subject: "Test Email"
captured_at: "2026-03-07T10:00:00Z"
urgency: normal
status: unread
tags: [inbox, gmail]
attachments: []
---

# Test Email

This is the email body.
"""
        email_file = tmp_path / "test_email.md"
        email_file.write_text(email_content)

        result = parse_email_file(email_file)

        assert result is not None
        assert result.message_id == "abc123"
        assert result.thread_id == "xyz789"
        assert result.sender == "test@example.com"
        assert result.subject == "Test Email"
        assert result.urgency == "normal"
        assert "This is the email body." in result.body

    def test_parse_missing_frontmatter(self, tmp_path):
        """Test that missing frontmatter returns None."""
        email_file = tmp_path / "no_frontmatter.md"
        email_file.write_text("# Just markdown, no frontmatter")

        result = parse_email_file(email_file)
        # frontmatter library returns empty metadata, so message_id check fails
        assert result is None

    def test_parse_missing_message_id(self, tmp_path):
        """Test that missing message_id returns None."""
        email_content = """---
sender: "test@example.com"
subject: "No message ID"
---

Body content.
"""
        email_file = tmp_path / "no_message_id.md"
        email_file.write_text(email_content)

        result = parse_email_file(email_file)
        assert result is None

    def test_parse_empty_body(self, tmp_path):
        """Test that empty body is handled correctly."""
        email_content = """---
message_id: "empty_body_123"
sender: "test@example.com"
subject: "Empty body email"
---
"""
        email_file = tmp_path / "empty_body.md"
        email_file.write_text(email_content)

        result = parse_email_file(email_file)

        assert result is not None
        assert result.message_id == "empty_body_123"
        assert result.body == ""

    def test_wikilink_generation(self, tmp_path):
        """Test that wikilink property generates correct format."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        email_content = """---
message_id: "wikilink_test"
sender: "test@example.com"
subject: "Wikilink Test"
---

Body.
"""
        email_file = inbox / "20260307_test.md"
        email_file.write_text(email_content)

        result = parse_email_file(email_file)

        assert result is not None
        assert "Inbox/email/20260307_test.md" in result.wikilink
        assert result.wikilink.startswith("[[")
        assert result.wikilink.endswith("]]")


class TestScanAndParseInbox:
    """Tests for scan_and_parse_inbox convenience function."""

    def test_scan_and_parse_multiple_emails(self, tmp_path):
        """Test scanning and parsing multiple valid emails."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        for i in range(3):
            email_content = f"""---
message_id: "msg_{i}"
sender: "sender{i}@example.com"
subject: "Email {i}"
---

Body {i}.
"""
            (inbox / f"email_{i}.md").write_text(email_content)

        results = scan_and_parse_inbox(inbox)

        assert len(results) == 3
        message_ids = {e.message_id for e in results}
        assert message_ids == {"msg_0", "msg_1", "msg_2"}

    def test_scan_and_parse_skips_invalid(self, tmp_path):
        """Test that invalid emails are skipped."""
        inbox = tmp_path / "Inbox" / "email"
        inbox.mkdir(parents=True)

        # Valid email
        valid_content = """---
message_id: "valid"
sender: "valid@example.com"
subject: "Valid"
---

Valid body.
"""
        (inbox / "valid.md").write_text(valid_content)

        # Invalid email (no message_id)
        invalid_content = """---
sender: "invalid@example.com"
subject: "Invalid"
---

Invalid body.
"""
        (inbox / "invalid.md").write_text(invalid_content)

        results = scan_and_parse_inbox(inbox)

        assert len(results) == 1
        assert results[0].message_id == "valid"
