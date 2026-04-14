"""Configuration loading for WhatsApp watcher.

Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WatcherConfig:
    """Configuration for WhatsApp watcher."""

    vault_path: Path
    poll_interval: int
    urgency_keywords: list[str]
    page_timeout: int
    session_path: Path
    dedup_path: Path
    dry_run: bool = False
    headless: bool = True

    @property
    def storage_state_path(self) -> Path:
        """Path to Playwright storage state JSON."""
        return self.session_path / "storage_state.json"


def load_config(dry_run: bool = False, headless: bool = True) -> WatcherConfig:
    """Load configuration from environment variables.

    Environment Variables:
        VAULT_PATH: Path to vault root (default: current directory)
        WHATSAPP_POLL_INTERVAL: Seconds between polls (default: 60)
        WHATSAPP_URGENCY_KEYWORDS: Comma-separated keywords (default: URGENT,ASAP,...)
        WHATSAPP_PAGE_TIMEOUT: Page load timeout in ms (default: 30000)

    Args:
        dry_run: If True, preview without writing files
        headless: If True, run browser headless (False for --auth mode)

    Returns:
        WatcherConfig instance
    """
    vault_path = Path(os.getenv("VAULT_PATH", ".")).resolve()

    poll_interval = int(os.getenv("WHATSAPP_POLL_INTERVAL", "60"))

    keywords_str = os.getenv(
        "WHATSAPP_URGENCY_KEYWORDS",
        "URGENT,ASAP,emergency,call me,time-sensitive",
    )
    urgency_keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

    page_timeout = int(os.getenv("WHATSAPP_PAGE_TIMEOUT", "30000"))

    # State paths are relative to current working directory
    watcher_state = Path(".watcher-state").resolve()
    session_path = watcher_state / "whatsapp"
    dedup_path = watcher_state / "whatsapp-dedup.json"

    return WatcherConfig(
        vault_path=vault_path,
        poll_interval=poll_interval,
        urgency_keywords=urgency_keywords,
        page_timeout=page_timeout,
        session_path=session_path,
        dedup_path=dedup_path,
        dry_run=dry_run,
        headless=headless,
    )
