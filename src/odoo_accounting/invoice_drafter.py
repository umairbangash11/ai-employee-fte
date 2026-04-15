"""
odoo_accounting.invoice_drafter — Build and write invoice draft proposals.

Reads partner info from Odoo, constructs an OdooProposalFile, writes it
to vault/Pending_Approval/odoo/, and logs the operation. Nothing is sent
to Odoo — the draft is proposal-only until a human approves it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odoo_accounting.config import OdooConfig
from odoo_accounting.vault_writer import write_proposal
from odoo_mcp.client import OdooConnection, read_records
from sentinel.logger import write_log_entry


def _resolve_partner_name(conn: OdooConnection, partner_id: int) -> str:
    """Fetch partner name from Odoo. Returns 'unknown' on failure."""
    result = read_records(
        conn,
        "res.partner",
        [("id", "=", partner_id)],
        ["name"],
        limit=1,
    )
    if result.error or not result.records:
        return "unknown"
    return result.records[0].get("name", "unknown")


def draft_invoice_proposal(
    conn: OdooConnection,
    partner_id: int,
    lines: list[dict[str, Any]],
    config: OdooConfig,
    source_path: str = "",
    ref: str = "",
) -> Path:
    """Prepare an invoice draft proposal and write it to vault/Pending_Approval/odoo/.

    Args:
        conn:        Active OdooConnection (read-only use here).
        partner_id:  Odoo partner record ID.
        lines:       List of line item dicts: [{"name": "...", "quantity": 1, "price_unit": 100.0}].
        config:      OdooConfig with vault_path.
        source_path: Path to the trigger file that initiated this draft (for audit).
        ref:         Optional internal reference / note.

    Returns:
        Path to the written proposal file in vault/Pending_Approval/odoo/.
    """
    partner_name = _resolve_partner_name(conn, partner_id)

    payload: dict[str, Any] = {
        "partner_id": partner_id,
        "lines": lines,
    }
    if ref:
        payload["ref"] = ref

    line_summary = ", ".join(
        f"{item.get('name', '?')} ×{item.get('quantity', 1)} @ {item.get('price_unit', 0)}"
        for item in lines
    )
    body = (
        f"## Invoice Draft Proposal\n\n"
        f"- **Partner**: {partner_name} (ID: {partner_id})\n"
        f"- **Line items**: {line_summary or 'none'}\n"
        f"- **Reference**: {ref or '—'}\n\n"
        f"Review and move to `Approved/odoo/` to execute.\n"
    )

    proposal_data = {
        "action_type": "create_invoice",
        "odoo_partner": partner_name,
        "source_path": source_path,
        "odoo_payload": payload,
        "body": body,
    }

    proposal_path = write_proposal(proposal_data, config.vault_path)

    logs_dir = config.vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    write_log_entry(
        logs_dir=logs_dir,
        action_type="odoo_draft_invoice_proposal",
        source_path=Path(source_path) if source_path else config.vault_path,
        dest_path=proposal_path,
        file_size=0,
        outcome="success",
        details=f"invoice draft proposal written for partner '{partner_name}' (id={partner_id})",
    )

    return proposal_path
