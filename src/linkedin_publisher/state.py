"""State management for LinkedIn publisher (idempotency)."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .models import ExecutionState


def load_execution_state(state_path: Path) -> ExecutionState:
    """Load execution state from JSON file.

    Args:
        state_path: Path to .watcher-state/linkedin/publisher.json

    Returns:
        ExecutionState with loaded or empty state
    """
    state_path = Path(state_path)

    if not state_path.exists():
        return ExecutionState()

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionState.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        # Corrupted state file, start fresh
        return ExecutionState()


def save_execution_state(state: ExecutionState, state_path: Path) -> None:
    """Save execution state to JSON file.

    Args:
        state: ExecutionState to save
        state_path: Path to .watcher-state/linkedin/publisher.json
    """
    state_path = Path(state_path)

    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update last_run timestamp
    state.last_run = datetime.utcnow()

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def compute_content_hash(action_type: str, content: str, source_path: str) -> str:
    """Compute SHA256 hash for idempotency.

    Hash is computed from:
    - action_type
    - content
    - source_path

    Args:
        action_type: Type of action (publish_linkedin_post)
        content: Post content
        source_path: Path to source file

    Returns:
        SHA256 hex digest
    """
    data = f"{action_type}|{content}|{source_path}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def is_duplicate(state: ExecutionState, hash_value: str) -> bool:
    """Check if content has already been published.

    Args:
        state: Current execution state
        hash_value: SHA256 hash to check

    Returns:
        True if already published, False otherwise
    """
    return hash_value in state.processed_hashes


def add_processed_hash(
    state: ExecutionState,
    hash_value: str,
    success: bool = True,
) -> None:
    """Add hash to processed set and update statistics.

    Args:
        state: Current execution state
        hash_value: SHA256 hash to add
        success: Whether publish was successful
    """
    state.processed_hashes.add(hash_value)

    if success:
        state.total_published += 1
    else:
        state.total_failed += 1
