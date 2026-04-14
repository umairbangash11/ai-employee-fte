"""File detection for approved LinkedIn posts."""

import time
import threading
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent


class ApprovedFileHandler(FileSystemEventHandler):
    """Watchdog event handler for approved LinkedIn post files.

    Calls callback when new .md files are created in /Approved/linkedin/.
    """

    def __init__(self, callback: Callable[[Path], None], detector: "LinkedInApprovedDetector"):
        """Initialize handler.

        Args:
            callback: Function to call with file path when file detected
            detector: Parent detector for validation
        """
        self.callback = callback
        self.detector = detector

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation event.

        Args:
            event: Watchdog file created event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self.detector._is_valid_approved_file(file_path):
            # Small delay to ensure file is fully written
            time.sleep(0.5)
            self.callback(file_path)


class LinkedInApprovedDetector:
    """Detects approved LinkedIn posts in /Approved/linkedin/.

    Monitors for:
    - New files created (via watch or poll)
    - Existing files at startup (catch-up processing)

    Does NOT monitor /Pending_Approval/linkedin/ (FR-010).

    Attributes:
        vault_path: Path to Obsidian vault root
        approved_dir: Path to /Approved/linkedin/
        mode: Detection mode ('watch' or 'poll')
        poll_interval: Seconds between poll scans
    """

    def __init__(
        self,
        vault_path: Path,
        mode: str = "watch",
        poll_interval: int = 30,
    ):
        """Initialize detector.

        Args:
            vault_path: Path to Obsidian vault root
            mode: 'watch' (watchdog) or 'poll' (periodic scan)
            poll_interval: Seconds between poll scans (for poll mode)
        """
        self.vault_path = Path(vault_path)
        self.approved_dir = self.vault_path / "Approved" / "linkedin"
        self.mode = mode
        self.poll_interval = poll_interval

        self._observer: Optional[Observer] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callback: Optional[Callable[[Path], None]] = None

    def scan_existing(self) -> list[Path]:
        """Return all .md files in /Approved/linkedin/ sorted by mtime (oldest first).

        Used for catch-up processing on startup.

        Returns:
            List of file paths sorted by modification time (oldest first)
        """
        if not self.approved_dir.exists():
            return []

        files = [
            f for f in self.approved_dir.glob("*.md")
            if self._is_valid_approved_file(f)
        ]

        # Sort by modification time (oldest first)
        files.sort(key=lambda f: f.stat().st_mtime)
        return files

    def _is_valid_approved_file(self, path: Path) -> bool:
        """Validate file is in /Approved/linkedin/ and is markdown.

        Critical safety check: NEVER process files from /Pending_Approval/.

        Args:
            path: Path to validate

        Returns:
            True if valid approved file, False otherwise
        """
        path = Path(path)

        # Must be .md file
        if path.suffix.lower() != ".md":
            return False

        # Must exist
        if not path.exists():
            return False

        # Must be in approved_dir
        try:
            path.relative_to(self.approved_dir)
        except ValueError:
            return False

        # SAFETY: Must NOT contain Pending_Approval in path
        if "Pending_Approval" in str(path):
            return False

        return True

    def start(self, callback: Callable[[Path], None]) -> None:
        """Start detection. Calls callback for each detected file.

        Args:
            callback: Function to call with file path when new file detected
        """
        self._callback = callback
        self._stop_event.clear()

        # Ensure directory exists
        self.approved_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "watch":
            self._start_watcher()
        else:
            self._start_poll()

    def _start_watcher(self) -> None:
        """Start watchdog observer mode."""
        handler = ApprovedFileHandler(self._callback, self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.approved_dir), recursive=False)
        self._observer.start()

    def _start_poll(self) -> None:
        """Start poll mode in background thread."""
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Background polling loop."""
        seen_files: set[Path] = set()

        # Initial scan
        for file_path in self.scan_existing():
            seen_files.add(file_path)

        while not self._stop_event.is_set():
            try:
                current_files = set(self.scan_existing())
                new_files = current_files - seen_files

                for file_path in sorted(new_files, key=lambda f: f.stat().st_mtime):
                    if self._callback:
                        self._callback(file_path)

                seen_files = current_files
            except Exception:
                # Log error but continue polling
                pass

            self._stop_event.wait(self.poll_interval)

    def stop(self) -> None:
        """Stop detection gracefully."""
        self._stop_event.set()

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        if self._poll_thread:
            self._poll_thread.join(timeout=5)
            self._poll_thread = None
