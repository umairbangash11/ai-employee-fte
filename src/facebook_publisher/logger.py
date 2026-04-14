"""Audit logger for Facebook Publisher.

Logs all publish events to /Logs/facebook/ as JSON lines.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.utils import ensure_directory

# Standard Python logger for console output
logger = logging.getLogger(__name__)


class FacebookLogger:
    """Logs Facebook publish events to JSON lines files.

    Log files are stored at /Logs/facebook/facebook-YYYYMMDD.log
    Each line is a JSON object with event details.

    Event types:
    - detected: New file detected in /Approved/facebook/
    - validated: File frontmatter validated successfully
    - publishing: Publish attempt started
    - published: Post published successfully
    - failed: Publish attempt failed
    - moved_to_done: File moved to /Done/facebook/
    - moved_to_needs_action: File moved to /Needs_Action/
    - duplicate_skipped: File skipped due to duplicate content hash
    """

    def __init__(self, config: FacebookPublisherConfig):
        """Initialize the logger.

        Args:
            config: Publisher configuration
        """
        self.config = config
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Ensure /Logs/facebook/ directory exists."""
        ensure_directory(self.config.logs_dir)

    def _get_log_path(self) -> Path:
        """Get the current log file path (daily rotation).

        Returns:
            Path to today's log file
        """
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return self.config.logs_dir / f"facebook-{date_str}.log"

    def log_event(
        self,
        event_type: str,
        file_path: Path | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an event to the JSON lines file.

        Args:
            event_type: Type of event (detected, validated, publishing, etc.)
            file_path: Path to the file being processed
            details: Additional event details
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "file": str(file_path) if file_path else None,
        }

        if details:
            event["details"] = details

        # Write JSON line to log file
        log_path = self._get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        # Also log to standard Python logger
        logger.debug(f"[{event_type}] {file_path}: {details}")

    def log_detected(self, file_path: Path) -> None:
        """Log file detection event."""
        self.log_event("detected", file_path)

    def log_validated(self, file_path: Path, content_length: int) -> None:
        """Log successful validation event."""
        self.log_event("validated", file_path, {"content_length": content_length})

    def log_publishing(self, file_path: Path, visibility: str) -> None:
        """Log publish attempt start."""
        self.log_event("publishing", file_path, {"visibility": visibility})

    def log_published(
        self,
        file_path: Path,
        post_url: str | None,
        duration_ms: int | None,
        retry_count: int,
    ) -> None:
        """Log successful publish event."""
        self.log_event(
            "published",
            file_path,
            {
                "post_url": post_url,
                "duration_ms": duration_ms,
                "retry_count": retry_count,
            },
        )

    def log_failed(
        self,
        file_path: Path,
        error: str,
        error_type: str,
        retry_count: int,
    ) -> None:
        """Log failed publish event."""
        self.log_event(
            "failed",
            file_path,
            {
                "error": error,
                "error_type": error_type,
                "retry_count": retry_count,
            },
        )

    def log_moved_to_done(self, source_path: Path, dest_path: Path) -> None:
        """Log file movement to /Done/."""
        self.log_event(
            "moved_to_done",
            source_path,
            {"destination": str(dest_path)},
        )

    def log_moved_to_needs_action(self, source_path: Path, dest_path: Path) -> None:
        """Log file movement to /Needs_Action/."""
        self.log_event(
            "moved_to_needs_action",
            source_path,
            {"destination": str(dest_path)},
        )

    def log_duplicate_skipped(self, file_path: Path, content_hash: str) -> None:
        """Log duplicate content skipped."""
        self.log_event(
            "duplicate_skipped",
            file_path,
            {"content_hash": content_hash},
        )

    def log_session_expired(self) -> None:
        """Log session expiry event."""
        self.log_event("session_expired", details={"action": "re-authentication required"})
