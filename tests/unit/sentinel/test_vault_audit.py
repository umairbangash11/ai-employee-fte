"""Unit tests for sentinel.vault_audit.run_vault_audit().

Tests cover:
    - test_clean_vault_passes: no type violations → passed=True
    - test_wrong_type_detected: file with wrong type → passed=False, violation recorded
    - test_missing_type_field_detected: file with no `type` field → violation recorded
    - test_nonexistent_dir_skipped: missing canonical dir → no error, dir skipped
    - test_report_fields_complete: all BoundaryAuditReport fields populated
"""

import textwrap
from pathlib import Path

import pytest

from sentinel.vault_audit import (
    TYPED_DIRECTORIES,
    BoundaryAuditReport,
    BoundaryViolation,
    run_vault_audit,
)


def _write_md(directory: Path, filename: str, type_value: str | None) -> Path:
    """Helper: write a minimal .md file with optional type frontmatter."""
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    if type_value is not None:
        content = textwrap.dedent(f"""\
            ---
            type: {type_value}
            source: test
            ---

            Body content.
        """)
    else:
        content = textwrap.dedent("""\
            ---
            source: test
            ---

            Body content without type field.
        """)
    filepath.write_text(content, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clean_vault_passes(tmp_path: Path) -> None:
    """Vault with correctly-typed files → passed=True, zero violations."""
    for dir_rel, expected_type in TYPED_DIRECTORIES.items():
        canonical = tmp_path / dir_rel
        _write_md(canonical, "item.md", expected_type)

    report = run_vault_audit(tmp_path)

    assert report.passed is True
    assert len(report.violations) == 0
    assert report.files_checked == len(TYPED_DIRECTORIES)
    assert report.directories_checked == len(TYPED_DIRECTORIES)


def test_wrong_type_detected(tmp_path: Path) -> None:
    """File with incorrect `type` value → passed=False, violation recorded."""
    canonical = tmp_path / "Needs_Action" / "plans"
    bad_file = _write_md(canonical, "bad.md", "wrong_type")

    report = run_vault_audit(tmp_path)

    assert report.passed is False
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.file_path == bad_file
    assert v.expected_type == "runtime_plan"
    assert v.actual_type == "wrong_type"
    assert v.directory == "Needs_Action/plans"


def test_missing_type_field_detected(tmp_path: Path) -> None:
    """File with no `type` field → violation with actual_type=None."""
    canonical = tmp_path / "Approved"
    missing_file = _write_md(canonical, "no_type.md", None)

    report = run_vault_audit(tmp_path)

    assert report.passed is False
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.file_path == missing_file
    assert v.actual_type is None
    assert v.expected_type == "execution_plan"


def test_nonexistent_dir_skipped(tmp_path: Path) -> None:
    """Missing canonical directory → no error, not counted in directories_checked."""
    # Don't create any directories — all typed dirs are absent
    report = run_vault_audit(tmp_path)

    assert report.passed is True
    assert report.directories_checked == 0
    assert report.files_checked == 0
    assert len(report.violations) == 0


def test_report_fields_complete(tmp_path: Path) -> None:
    """All BoundaryAuditReport fields are populated after a scan."""
    canonical = tmp_path / "Needs_Action" / "plans"
    _write_md(canonical, "plan.md", "runtime_plan")

    report = run_vault_audit(tmp_path)

    assert isinstance(report, BoundaryAuditReport)
    assert report.vault_path == tmp_path
    assert report.scanned_at != ""
    assert "T" in report.scanned_at  # ISO 8601 format
    assert report.directories_checked >= 1
    assert report.files_checked >= 1
    assert isinstance(report.violations, list)
    assert isinstance(report.passed, bool)
