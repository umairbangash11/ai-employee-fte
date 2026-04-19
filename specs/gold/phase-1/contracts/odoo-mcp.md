# MCP Contract: Odoo Accounting Integration

**Domain**: `odoo`
**Feature**: `012-odoo-accounting`
**Phase**: Gold Phase 2 — implemented and finalized
**Server**: `src/odoo_mcp/server.py`
**Status**: ✅ Implemented — authoritative for Phase 2 (FR-014 close gate)
**Updated**: 2026-04-15

---

## Overview

The Odoo MCP server exposes six tools over stdio. Three are read-only (no
approval gate). Three are write tools — EXECUTOR-ONLY — that MUST only be
called by `executor.py` after detecting an authorized file in
`vault/Approved/odoo/`. They MUST NOT be invoked directly by Claude Code or
any external agent.

All tools log to `vault/Logs/` via `sentinel.logger.write_log_entry` with
all 6 required fields.

---

## Read Tools (No Approval Gate)

### `odoo_get_invoices`

Retrieve invoices from Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_invoices` |
| **Requires approval** | No |

**Input**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `state` | `string` | No | `"open"` | `"open"` (posted, unpaid), `"draft"`, or `"all"` |
| `limit` | `int` | No | `50` | Max records to return |

**Output**:

```json
{
  "records": [
    {"id": 42, "partner_name": "Acme Corp", "amount_total": 1500.00, "currency": "USD",
     "state": "posted", "payment_state": "not_paid", "invoice_date": "2026-04-10"}
  ],
  "count": 1,
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error**: `{"error": "<message>", "records": []}` — logs `outcome: failure`.

---

### `odoo_get_partners`

Look up partner (customer/vendor) records.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_partners` |
| **Requires approval** | No |

**Input**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `string` | No | `""` | Name search string (empty = first 20 partners) |
| `limit` | `int` | No | `20` | Max records to return |

**Output**:

```json
{
  "records": [
    {"id": 7, "name": "Acme Corp", "email": "billing@acme.com", "credit": 0.0, "debit": 1500.0}
  ],
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error**: `{"error": "<message>", "records": []}`.

---

### `odoo_get_unreconciled`

Retrieve unreconciled account move lines.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_unreconciled` |
| **Requires approval** | No |

**Input**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | `int` | No | `50` | Max unreconciled lines to return |

**Output**:

```json
{
  "records": [
    {"id": 201, "partner_name": "Acme Corp", "account": "110100",
     "balance": 1500.0, "date": "2026-04-01", "move_name": "INV/2026/00042"}
  ],
  "count": 1,
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error**: `{"error": "<message>", "records": []}`.

---

## Write Tools (Post-Approval — Executor Only)

> ⚠️ These tools MUST only be called by `odoo_accounting/executor.py` after
> detecting an authorized file in `vault/Approved/odoo/`. They MUST NOT be
> invoked directly by any external agent or Claude Code session.

---

### `odoo_create_invoice_draft`

Create a draft invoice record in Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_create_invoice_draft` |
| **Requires approval** | Yes — executor only |
| **Approval gate** | File moved to `vault/Approved/odoo/` by human operator |
| **Odoo model** | `account.move` (move_type: out_invoice, state: draft) |

**Input**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `partner_id` | `int` | Yes | Odoo partner record ID |
| `lines` | `string` | Yes | JSON array: `[{"name":"...","quantity":1,"price_unit":100.0}]` |
| `currency_code` | `string` | No | ISO currency code (default: Odoo company currency) |
| `ref` | `string` | No | Internal reference / note |

**Output**:

```json
{"odoo_id": 99, "state": "draft", "created_at": "2026-04-15T10:05:00Z"}
```

**Errors**:

| Condition | Response |
|-----------|----------|
| Invalid lines JSON | `{"error": "invalid lines format: ..."}` |
| Odoo API failure | `{"error": "<api error>"}` — executor retries (Ralph Wiggum Loop) |

---

### `odoo_create_payment_draft`

Create a draft payment record in Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_create_payment_draft` |
| **Requires approval** | Yes — executor only |
| **Odoo model** | `account.payment` |

**Input**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `partner_id` | `int` | Yes | Odoo partner record ID |
| `amount` | `float` | Yes | Payment amount (positive) |
| `payment_type` | `string` | No | `"outbound"` (default) or `"inbound"` |
| `ref` | `string` | No | Invoice reference or memo |

**Output**:

```json
{"odoo_id": 55, "state": "draft", "created_at": "2026-04-15T10:06:00Z"}
```

**Errors**: Same pattern as `odoo_create_invoice_draft`.

---

### `odoo_reconcile_payment`

Apply reconciliation between an invoice move line and a payment move line.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_reconcile_payment` |
| **Requires approval** | Yes — executor only |
| **Odoo model** | `account.move.line` (reconcile method) |

**Input**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_line_id` | `int` | Yes | `account.move.line` ID for the invoice line |
| `payment_line_id` | `int` | Yes | `account.move.line` ID for the payment line |

**Output**:

```json
{
  "reconciled": true,
  "invoice_line_id": 201,
  "payment_line_id": 303,
  "reconciled_at": "2026-04-15T10:07:00Z"
}
```

**Errors**:

| Condition | Response |
|-----------|----------|
| Missing line ID in payload | `{"error": "reconcile_payment requires both invoice_line_id and payment_line_id"}` |
| Odoo API failure | `{"error": "<api error>"}` — executor retries |

---

## Approval Gate Flow

```
vault/Pending_Approval/odoo/<slug>.md   [status: awaiting_approval]
        │
        │  HUMAN OPERATOR moves file manually
        ▼
vault/Approved/odoo/<slug>.md
        │
        │  executor.py OdooApprovalHandler.on_created()
        │  Ralph Wiggum Loop (3 attempts)
        │
        ├── success
        │   ├── write vault/Accounting/<slug>.md  [type: accounting_record]
        │   ├── move → vault/Done/odoo/<slug>.md
        │   └── vault/Logs/ entry [outcome: success]
        │
        └── failure (after 3 attempts)
            ├── move → vault/Needs_Action/odoo/<slug>.md
            └── vault/Logs/ entry [outcome: failure]
```

---

## Logging (All Tools)

Every tool call produces a `vault/Logs/` entry via `sentinel.logger.write_log_entry`:

| Field | Value |
|-------|-------|
| `timestamp` | ISO 8601 UTC |
| `action_type` | tool name (e.g. `odoo_create_invoice_draft`) |
| `source_path` | Odoo URL (reads) or source vault path (writes) |
| `dest_path` | Odoo model name or destination vault path |
| `outcome` | `success` \| `failure` |
| `details` | tool name, Odoo record ID or error, partner name |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ODOO_URL` | ✅ | Odoo instance base URL |
| `ODOO_DB` | ✅ | Odoo database name |
| `ODOO_USER` | ✅ | Odoo login username |
| `ODOO_API_KEY` | ✅ | Odoo API key (used as password in XML-RPC) |
| `VAULT_PATH` | ✅ | Local vault root directory |
| `ODOO_RECONCILE_BATCH` | optional | Max reconciliation proposals per scan (default: 20) |

---

## Implementation Notes

- **Protocol**: stdlib `xmlrpc.client` — zero new dependencies
- **Minimum Odoo version**: Community 14+ (`account.move` model required)
- **Server entrypoint**: `python -m odoo_mcp` or `odoo-mcp` (CLI)
- **Executor entrypoint**: `python -m odoo_accounting.executor` or `odoo-executor` (CLI)
- **Detailed tool contracts**: `specs/012-odoo-accounting/contracts/odoo-tools.md`
