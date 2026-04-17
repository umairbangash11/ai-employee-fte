"""Configuration for LinkedIn publisher."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LinkedInPublisherConfig:
    """Configuration for LinkedIn publisher.

    Attributes:
        vault_path: Path to Obsidian vault root
        session_path: Path to Playwright session storage
        state_path: Path to publisher state file (processed hashes)
        headless: Run browser in headless mode
        poll_interval: Seconds between poll mode scans
        detection_mode: 'watch' or 'poll'
        verbose: Enable verbose logging
    """

    vault_path: Path
    session_path: Optional[Path] = None
    state_path: Optional[Path] = None
    headless: bool = True
    poll_interval: int = 30
    detection_mode: str = "watch"
    verbose: bool = False

    def __post_init__(self):
        """Set defaults and validate paths."""
        self.vault_path = Path(self.vault_path)

        # Default session path: .watcher-state/linkedin/session/
        if self.session_path is None:
            self.session_path = self.vault_path.parent / ".watcher-state" / "linkedin" / "session"
        else:
            self.session_path = Path(self.session_path)

        # Default state path: .watcher-state/linkedin/publisher.json
        if self.state_path is None:
            self.state_path = self.vault_path.parent / ".watcher-state" / "linkedin" / "publisher.json"
        else:
            self.state_path = Path(self.state_path)

    @property
    def storage_state_path(self) -> Path:
        """Path to portable session JSON (cookies + localStorage).

        Exported by auth, loaded by run/watch. Avoids headed-vs-headless
        Chrome profile incompatibility.
        """
        return self.session_path.parent / "storage_state.json"

    @property
    def approved_path(self) -> Path:
        """Path to /Approved/linkedin/ directory."""
        return self.vault_path / "Approved" / "linkedin"

    @property
    def done_path(self) -> Path:
        """Path to /Done/linkedin/ directory."""
        return self.vault_path / "Done" / "linkedin"

    @property
    def needs_action_path(self) -> Path:
        """Path to /Needs_Action/linkedin/ directory."""
        return self.vault_path / "Needs_Action" / "linkedin"

    @property
    def logs_path(self) -> Path:
        """Path to /Logs/ directory."""
        return self.vault_path / "Logs"

    @classmethod
    def from_env(cls) -> "LinkedInPublisherConfig":
        """Create config from environment variables.

        Environment Variables:
            VAULT_PATH: Path to Obsidian vault (required)
            LINKEDIN_SESSION_PATH: Path to Playwright session (optional)
            LINKEDIN_STATE_PATH: Path to state file (optional)
            LINKEDIN_HEADLESS: Browser mode (optional, default True)
            LINKEDIN_POLL_INTERVAL: Poll interval in seconds (optional)
            LINKEDIN_DETECTION_MODE: 'watch' or 'poll' (optional)
            LINKEDIN_VERBOSE: Verbose mode (optional)
        """
        vault_path = os.environ.get("VAULT_PATH")
        if not vault_path:
            raise ValueError("VAULT_PATH environment variable is required")

        session_path = os.environ.get("LINKEDIN_SESSION_PATH")
        state_path = os.environ.get("LINKEDIN_STATE_PATH")
        headless = os.environ.get("LINKEDIN_HEADLESS", "true").lower() not in ("0", "false", "no")
        poll_interval = int(os.environ.get("LINKEDIN_POLL_INTERVAL", "30"))
        detection_mode = os.environ.get("LINKEDIN_DETECTION_MODE", "watch")
        verbose = os.environ.get("LINKEDIN_VERBOSE", "").lower() in ("1", "true", "yes")

        return cls(
            vault_path=Path(vault_path),
            session_path=Path(session_path) if session_path else None,
            state_path=Path(state_path) if state_path else None,
            headless=headless,
            poll_interval=poll_interval,
            detection_mode=detection_mode,
            verbose=verbose,
        )
