"""Vault directory bootstrapper for social post lifecycle directories."""

from pathlib import Path

_LIFECYCLE_DIRS = ("Pending_Approval", "Approved", "Done", "Needs_Action")


def ensure_vault_dirs(vault_path: Path, platform: str) -> None:
    """Create all canonical subdirectories for a platform if absent.

    Creates: Pending_Approval/<platform>/, Approved/<platform>/,
             Done/<platform>/, Needs_Action/<platform>/

    Idempotent — safe to call on every executor startup (FR-007).

    Args:
        vault_path: Vault root directory
        platform: Platform name ('facebook', 'instagram', 'x')
    """
    for parent_dir in _LIFECYCLE_DIRS:
        target = vault_path / parent_dir / platform
        target.mkdir(parents=True, exist_ok=True)
