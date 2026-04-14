"""Configuration for Facebook Publisher."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FacebookPublisherConfig:
    """Configuration for Facebook Publisher.

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
    session_path: Path = field(default_factory=lambda: Path(".watcher-state/facebook"))
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
        """Path to /Approved/facebook/ directory."""
        return self.vault_path / "Approved" / "facebook"

    @property
    def done_dir(self) -> Path:
        """Path to /Done/facebook/ directory."""
        return self.vault_path / "Done" / "facebook"

    @property
    def needs_action_dir(self) -> Path:
        """Path to /Needs_Action/facebook/ directory."""
        return self.vault_path / "Needs_Action" / "facebook"

    @property
    def logs_dir(self) -> Path:
        """Path to /Logs/facebook/ directory."""
        return self.vault_path / "Logs" / "facebook"

    @property
    def pending_approval_dir(self) -> Path:
        """Path to /Pending_Approval/facebook/ directory (NOT processed)."""
        return self.vault_path / "Pending_Approval" / "facebook"

    @property
    def storage_state_path(self) -> Path:
        """Path to Playwright storage state file."""
        return self.session_path / "storage_state.json"

    @property
    def publisher_state_path(self) -> Path:
        """Path to publisher state file (processed hashes)."""
        return self.session_path / "publisher.json"

    @classmethod
    def from_env(cls) -> "FacebookPublisherConfig":
        """Create configuration from environment variables."""
        return cls(
            vault_path=Path(os.environ.get("VAULT_PATH", ".")),
            session_path=Path(os.environ.get("FB_SESSION_PATH", ".watcher-state/facebook")),
            poll_interval=int(os.environ.get("FB_POLL_INTERVAL", "30")),
            detection_mode=os.environ.get("FB_DETECTION_MODE", "watch"),
            headless=os.environ.get("FB_HEADLESS", "true").lower() == "true",
            publish_timeout=int(os.environ.get("FB_PUBLISH_TIMEOUT", "60")),
            page_load_timeout=int(os.environ.get("FB_PAGE_LOAD_TIMEOUT", "30")),
            retry_attempts=int(os.environ.get("FB_RETRY_ATTEMPTS", "3")),
            retry_delay=int(os.environ.get("FB_RETRY_DELAY", "5")),
        )
