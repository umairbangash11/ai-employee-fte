"""LinkedIn publisher audit logger."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class LinkedInLogger:
    """Logs LinkedIn publish lifecycle events to /Logs/linkedin/.

    Events logged:
    - detected: File found in /Approved/linkedin/
    - publishing: Publish attempt started
    - published: Post successfully published
    - failed: Publish attempt failed
    - moved_to_done: File moved to /Done/linkedin/
    - moved_to_needs_action: File moved to /Needs_Action/linkedin/
    - duplicate_skipped: Duplicate content skipped

    All logs use JSON lines format (NFR-003).

    Attributes:
        logs_path: Path to /Logs/ directory
    """

    def __init__(self, logs_path: Path):
        """Initialize logger with logs directory.

        Args:
            logs_path: Path to /Logs/ directory
        """
        self.logs_path = Path(logs_path)
        self.linkedin_dir = self.logs_path / "linkedin"
        self.linkedin_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self) -> Path:
        """Get path to current log file.

        Format: /Logs/linkedin/linkedin-YYYYMMDD.log

        Returns:
            Path to log file
        """
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return self.linkedin_dir / f"linkedin-{date_str}.log"

    def _write_log_entry(self, entry: dict) -> None:
        """Write log entry as JSON line.

        Args:
            entry: Log entry dict to write
        """
        log_file = self._get_log_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_event(
        self,
        event: str,
        file_path: str,
        details: Optional[dict] = None,
    ) -> None:
        """Log a LinkedIn publish lifecycle event.

        Args:
            event: Event type (detected, publishing, published, etc.)
            file_path: Path to the approval file
            details: Additional details (post_url, error, etc.)
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "file_path": file_path,
        }

        if details:
            entry["details"] = details

        self._write_log_entry(entry)

    def log_detected(self, file_path: str) -> None:
        """Log file detection event.

        Args:
            file_path: Path to detected file
        """
        self.log_event(
            event="detected",
            file_path=file_path,
        )

    def log_publishing(self, file_path: str, content_preview: str) -> None:
        """Log publish attempt started.

        Args:
            file_path: Path to approval file
            content_preview: First 100 chars of content
        """
        self.log_event(
            event="publishing",
            file_path=file_path,
            details={"content_preview": content_preview[:100]},
        )

    def log_published(
        self,
        file_path: str,
        post_url: Optional[str] = None,
        retry_count: int = 1,
        publish_duration_ms: Optional[int] = None,
    ) -> None:
        """Log successful publish.

        Args:
            file_path: Path to approval file
            post_url: URL of published post (if available)
            retry_count: Number of attempts made
            publish_duration_ms: Time taken in milliseconds
        """
        details = {
            "retry_count": retry_count,
        }
        if post_url:
            details["post_url"] = post_url
        if publish_duration_ms:
            details["publish_duration_ms"] = publish_duration_ms

        self.log_event(
            event="published",
            file_path=file_path,
            details=details,
        )

    def log_failed(
        self,
        file_path: str,
        error: str,
        error_type: Optional[str] = None,
        retry_count: int = 0,
        retryable: bool = True,
    ) -> None:
        """Log publish failure.

        Args:
            file_path: Path to approval file
            error: Error message
            error_type: Exception class name
            retry_count: Number of attempts made
            retryable: Whether error is retryable
        """
        details = {
            "error": error,
            "retry_count": retry_count,
            "retryable": retryable,
        }
        if error_type:
            details["error_type"] = error_type

        self.log_event(
            event="failed",
            file_path=file_path,
            details=details,
        )

    def log_moved_to_done(self, file_path: str, new_path: str) -> None:
        """Log file moved to Done.

        Args:
            file_path: Original path in /Approved/
            new_path: New path in /Done/
        """
        self.log_event(
            event="moved_to_done",
            file_path=file_path,
            details={"new_path": new_path},
        )

    def log_moved_to_needs_action(
        self,
        file_path: str,
        new_path: str,
        reason: str,
    ) -> None:
        """Log file moved to Needs_Action.

        Args:
            file_path: Original path in /Approved/
            new_path: New path in /Needs_Action/
            reason: Why file was moved
        """
        self.log_event(
            event="moved_to_needs_action",
            file_path=file_path,
            details={"new_path": new_path, "reason": reason},
        )

    def log_duplicate_skipped(self, file_path: str, hash_value: str) -> None:
        """Log duplicate content skipped.

        Args:
            file_path: Path to approval file
            hash_value: Content hash that matched
        """
        self.log_event(
            event="duplicate_skipped",
            file_path=file_path,
            details={"hash": hash_value[:8] + "..."},
        )

    def get_log_path_for_today(self) -> str:
        """Get relative log path for frontmatter linking.

        Returns:
            Relative path like "Logs/linkedin/linkedin-20260312.log"
        """
        log_file = self._get_log_file()
        # Return relative path from vault root
        return f"Logs/linkedin/{log_file.name}"
