"""
odoo_accounting.executor — Watchdog-based executor for approved Odoo actions.

Watches vault/Approved/odoo/ for new .md files (via watchdog Observer).
On detection, reads the proposal, calls the appropriate Odoo MCP write tool
via odoo_mcp.client, applies the Ralph Wiggum Loop (3 attempts), then:
  - success: writes vault/Accounting/ confirmation + moves to Done/odoo/ + logs
  - exhausted: moves to Needs_Action/odoo/ + logs (outcome: failure)

The executor also performs a startup scan for pre-existing files in
Approved/odoo/ before starting the Observer (mitigates missed-event race).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from odoo_accounting.config import OdooConfig, OdooConfigError, load_odoo_config
from odoo_accounting.vault_writer import (
    ensure_vault_dirs,
    move_to_done,
    move_to_needs_action,
    write_accounting_record,
)
from odoo_mcp.client import (
    OdooConnection,
    OdooConnectionError,
    connect,
    create_record,
    reconcile_lines,
)
from sentinel.logger import write_log_entry

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _log(
    config: OdooConfig,
    action_type: str,
    source: Path,
    dest: Path,
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
            source_path=source,
            dest_path=dest,
            file_size=0,
            outcome=outcome,
            details=details,
        )
    except Exception as exc:
        logger.warning("Log write failed: %s", exc)


def _read_proposal(path: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a proposal .md file.

    Returns a dict with at least 'action_type' and 'odoo_payload' on success,
    or None if the file cannot be parsed.
    """
    try:
        import yaml  # noqa: PLC0415

        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning("No frontmatter in %s", path)
            return None
        fm = yaml.safe_load(parts[1]) or {}
        return fm
    except Exception as exc:
        logger.error("Failed to read proposal %s: %s", path, exc)
        return None


def _execute_invoice(
    conn: OdooConnection,
    payload: dict[str, Any],
) -> int:
    """Create a draft invoice in Odoo. Returns odoo_id."""
    partner_id = payload.get("partner_id")
    lines_raw = payload.get("lines", [])
    ref = payload.get("ref", "")

    invoice_lines = [
        (0, 0, {
            "name": item.get("name", ""),
            "quantity": item.get("quantity", 1),
            "price_unit": item.get("price_unit", 0.0),
        })
        for item in lines_raw
    ]
    values: dict[str, Any] = {
        "move_type": "out_invoice",
        "state": "draft",
        "partner_id": partner_id,
        "invoice_line_ids": invoice_lines,
    }
    if ref:
        values["ref"] = ref

    return create_record(conn, "account.move", values)


def _execute_payment(
    conn: OdooConnection,
    payload: dict[str, Any],
) -> int:
    """Create a draft payment in Odoo. Returns odoo_id."""
    values: dict[str, Any] = {
        "partner_id": payload.get("partner_id"),
        "amount": payload.get("amount", 0.0),
        "payment_type": payload.get("payment_type", "outbound"),
    }
    ref = payload.get("ref", "")
    if ref:
        values["ref"] = ref

    return create_record(conn, "account.payment", values)


def _execute_reconciliation(
    conn: OdooConnection,
    payload: dict[str, Any],
) -> int:
    """Apply invoice-payment reconciliation. Returns 0 (no single record ID)."""
    invoice_line_id = payload.get("invoice_line_id")
    payment_line_id = payload.get("payment_line_id")
    if not invoice_line_id or not payment_line_id:
        raise OdooConnectionError(
            "reconcile_payment requires both invoice_line_id and payment_line_id in payload"
        )
    reconcile_lines(conn, [invoice_line_id, payment_line_id])
    return 0  # Reconciliation doesn't create a new record


