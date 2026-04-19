"""Logging wrapper for CEO Briefing Generator.

Wraps sentinel.logger.write_log_entry() for briefing-specific logging.
"""

from pathlib import Path

from briefing_generator.config import VAULT_DIRS
from sentinel.logger import write_log_entry


def log_briefing_generation(
    vault_path: Path,
    briefing_path: Path,
    outcome: str,
    details: str = "",
) -> Path:
    """Log a briefing generation event.

    Args:
        vault_path: Path to vault root (source).
        briefing_path: Path to generated briefing file (destination).
        outcome: "success", "failure", or "partial".
        details: Human-readable description of the operation.

    Returns:
        Path to the created log file.
    """
    logs_dir = vault_path / VAULT_DIRS["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)

    file_size = briefing_path.stat().st_size if briefing_path.exists() else 0

    return write_log_entry(
        logs_dir=logs_dir,
        action_type="briefing_generation",
        source_path=vault_path,
        dest_path=briefing_path,
        file_size=file_size,
        outcome=outcome,
        details=details,
    )
