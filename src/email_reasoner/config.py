"""Configuration management for Email Reasoning Layer.

Loads configuration from environment variables and CLI overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# =============================================================================
# T013-T015: ReasonerConfig dataclass with environment loading
# =============================================================================


@dataclass
class ReasonerConfig:
    """Configuration for the email reasoner.

    Values can be set via:
    1. Environment variables (VAULT_PATH, OPENAI_API_KEY)
    2. CLI options (--vault-path, --dry-run, --limit, etc.)
    3. Defaults (defined here)
    """

    # Required paths
    vault_path: Path = field(default_factory=lambda: Path.cwd())
    state_path: Optional[Path] = None  # Defaults to vault_path/.watcher-state/reasoner.json

    # API configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # Processing options
    dry_run: bool = False
    limit: Optional[int] = None  # Max emails to process (None = all)
    verbose: bool = False

    # Confidence threshold
    confidence_threshold: float = 0.6  # Below this → informational fallback

    def __post_init__(self):
        """Resolve state_path default if not provided."""
        if self.state_path is None:
            self.state_path = self.vault_path / ".watcher-state" / "reasoner.json"

    @property
    def inbox_email_path(self) -> Path:
        """Path to Inbox/email directory."""
        return self.vault_path / "Inbox" / "email"

    @property
    def needs_action_tasks_path(self) -> Path:
        """Path to Needs_Action/tasks directory."""
        return self.vault_path / "Needs_Action" / "tasks"

    @property
    def plans_path(self) -> Path:
        """Path to Plans directory."""
        return self.vault_path / "Plans"

    @property
    def logs_path(self) -> Path:
        """Path to Logs directory."""
        return self.vault_path / "Logs"

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "ReasonerConfig":
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file. Defaults to current directory.

        Returns:
            ReasonerConfig populated from environment.
        """
        # Load .env file if it exists
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Build config from environment
        vault_path_str = os.getenv("VAULT_PATH")
        vault_path = Path(vault_path_str) if vault_path_str else Path.cwd()

        state_path_str = os.getenv("REASONER_STATE_PATH")
        state_path = Path(state_path_str) if state_path_str else None

        return cls(
            vault_path=vault_path,
            state_path=state_path,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            dry_run=os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes"),
            verbose=os.getenv("VERBOSE", "").lower() in ("true", "1", "yes"),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []

        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required but not set")

        if not self.vault_path.exists():
            errors.append(f"Vault path does not exist: {self.vault_path}")

        if not self.inbox_email_path.exists():
            errors.append(f"Inbox email path does not exist: {self.inbox_email_path}")

        return errors
