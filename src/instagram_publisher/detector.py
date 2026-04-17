"""File detection for approved Instagram posts.

Monitors vault/Approved/instagram/ for new files.
Does NOT monitor /Pending_Approval/instagram/ (safety boundary — FR-003).
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from instagram_publisher.config import InstagramPublisherConfig
from instagram_publisher.exceptions import DetectionError

logger = logging.getLogger(__name__)


class ApprovedFileHandler(FileSystemEventHandler):
    """Watchdog handler for approved Instagram post files."""

    def __init__(self, callback: Callable[[Path], None], approved_dir: Path):
        self.callback = callback
        self.approved_dir = approved_dir
        super().__init__()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._is_valid(path):
            logger.info(f"Detected new file: {path}")
            self.callback(path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if self._is_valid(path):
            logger.info(f"Detected moved file: {path}")
            self.callback(path)

    def _is_valid(self, path: Path) -> bool:
        if path.suffix.lower() != ".md":
            return False
        try:
            path.relative_to(self.approved_dir)
        except ValueError:
            return False
        # Safety: reject files that somehow contain /Pending_Approval/ in path
        path_str = str(path)
        if "/Pending_Approval/" in path_str or "\\Pending_Approval\\" in path_str:
            logger.warning(f"Rejected file from Pending_Approval: {path}")
            return False
        return True


class InstagramApprovedDetector:
    """Detects approved Instagram posts in vault/Approved/instagram/."""

    def __init__(self, config: InstagramPublisherConfig):
        self.config = config
        self.approved_dir = config.approved_dir
        self.mode = config.detection_mode
        self._observer: Observer | None = None
        self._poll_thread: threading.Thread | None = None
        self._running = False
        self._callback: Callable[[Path], None] | None = None
        self._processed_in_session: set[Path] = set()

    def scan_existing(self) -> list[Path]:
        """Return all .md files in Approved/instagram/, sorted by mtime (oldest first)."""
        if not self.approved_dir.exists():
            return []
        files = [p for p in self.approved_dir.glob("*.md") if self._is_valid_file(p)]
        files.sort(key=lambda p: p.stat().st_mtime)
        return files

    def start(self, callback: Callable[[Path], None]) -> None:
        if self._running:
            return
        self._callback = callback
        self._running = True
        self._processed_in_session.clear()
        self.approved_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "watch":
            self._start_watcher()
        else:
            self._start_poll()

        logger.info(f"Instagram detector started in {self.mode} mode")

    def stop(self) -> None:
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5)
            self._poll_thread = None

    def _start_watcher(self) -> None:
        try:
            self._observer = Observer()
            handler = ApprovedFileHandler(self._on_file_detected, self.approved_dir)
            self._observer.schedule(handler, str(self.approved_dir), recursive=False)
            self._observer.start()
        except Exception as e:
            self._running = False
            raise DetectionError(f"Failed to start watcher: {e}")

    def _start_poll(self) -> None:
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        while self._running:
            try:
                for path in self.scan_existing():
                    if path not in self._processed_in_session:
                        self._on_file_detected(path)
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
            for _ in range(self.config.poll_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _on_file_detected(self, path: Path) -> None:
        if path in self._processed_in_session:
            return
        self._processed_in_session.add(path)
        if self._callback:
            try:
                self._callback(path)
            except Exception as e:
                logger.error(f"Error in callback for {path}: {e}")
                self._processed_in_session.discard(path)

    def _is_valid_file(self, path: Path) -> bool:
        if not path.exists() or not path.is_file():
            return False
        if path.suffix.lower() != ".md":
            return False
        try:
            path.relative_to(self.approved_dir)
        except ValueError:
            return False
        path_str = str(path)
        if "/Pending_Approval/" in path_str or "\\Pending_Approval\\" in path_str:
            return False
        return True

    @property
    def is_running(self) -> bool:
        return self._running