class OdooApprovalHandler(FileSystemEventHandler):
    """Watchdog handler for vault/Approved/odoo/ — processes approved proposal files."""

    def __init__(self, conn: OdooConnection, config: OdooConfig) -> None:
        super().__init__()
        self.conn = conn
        self.config = config

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md":
            return
        self._process(path)

    def _process(self, path: Path) -> None:
        """Read proposal and execute the Odoo action with Ralph Wiggum Loop."""
        logger.info("Processing approved proposal: %s", path.name)

        fm = _read_proposal(path)
        if fm is None:
            _log(
                self.config, "odoo_executor_failure",
                path, self.config.vault_path / "Needs_Action" / "odoo",
                "failure", f"could not parse proposal: {path.name}",
            )
            move_to_needs_action(path, "unparseable proposal", self.config.vault_path)
            return

        action_type = fm.get("action_type", "")
        odoo_payload_raw = fm.get("odoo_payload", "{}")
        partner_name = fm.get("odoo_partner", "unknown")

        try:
            payload: dict[str, Any] = (
                json.loads(odoo_payload_raw)
                if isinstance(odoo_payload_raw, str)
                else odoo_payload_raw
            )
        except (json.JSONDecodeError, TypeError) as exc:
            _log(
                self.config, "odoo_executor_failure",
                path, self.config.vault_path / "Needs_Action" / "odoo",
                "failure", f"invalid odoo_payload JSON: {exc}",
            )
            move_to_needs_action(path, f"invalid payload: {exc}", self.config.vault_path)
            return

        # Ralph Wiggum Loop: up to MAX_RETRIES attempts
        last_exc: Exception | None = None
        odoo_id: int = -1

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if action_type == "create_invoice":
                    odoo_id = _execute_invoice(self.conn, payload)
                elif action_type == "prepare_payment":
                    odoo_id = _execute_payment(self.conn, payload)
                elif action_type == "reconcile_payment":
                    odoo_id = _execute_reconciliation(self.conn, payload)
                else:
                    raise OdooConnectionError(f"Unknown action_type: '{action_type}'")

                # Success path
                accounting_path = write_accounting_record(
                    odoo_id=odoo_id,
                    proposal_path=path,
                    action_type=action_type,
                    partner_name=partner_name,
                    vault_path=self.config.vault_path,
                )
                done_path = move_to_done(path, self.config.vault_path)
                _log(
                    self.config, "odoo_executor_success",
                    path, done_path,
                    "success",
                    f"action={action_type} partner='{partner_name}' odoo_id={odoo_id} "
                    f"accounting={accounting_path.name}",
                )
                logger.info(
                    "Executed %s → odoo_id=%s (attempt %s)", action_type, odoo_id, attempt
                )
                return

            except OdooConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "Attempt %s/%s failed for %s: %s",
                    attempt, MAX_RETRIES, path.name, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)  # brief back-off: 2s, 4s

        # Exhausted all retries
        na_path = move_to_needs_action(
            path, f"exhausted {MAX_RETRIES} retries: {last_exc}", self.config.vault_path
        )
        _log(
            self.config, "odoo_executor_failure",
            path, na_path,
            "failure",
            f"action={action_type} partner='{partner_name}' exhausted {MAX_RETRIES} attempts: {last_exc}",
        )
        logger.error(
            "Failed to execute %s after %s attempts: %s",
            path.name, MAX_RETRIES, last_exc,
        )


def run_executor(config: OdooConfig, conn: OdooConnection) -> None:
    """Start the executor: ensure dirs, startup scan, then watch Approved/odoo/.

    Blocks until KeyboardInterrupt or SIGTERM.
    """
    ensure_vault_dirs(config.vault_path)

    approved_dir = config.vault_path / "Approved" / "odoo"
    approved_dir.mkdir(parents=True, exist_ok=True)

    handler = OdooApprovalHandler(conn=conn, config=config)

    # Startup scan: process any files that arrived before the Observer starts
    existing = list(approved_dir.glob("*.md"))
    if existing:
        logger.info("Startup scan: found %d pre-existing approved file(s)", len(existing))
        for path in existing:
            handler._process(path)

    observer = Observer()
    observer.schedule(handler, str(approved_dir), recursive=False)
    observer.start()
    logger.info("Executor watching: %s", approved_dir)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Executor stopping…")
    finally:
        observer.stop()
        observer.join()


def main() -> None:
    """CLI entrypoint: load config, connect, run executor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s odoo-executor: %(message)s",
        stream=sys.stderr,
    )

    try:
        config = load_odoo_config()
    except OdooConfigError as exc:
        logging.error("Configuration error: %s", exc)
        sys.exit(1)

    try:
        conn = connect(config.url, config.db, config.user, config.api_key)
        logging.info("Connected to Odoo uid=%s", conn.uid)
    except OdooConnectionError as exc:
        logging.error("Odoo connection failed: %s", exc)
        sys.exit(1)

    run_executor(config, conn)


if __name__ == "__main__":
    main()
