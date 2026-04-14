"""Integration tests for LinkedIn success flow."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from linkedin_publisher.config import LinkedInPublisherConfig
from linkedin_publisher.logger import LinkedInLogger
from linkedin_publisher.models import PublishResult
from linkedin_publisher.__main__ import process_approved_file


class TestLinkedInSuccessFlow:
    """Integration tests for successful publish flow."""

    @pytest.mark.asyncio
    async def test_full_success_path(self, tmp_path):
        """Test complete success flow: parse -> publish -> move to done."""
        # Setup vault structure
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        # Create test file
        test_file = vault_path / "Approved" / "linkedin" / "test_post.md"
        test_file.write_text("""---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
status: pending
target:
  platform: linkedin
  post_type: text
source:
  path: /Inbox/email/source.md
---

## Content Preview

This is a test LinkedIn post.
""")

        # Create config
        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            session_path=tmp_path / ".watcher-state" / "linkedin" / "session",
            state_path=tmp_path / ".watcher-state" / "linkedin" / "publisher.json",
        )

        # Create logger
        logger = LinkedInLogger(vault_path / "Logs")

        # Mock the publisher
        mock_publisher = MagicMock()
        mock_publisher.publish_with_retry = AsyncMock(return_value=PublishResult(
            success=True,
            post_url="https://linkedin.com/feed/update/urn:li:activity:123",
            retry_count=1,
            publish_duration_ms=5000,
        ))
        mock_publisher.close = AsyncMock()

        # Process the file
        result = await process_approved_file(
            test_file,
            config,
            logger,
            mock_publisher,
            verbose=True,
        )

        # Verify success
        assert result is True

        # Verify file moved to Done
        assert not test_file.exists()
        done_file = vault_path / "Done" / "linkedin" / "test_post.md"
        assert done_file.exists()

        # Verify frontmatter updated
        content = done_file.read_text()
        assert "status: published" in content
        assert "linkedin_post_url:" in content

        # Verify log written
        log_file = logger._get_log_file()
        assert log_file.exists()

    @pytest.mark.asyncio
    async def test_duplicate_content_handled(self, tmp_path):
        """Test that duplicate content is detected and handled."""
        # Setup
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        # Create state with existing hash
        state_dir = tmp_path / ".watcher-state" / "linkedin"
        state_dir.mkdir(parents=True)

        # Create test file
        test_file = vault_path / "Approved" / "linkedin" / "duplicate.md"
        test_file.write_text("""---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
status: pending
target:
  platform: linkedin
source:
  path: /original.md
---

## Content Preview

Duplicate content
""")

        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            session_path=state_dir / "session",
            state_path=state_dir / "publisher.json",
        )
        logger = LinkedInLogger(vault_path / "Logs")

        # First publish
        mock_publisher = MagicMock()
        mock_publisher.publish_with_retry = AsyncMock(return_value=PublishResult(success=True))
        mock_publisher.close = AsyncMock()

        await process_approved_file(test_file, config, logger, mock_publisher, verbose=False)

        # Create second file with same content
        test_file2 = vault_path / "Approved" / "linkedin" / "duplicate2.md"
        test_file2.write_text("""---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T11:00:00Z
status: pending
target:
  platform: linkedin
source:
  path: /original.md
---

## Content Preview

Duplicate content
""")

        # Second publish should skip
        result = await process_approved_file(test_file2, config, logger, mock_publisher, verbose=False)

        # Should succeed (moved to done) but publisher not called again
        assert result is True
        # Publisher should only have been called once (for first file)
        assert mock_publisher.publish_with_retry.call_count == 1
