"""Deduplication state management for WhatsApp watcher.

Persists and queries message hashes to prevent duplicate file creation.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .config import WatcherConfig
from .models import DeduplicationState, WhatsAppMessage


def load_dedup_state(config: WatcherConfig) -> DeduplicationState:
    """Load deduplication state from JSON file.

    If file doesn't exist → return empty DeduplicationState
    If file corrupted → log warning, backup corrupted file, return empty state

    Args:
        config: WatcherConfig with dedup_path

    Returns:
        DeduplicationState instance
    """
    if not config.dedup_path.exists():
        print("No existing dedup state found, starting fresh.", file=sys.stderr)
        return DeduplicationState()

    try:
        with open(config.dedup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse data to DeduplicationState
        version = data.get("version", 1)

        last_poll = None
        if data.get("last_poll"):
            last_poll = datetime.fromisoformat(data["last_poll"])

        message_hashes = {}
        for hash_val, timestamp_str in data.get("message_hashes", {}).items():
            message_hashes[hash_val] = timestamp_str

        state = DeduplicationState(
            version=version,
            last_poll=last_poll,
            message_hashes=message_hashes
        )

        print(f"Loaded dedup state: {len(message_hashes)} hashes", file=sys.stderr)
        return state

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Corrupted state file
        print(f"Warning: Corrupted dedup state file: {e}", file=sys.stderr)

        # Backup corrupted file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = config.dedup_path.parent / f"whatsapp-dedup.json.corrupted.{timestamp}"
        try:
            os.rename(config.dedup_path, backup_path)
            print(f"Backed up corrupted state to: {backup_path}", file=sys.stderr)
        except Exception:
            pass

        print("Starting with empty dedup state. All messages will be reprocessed.", file=sys.stderr)
        return DeduplicationState()


def save_dedup_state(state: DeduplicationState, config: WatcherConfig) -> None:
    """Save deduplication state to JSON file.

    Uses atomic write (temp file + rename).
    Updates state.last_poll to current timestamp.

    Args:
        state: DeduplicationState to save
        config: WatcherConfig with dedup_path
    """
    # Update last poll timestamp
    state.last_poll = datetime.now()

    # Ensure directory exists
    config.dedup_path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize to dict
    data = {
        "version": state.version,
        "last_poll": state.last_poll.isoformat() if state.last_poll else None,
        "message_hashes": state.message_hashes
    }

    # Write to temp file
    temp_fd, temp_path = tempfile.mkstemp(
        dir=config.dedup_path.parent,
        prefix=".tmp_state_",
        suffix=".json"
    )

    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Atomic rename
        os.rename(temp_path, config.dedup_path)
        print(f"Saved dedup state: {len(state.message_hashes)} hashes", file=sys.stderr)

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise e


def is_message_processed(message: WhatsAppMessage, state: DeduplicationState) -> bool:
    """Check if message hash exists in state.

    Args:
        message: WhatsAppMessage to check
        state: Current deduplication state

    Returns:
        True if message.hash in state.message_hashes
    """
    return message.hash in state.message_hashes


def mark_message_processed(
    message: WhatsAppMessage,
    state: DeduplicationState,
    captured_at: datetime
) -> None:
    """Add message hash to state.

    Args:
        message: WhatsAppMessage that was processed
        state: DeduplicationState to update (mutated in-place)
        captured_at: Timestamp when message was captured
    """
    state.message_hashes[message.hash] = captured_at.isoformat()
