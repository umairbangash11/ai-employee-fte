"""Integration tests for LinkedIn file detection."""

import pytest
import time
import threading
from pathlib import Path

from linkedin_publisher.detector import LinkedInApprovedDetector


class TestLinkedInDetectionIntegration:
    """Integration tests for file detection within 30 seconds."""

    def test_detect_file_within_timeout(self, tmp_path):
        """Test that files are detected within 30 seconds (FR-001).

        This test creates a file in /Approved/linkedin/ and verifies
        the detector triggers the callback within the timeout.
        """
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        detector = LinkedInApprovedDetector(vault_path, mode="poll", poll_interval=1)

        detected_files = []
        detection_event = threading.Event()

        def on_detected(file_path: Path):
            detected_files.append(file_path)
            detection_event.set()

        # Start detector
        detector.start(on_detected)

        try:
            # Create a file after detector is running
            test_file = approved_dir / "test_post.md"
            test_file.write_text("""---
type: approval_request
action_type: publish_linkedin_post
target:
  platform: linkedin
---

Test content
""")

            # Wait for detection (max 30 seconds per FR-001)
            detected = detection_event.wait(timeout=30)

            assert detected, "File was not detected within 30 seconds"
            assert len(detected_files) >= 1
            assert any(f.name == "test_post.md" for f in detected_files)

        finally:
            detector.stop()

    def test_startup_catchup_processing(self, tmp_path):
        """Test that existing files are processed on startup."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        approved_dir.mkdir(parents=True)

        # Create files before detector starts
        (approved_dir / "existing1.md").write_text("content 1")
        (approved_dir / "existing2.md").write_text("content 2")

        detector = LinkedInApprovedDetector(vault_path)

        # Scan existing should find them
        existing = detector.scan_existing()

        assert len(existing) == 2
        assert {f.name for f in existing} == {"existing1.md", "existing2.md"}

    def test_detection_respects_safety_boundary(self, tmp_path):
        """Test that files in Pending_Approval are never processed."""
        vault_path = tmp_path / "vault"
        approved_dir = vault_path / "Approved" / "linkedin"
        pending_dir = vault_path / "Pending_Approval" / "linkedin"
        approved_dir.mkdir(parents=True)
        pending_dir.mkdir(parents=True)

        # Create files in both directories
        (approved_dir / "approved.md").write_text("content")
        (pending_dir / "pending.md").write_text("content")

        detector = LinkedInApprovedDetector(vault_path)

        # Only approved files should be found
        existing = detector.scan_existing()

        assert len(existing) == 1
        assert existing[0].name == "approved.md"

        # Explicitly verify pending file is rejected
        pending_file = pending_dir / "pending.md"
        assert detector._is_valid_approved_file(pending_file) is False
