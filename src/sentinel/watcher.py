"""Sentinel file watcher using watchdog."""

import os
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from sentinel.mover import move_file
from sentinel.vault import validate_vault


def wait_for_stability(
    filepath: str | Path,
    timeout: float = 30,
    check_interval: float = 0.1,
    stable_duration: float = 0.5,
) -> bool:
    """Wait until a file's size stabilizes (write complete).

    Returns True if stable, False on timeout or disappearance.
    """
    start_time = time.time()
    last_size = None
    stable_time = 0.0

    while time.time() - start_time < timeout:
        try:
            current_size = os.path.getsize(filepath)
        except (FileNotFoundError, OSError):
            return False

        if last_size is None or current_size != last_size:
            last_size = current_size
            stable_time = 0.0
        else:
            stable_time += check_interval
            if stable_time >= stable_duration:
                return True

        time.sleep(check_interval)

    return False


SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


class InboxHandler(FileSystemEventHandler):
    """Watchdog handler that processes new files in Inbox/."""

    def __init__(self, vault_path: Path):
        super().__init__()
        self.vault_path = Path(vault_path).resolve()
        self.inbox_dir = self.vault_path / "Inbox"
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.approved_dir = self.vault_path / "Approved"
        self.logs_dir = self.vault_path / "Logs"

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        if not wait_for_stability(filepath):
            return

        if not filepath.exists():
            return

        move_file(
            source_path=filepath,
            needs_action_dir=self.needs_action_dir,
            approved_dir=self.approved_dir,
            logs_dir=self.logs_dir,
        )


def start_watching(vault_path: str = ".", poll_interval: float = 1.0):
    """Start watching the Inbox/ folder for new files.

    Raises ValueError if vault is not initialized.
    """
    vault = Path(vault_path).resolve()

    if not validate_vault(str(vault)):
        raise ValueError(
            f"Vault not initialized at '{vault}'. "
            f"Run 'python -m sentinel init' first."
        )

    inbox_dir = vault / "Inbox"
    handler = InboxHandler(vault)
    observer = Observer()
    observer.schedule(handler, str(inbox_dir), recursive=False)
    observer.start()

    print(f"Sentinel watching: {inbox_dir}")
    print(f"  Extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print(f"  Press Ctrl+C to stop.")

    try:
        while True:
            if not inbox_dir.is_dir():
                print(
                    f"\nError: Inbox directory '{inbox_dir}' no longer exists.",
                    flush=True,
                )
                # Log the error
                from sentinel.logger import write_log_entry

                logs_dir = vault / "Logs"
                if logs_dir.is_dir():
                    write_log_entry(
                        logs_dir=logs_dir,
                        action_type="error",
                        source_path=inbox_dir,
                        dest_path=inbox_dir,
                        file_size=0,
                        outcome="failure",
                        details="Inbox directory deleted while Sentinel was running.",
                    )
                observer.stop()
                observer.join()
                raise SystemExit(2)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
