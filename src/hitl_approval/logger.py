"""Approval lifecycle logger for HITL system."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_log_path(logs_path: Path) -> Path:
    """Get path to today's approval log file.

    Format: /Logs/approvals/approval-YYYYMMDD.log

    Args:
        logs_path: Path to /Logs/ directory

    Returns:
        Path to log file
    """
    approvals_dir = logs_path / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y%m%d")
    return approvals_dir / f"approval-{date_str}.log"


class ApprovalLogger:
    """Logs approval lifecycle events to /Logs/approvals/.

    Events logged:
    - created: Approval request file written
    - approved: File moved to /Approved/
    - rejected: File moved to /Rejected/
    - expired: Pending request past expires_at
    - error: Invalid frontmatter or processing error
    - abandoned: File deleted from /Pending_Approval/

    All logs use JSON lines format (NFR-003).
    """

    def __init__(self, logs_path: Path):
        """Initialize logger with logs directory.

        Args:
            logs_path: Path to /Logs/ directory
        """
        self.logs_path = Path(logs_path)
        self.approvals_dir = self.logs_path / "approvals"
        self.approvals_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self) -> Path:
        """Get path to current log file."""
        return get_log_path(self.logs_path)

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
        actor: str,
        action_type: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log an approval lifecycle event.

        Args:
            event: Event type (created, approved, rejected, expired, error, abandoned)
            file_path: Path to approval file
            actor: Who triggered the event (email_reasoner, orchestrator, human, system)
            action_type: Type of action (send_email_reply, etc.)
            details: Additional details (target, subject, error message, etc.)
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "file_path": file_path,
            "actor": actor,
        }

        if action_type:
            entry["action_type"] = action_type

        if details:
            entry["details"] = details

        self._write_log_entry(entry)

    def log_created(
        self,
        file_path: str,
        action_type: str,
        actor: str,
        target: str,
        subject: str,
    ) -> None:
        """Log approval request creation.

        Args:
            file_path: Path to created file
            action_type: Type of action
            actor: Creator (email_reasoner, orchestrator)
            target: Target recipient
            subject: Action subject
        """
        self.log_event(
            event="created",
            file_path=file_path,
            actor=actor,
            action_type=action_type,
            details={"target": target, "subject": subject},
        )

    def log_approved(self, file_path: str, original_path: str) -> None:
        """Log approval event.

        Args:
            file_path: New path in /Approved/
            original_path: Original path in /Pending_Approval/
        """
        self.log_event(
            event="approved",
            file_path=file_path,
            actor="human",
            details={"original_path": original_path},
        )

    def log_rejected(self, file_path: str, original_path: str) -> None:
        """Log rejection event.

        Args:
            file_path: New path in /Rejected/
            original_path: Original path in /Pending_Approval/
        """
        self.log_event(
            event="rejected",
            file_path=file_path,
            actor="human",
            details={"original_path": original_path},
        )

    def log_abandoned(self, file_path: str) -> None:
        """Log abandoned event (file deleted from Pending).

        Args:
            file_path: Path that was deleted
        """
        self.log_event(
            event="abandoned",
            file_path=file_path,
            actor="human",
        )

    def log_error(self, file_path: str, error_message: str) -> None:
        """Log error event.

        Args:
            file_path: Path to problematic file
            error_message: Error description
        """
        self.log_event(
            event="error",
            file_path=file_path,
            actor="system",
            details={"error": error_message},
        )
