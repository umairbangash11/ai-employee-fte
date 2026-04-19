"""Configuration for Instagram Publisher."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstagramPublisherConfig:
    """Configuration for Instagram Publisher.

    Attributes:
        vault_path: Path to the Obsidian vault root
        session_path: Path to store Playwright session data
        poll_interval: Interval in seconds for poll mode (default: 30)
        detection_mode: Detection mode - 'watch' or 'poll' (default: watch)
        headless: Run browser in headless mode (default: True)
        publish_timeout: Timeout in seconds for publish operation (default: 60)
        page_load_timeout: Timeout in seconds for page loads (default: 30)
        retry_attempts: Number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 5)
    """

    vault_path: Path = field(default_factory=lambda: Path(os.environ.get("VAULT_PATH", ".")))
    session_path: Path = field(default_factory=lambda: Path(".watcher-state/instagram"))
    poll_interval: int = 30
    detection_mode: str = "watch"
    headless: bool = True
    publish_timeout: int = 60
    page_load_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5

    def __post_init__(self) -> None:
        """Convert string paths to Path objects."""
        if isinstance(self.vault_path, str):
            self.vault_path = Path(self.vault_path)
        if isinstance(self.session_path, str):
            self.session_path = Path(self.session_path)

    @property
    def approved_dir(self) -> Path:
        """Path to /Approved/instagram/ directory."""
        return self.vault_path / "Approved" / "instagram"

    @property
    def done_dir(self) -> Path:
        """Path to /Done/instagram/ directory."""
        return self.vault_path / "Done" / "instagram"

    @property
    def needs_action_dir(self) -> Path:
        """Path to /Needs_Action/instagram/ directory."""
        return self.vault_path / "Needs_Action" / "instagram"

    @property
    def pending_approval_dir(self) -> Path:
        """Path to /Pending_Approval/instagram/ directory (NOT processed)."""
        return self.vault_path / "Pending_Approval" / "instagram"

    @property
    def logs_dir(self) -> Path:
        """Path to /Logs/ directory."""
        return self.vault_path / "Logs"

    @property
    def storage_state_path(self) -> Path:
        """Path to Playwright storage state JSON (cookies + localStorage)."""
        return self.session_path / "storage_state.json"

    @property
    def publisher_state_path(self) -> Path:
        """Path to publisher state file (processed hashes)."""
        return self.session_path / "publisher.json"

    @classmethod
    def from_env(cls) -> "InstagramPublisherConfig":
        """Create configuration from environment variables.

        Environment Variables:
            VAULT_PATH: Path to vault root (required)
            INSTAGRAM_SESSION_PATH: Path to Playwright session (optional)
            INSTAGRAM_HEADLESS: Browser mode (optional, default True)
            INSTAGRAM_POLL_INTERVAL: Poll interval in seconds (optional)
            INSTAGRAM_DETECTION_MODE: 'watch' or 'poll' (optional)
        """
        vault_path = os.environ.get("VAULT_PATH")
        if not vault_path:
            raise ValueError("VAULT_PATH environment variable is required")

        session_path = os.environ.get("INSTAGRAM_SESSION_PATH", ".watcher-state/instagram")
        headless = os.environ.get("INSTAGRAM_HEADLESS", "true").lower() not in ("0", "false", "no")
        poll_interval = int(os.environ.get("INSTAGRAM_POLL_INTERVAL", "30"))
        detection_mode = os.environ.get("INSTAGRAM_DETECTION_MODE", "watch")

        return cls(
            vault_path=Path(vault_path),
            session_path=Path(session_path),
            headless=headless,
            poll_interval=poll_interval,
            detection_mode=detection_mode,
        )
