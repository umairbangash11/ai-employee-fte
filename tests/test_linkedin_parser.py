"""Tests for LinkedIn publisher parser."""

import pytest
import tempfile
from pathlib import Path

from linkedin_publisher.parser import (
    parse_approved_file,
    extract_post_content,
    validate_frontmatter,
)
from linkedin_publisher.exceptions import InvalidFrontmatterError


class TestParseApprovedFile:
    """Tests for parse_approved_file function."""

    def test_parse_valid_file(self, tmp_path):
        """Test parsing valid approved file."""
        file_content = """---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
target:
  platform: linkedin
  post_type: text
---

## Content Preview

This is the post content to publish on LinkedIn.
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(file_content)

        post = parse_approved_file(file_path)

        assert post.content == "This is the post content to publish on LinkedIn."
        assert post.frontmatter["type"] == "approval_request"
        assert post.frontmatter["action_type"] == "publish_linkedin_post"

    def test_parse_file_no_frontmatter(self, tmp_path):
        """Test parsing file without frontmatter raises error."""
        file_content = "Just plain content"
        file_path = tmp_path / "test.md"
        file_path.write_text(file_content)

        with pytest.raises(InvalidFrontmatterError) as exc_info:
            parse_approved_file(file_path)

        assert "no frontmatter" in str(exc_info.value).lower()

    def test_parse_file_invalid_yaml(self, tmp_path):
        """Test parsing file with invalid YAML."""
        file_content = """---
type: [unclosed bracket
---

Content
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(file_content)

        with pytest.raises(InvalidFrontmatterError) as exc_info:
            parse_approved_file(file_path)

        assert "yaml" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


class TestExtractPostContent:
    """Tests for extract_post_content function."""

    def test_extract_from_content_preview(self):
        """Test extracting content from ## Content Preview section."""
        body = """## Reasoning

Some reasoning here.

## Content Preview

This is the actual post content.

## Expected Outcome

Post will be published.
"""
        frontmatter = {}

        content = extract_post_content(body, frontmatter)

        assert content == "This is the actual post content."

    def test_extract_from_content_section(self):
        """Test extracting content from ## Content section."""
        body = """## Content

LinkedIn post content here.

## Other Section

Other stuff.
"""
        frontmatter = {}

        content = extract_post_content(body, frontmatter)

        assert content == "LinkedIn post content here."

    def test_extract_from_frontmatter(self):
        """Test extracting content from frontmatter when no section exists."""
        body = "## Other Section\n\nNo content section here."
        frontmatter = {"content": "Content from frontmatter"}

        content = extract_post_content(body, frontmatter)

        assert content == "Content from frontmatter"

    def test_extract_fallback_to_body(self):
        """Test falling back to cleaned body when no content section."""
        body = "Just some plain content without sections."
        frontmatter = {}

        content = extract_post_content(body, frontmatter)

        assert "plain content" in content


class TestValidateFrontmatter:
    """Tests for validate_frontmatter function."""

    def test_valid_frontmatter(self):
        """Test validating correct frontmatter."""
        frontmatter = {
            "type": "approval_request",
            "action_type": "publish_linkedin_post",
            "target": {"platform": "linkedin", "post_type": "text"},
        }

        # Should not raise
        validate_frontmatter(frontmatter)

    def test_invalid_type(self):
        """Test validation fails for wrong type."""
        frontmatter = {
            "type": "something_else",
            "action_type": "publish_linkedin_post",
            "target": {"platform": "linkedin"},
        }

        with pytest.raises(InvalidFrontmatterError) as exc_info:
            validate_frontmatter(frontmatter)

        assert "type=approval_request" in str(exc_info.value)

    def test_invalid_action_type(self):
        """Test validation fails for wrong action_type."""
        frontmatter = {
            "type": "approval_request",
            "action_type": "send_email_reply",
            "target": {"platform": "linkedin"},
        }

        with pytest.raises(InvalidFrontmatterError) as exc_info:
            validate_frontmatter(frontmatter)

        assert "action_type=publish_linkedin_post" in str(exc_info.value)

    def test_invalid_platform(self):
        """Test validation fails for wrong platform."""
        frontmatter = {
            "type": "approval_request",
            "action_type": "publish_linkedin_post",
            "target": {"platform": "twitter"},
        }

        with pytest.raises(InvalidFrontmatterError) as exc_info:
            validate_frontmatter(frontmatter)

        assert "platform=linkedin" in str(exc_info.value)

    def test_missing_target(self):
        """Test validation fails for missing target."""
        frontmatter = {
            "type": "approval_request",
            "action_type": "publish_linkedin_post",
        }

        with pytest.raises(InvalidFrontmatterError):
            validate_frontmatter(frontmatter)
