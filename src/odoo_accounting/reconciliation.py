"""
odoo_accounting.reconciliation — Scan for unreconciled invoice-payment pairs
and write reconciliation draft proposals.

Each unreconciled pair in Odoo becomes one proposal in
vault/Pending_Approval/odoo/ with action_type: reconcile_payment.
The batch limit (default: 20) prevents flooding the vault on large Odoo instances.
If no pairs are found, a summary log entry is written with outcome: success.
"""

from __future__ import annotations

from pathlib import Path

from odoo_accounting.config import OdooConfig
from odoo_accounting.vault_writer import write_proposal
from odoo_mcp.client import OdooConnection, read_records
from sentinel.logger import write_log_entry


def scan_and_draft_reconciliation(
    conn: OdooConnection,
    config: OdooConfig,
    source_path: str = "",
) -> list[Path]:
    """Scan Odoo for unreconciled lines and write one proposal per pair.

    Args:
        conn:        Active OdooConnection.
        config:      OdooConfig with vault_path and reconcile_batch_limit.
        source_path: Optional trigger context for audit logging.

    Returns:
        List of paths written to vault/Pending_Approval/odoo/.
        Empty list if no unreconciled items found.
    """
    logs_dir = config.vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    domain = [
        ("reconciled", "=", False),
        ("account_id.reconcile", "=", True),
        ("balance", "!=", 0),
    ]
    fields = ["id", "partner_id", "account_id", "balance", "date", "move_id"]

    result = read_records(
        conn,
        "account.move.line",
        domain,
        fields,
        limit=config.reconcile_batch_limit,
    )

    if result.error:
        write_log_entry(
            logs_dir=logs_dir,
            action_type="odoo_reconciliation_scan",
            source_path=Path(source_path) if source_path else config.vault_path,
            dest_path=config.vault_path / "Pending_Approval" / "odoo",
            file_size=0,
            outcome="failure",
            details=f"read failed: {result.error}",
        )
        return []

    if not result.records:
        write_log_entry(
            logs_dir=logs_dir,
            action_type="odoo_reconciliation_scan",
            source_path=Path(source_path) if source_path else config.vault_path,
            dest_path=config.vault_path / "Pending_Approval" / "odoo",
            file_size=0,
            outcome="success",
            details="no items to reconcile",
        )
        return []

    written: list[Path] = []
    for line in result.records:
        line_id = line.get("id")
        partner_name = (
            line.get("partner_id", [None, "unknown"])[1]
            if isinstance(line.get("partner_id"), list)
            else "unknown"
        )
        move_name = (
            line.get("move_id", [None, ""])[1]
            if isinstance(line.get("move_id"), list)
            else ""
        )
        balance = line.get("balance", 0.0)
        date = line.get("date", "")
        account = (
            line.get("account_id", [None, ""])[1]
            if isinstance(line.get("account_id"), list)
            else ""
        )

        payload = {
            "invoice_line_id": line_id,
            # payment_line_id will be determined by human operator on review
            "payment_line_id": None,
            "move_name": move_name,
            "balance": balance,
        }

        body = (
            f"## Reconciliation Draft Proposal\n\n"
            f"- **Partner**: {partner_name}\n"
            f"- **Move**: {move_name}\n"
            f"- **Account**: {account}\n"
            f"- **Balance**: {balance}\n"
            f"- **Date**: {date}\n"
            f"- **Invoice line ID**: {line_id}\n\n"
            f"Assign the matching payment_line_id and move to `Approved/odoo/` to execute.\n"
        )

        proposal_data = {
            "action_type": "reconcile_payment",
            "odoo_partner": partner_name,
            "source_path": source_path,
            "odoo_payload": payload,
            "body": body,
        }

        proposal_path = write_proposal(proposal_data, config.vault_path)
        written.append(proposal_path)

    write_log_entry(
        logs_dir=logs_dir,
        action_type="odoo_reconciliation_scan",
        source_path=Path(source_path) if source_path else config.vault_path,
        dest_path=config.vault_path / "Pending_Approval" / "odoo",
        file_size=0,
        outcome="success",
        details=f"wrote {len(written)} reconciliation proposal(s); batch_limit={config.reconcile_batch_limit}",
    )

    return written
