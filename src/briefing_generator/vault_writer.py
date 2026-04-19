"""Vault writer for CEO Briefing Generator.

Writes briefing files to vault/Briefings/ with proper filename handling
and deduplication.
"""

from datetime import datetime, timezone
from pathlib import Path

from briefing_generator.config import VAULT_DIRS


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


def _unique_path(target: Path) -> Path:
    """Return target if it doesn't exist; otherwise append a counter suffix.

    Example: If 2026-04-18_Monday_Briefing.md exists, returns
    2026-04-18_Monday_Briefing-2.md, then -3, etc.
    """
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def get_briefing_filename(briefing_type: str) -> str:
    """Generate briefing filename based on type.

    Args:
        briefing_type: "Monday" or "Adhoc"

    Returns:
        Filename like "2026-04-18_Monday_Briefing.md"
    """
    date_str = _today_str()
    return f"{date_str}_{briefing_type}_Briefing.md"


def ensure_briefings_dir(vault_path: Path) -> Path:
    """Ensure vault/Briefings/ directory exists.

    Args:
        vault_path: Path to vault root.

    Returns:
        Path to Briefings directory.
    """
    briefings_dir = vault_path / VAULT_DIRS["briefings"]
    briefings_dir.mkdir(parents=True, exist_ok=True)
    return briefings_dir


def write_briefing(
    vault_path: Path,
    briefing_type: str,
    content: str,
) -> Path:
    """Write briefing content to vault/Briefings/.

    Args:
        vault_path: Path to vault root.
        briefing_type: "Monday" or "Adhoc"
        content: Complete markdown content to write.

    Returns:
        Path to the written briefing file.
    """
    briefings_dir = ensure_briefings_dir(vault_path)
    filename = get_briefing_filename(briefing_type)
    target = briefings_dir / filename
    final_path = _unique_path(target)
    final_path.write_text(content, encoding="utf-8")
    return final_path
