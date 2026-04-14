"""File detection for approved Facebook posts.

Monitors /Approved/facebook/ for new files using watchdog or polling.
Does NOT monitor /Pending_Approval/facebook/ (safety boundary).
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.exceptions import DetectionError

logger = logging.getLogger(__name__)


class ApprovedFileHandler(FileSystemEventHandler):
    """Watchdog handler for approved Facebook post files."""

    def __init__(self, callback: Callable[[Path], None], approved_dir: Path):
        self.callback = callback
        self.approved_dir = approved_dir
        super().__init__()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._is_valid_approved_file(path):
            logger.info(f"Detected new file: {path}")
            self.callback(path)

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle file move events (file moved into the directory)."""
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if self._is_valid_approved_file(path):
            logger.info(f"Detected moved file: {path}")
            self.callback(path)

    def _is_valid_approved_file(self, path: Path) -> bool:
        """Validate file is in /Approved/facebook/ and is markdown.

        SAFETY BOUNDARY: Rejects files from /Pending_Approval/.
        """
        # Must be a markdown file
        if path.suffix.lower() != ".md":
            return False

        # Must be within the approved directory
        try:
            path.relative_to(self.approved_dir)
        except ValueError:
            return False

        # SAFETY: Must NOT contain /Pending_Approval/ in path
        if "/Pending_Approval/" in str(path) or "\\Pending_Approval\\" in str(path):
            logger.warning(f"Rejected file from Pending_Approval: {path}")
            return False

        return True


class FacebookApprovedDetector:
    """Detects approved Facebook posts in /Approved/facebook/.

    Monitors for:
    - New files created (via watch or poll)
    - Existing files at startup (catch-up processing)

    Does NOT monitor /Pending_Approval/facebook/ (FR-010).
    """

    def __init__(self, config: FacebookPublisherConfig):
        """Initialize the detector.

        Args:
            config: Publisher configuration
        """
        self.config = config
        self.approved_dir = config.approved_dir
        self.mode = config.detection_mode
        self._observer: Observer | None = None
        self._poll_thread: threading.Thread | None = None
        self._running = False
        self._callback: Callable[[Path], None] | None = None
        self._processed_in_session: set[Path] = set()

    def scan_existing(self) -> list[Path]:
        """Return all .md files in /Approved/facebook/ sorted by mtime (oldest first).

        Returns:
            List of paths to existing approved files
        """
        if not self.approved_dir.exists():
            logger.debug(f"Approved directory does not exist: {self.approved_dir}")
            return []

        files = []
        for path in self.approved_dir.glob("*.md"):
            if self._is_valid_approved_file(path):
                files.append(path)

        # Sort by modification time (oldest first) for FIFO processing
        files.sort(key=lambda p: p.stat().st_mtime)
        logger.info(f"Found {len(files)} existing approved files")
        return files

    def start(self, callback: Callable[[Path], None]) -> None:
        """Start detection. Calls callback for each detected file.

        Args:
            callback: Function to call when a file is detected

        Raises:
            DetectionError: If detection cannot be started
        """
        if self._running:
            logger.warning("Detector already running")
            return

        self._callback = callback
        self._running = True
        self._processed_in_session.clear()

        # Create approved directory if it doesn't exist
        self.approved_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "watch":
            self._start_watcher()
        else:
            self._start_poll()

        logger.info(f"Started detector in {self.mode} mode")

    def stop(self) -> None:
        """Stop detection."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5)
            self._poll_thread = None

        logger.info("Detector stopped")

    def _start_watcher(self) -> None:
        """Start watchdog observer for file system events."""
        try:
            self._observer = Observer()
            handler = ApprovedFileHandler(self._on_file_detected, self.approved_dir)
            self._observer.schedule(handler, str(self.approved_dir), recursive=False)
            self._observer.start()
            logger.debug(f"Watchdog observer started for {self.approved_dir}")
        except Exception as e:
            self._running = False
            raise DetectionError(f"Failed to start watcher: {e}")

    def _start_poll(self) -> None:
        """Start polling thread for periodic directory scans."""
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.debug(f"Poll thread started with interval {self.config.poll_interval}s")

    def _poll_loop(self) -> None:
        """Polling loop that scans directory at regular intervals."""
        while self._running:
            try:
                for path in self.scan_existing():
                    if path not in self._processed_in_session:
                        self._on_file_detected(path)
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")

            # Wait for next poll interval
            for _ in range(self.config.poll_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _on_file_detected(self, path: Path) -> None:
        """Handle a detected file.

        Args:
            path: Path to the detected file
        """
        if path in self._processed_in_session:
            logger.debug(f"Skipping already processed file: {path}")
            return

        self._processed_in_session.add(path)

        if self._callback:
            try:
                self._callback(path)
            except Exception as e:
                logger.error(f"Error in callback for {path}: {e}")
                # Remove from processed so it can be retried
                self._processed_in_session.discard(path)

    def _is_valid_approved_file(self, path: Path) -> bool:
        """Validate file is in /Approved/facebook/ and is markdown.

        SAFETY BOUNDARY: Rejects files from /Pending_Approval/.

        Args:
            path: File path to validate

        Returns:
            True if valid approved file, False otherwise
        """
        # Must exist
        if not path.exists():
            return False

        # Must be a file, not directory
        if not path.is_file():
            return False

        # Must be a markdown file
        if path.suffix.lower() != ".md":
            return False

        # Must be within the approved directory
        try:
            path.relative_to(self.approved_dir)
        except ValueError:
            return False

        # SAFETY: Must NOT contain /Pending_Approval/ in path
        path_str = str(path)
        if "/Pending_Approval/" in path_str or "\\Pending_Approval\\" in path_str:
            logger.warning(f"Rejected file from Pending_Approval: {path}")
            return False

        return True

    @property
    def is_running(self) -> bool:
        """Check if detector is currently running."""
        return self._running
