"""State management for Facebook Publisher.

Tracks processed files for idempotency and maintains publish statistics.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.utils import ensure_directory

logger = logging.getLogger(__name__)


class PublisherState:
    """Manages publisher state for idempotency and statistics.

    State is persisted to .watcher-state/facebook/publisher.json

    State structure:
    {
        "processed_hashes": ["hash1", "hash2", ...],
        "last_run": "2026-03-22T10:00:00Z",
        "stats": {
            "published": 10,
            "failed": 2,
            "skipped": 3
        }
    }
    """

    def __init__(self, config: FacebookPublisherConfig):
        """Initialize state manager.

        Args:
            config: Publisher configuration
        """
        self.config = config
        self.state_path = config.session_path / "publisher.json"
        self._processed_hashes: set[str] = set()
        self._last_run: datetime | None = None
        self._stats: dict[str, int] = {
            "published": 0,
            "failed": 0,
            "skipped": 0,
        }

    def load(self) -> None:
        """Load state from .watcher-state/facebook/publisher.json."""
        if not self.state_path.exists():
            logger.debug(f"State file not found: {self.state_path}")
            return

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._processed_hashes = set(data.get("processed_hashes", []))
            self._stats = data.get("stats", {"published": 0, "failed": 0, "skipped": 0})

            last_run_str = data.get("last_run")
            if last_run_str:
                self._last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))

            logger.debug(f"State loaded: {len(self._processed_hashes)} hashes, stats={self._stats}")

        except Exception as e:
            logger.warning(f"Failed to load state: {e}")

    def save(self) -> None:
        """Persist state to .watcher-state/facebook/publisher.json."""
        ensure_directory(self.config.session_path)

        data = {
            "processed_hashes": list(self._processed_hashes),
            "last_run": self._last_run.isoformat() + "Z" if self._last_run else None,
            "stats": self._stats,
        }

        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"State saved to {self.state_path}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def is_duplicate(self, content_hash: str) -> bool:
        """Check if content hash has already been processed.

        Args:
            content_hash: SHA-256 hash of the content

        Returns:
            True if already processed, False otherwise
        """
        return content_hash in self._processed_hashes

    def add_hash(self, content_hash: str) -> None:
        """Add a processed content hash to state.

        Args:
            content_hash: SHA-256 hash of the processed content
        """
        self._processed_hashes.add(content_hash)

    def update_stats(self, event_type: str) -> None:
        """Update statistics counter.

        Args:
            event_type: One of 'published', 'failed', 'skipped'
        """
        if event_type in self._stats:
            self._stats[event_type] += 1
            self._last_run = datetime.utcnow()

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics.

        Returns:
            Dictionary with stats and last_run
        """
        return {
            "stats": self._stats.copy(),
            "last_run": self._last_run.isoformat() + "Z" if self._last_run else None,
            "processed_count": len(self._processed_hashes),
        }

    def clear(self) -> None:
        """Clear all state (for testing)."""
        self._processed_hashes.clear()
        self._last_run = None
        self._stats = {"published": 0, "failed": 0, "skipped": 0}

    @property
    def processed_hashes(self) -> set[str]:
        """Get the set of processed hashes."""
        return self._processed_hashes

    @property
    def last_run(self) -> datetime | None:
        """Get the last run timestamp."""
        return self._last_run

    @property
    def stats(self) -> dict[str, int]:
        """Get the statistics dictionary."""
        return self._stats.copy()
