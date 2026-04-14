"""Configuration management for Gmail watcher."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SentinelConfig:
    """Runtime configuration loaded from CLI args and environment variables."""

    vault_path: Path = field(default_factory=lambda: Path(os.getenv("VAULT_PATH", ".")))
    poll_interval: int = 120  # seconds, minimum allowed
    max_initial_fetch: int = 100

    # File paths
    credentials_path: Path = field(default_factory=lambda: Path("./secrets/gmail/credentials.json"))
    token_path: Path = field(default_factory=lambda: Path("./secrets/gmail/token.json"))
    state_path: Path = field(default_factory=lambda: Path("./.watcher-state/gmail-api.json"))

    # CLI flags
    dry_run: bool = False
    auth_mode: bool = False
    once: bool = False

    def __post_init__(self):
        """Ensure paths are Path objects and interval is valid."""
        if isinstance(self.vault_path, str):
            self.vault_path = Path(self.vault_path)
        if isinstance(self.credentials_path, str):
            self.credentials_path = Path(self.credentials_path)
        if isinstance(self.token_path, str):
            self.token_path = Path(self.token_path)
        if isinstance(self.state_path, str):
            self.state_path = Path(self.state_path)

        # Enforce minimum poll interval (Constitution Principle VIII)
        if self.poll_interval < 60:
            self.poll_interval = 60
