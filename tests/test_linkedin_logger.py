"""Tests for LinkedIn publisher logger."""

import pytest
import json
from datetime import datetime
from pathlib import Path

from linkedin_publisher.logger import LinkedInLogger


class TestLinkedInLogger:
    """Tests for LinkedInLogger class."""

    def test_init_creates_directory(self, tmp_path):
        """Test logger creates linkedin directory."""
        logs_path = tmp_path / "Logs"

        logger = LinkedInLogger(logs_path)

        assert (logs_path / "linkedin").exists()

    def test_get_log_file_path(self, tmp_path):
        """Test log file path format."""
        logs_path = tmp_path / "Logs"
        logger = LinkedInLogger(logs_path)

        log_file = logger._get_log_file()

        assert "linkedin-" in log_file.name
        assert log_file.suffix == ".log"
        assert log_file.parent == logs_path / "linkedin"

    def test_log_event_writes_json(self, tmp_path):
        """Test log_event writes JSON line."""
        logs_path = tmp_path / "Logs"
        logger = LinkedInLogger(logs_path)

        logger.log_event("test_event", "/path/to/file.md", {"key": "value"})

        log_file = logger._get_log_file()
        assert log_file.exists()

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "test_event"
        assert entry["file_path"] == "/path/to/file.md"
        assert entry["details"]["key"] == "value"
        assert "timestamp" in entry

    def test_log_detected(self, tmp_path):
        """Test log_detected method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_detected("/Approved/linkedin/post.md")

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "detected"
        assert entry["file_path"] == "/Approved/linkedin/post.md"

    def test_log_publishing(self, tmp_path):
        """Test log_publishing method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_publishing("/Approved/linkedin/post.md", "This is my post content...")

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "publishing"
        assert "content_preview" in entry["details"]

    def test_log_published(self, tmp_path):
        """Test log_published method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_published(
            "/Approved/linkedin/post.md",
            post_url="https://linkedin.com/post/123",
            retry_count=2,
            publish_duration_ms=5000,
        )

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "published"
        assert entry["details"]["post_url"] == "https://linkedin.com/post/123"
        assert entry["details"]["retry_count"] == 2
        assert entry["details"]["publish_duration_ms"] == 5000

    def test_log_failed(self, tmp_path):
        """Test log_failed method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_failed(
            "/Approved/linkedin/post.md",
            error="Network timeout",
            error_type="TimeoutError",
            retry_count=3,
            retryable=True,
        )

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "failed"
        assert entry["details"]["error"] == "Network timeout"
        assert entry["details"]["error_type"] == "TimeoutError"
        assert entry["details"]["retryable"] is True

    def test_log_moved_to_done(self, tmp_path):
        """Test log_moved_to_done method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_moved_to_done(
            "/Approved/linkedin/post.md",
            "/Done/linkedin/post.md",
        )

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "moved_to_done"
        assert entry["details"]["new_path"] == "/Done/linkedin/post.md"

    def test_log_moved_to_needs_action(self, tmp_path):
        """Test log_moved_to_needs_action method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_moved_to_needs_action(
            "/Approved/linkedin/post.md",
            "/Needs_Action/linkedin/post.md",
            "Auth failure",
        )

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "moved_to_needs_action"
        assert entry["details"]["reason"] == "Auth failure"

    def test_log_duplicate_skipped(self, tmp_path):
        """Test log_duplicate_skipped method."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_duplicate_skipped(
            "/Approved/linkedin/post.md",
            "abc123def456",
        )

        log_file = logger._get_log_file()
        entry = json.loads(log_file.read_text().strip())

        assert entry["event"] == "duplicate_skipped"
        assert "abc123" in entry["details"]["hash"]

    def test_multiple_logs_append(self, tmp_path):
        """Test multiple log entries append to same file."""
        logger = LinkedInLogger(tmp_path / "Logs")

        logger.log_detected("/file1.md")
        logger.log_detected("/file2.md")
        logger.log_detected("/file3.md")

        log_file = logger._get_log_file()
        lines = log_file.read_text().strip().split("\n")

        assert len(lines) == 3

    def test_get_log_path_for_today(self, tmp_path):
        """Test get_log_path_for_today returns relative path."""
        logger = LinkedInLogger(tmp_path / "Logs")

        path = logger.get_log_path_for_today()

        assert path.startswith("Logs/linkedin/linkedin-")
        assert path.endswith(".log")
