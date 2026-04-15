"""
Tests for odoo_accounting.vault_writer.

Minimal validation per spec intent: vault writes + frontmatter completeness.
"""

import json
from pathlib import Path

import pytest
import yaml

from odoo_accounting.vault_writer import (
    VaultBoundaryError,
    move_to_done,
    write_accounting_record,
    write_proposal,
)


REQUIRED_PROPOSAL_FIELDS = {
    "type",
    "action_type",
    "status",
    "source_path",
    "dest_path",
    "captured_at",
    "odoo_partner",
    "odoo_payload",
}


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter between the first two '---' delimiters."""
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) >= 3, "No valid frontmatter found"
    return yaml.safe_load(parts[1])


# ─── T009-1: Proposal written to Pending_Approval ────────────────────────────


def test_proposal_written_to_pending_approval(tmp_path: Path) -> None:
    """write_proposal() creates a file in vault/Pending_Approval/odoo/."""
    proposal_data = {
        "action_type": "create_invoice",
        "odoo_partner": "Acme Corp",
        "source_path": "Inbox/email/some-email.md",
        "odoo_payload": {"partner_id": 7, "lines": []},
        "body": "Invoice draft for Acme Corp.",
    }
    result = write_proposal(proposal_data, tmp_path)

    assert result.exists(), f"Proposal file not created at {result}"
    assert "Pending_Approval" in str(result)
    assert "odoo" in str(result)
    assert result.suffix == ".md"


# ─── T009-2: Proposal frontmatter completeness ───────────────────────────────


def test_proposal_frontmatter_complete(tmp_path: Path) -> None:
    """write_proposal() writes all required YAML frontmatter fields."""
    proposal_data = {
        "action_type": "create_invoice",
        "odoo_partner": "Beta Ltd",
        "source_path": "Inbox/email/trigger.md",
        "odoo_payload": {"partner_id": 12, "lines": [{"name": "Widget", "quantity": 2, "price_unit": 50.0}]},
        "body": "Proposed invoice for Beta Ltd.",
    }
    result = write_proposal(proposal_data, tmp_path)
    fm = _parse_frontmatter(result)

    missing = REQUIRED_PROPOSAL_FIELDS - set(fm.keys())
    assert not missing, f"Missing frontmatter fields: {missing}"

    assert fm["type"] == "pending_action"
    assert fm["action_type"] == "create_invoice"
    assert fm["status"] == "awaiting_approval"
    assert fm["odoo_partner"] == "Beta Ltd"

    # odoo_payload must be valid JSON
    payload = json.loads(fm["odoo_payload"])
    assert payload["partner_id"] == 12


# ─── T009-3: Accounting record written to Accounting dir ─────────────────────


def test_accounting_record_written_to_accounting_dir(tmp_path: Path) -> None:
    """write_accounting_record() creates a file in vault/Accounting/."""
    # Create a dummy proposal path inside the vault
    proposal_path = tmp_path / "Approved" / "odoo" / "20260415-120000-create_invoice-acme.md"
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text("---\ntype: pending_action\n---\n", encoding="utf-8")

    result = write_accounting_record(
        odoo_id=99,
        proposal_path=proposal_path,
        action_type="create_invoice",
        partner_name="Acme Corp",
        vault_path=tmp_path,
    )

    assert result.exists(), f"Accounting record not created at {result}"
    assert "Accounting" in str(result)

    fm = _parse_frontmatter(result)
    assert fm["type"] == "accounting_record"
    assert fm["status"] == "executed"
    assert fm["odoo_id"] == 99
    assert fm["outcome"] == "success"


# ─── T009-4: move_to_done ─────────────────────────────────────────────────────


def test_move_to_done(tmp_path: Path) -> None:
    """move_to_done() moves a file from Approved/odoo/ to Done/odoo/."""
    src = tmp_path / "Approved" / "odoo" / "test-proposal.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("---\ntype: pending_action\n---\n", encoding="utf-8")

    dest = move_to_done(src, tmp_path)

    assert not src.exists(), "Source file should have been moved"
    assert dest.exists(), f"File not found at Done destination {dest}"
    assert "Done" in str(dest)
    assert "odoo" in str(dest)


# ─── T009-5: Path outside vault rejected ─────────────────────────────────────


def test_path_outside_vault_rejected(tmp_path: Path) -> None:
    """write_proposal() raises VaultBoundaryError for path traversal attempts."""
    # Craft a proposal_data that attempts to write outside the vault
    # by manipulating the partner slug to create a traversal — but since
    # vault_writer builds the path internally, we test by passing a vault_path
    # and then verifying that a file genuinely outside would be rejected via
    # _safe_resolve directly.
    from odoo_accounting.vault_writer import _safe_resolve

    outer_path = tmp_path.parent / "secret.md"
    with pytest.raises(VaultBoundaryError):
        _safe_resolve(tmp_path, outer_path)
