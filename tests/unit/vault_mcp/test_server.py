"""Unit tests for vault_mcp server tool logic.

Tests call the _*_impl functions directly — no MCP protocol overhead.
All tests use pytest's tmp_path fixture for an isolated temporary vault.
"""

import pytest
from pathlib import Path

from vault_mcp.server import (
    _safe_resolve,
    _list_files_impl,
    _read_file_impl,
    _write_file_impl,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """A minimal vault with canonical subdirs and a test file."""
    (tmp_path / "Inbox" / "email").mkdir(parents=True)
    (tmp_path / "Inbox" / "email" / "msg1.md").write_text("# Hello", encoding="utf-8")
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# _safe_resolve
# ---------------------------------------------------------------------------


def test_safe_resolve_valid_path(vault: Path) -> None:
    result = _safe_resolve(vault, "Inbox/email/msg1.md")
    assert result == (vault / "Inbox" / "email" / "msg1.md").resolve()


def test_safe_resolve_vault_root(vault: Path) -> None:
    result = _safe_resolve(vault, "")
    assert result == vault.resolve()


def test_safe_resolve_traversal_raises(vault: Path) -> None:
    with pytest.raises(ValueError, match="Path escapes vault root"):
        _safe_resolve(vault, "../../etc/passwd")


def test_safe_resolve_absolute_path_outside_raises(vault: Path) -> None:
    with pytest.raises(ValueError, match="Path escapes vault root"):
        _safe_resolve(vault, "/etc/passwd")


# ---------------------------------------------------------------------------
# list_files — US1
# ---------------------------------------------------------------------------


def test_list_files_existing_path(vault: Path) -> None:
    result = _list_files_impl(vault, "Inbox/email")
    assert "msg1.md" in result.splitlines()


def test_list_files_missing_path(vault: Path) -> None:
    result = _list_files_impl(vault, "NoSuchFolder")
    assert result == ""


def test_list_files_vault_root(vault: Path) -> None:
    result = _list_files_impl(vault, "")
    names = result.splitlines()
    assert "Inbox" in names
    assert "Needs_Action" in names
    assert "Done" in names


def test_list_files_traversal_rejected(vault: Path) -> None:
    result = _list_files_impl(vault, "../../etc")
    assert result.startswith("Error:")
    assert "Path escapes vault root" in result


def test_list_files_dir_with_only_subdirs(vault: Path) -> None:
    (vault / "Inbox" / "sub").mkdir()
    result = _list_files_impl(vault, "Inbox")
    names = result.splitlines()
    assert "email" in names
    assert "sub" in names


# ---------------------------------------------------------------------------
# read_file — US2
# ---------------------------------------------------------------------------


def test_read_file_success(vault: Path) -> None:
    result = _read_file_impl(vault, "Inbox/email/msg1.md")
    assert result == "# Hello"


def test_read_file_not_found(vault: Path) -> None:
    result = _read_file_impl(vault, "Inbox/email/ghost.md")
    assert "File not found" in result
    assert result.startswith("Error:")


def test_read_file_traversal_rejected(vault: Path) -> None:
    result = _read_file_impl(vault, "../../etc/passwd")
    assert result.startswith("Error:")
    assert "Path escapes vault root" in result


def test_read_file_directory_rejected(vault: Path) -> None:
    result = _read_file_impl(vault, "Inbox")
    assert result.startswith("Error:")
    assert "directory" in result.lower()


def test_read_file_empty_path_rejected(vault: Path) -> None:
    result = _read_file_impl(vault, "")
    assert result.startswith("Error:")
    assert "empty" in result.lower()


def test_read_file_binary_rejected(vault: Path, tmp_path: Path) -> None:
    bin_file = vault / "Inbox" / "data.bin"
    bin_file.write_bytes(b"\xff\xfe\x00\x01")
    result = _read_file_impl(vault, "Inbox/data.bin")
    assert result.startswith("Error:")
    assert "UTF-8" in result


# ---------------------------------------------------------------------------
# write_file — US3
# ---------------------------------------------------------------------------


def test_write_file_creates_new(vault: Path) -> None:
    result = _write_file_impl(vault, "Needs_Action/new.md", "# New File")
    assert result == "Written: Needs_Action/new.md"
    assert (vault / "Needs_Action" / "new.md").read_text(encoding="utf-8") == "# New File"


def test_write_file_overwrites_existing(vault: Path) -> None:
    _write_file_impl(vault, "Inbox/email/msg1.md", "# Updated")
    content = (vault / "Inbox" / "email" / "msg1.md").read_text(encoding="utf-8")
    assert content == "# Updated"


def test_write_file_creates_parent_dirs(vault: Path) -> None:
    result = _write_file_impl(vault, "Deep/Sub/Dir/note.md", "nested")
    assert result == "Written: Deep/Sub/Dir/note.md"
    assert (vault / "Deep" / "Sub" / "Dir" / "note.md").exists()


def test_write_file_traversal_rejected(vault: Path) -> None:
    target = vault.parent / "evil.md"
    result = _write_file_impl(vault, "../evil.md", "bad content")
    assert result.startswith("Error:")
    assert "Path escapes vault root" in result
    assert not target.exists()


def test_write_file_empty_path_rejected(vault: Path) -> None:
    result = _write_file_impl(vault, "", "content")
    assert result.startswith("Error:")
    assert "empty" in result.lower()
