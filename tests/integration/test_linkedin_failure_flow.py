"""Integration tests for LinkedIn failure flow."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from linkedin_publisher.config import LinkedInPublisherConfig
from linkedin_publisher.logger import LinkedInLogger
from linkedin_publisher.models import PublishResult
from linkedin_publisher.__main__ import process_approved_file


class TestLinkedInFailureFlow:
    """Integration tests for failure handling."""

    @pytest.mark.asyncio
    async def test_retryable_failure_preserves_file(self, tmp_path):
        """Test that retryable failure keeps file in Approved with error metadata."""
        # Setup
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Needs_Action" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        test_file = vault_path / "Approved" / "linkedin" / "failing_post.md"
        test_file.write_text("""---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
status: pending
target:
  platform: linkedin
---

## Content Preview

This post will fail.
""")

        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            session_path=tmp_path / ".watcher-state" / "linkedin" / "session",
            state_path=tmp_path / ".watcher-state" / "linkedin" / "publisher.json",
        )
        logger = LinkedInLogger(vault_path / "Logs")

        # Mock publisher to return failure
        mock_publisher = MagicMock()
        mock_publisher.publish_with_retry = AsyncMock(return_value=PublishResult(
            success=False,
            error="Network timeout",
            error_type="TimeoutError",
            retry_count=3,
        ))
        mock_publisher.close = AsyncMock()

        # Process
        result = await process_approved_file(test_file, config, logger, mock_publisher, verbose=False)

        # Verify failure
        assert result is False

        # File should still be in Approved (not moved)
        assert test_file.exists()

        # Frontmatter should have error info
        content = test_file.read_text()
        assert "status: failed" in content
        assert "last_error:" in content
        assert "retry_count:" in content

    @pytest.mark.asyncio
    async def test_auth_failure_moves_to_needs_action(self, tmp_path):
        """Test that auth failure moves file to Needs_Action."""
        # Setup
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Needs_Action" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        test_file = vault_path / "Approved" / "linkedin" / "auth_failure.md"
        test_file.write_text("""---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
status: pending
target:
  platform: linkedin
---

## Content Preview

This will have auth failure.
""")

        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            session_path=tmp_path / ".watcher-state" / "linkedin" / "session",
            state_path=tmp_path / ".watcher-state" / "linkedin" / "publisher.json",
        )
        logger = LinkedInLogger(vault_path / "Logs")

        # Mock publisher to return auth failure
        mock_publisher = MagicMock()
        mock_publisher.publish_with_retry = AsyncMock(return_value=PublishResult(
            success=False,
            error="Session expired",
            error_type="AuthenticationError",
            retry_count=1,
        ))
        mock_publisher.close = AsyncMock()

        # Process
        result = await process_approved_file(test_file, config, logger, mock_publisher, verbose=False)

        # Verify failure
        assert result is False

        # File should be moved to Needs_Action
        assert not test_file.exists()
        needs_action_file = vault_path / "Needs_Action" / "linkedin" / "auth_failure.md"
        assert needs_action_file.exists()

    @pytest.mark.asyncio
    async def test_invalid_frontmatter_moves_to_needs_action(self, tmp_path):
        """Test that invalid frontmatter moves file to Needs_Action."""
        # Setup
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)
        (vault_path / "Done" / "linkedin").mkdir(parents=True)
        (vault_path / "Needs_Action" / "linkedin").mkdir(parents=True)
        (vault_path / "Logs" / "linkedin").mkdir(parents=True)

        # Invalid: wrong action_type
        test_file = vault_path / "Approved" / "linkedin" / "invalid.md"
        test_file.write_text("""---
type: approval_request
action_type: send_email_reply
target:
  platform: email
---

Wrong action type
""")

        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            session_path=tmp_path / ".watcher-state" / "linkedin" / "session",
            state_path=tmp_path / ".watcher-state" / "linkedin" / "publisher.json",
        )
        logger = LinkedInLogger(vault_path / "Logs")

        # Process (no publisher needed - should fail at parse)
        result = await process_approved_file(test_file, config, logger, verbose=False)

        # Verify failure
        assert result is False

        # File should be moved to Needs_Action
        assert not test_file.exists()
        needs_action_file = vault_path / "Needs_Action" / "linkedin" / "invalid.md"
        assert needs_action_file.exists()
