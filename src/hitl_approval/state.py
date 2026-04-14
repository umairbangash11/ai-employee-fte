"""State management for HITL approval deduplication."""

import json
from datetime import datetime
from pathlib import Path

from .models import ApprovalState


def load_approval_state(state_path: Path) -> ApprovalState:
    """Load approval state from JSON file.

    Args:
        state_path: Path to state JSON file

    Returns:
        ApprovalState with loaded or empty state
    """
    state_path = Path(state_path)

    if not state_path.exists():
        return ApprovalState()

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ApprovalState.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        # Corrupted state file, start fresh
        return ApprovalState()


def save_approval_state(state: ApprovalState, state_path: Path) -> None:
    """Save approval state to JSON file.

    Args:
        state: ApprovalState to save
        state_path: Path to state JSON file
    """
    state_path = Path(state_path)

    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state.last_updated = datetime.utcnow()

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def is_duplicate(state: ApprovalState, hash_value: str) -> bool:
    """Check if approval request with given hash already exists.

    Args:
        state: Current approval state
        hash_value: SHA256 hash of approval request

    Returns:
        True if duplicate, False otherwise
    """
    return hash_value in state.created_hashes


def add_hash(state: ApprovalState, hash_value: str) -> None:
    """Add hash to state (marks approval as created).

    Args:
        state: Current approval state
        hash_value: SHA256 hash to add
    """
    state.created_hashes.add(hash_value)
