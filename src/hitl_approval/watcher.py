"""Approval watcher for detecting file moves between approval directories."""

import logging
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent

from .logger import ApprovalLogger

logger = logging.getLogger(__name__)


class ApprovalEventHandler(FileSystemEventHandler):
    """Handles file system events for approval directories.

    Detects:
    - Files created in /Approved/ → log approval
    - Files created in /Rejected/ → log rejection
    - Files deleted from /Pending_Approval/ → log abandoned
    """

    def __init__(self, vault_path: Path, approval_logger: ApprovalLogger):
        """Initialize handler.

        Args:
            vault_path: Path to Obsidian vault
            approval_logger: Logger for approval events
        """
        super().__init__()
        self.vault_path = Path(vault_path)
        self.logger = approval_logger
        self._pending_files: dict[str, str] = {}  # filename -> original_path

    def _is_approved_path(self, path: str) -> bool:
        """Check if path is in /Approved/ directory.

        Args:
            path: File path to check

        Returns:
            True if in /Approved/
        """
        return "/Approved/" in path or "\\Approved\\" in path

    def _is_rejected_path(self, path: str) -> bool:
        """Check if path is in /Rejected/ directory.

        Args:
            path: File path to check

        Returns:
            True if in /Rejected/
        """
        return "/Rejected/" in path or "\\Rejected\\" in path

    def _is_pending_approval_path(self, path: str) -> bool:
        """Check if path is in /Pending_Approval/ directory.

        Args:
            path: File path to check

        Returns:
            True if in /Pending_Approval/
        """
        return "/Pending_Approval/" in path or "\\Pending_Approval\\" in path

    def _get_relative_path(self, path: str) -> str:
        """Get path relative to vault.

        Args:
            path: Absolute path

        Returns:
            Path relative to vault root
        """
        try:
            return str(Path(path).relative_to(self.vault_path))
        except ValueError:
            return path

    def _handle_approval(self, path: str) -> None:
        """Handle file created in /Approved/.

        Args:
            path: Path to approved file
        """
        relative_path = self._get_relative_path(path)
        filename = Path(path).name

        # Try to find original path from pending files
        original_path = self._pending_files.pop(filename, f"Pending_Approval/{filename}")

        logger.info(f"Approval detected: {filename}")
        self.logger.log_approved(relative_path, original_path)

    def _handle_rejection(self, path: str) -> None:
        """Handle file created in /Rejected/.

        Args:
            path: Path to rejected file
        """
        relative_path = self._get_relative_path(path)
        filename = Path(path).name

        # Try to find original path from pending files
        original_path = self._pending_files.pop(filename, f"Pending_Approval/{filename}")

        logger.info(f"Rejection detected: {filename}")
        self.logger.log_rejected(relative_path, original_path)

    def _handle_pending_deleted(self, path: str) -> None:
        """Handle file deleted from /Pending_Approval/.

        This could be:
        1. File moved to /Approved/ or /Rejected/ (will be handled by on_created)
        2. File truly deleted (abandoned)

        We track the filename to correlate with any subsequent create event.
        If no corresponding create event occurs, we schedule an abandoned log.

        Args:
            path: Path that was deleted
        """
        import threading

        filename = Path(path).name
        relative_path = self._get_relative_path(path)

        # Track for potential move detection
        self._pending_files[filename] = relative_path

        # Schedule abandoned check after a short delay
        # If file appears in Approved/Rejected, it will be removed from _pending_files
        def check_abandoned():
            if filename in self._pending_files:
                # File was not moved, it was truly deleted (abandoned)
                logger.info(f"Abandoned detected: {filename}")
                self.logger.log_abandoned(self._pending_files.pop(filename))

        # Wait 2 seconds for potential move event
        timer = threading.Timer(2.0, check_abandoned)
        timer.daemon = True
        timer.start()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file created event.

        Args:
            event: File created event
        """
        if event.is_directory:
            return

        if not event.src_path.endswith(".md"):
            return

        if self._is_approved_path(event.src_path):
            self._handle_approval(event.src_path)
        elif self._is_rejected_path(event.src_path):
            self._handle_rejection(event.src_path)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Handle file deleted event.

        Args:
            event: File deleted event
        """
        if event.is_directory:
            return

        if not event.src_path.endswith(".md"):
            return

        if self._is_pending_approval_path(event.src_path):
            self._handle_pending_deleted(event.src_path)


class ApprovalWatcher:
    """Watches for file moves between approval directories.

    Monitors:
    - /Pending_Approval/email/
    - /Pending_Approval/linkedin/
    - /Approved/email/
    - /Approved/linkedin/
    - /Rejected/email/
    - /Rejected/linkedin/

    Logs all state transitions to /Logs/approvals/.
    """

    def __init__(
        self,
        vault_path: Path,
        log_callback: Optional[Callable] = None,
    ):
        """Initialize watcher.

        Args:
            vault_path: Path to Obsidian vault
            log_callback: Optional callback for log events
        """
        self.vault_path = Path(vault_path)
        self.log_callback = log_callback
        self.observer = Observer()
        self._running = False

        # Initialize logger
        self.approval_logger = ApprovalLogger(self.vault_path / "Logs")

        # Initialize event handler
        self.event_handler = ApprovalEventHandler(self.vault_path, self.approval_logger)

    def start(self) -> None:
        """Start watching approval directories.

        Watches:
        - /Pending_Approval/email/ and /Pending_Approval/linkedin/
        - /Approved/email/ and /Approved/linkedin/
        - /Rejected/email/ and /Rejected/linkedin/
        """
        if self._running:
            return

        # Directories to watch
        watch_dirs = [
            self.vault_path / "Pending_Approval" / "email",
            self.vault_path / "Pending_Approval" / "linkedin",
            self.vault_path / "Approved" / "email",
            self.vault_path / "Approved" / "linkedin",
            self.vault_path / "Rejected" / "email",
            self.vault_path / "Rejected" / "linkedin",
        ]

        # Ensure directories exist
        for dir_path in watch_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Schedule watches
        for dir_path in watch_dirs:
            self.observer.schedule(
                self.event_handler,
                str(dir_path),
                recursive=False,
            )
            logger.info(f"Watching: {dir_path}")

        # Start observer
        self.observer.start()
        self._running = True
        logger.info("Approval watcher started")

    def stop(self) -> None:
        """Stop the watcher."""
        if not self._running:
            return

        self.observer.stop()
        self.observer.join()
        self._running = False
        logger.info("Approval watcher stopped")

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running
