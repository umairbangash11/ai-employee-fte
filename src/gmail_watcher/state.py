"""Deduplication state persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path

from gmail_watcher.models import DeduplicationState


def load_state(path: Path) -> DeduplicationState:
    """Load deduplication state from disk.

    Creates empty state if file doesn't exist.

    Args:
        path: Path to state JSON file

    Returns:
        DeduplicationState with loaded or empty data
    """
    if not path.exists():
        return DeduplicationState()

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Parse last_poll if present
        last_poll = None
        if data.get("last_poll"):
            last_poll = datetime.fromisoformat(data["last_poll"].replace("Z", "+00:00"))

        return DeduplicationState(
            version=data.get("version", 1),
            last_poll=last_poll,
            message_ids=data.get("message_ids", {}),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        # Corrupted state file, start fresh
        return DeduplicationState()


def save_state(state: DeduplicationState, path: Path) -> None:
    """Save deduplication state to disk.

    Args:
        state: DeduplicationState to persist
        path: Path to state JSON file
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Format last_poll for JSON
    last_poll_str = None
    if state.last_poll:
        last_poll_str = state.last_poll.strftime("%Y-%m-%dT%H:%M:%SZ")

    data = {
        "version": state.version,
        "last_poll": last_poll_str,
        "message_ids": state.message_ids,
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def is_captured(state: DeduplicationState, message_id: str) -> bool:
    """Check if a message has already been captured.

    Args:
        state: Current deduplication state
        message_id: Gmail message ID to check

    Returns:
        True if message was previously captured
    """
    return message_id in state.message_ids


def mark_captured(state: DeduplicationState, message_id: str) -> None:
    """Mark a message as captured.

    Args:
        state: Deduplication state to update
        message_id: Gmail message ID to mark
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.message_ids[message_id] = timestamp
    state.last_poll = datetime.now(timezone.utc)
