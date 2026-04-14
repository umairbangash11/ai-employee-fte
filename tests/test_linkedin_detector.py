"""Tests for LinkedIn publisher detector."""

import pytest
import time
from pathlib import Path

from linkedin_publisher.detector import LinkedInApprovedDetector


class TestLinkedInApprovedDetector:
    """Tests for LinkedInApprovedDetector class."""

    def test_scan_existing_empty(self, tmp_path):
        """Test scanning empty directory."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        detector = LinkedInApprovedDetector(vault_path)
        files = detector.scan_existing()

        assert files == []

    def test_scan_existing_with_files(self, tmp_path):
        """Test scanning directory with markdown files."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        # Create test files with different mtimes
        (approved_dir / "file1.md").write_text("content 1")
        time.sleep(0.1)
        (approved_dir / "file2.md").write_text("content 2")
        time.sleep(0.1)
        (approved_dir / "file3.md").write_text("content 3")

        detector = LinkedInApprovedDetector(vault_path)
        files = detector.scan_existing()

        assert len(files) == 3
        # Should be sorted oldest first
        assert files[0].name == "file1.md"
        assert files[2].name == "file3.md"

    def test_scan_existing_ignores_non_md(self, tmp_path):
        """Test that non-markdown files are ignored."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        (approved_dir / "file.md").write_text("markdown")
        (approved_dir / "file.txt").write_text("text")
        (approved_dir / "file.json").write_text("{}")

        detector = LinkedInApprovedDetector(vault_path)
        files = detector.scan_existing()

        assert len(files) == 1
        assert files[0].name == "file.md"

    def test_is_valid_approved_file(self, tmp_path):
        """Test validation of approved files."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        valid_file = approved_dir / "valid.md"
        valid_file.write_text("content")

        detector = LinkedInApprovedDetector(vault_path)

        assert detector._is_valid_approved_file(valid_file) is True

    def test_is_valid_rejects_non_md(self, tmp_path):
        """Test that non-md files are rejected."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        txt_file = approved_dir / "file.txt"
        txt_file.write_text("content")

        detector = LinkedInApprovedDetector(vault_path)

        assert detector._is_valid_approved_file(txt_file) is False

    def test_is_valid_rejects_pending_approval(self, tmp_path):
        """Test that files in Pending_Approval are rejected."""
        vault_path = tmp_path / "vault"
        pending_dir = vault_path / "Pending_Approval" / "linkedin"
        pending_dir.mkdir(parents=True)

        pending_file = pending_dir / "pending.md"
        pending_file.write_text("content")

        detector = LinkedInApprovedDetector(vault_path)

        assert detector._is_valid_approved_file(pending_file) is False

    def test_is_valid_rejects_outside_approved(self, tmp_path):
        """Test that files outside approved_dir are rejected."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        other_dir = vault_path / "Other"
        approved_dir.mkdir(parents=True)
        other_dir.mkdir(parents=True)

        other_file = other_dir / "file.md"
        other_file.write_text("content")

        detector = LinkedInApprovedDetector(vault_path)

        assert detector._is_valid_approved_file(other_file) is False

    def test_is_valid_rejects_nonexistent(self, tmp_path):
        """Test that non-existent files are rejected."""
        vault_path = tmp_path / "vault"
        (vault_path / "Approved" / "linkedin").mkdir(parents=True)

        detector = LinkedInApprovedDetector(vault_path)
        nonexistent = vault_path / "Approved" / "linkedin" / "missing.md"

        assert detector._is_valid_approved_file(nonexistent) is False

    def test_scan_creates_directory_if_missing(self, tmp_path):
        """Test that scan_existing handles missing directory."""
        vault_path = tmp_path / "vault"
        # Don't create the directory

        detector = LinkedInApprovedDetector(vault_path)
        files = detector.scan_existing()

        assert files == []
