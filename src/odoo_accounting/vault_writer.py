"""
odoo_accounting.vault_writer — Central vault write point for all Odoo accounting artifacts.

All files go through this module to ensure:
  - Consistent YAML frontmatter
  - Path boundary enforcement (no escapes outside vault_path)
  - Automatic parent directory creation
  - Duplicate slug collision avoidance (counter suffix)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class VaultBoundaryError(Exception):
    """Raised when a resolved path would escape the vault root."""


def _safe_resolve(vault_root: Path, relative_path: Path | str) -> Path:
    """Resolve a path relative to vault_root and verify it stays inside.

    Raises:
        VaultBoundaryError: if the resolved path escapes vault_root.
    """
    resolved = (vault_root / relative_path).resolve()
    try:
        resolved.relative_to(vault_root.resolve())
    except ValueError:
        raise VaultBoundaryError(
            f"Path '{relative_path}' resolves outside vault root '{vault_root}'"
        )
    return resolved


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _unique_path(target: Path) -> Path:
    """Return target if it doesn't exist; otherwise append a counter suffix."""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _build_frontmatter(fields: dict[str, Any]) -> str:
    """Render a YAML frontmatter block from a flat dict of scalar/string values."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, str):
            # Escape internal double-quotes and wrap in double-quotes
            escaped = value.replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def write_proposal(proposal_data: dict[str, Any], vault_path: Path) -> Path:
    """Write an Odoo action proposal to vault/Pending_Approval/odoo/<slug>.md.

    Required keys in proposal_data:
        action_type: str   — 'create_invoice' | 'prepare_payment' | 'reconcile_payment'
        odoo_partner: str  — human-readable partner name
        odoo_payload: dict — the action payload to be executed on approval
        source_path: str   — trigger file path that initiated this draft
        body: str          — human-readable summary for operator review

    Returns:
        Path to the written proposal file.

    Raises:
        VaultBoundaryError: if the resolved path escapes vault_path.
        KeyError: if a required key is missing from proposal_data.
    """
    action_type = proposal_data["action_type"]
    partner_name = proposal_data.get("odoo_partner", "unknown")
    partner_slug = partner_name.lower().replace(" ", "-")[:30]

    slug = f"{_now_slug()}-{action_type}-{partner_slug}.md"
    pending_dir = vault_path / "Pending_Approval" / "odoo"

    target = _safe_resolve(vault_path, pending_dir / slug)
    target = _unique_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    rel_dest = str(target.relative_to(vault_path))

    frontmatter = _build_frontmatter({
        "type": "pending_action",
        "action_type": action_type,
        "status": "awaiting_approval",
        "source_path": proposal_data.get("source_path", ""),
        "dest_path": rel_dest,
        "captured_at": _now_iso(),
        "odoo_partner": partner_name,
        "odoo_payload": json.dumps(proposal_data.get("odoo_payload", {})),
    })

    body = proposal_data.get("body", f"Proposed action: {action_type} for {partner_name}")
    content = f"{frontmatter}\n\n{body}\n"
    target.write_text(content, encoding="utf-8")
    return target


def write_accounting_record(
    odoo_id: int,
    proposal_path: Path,
    action_type: str,
    partner_name: str,
    vault_path: Path,
) -> Path:
    """Write a confirmation record to vault/Accounting/<slug>.md after execution.

    Returns:
        Path to the written accounting record.

    Raises:
        VaultBoundaryError: if the resolved path escapes vault_path.
    """
    accounting_dir = vault_path / "Accounting"
    slug = f"{_now_slug()}-{action_type}-confirmed.md"
    target = _safe_resolve(vault_path, accounting_dir / slug)
    target = _unique_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    rel_dest = str(target.relative_to(vault_path))
    rel_proposal = str(proposal_path.relative_to(vault_path)) if proposal_path.is_relative_to(vault_path) else str(proposal_path)

    frontmatter = _build_frontmatter({
        "type": "accounting_record",
        "action_type": action_type,
        "status": "executed",
        "odoo_id": odoo_id,
        "source_proposal": rel_proposal,
        "executed_at": _now_iso(),
        "dest_path": rel_dest,
        "outcome": "success",
    })

    body = (
        f"## Execution Confirmed\n\n"
        f"- **Action**: {action_type}\n"
        f"- **Partner**: {partner_name}\n"
        f"- **Odoo record ID**: {odoo_id}\n"
        f"- **Source proposal**: {rel_proposal}\n"
        f"- **Executed at**: {_now_iso()}\n"
    )
    content = f"{frontmatter}\n\n{body}\n"
    target.write_text(content, encoding="utf-8")
    return target


def move_to_done(proposal_path: Path, vault_path: Path) -> Path:
    """Move a file from vault/Approved/odoo/ to vault/Done/odoo/.

    Returns:
        New path in Done/odoo/.

    Raises:
        VaultBoundaryError: if source or destination escapes vault_path.
        FileNotFoundError: if proposal_path does not exist.
    """
    _safe_resolve(vault_path, proposal_path)
    done_dir = vault_path / "Done" / "odoo"
    done_dir.mkdir(parents=True, exist_ok=True)

    dest = _unique_path(done_dir / proposal_path.name)
    _safe_resolve(vault_path, dest)
    shutil.move(str(proposal_path), str(dest))
    return dest


def move_to_needs_action(
    proposal_path: Path,
    reason: str,
    vault_path: Path,
) -> Path:
    """Move a file from vault/Approved/odoo/ to vault/Needs_Action/odoo/.

    Returns:
        New path in Needs_Action/odoo/.

    Raises:
        VaultBoundaryError: if source or destination escapes vault_path.
    """
    _safe_resolve(vault_path, proposal_path)
    na_dir = vault_path / "Needs_Action" / "odoo"
    na_dir.mkdir(parents=True, exist_ok=True)

    dest = _unique_path(na_dir / proposal_path.name)
    _safe_resolve(vault_path, dest)

    try:
        shutil.move(str(proposal_path), str(dest))
    except FileNotFoundError:
        # File may have already been moved; log but don't raise
        pass

    return dest


def ensure_vault_dirs(vault_path: Path) -> None:
    """Create all required Odoo canonical vault subdirectories if missing."""
    required_dirs = [
        vault_path / "Accounting",
        vault_path / "Pending_Approval" / "odoo",
        vault_path / "Approved" / "odoo",
        vault_path / "Done" / "odoo",
        vault_path / "Needs_Action" / "odoo",
        vault_path / "Logs",
    ]
    for d in required_dirs:
        d.mkdir(parents=True, exist_ok=True)
