"""Audit logger for X Publisher."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from x_publisher.config import XPublisherConfig
from x_publisher.utils import ensure_directory

logger = logging.getLogger(__name__)


class XLogger:
    """Logs X publish events to JSON lines files in vault/Logs/."""

    def __init__(self, config: XPublisherConfig):
        self.config = config
        ensure_directory(config.logs_dir)

    def _get_log_path(self) -> Path:
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return self.config.logs_dir / f"x-{date_str}.log"

    def log_event(self, event_type: str, file_path: Path | None = None, details: dict[str, Any] | None = None) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "file": str(file_path) if file_path else None,
        }
        if details:
            event["details"] = details
        log_path = self._get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        logger.debug(f"[{event_type}] {file_path}: {details}")

    def write_vault_log_entry(
        self,
        action_type: str,
        source_path: str,
        dest_path: str,
        outcome: str,
        details: str,
    ) -> None:
        """Write a 6-field vault log entry per Constitution Principle IX."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "timestamp": timestamp,
            "action_type": action_type,
            "source_path": source_path,
            "dest_path": dest_path,
            "outcome": outcome,
            "details": details,
        }
        log_path = self._get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_detected(self, file_path: Path) -> None:
        self.log_event("detected", file_path)

    def log_validated(self, file_path: Path, content_length: int) -> None:
        self.log_event("validated", file_path, {"content_length": content_length})

    def log_publishing(self, file_path: Path, char_count: int | None = None) -> None:
        self.log_event("publishing", file_path, {"char_count": char_count})

    def log_published(self, file_path: Path, post_url: str | None, duration_ms: int | None, retry_count: int) -> None:
        self.log_event("published", file_path, {"post_url": post_url, "duration_ms": duration_ms, "retry_count": retry_count})

    def log_failed(self, file_path: Path, error: str, error_type: str, retry_count: int) -> None:
        self.log_event("failed", file_path, {"error": error, "error_type": error_type, "retry_count": retry_count})

    def log_moved_to_done(self, source_path: Path, dest_path: Path) -> None:
        self.log_event("moved_to_done", source_path, {"destination": str(dest_path)})

    def log_moved_to_needs_action(self, source_path: Path, dest_path: Path) -> None:
        self.log_event("moved_to_needs_action", source_path, {"destination": str(dest_path)})

    def log_session_expired(self) -> None:
        self.log_event("session_expired", details={"action": "re-authentication required"})
