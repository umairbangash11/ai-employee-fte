"""
odoo_mcp.client — Odoo XML-RPC connection and low-level operations.

Uses stdlib xmlrpc.client — zero new dependencies.

Supported Odoo versions: Community 14+ (account.move model required).
"""

from __future__ import annotations

import xmlrpc.client
from dataclasses import dataclass, field
from typing import Any


class OdooConnectionError(Exception):
    """Raised when Odoo authentication fails or server is unreachable."""


@dataclass
class OdooReadResult:
    """Data returned from a read operation against Odoo."""

    record_type: str
    odoo_id: int | None
    records: list[dict[str, Any]]
    fetched_at: str
    error: str | None = None


@dataclass
class OdooConnection:
    """Runtime state for an active Odoo XML-RPC session."""

    url: str
    db: str
    uid: int | None
    # api_key is never logged — stored here for execute_kw calls only
    _api_key: str = field(repr=False)

    def _object_proxy(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")


def connect(url: str, db: str, user: str, api_key: str) -> OdooConnection:
    """Authenticate against Odoo and return a live OdooConnection.

    Args:
        url:      Base URL of the Odoo instance (e.g. 'https://demo.odoo.com').
        db:       Odoo database name.
        user:     Odoo login (email or username).
        api_key:  Odoo API key used as password.

    Returns:
        OdooConnection with uid populated.

    Raises:
        OdooConnectionError: if authentication fails or server is unreachable.
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, user, api_key, {})
    except Exception as exc:
        raise OdooConnectionError(
            f"Failed to connect to Odoo at {url}: {exc}"
        ) from exc

    if not uid:
        raise OdooConnectionError(
            f"Authentication failed for user '{user}' on database '{db}'. "
            "Check credentials in .env."
        )

    return OdooConnection(url=url, db=db, uid=uid, _api_key=api_key)


def read_records(
    conn: OdooConnection,
    model: str,
    domain: list[Any],
    fields: list[str],
    limit: int = 50,
) -> OdooReadResult:
    """Read records from an Odoo model using search_read.

    Args:
        conn:    Active OdooConnection.
        model:   Odoo model name (e.g. 'account.move').
        domain:  Odoo domain filter (list of tuples).
        fields:  Field names to return.
        limit:   Maximum number of records to return.

    Returns:
        OdooReadResult with records list populated on success, error set on failure.
    """
    from datetime import datetime, timezone

    fetched_at = datetime.now(timezone.utc).isoformat()

    try:
        obj = conn._object_proxy()
        records: list[dict[str, Any]] = obj.execute_kw(
            conn.db,
            conn.uid,
            conn._api_key,
            model,
            "search_read",
            [domain],
            {"fields": fields, "limit": limit},
        )
        return OdooReadResult(
            record_type=model,
            odoo_id=None,
            records=records,
            fetched_at=fetched_at,
        )
    except Exception as exc:
        return OdooReadResult(
            record_type=model,
            odoo_id=None,
            records=[],
            fetched_at=fetched_at,
            error=str(exc),
        )


def create_record(
    conn: OdooConnection,
    model: str,
    values: dict[str, Any],
) -> int:
    """Create a record in Odoo and return the new record ID.

    IMPORTANT: This function MUST only be called from the executor after an
    authorized file is detected in vault/Approved/odoo/. It MUST NOT be called
    directly from any drafter, MCP server handler, or external agent.

    Args:
        conn:    Active OdooConnection.
        model:   Odoo model name (e.g. 'account.move').
        values:  Field values for the new record.

    Returns:
        Odoo record ID (int) of the created record.

    Raises:
        OdooConnectionError: if the create call fails.
    """
    try:
        obj = conn._object_proxy()
        record_id: int = obj.execute_kw(
            conn.db,
            conn.uid,
            conn._api_key,
            model,
            "create",
            [values],
        )
        return record_id
    except Exception as exc:
        raise OdooConnectionError(
            f"Failed to create record in model '{model}': {exc}"
        ) from exc


def reconcile_lines(
    conn: OdooConnection,
    line_ids: list[int],
) -> None:
    """Reconcile a set of account.move.line IDs in Odoo.

    IMPORTANT: Must only be called from executor post-approval.

    Args:
        conn:     Active OdooConnection.
        line_ids: List of account.move.line IDs to reconcile.

    Raises:
        OdooConnectionError: if the reconcile call fails.
    """
    try:
        obj = conn._object_proxy()
        obj.execute_kw(
            conn.db,
            conn.uid,
            conn._api_key,
            "account.move.line",
            "reconcile",
            [line_ids],
        )
    except Exception as exc:
        raise OdooConnectionError(
            f"Failed to reconcile lines {line_ids}: {exc}"
        ) from exc
