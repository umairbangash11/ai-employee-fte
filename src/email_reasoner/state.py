"""State management for Email Reasoning Layer.

Handles loading and saving the reasoner state file for deduplication,
tracking which emails have been processed to prevent duplicate tasks.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .models import ReasonerState


logger = logging.getLogger(__name__)


# =============================================================================
# T023-T028: State management implementation
# =============================================================================


def load_state(path: Path) -> ReasonerState:
    """Load reasoner state from JSON file.

    If the file doesn't exist, returns a new empty state.
    If the file is corrupt, logs a warning and returns new state.

    Args:
        path: Path to reasoner.json state file.

    Returns:
        ReasonerState loaded from file or new empty state.
    """
    if not path.exists():
        logger.debug(f"State file does not exist, creating new state: {path}")
        return ReasonerState()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = ReasonerState.from_dict(data)
        logger.debug(f"Loaded state with {len(state.processed)} processed emails")
        return state
    except json.JSONDecodeError as e:
        logger.warning(f"State file is corrupt, starting fresh: {e}")
        return ReasonerState()
    except Exception as e:
        logger.warning(f"Failed to load state file, starting fresh: {e}")
        return ReasonerState()


def save_state(state: ReasonerState, path: Path) -> None:
    """Save reasoner state to JSON file.

    Creates parent directories if they don't exist.

    Args:
        state: ReasonerState to persist.
        path: Path to reasoner.json state file.
    """
    # T028: Create .watcher-state/ directory if missing
    ensure_state_directory(path.parent)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)
        logger.debug(f"Saved state with {len(state.processed)} processed emails")
    except Exception as e:
        logger.error(f"Failed to save state file: {e}")
        raise


def is_processed(state: ReasonerState, message_id: str) -> bool:
    """Check if an email has already been processed.

    Args:
        state: Current reasoner state.
        message_id: Message ID from email frontmatter.

    Returns:
        True if the email has been processed before.
    """
    return state.is_processed(message_id)


def mark_processed(
    state: ReasonerState,
    message_id: str,
    classification: str,
    task_file: Optional[str] = None
) -> None:
    """Mark an email as processed in the state.

    Args:
        state: Current reasoner state (modified in place).
        message_id: Message ID from email frontmatter.
        classification: Classification result (actionable, informational, etc.).
        task_file: Relative path to created task file, if any.
    """
    state.mark_processed(message_id, classification, task_file)
    logger.debug(f"Marked {message_id} as processed ({classification})")


def ensure_state_directory(directory: Path) -> None:
    """Create state directory if it doesn't exist.

    Args:
        directory: Path to .watcher-state directory.
    """
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created state directory: {directory}")
