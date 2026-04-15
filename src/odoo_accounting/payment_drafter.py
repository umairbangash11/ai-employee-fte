"""
odoo_accounting.payment_drafter — Build and write payment draft proposals.

Reads partner info from Odoo, constructs an OdooProposalFile with
action_type: prepare_payment, writes it to vault/Pending_Approval/odoo/,
and logs the operation. Nothing is registered in Odoo until a human approves.
"""

from __future__ import annotations

from pathlib import Path

from odoo_accounting.config import OdooConfig
from odoo_accounting.vault_writer import write_proposal
from odoo_accounting.invoice_drafter import _resolve_partner_name
from odoo_mcp.client import OdooConnection
from sentinel.logger import write_log_entry


def draft_payment_proposal(
    conn: OdooConnection,
    partner_id: int,
    amount: float,
    config: OdooConfig,
    invoice_ref: str = "",
    source_path: str = "",
) -> Path:
    """Prepare a payment draft proposal and write it to vault/Pending_Approval/odoo/.

    Args:
        conn:        Active OdooConnection (read-only use here).
        partner_id:  Odoo partner record ID.
        amount:      Payment amount (positive float).
        config:      OdooConfig with vault_path.
        invoice_ref: Optional invoice reference or memo.
        source_path: Path to the trigger file that initiated this draft.

    Returns:
        Path to the written proposal file in vault/Pending_Approval/odoo/.
    """
    partner_name = _resolve_partner_name(conn, partner_id)

    payload = {
        "partner_id": partner_id,
        "amount": amount,
        "payment_type": "outbound",
    }
    if invoice_ref:
        payload["ref"] = invoice_ref

    body = (
        f"## Payment Draft Proposal\n\n"
        f"- **Partner**: {partner_name} (ID: {partner_id})\n"
        f"- **Amount**: {amount}\n"
        f"- **Invoice reference**: {invoice_ref or '—'}\n\n"
        f"Review and move to `Approved/odoo/` to execute.\n"
    )

    proposal_data = {
        "action_type": "prepare_payment",
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
        action_type="odoo_draft_payment_proposal",
        source_path=Path(source_path) if source_path else config.vault_path,
        dest_path=proposal_path,
        file_size=0,
        outcome="success",
        details=f"payment draft proposal written for partner '{partner_name}' (id={partner_id}) amount={amount}",
    )

    return proposal_path
