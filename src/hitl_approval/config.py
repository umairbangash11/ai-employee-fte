"""Configuration for HITL approval system."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class HITLConfig:
    """Configuration for HITL approval system.

    Attributes:
        vault_path: Path to Obsidian vault root
        state_path: Path to approval state file (for deduplication)
        verbose: Enable verbose logging
    """

    vault_path: Path
    state_path: Optional[Path] = None
    verbose: bool = False

    def __post_init__(self):
        """Set defaults and validate paths."""
        self.vault_path = Path(self.vault_path)
        if self.state_path is None:
            self.state_path = self.vault_path.parent / ".watcher-state" / "approvals.json"
        else:
            self.state_path = Path(self.state_path)

    @property
    def pending_approval_path(self) -> Path:
        """Path to /Pending_Approval/ directory."""
        return self.vault_path / "Pending_Approval"

    @property
    def approved_path(self) -> Path:
        """Path to /Approved/ directory."""
        return self.vault_path / "Approved"

    @property
    def rejected_path(self) -> Path:
        """Path to /Rejected/ directory."""
        return self.vault_path / "Rejected"

    @property
    def logs_path(self) -> Path:
        """Path to /Logs/ directory."""
        return self.vault_path / "Logs"

    @classmethod
    def from_env(cls) -> "HITLConfig":
        """Create config from environment variables.

        Environment Variables:
            VAULT_PATH: Path to Obsidian vault (required)
            HITL_STATE_PATH: Path to state file (optional)
            HITL_VERBOSE: Enable verbose mode (optional)
        """
        vault_path = os.environ.get("VAULT_PATH")
        if not vault_path:
            raise ValueError("VAULT_PATH environment variable is required")

        state_path = os.environ.get("HITL_STATE_PATH")
        verbose = os.environ.get("HITL_VERBOSE", "").lower() in ("1", "true", "yes")

        return cls(
            vault_path=Path(vault_path),
            state_path=Path(state_path) if state_path else None,
            verbose=verbose,
        )
