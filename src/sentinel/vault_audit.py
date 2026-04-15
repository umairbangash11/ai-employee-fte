"""Vault boundary audit tool.

Scans canonical vault directories and reports files whose `type` frontmatter
field does not match the expected type for that directory.

Public interface:
    run_vault_audit(vault_path: Path) -> BoundaryAuditReport
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# Typed directories: maps canonical subdirectory → expected `type` value.
# Other directories (Inbox/, Done/, Logs/, etc.) are intentionally excluded —
# their contents are heterogeneous and have no mandatory `type` constraint.
TYPED_DIRECTORIES: dict[str, str] = {
    "Needs_Action/plans": "runtime_plan",
    "Approved": "execution_plan",
    "Pending_Approval": "pending_action",
    "Needs_Action/drafts": "draft_reply",
}


@dataclass
class BoundaryViolation:
    """A single file that violates directory type expectations.

    Attributes:
        file_path: Absolute path to the offending file.
        directory: Canonical directory name (relative to vault root).
        expected_type: Expected `type` value for this directory.
        actual_type: Actual `type` value found, or None if field is absent.
    """

    file_path: Path
    directory: str
    expected_type: str
    actual_type: str | None


@dataclass
class BoundaryAuditReport:
    """Report produced by run_vault_audit().

    Attributes:
        vault_path: Vault root that was scanned.
        scanned_at: ISO 8601 timestamp of when the scan ran.
        directories_checked: Count of canonical directories scanned.
        files_checked: Total .md files inspected.
        violations: Files whose `type` field mismatches directory expectation.
        passed: True if violations is empty.
    """

    vault_path: Path
    scanned_at: str
    directories_checked: int
    files_checked: int
    violations: list[BoundaryViolation] = field(default_factory=list)
    passed: bool = True


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_TYPE_FIELD_RE = re.compile(r"^\s*type\s*:\s*(.+)$", re.MULTILINE)


def _extract_type_from_file(file_path: Path) -> str | None:
    """Parse the `type:` field from YAML frontmatter of a Markdown file.

    Returns the type value string, or None if the field is absent or the file
    cannot be read / parsed. Errors are non-blocking — caller decides how to
    handle None.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None

    frontmatter_block = match.group(1)
    type_match = _TYPE_FIELD_RE.search(frontmatter_block)
    if not type_match:
        return None

    return type_match.group(1).strip().strip('"').strip("'")


def run_vault_audit(vault_path: Path) -> BoundaryAuditReport:
    """Scan typed canonical directories for `type` frontmatter mismatches.

    For each directory listed in TYPED_DIRECTORIES:
    - If the directory does not exist, it is skipped (not an error).
    - For each .md file in the directory, the `type` frontmatter field is read.
    - If the value does not match the expected type, a BoundaryViolation is
      recorded.
    - Files that cannot be read individually are skipped non-blocking and
      recorded as violations with actual_type=None.

    Args:
        vault_path: Path to the vault root directory.

    Returns:
        BoundaryAuditReport with violations list and passed flag.
    """
    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    violations: list[BoundaryViolation] = []
    directories_checked = 0
    files_checked = 0

    for dir_rel, expected_type in TYPED_DIRECTORIES.items():
        canonical_dir = vault_path / dir_rel
        if not canonical_dir.exists():
            continue

        directories_checked += 1

        try:
            md_files = list(canonical_dir.glob("*.md"))
        except OSError:
            continue

        for md_file in md_files:
            files_checked += 1
            actual_type = _extract_type_from_file(md_file)

            if actual_type != expected_type:
                violations.append(
                    BoundaryViolation(
                        file_path=md_file,
                        directory=dir_rel,
                        expected_type=expected_type,
                        actual_type=actual_type,
                    )
                )

    return BoundaryAuditReport(
        vault_path=vault_path,
        scanned_at=scanned_at,
        directories_checked=directories_checked,
        files_checked=files_checked,
        violations=violations,
        passed=len(violations) == 0,
    )
