"""Tests for LinkedIn publisher utilities."""

import pytest
from pathlib import Path

from linkedin_publisher.utils import (
    ensure_directories,
    move_file_to_done,
    move_file_to_needs_action,
    update_frontmatter,
    update_file_with_success,
    update_file_with_failure,
    handle_publish_success,
)


class TestEnsureDirectories:
    """Tests for ensure_directories function."""

    def test_creates_all_directories(self, tmp_path):
        """Test all LinkedIn directories are created."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        dirs = ensure_directories(vault_path)

        assert (vault_path / "Approved" / "linkedin").exists()
        assert (vault_path / "Done" / "linkedin").exists()
        assert (vault_path / "Needs_Action" / "linkedin").exists()
        assert (vault_path / "Logs" / "linkedin").exists()

        assert "approved_linkedin" in dirs
        assert "done_linkedin" in dirs

    def test_idempotent(self, tmp_path):
        """Test calling multiple times is safe."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        ensure_directories(vault_path)
        ensure_directories(vault_path)

        assert (vault_path / "Approved" / "linkedin").exists()


class TestMoveFileToDone:
    """Tests for move_file_to_done function."""

    def test_moves_file(self, tmp_path):
        """Test file is moved to Done directory."""
        source = tmp_path / "source.md"
        source.write_text("content")
        done_dir = tmp_path / "Done" / "linkedin"

        new_path = move_file_to_done(source, done_dir)

        assert not source.exists()
        assert new_path.exists()
        assert new_path.parent == done_dir
        assert new_path.name == "source.md"

    def test_creates_done_directory(self, tmp_path):
        """Test Done directory is created if missing."""
        source = tmp_path / "source.md"
        source.write_text("content")
        done_dir = tmp_path / "Done" / "linkedin"  # Doesn't exist yet

        new_path = move_file_to_done(source, done_dir)

        assert done_dir.exists()
        assert new_path.exists()


class TestMoveFileToNeedsAction:
    """Tests for move_file_to_needs_action function."""

    def test_moves_file(self, tmp_path):
        """Test file is moved to Needs_Action directory."""
        source = tmp_path / "source.md"
        source.write_text("content")
        needs_action_dir = tmp_path / "Needs_Action" / "linkedin"

        new_path = move_file_to_needs_action(source, needs_action_dir)

        assert not source.exists()
        assert new_path.exists()
        assert new_path.parent == needs_action_dir


class TestUpdateFrontmatter:
    """Tests for update_frontmatter function."""

    def test_updates_existing_field(self, tmp_path):
        """Test updating existing frontmatter field."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
status: pending
other: value
---

Body content
""")

        update_frontmatter(file_path, {"status": "published"})

        content = file_path.read_text()
        assert "status: published" in content
        assert "other: value" in content
        assert "Body content" in content

    def test_adds_new_field(self, tmp_path):
        """Test adding new frontmatter field."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
existing: value
---

Body
""")

        update_frontmatter(file_path, {"new_field": "new_value"})

        content = file_path.read_text()
        assert "existing: value" in content
        assert "new_field: new_value" in content

    def test_raises_for_no_frontmatter(self, tmp_path):
        """Test raises error for file without frontmatter."""
        file_path = tmp_path / "test.md"
        file_path.write_text("Just content, no frontmatter")

        with pytest.raises(ValueError) as exc_info:
            update_frontmatter(file_path, {"key": "value"})

        assert "no frontmatter" in str(exc_info.value).lower()


class TestUpdateFileWithSuccess:
    """Tests for update_file_with_success function."""

    def test_updates_status_and_timestamp(self, tmp_path):
        """Test success updates set correct fields."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
status: pending
---

Content
""")

        update_file_with_success(file_path)

        content = file_path.read_text()
        assert "status: published" in content
        assert "published_at:" in content
        assert "executed_by: linkedin_publisher" in content

    def test_includes_post_url(self, tmp_path):
        """Test success includes post URL when provided."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
status: pending
---

Content
""")

        update_file_with_success(file_path, post_url="https://linkedin.com/post/123")

        content = file_path.read_text()
        assert "linkedin_post_url: https://linkedin.com/post/123" in content


class TestUpdateFileWithFailure:
    """Tests for update_file_with_failure function."""

    def test_updates_error_fields(self, tmp_path):
        """Test failure updates set correct fields."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
status: pending
---

Content
""")

        update_file_with_failure(file_path, "Network error", 3)

        content = file_path.read_text()
        assert "status: failed" in content
        assert "last_error: Network error" in content
        assert "retry_count: 3" in content


class TestHandlePublishSuccess:
    """Tests for handle_publish_success function."""

    def test_updates_and_moves(self, tmp_path):
        """Test success handler updates frontmatter and moves file."""
        source_dir = tmp_path / "Approved" / "linkedin"
        source_dir.mkdir(parents=True)
        done_dir = tmp_path / "Done" / "linkedin"

        source = source_dir / "post.md"
        source.write_text("""---
status: pending
---

Content
""")

        new_path = handle_publish_success(source, done_dir)

        assert not source.exists()
        assert new_path.exists()
        assert new_path.parent == done_dir

        content = new_path.read_text()
        assert "status: published" in content
