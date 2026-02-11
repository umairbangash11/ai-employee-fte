"""Vault initialization and validation."""

import os
from pathlib import Path

CANONICAL_FOLDERS = ["Inbox", "Needs_Action", "Approved", "Done", "Logs"]


def init_vault(vault_path: str = ".") -> dict:
    """Create the 5 canonical folders in the vault directory.

    Idempotent: skips existing folders, creates missing ones.

    Returns a dict with keys: vault_path, created, existing.
    Raises ValueError if vault_path does not exist.
    Raises PermissionError if vault_path is not writable.
    """
    vault = Path(vault_path).resolve()

    if not vault.exists():
        raise ValueError(f"Vault path '{vault_path}' does not exist.")
    if not os.access(vault, os.W_OK):
        raise PermissionError(f"No write permission on '{vault_path}'.")

    created = []
    existing = []

    for folder in CANONICAL_FOLDERS:
        folder_path = vault / folder
        if folder_path.exists():
            existing.append(folder)
        else:
            folder_path.mkdir(parents=True, exist_ok=True)
            created.append(folder)

    return {
        "vault_path": str(vault),
        "created": created,
        "existing": existing,
    }


def validate_vault(vault_path: str = ".") -> bool:
    """Check that all 5 canonical folders exist in the vault directory."""
    vault = Path(vault_path).resolve()
    return all((vault / folder).is_dir() for folder in CANONICAL_FOLDERS)
