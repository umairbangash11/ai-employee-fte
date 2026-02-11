"""Shared pytest fixtures for Vault Sentinel tests."""

import pytest
from pathlib import Path

CANONICAL_FOLDERS = ["Inbox", "Needs_Action", "Approved", "Done", "Logs"]


@pytest.fixture
def vault_dir(tmp_path):
    """Create a temporary vault directory with all 5 canonical folders."""
    for folder in CANONICAL_FOLDERS:
        (tmp_path / folder).mkdir()
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path):
    """Create an empty temporary directory (no vault folders)."""
    return tmp_path
