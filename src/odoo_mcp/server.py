"""
odoo_mcp.server — FastMCP server exposing 6 Odoo tools.

Read tools (no approval gate):
  odoo_get_invoices, odoo_get_partners, odoo_get_unreconciled

Write tools (executor-only, post-approval):
  odoo_create_invoice_draft, odoo_create_payment_draft, odoo_reconcile_payment

All tools log to vault/Logs/ via sentinel.logger.write_log_entry.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from odoo_accounting.config import OdooConfig
from odoo_mcp.client import (
    OdooConnection,
    OdooConnectionError,
    create_record,
    read_records,
    reconcile_lines,
)
from sentinel.logger import write_log_entry


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(
    config: OdooConfig,
    action_type: str,
    source: str,
    dest: str,
    outcome: str,
    details: str,
) -> None:
    """Write a 6-field log entry to vault/Logs/."""
    logs_dir = config.vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    try:
        write_log_entry(
            logs_dir=logs_dir,
            action_type=action_type,
            source_path=Path(source),
            dest_path=Path(dest),
            file_size=0,
            outcome=outcome,
            details=details,
        )
    except Exception:
        pass  # Never crash the MCP tool on a logging failure


def create_server(conn: OdooConnection, config: OdooConfig) -> FastMCP:
    """Build and return the FastMCP server with all 6 Odoo tools wired."""

    mcp = FastMCP("odoo-accounting")

    # ─────────────────────────────────────────────────────────────
    # READ TOOLS — no approval gate
    # ─────────────────────────────────────────────────────────────

    @mcp.tool()
    def odoo_get_invoices(state: str = "open", limit: int = 50) -> dict[str, Any]:
        """Retrieve invoices from Odoo.

        Args:
            state: Filter by state — 'open' (posted, unpaid), 'draft', or 'all'.
            limit: Maximum number of records to return.
        """
        if state == "open":
            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
            ]
        elif state == "draft":
            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
            ]
        else:
            domain = [("move_type", "=", "out_invoice")]

        fields = [
            "id", "name", "partner_id", "amount_total",
            "currency_id", "state", "payment_state", "invoice_date",
        ]
        result = read_records(conn, "account.move", domain, fields, limit)

        if result.error:
            _log(
                config, "odoo_get_invoices",
                conn.url, "account.move",
                "failure", result.error,
            )
            return {"error": result.error, "records": []}

        records = [
            {
                "id": r.get("id"),
                "partner_name": r.get("partner_id", [None, ""])[1] if isinstance(r.get("partner_id"), list) else r.get("partner_id"),
                "amount_total": r.get("amount_total"),
                "currency": r.get("currency_id", [None, ""])[1] if isinstance(r.get("currency_id"), list) else r.get("currency_id"),
                "state": r.get("state"),
                "payment_state": r.get("payment_state"),
                "invoice_date": r.get("invoice_date"),
            }
            for r in result.records
        ]
        _log(
            config, "odoo_get_invoices",
            conn.url, "account.move",
            "success", f"returned {len(records)} invoice(s), state={state}",
        )
        return {"records": records, "count": len(records), "fetched_at": result.fetched_at}

    @mcp.tool()
    def odoo_get_partners(query: str = "", limit: int = 20) -> dict[str, Any]:
        """Look up partner (customer/vendor) records.

        Args:
            query: Name search string. Empty returns first `limit` partners.
            limit: Maximum number of records to return.
        """
        domain: list[Any] = []
        if query:
            domain = [("name", "ilike", query)]

        fields = ["id", "name", "email", "credit", "debit"]
        result = read_records(conn, "res.partner", domain, fields, limit)

        if result.error:
            _log(
                config, "odoo_get_partners",
                conn.url, "res.partner",
                "failure", result.error,
            )
            return {"error": result.error, "records": []}

        records = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "email": r.get("email") or "",
                "credit": r.get("credit", 0.0),
                "debit": r.get("debit", 0.0),
            }
            for r in result.records
        ]
        _log(
            config, "odoo_get_partners",
            conn.url, "res.partner",
            "success", f"returned {len(records)} partner(s), query='{query}'",
        )
        return {"records": records, "fetched_at": result.fetched_at}

    @mcp.tool()
    def odoo_get_unreconciled(limit: int = 50) -> dict[str, Any]:
        """Retrieve unreconciled invoice-payment account move lines.

        Args:
            limit: Maximum number of unreconciled lines to return.
        """
        domain = [
            ("reconciled", "=", False),
            ("account_id.reconcile", "=", True),
            ("balance", "!=", 0),
        ]
        fields = ["id", "partner_id", "account_id", "balance", "date", "move_id"]
        result = read_records(conn, "account.move.line", domain, fields, limit)

        if result.error:
            _log(
                config, "odoo_get_unreconciled",
                conn.url, "account.move.line",
                "failure", result.error,
            )
            return {"error": result.error, "records": []}

        records = [
            {
                "id": r.get("id"),
                "partner_name": r.get("partner_id", [None, ""])[1] if isinstance(r.get("partner_id"), list) else "",
                "account": r.get("account_id", [None, ""])[1] if isinstance(r.get("account_id"), list) else "",
                "balance": r.get("balance", 0.0),
                "date": r.get("date"),
                "move_name": r.get("move_id", [None, ""])[1] if isinstance(r.get("move_id"), list) else "",
            }
            for r in result.records
        ]
        _log(
            config, "odoo_get_unreconciled",
            conn.url, "account.move.line",
            "success", f"returned {len(records)} unreconciled line(s)",
        )
        return {"records": records, "count": len(records), "fetched_at": result.fetched_at}

    # ─────────────────────────────────────────────────────────────
    # WRITE TOOLS — executor-only, post-approval
    # These tools MUST only be called by executor.py after detecting
    # an authorized file in vault/Approved/odoo/. They MUST NOT be
    # called directly by any external agent or Claude Code session.
    # ─────────────────────────────────────────────────────────────

    @mcp.tool()
    def odoo_create_invoice_draft(
        partner_id: int,
        lines: str,
        currency_code: str = "",
        ref: str = "",
    ) -> dict[str, Any]:
        """Create a draft invoice in Odoo. EXECUTOR-ONLY — post-approval.

        Args:
            partner_id:    Odoo partner record ID.
            lines:         JSON array of line items: [{"name":"...", "quantity":1, "price_unit":100.0}].
            currency_code: ISO currency code (defaults to Odoo company currency).
            ref:           Internal reference / note.
        """
        try:
            line_items = json.loads(lines)
        except (json.JSONDecodeError, TypeError) as exc:
            return {"error": f"invalid lines format: {exc}"}

        invoice_lines = [
            (0, 0, {
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 1),
                "price_unit": item.get("price_unit", 0.0),
            })
            for item in line_items
        ]

        values: dict[str, Any] = {
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": partner_id,
            "invoice_line_ids": invoice_lines,
        }
        if ref:
            values["ref"] = ref

        try:
            odoo_id = create_record(conn, "account.move", values)
        except OdooConnectionError as exc:
            _log(
                config, "odoo_create_invoice_draft",
                conn.url, "account.move",
                "failure", str(exc),
            )
            return {"error": str(exc)}

        _log(
            config, "odoo_create_invoice_draft",
            conn.url, "account.move",
            "success", f"created invoice draft odoo_id={odoo_id} partner_id={partner_id}",
        )
        return {
            "odoo_id": odoo_id,
            "state": "draft",
            "created_at": _now_iso(),
        }

    @mcp.tool()
    def odoo_create_payment_draft(
        partner_id: int,
        amount: float,
        payment_type: str = "outbound",
        ref: str = "",
    ) -> dict[str, Any]:
        """Create a draft payment in Odoo. EXECUTOR-ONLY — post-approval.

        Args:
            partner_id:   Odoo partner record ID.
            amount:       Payment amount (positive float).
            payment_type: 'outbound' (default) or 'inbound'.
            ref:          Invoice reference or memo.
        """
        values: dict[str, Any] = {
            "partner_id": partner_id,
            "amount": amount,
            "payment_type": payment_type,
        }
        if ref:
            values["ref"] = ref

        try:
            odoo_id = create_record(conn, "account.payment", values)
        except OdooConnectionError as exc:
            _log(
                config, "odoo_create_payment_draft",
                conn.url, "account.payment",
                "failure", str(exc),
            )
            return {"error": str(exc)}

        _log(
            config, "odoo_create_payment_draft",
            conn.url, "account.payment",
            "success", f"created payment draft odoo_id={odoo_id} partner_id={partner_id} amount={amount}",
        )
        return {
            "odoo_id": odoo_id,
            "state": "draft",
            "created_at": _now_iso(),
        }

    @mcp.tool()
    def odoo_reconcile_payment(
        invoice_line_id: int,
        payment_line_id: int,
    ) -> dict[str, Any]:
        """Reconcile an invoice move line with a payment move line. EXECUTOR-ONLY.

        Args:
            invoice_line_id: Odoo account.move.line ID for the invoice line.
            payment_line_id: Odoo account.move.line ID for the payment line.
        """
        try:
            reconcile_lines(conn, [invoice_line_id, payment_line_id])
        except OdooConnectionError as exc:
            _log(
                config, "odoo_reconcile_payment",
                conn.url, "account.move.line",
                "failure", str(exc),
            )
            return {"error": str(exc)}

        _log(
            config, "odoo_reconcile_payment",
            conn.url, "account.move.line",
            "success",
            f"reconciled invoice_line_id={invoice_line_id} payment_line_id={payment_line_id}",
        )
        return {
            "reconciled": True,
            "invoice_line_id": invoice_line_id,
            "payment_line_id": payment_line_id,
            "reconciled_at": _now_iso(),
        }

    return mcp
