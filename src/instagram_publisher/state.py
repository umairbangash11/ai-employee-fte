"""State management for Instagram Publisher."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from instagram_publisher.config import InstagramPublisherConfig
from instagram_publisher.utils import ensure_directory

logger = logging.getLogger(__name__)


class PublisherState:
    """Manages publisher state for idempotency and statistics.

    State persisted to .watcher-state/instagram/publisher.json
    """

    def __init__(self, config: InstagramPublisherConfig):
        self.config = config
        self.state_path = config.publisher_state_path
        self._processed_hashes: set[str] = set()
        self._last_run: datetime | None = None
        self._stats: dict[str, int] = {"published": 0, "failed": 0, "skipped": 0}

    def load(self) -> None:
        """Load state from disk."""
        if not self.state_path.exists():
            return
        try:
            with open(self.state_path, encoding="utf-8") as f:
                data = json.load(f)
            self._processed_hashes = set(data.get("processed_hashes", []))
            self._stats = data.get("stats", {"published": 0, "failed": 0, "skipped": 0})
            last_run_str = data.get("last_run")
            if last_run_str:
                self._last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")

    def save(self) -> None:
        """Persist state to disk."""
        ensure_directory(self.config.session_path)
        data = {
            "processed_hashes": list(self._processed_hashes),
            "last_run": self._last_run.isoformat() + "Z" if self._last_run else None,
            "stats": self._stats,
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def is_duplicate(self, content_hash: str) -> bool:
        return content_hash in self._processed_hashes

    def add_hash(self, content_hash: str) -> None:
        self._processed_hashes.add(content_hash)

    def update_stats(self, event_type: str) -> None:
        if event_type in self._stats:
            self._stats[event_type] += 1
            self._last_run = datetime.utcnow()

    def get_stats(self) -> dict[str, Any]:
        return {
            "stats": self._stats.copy(),
            "last_run": self._last_run.isoformat() + "Z" if self._last_run else None,
            "processed_count": len(self._processed_hashes),
        }

    @property
    def processed_hashes(self) -> set[str]:
        return self._processed_hashes

    @property
    def stats(self) -> dict[str, int]:
        return self._stats.copy()
