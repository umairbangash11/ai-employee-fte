# MCP Tool Contracts: Odoo Accounting (Phase 2)

**Domain**: `odoo`
**Feature**: `012-odoo-accounting`
**Phase**: Gold Phase 2
**Server**: `src/odoo_mcp/server.py`
**Status**: Authoritative for implementation

---

## Overview

The Odoo MCP Server exposes six tools over stdio. Three are read-only (no
approval gate). Three are write tools that MUST only be called by the executor
after detecting an authorized file in `vault/Approved/odoo/` — they are NOT
to be called directly by Claude Code or any external agent.

All tools log their operation to `vault/Logs/` via `sentinel.logger`.

---

## Read Tools (No Approval Gate)

### `odoo_get_invoices`

Retrieve open invoices from Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_invoices` |
| **Requires approval** | No |

**Input parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `state` | `string` | No | `"open"` | Filter by invoice state: `"open"` (posted, unpaid), `"draft"`, `"all"` |
| `limit` | `int` | No | `50` | Max records to return |

**Output**:

```json
{
  "records": [
    {"id": 42, "partner_name": "Acme Corp", "amount_total": 1500.00, "currency": "USD", "state": "posted", "payment_state": "not_paid", "invoice_date": "2026-04-10"},
    ...
  ],
  "count": 1,
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error behavior**: Returns `{"error": "<message>", "records": []}` on failure; logs `outcome: failure`.

---

### `odoo_get_partners`

Look up partner (customer/vendor) records.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_partners` |
| **Requires approval** | No |

**Input parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `string` | No | `""` | Name search string (empty = return first 20 partners) |
| `limit` | `int` | No | `20` | Max records to return |

**Output**:

```json
{
  "records": [
    {"id": 7, "name": "Acme Corp", "email": "billing@acme.com", "credit": 0.00, "debit": 1500.00},
    ...
  ],
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error behavior**: Returns `{"error": "<message>", "records": []}` on failure.

---

### `odoo_get_unreconciled`

Retrieve unreconciled invoice-payment line pairs.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_get_unreconciled` |
| **Requires approval** | No |

**Input parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | `int` | No | `50` | Max unreconciled lines to return |

**Output**:

```json
{
  "records": [
    {"id": 201, "partner_name": "Acme Corp", "account": "110100", "balance": 1500.00, "date": "2026-04-01", "move_name": "INV/2026/00042"},
    ...
  ],
  "count": 1,
  "fetched_at": "2026-04-15T10:00:00Z"
}
```

**Error behavior**: Returns `{"error": "<message>", "records": []}` on failure.

---

## Write Tools (Post-Approval Only)

> ⚠️ These tools MUST only be called by `odoo_accounting/executor.py` after
> detecting an authorized file in `vault/Approved/odoo/`. They MUST NOT be
> invoked directly by any external agent or Claude Code session.

---

### `odoo_create_invoice_draft`

Create a draft invoice record in Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_create_invoice_draft` |
| **Requires approval** | Yes — executor only, called post-approval |
| **Approval gate** | File moved to `vault/Approved/odoo/` by human operator |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `partner_id` | `int` | Yes | Odoo partner record ID |
| `lines` | `string` | Yes | JSON array of line items: `[{"name": "...", "quantity": 1, "price_unit": 100.0}]` |
| `currency_code` | `string` | No | ISO currency code (default: Odoo company currency) |
| `ref` | `string` | No | Internal reference / note |

**Output**:

```json
{"odoo_id": 99, "state": "draft", "name": "INV/2026/00099", "created_at": "2026-04-15T10:05:00Z"}
```

**Error behavior**:

| Condition | Response |
|-----------|----------|
| Partner not found | `{"error": "partner_id 7 not found"}` |
| Invalid line item format | `{"error": "invalid lines format: ..."}` |
| Odoo API failure | `{"error": "<api error>"}` — executor retries via Ralph Wiggum Loop |

---

### `odoo_create_payment_draft`

Create a draft payment record in Odoo.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_create_payment_draft` |
| **Requires approval** | Yes — executor only, called post-approval |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `partner_id` | `int` | Yes | Odoo partner record ID |
| `amount` | `float` | Yes | Payment amount (positive) |
| `payment_type` | `string` | No | `"outbound"` (default) or `"inbound"` |
| `ref` | `string` | No | Invoice reference or memo |

**Output**:

```json
{"odoo_id": 55, "state": "draft", "name": "BNK1/2026/00055", "created_at": "2026-04-15T10:06:00Z"}
```

**Error behavior**: Same pattern as `odoo_create_invoice_draft`.

---

### `odoo_reconcile_payment`

Apply reconciliation between an invoice move line and a payment move line.

| Field | Value |
|-------|-------|
| **Tool name** | `odoo_reconcile_payment` |
| **Requires approval** | Yes — executor only, called post-approval |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_line_id` | `int` | Yes | Odoo `account.move.line` ID for the invoice line |
| `payment_line_id` | `int` | Yes | Odoo `account.move.line` ID for the payment line |

**Output**:

```json
{"reconciled": true, "invoice_line_id": 201, "payment_line_id": 303, "reconciled_at": "2026-04-15T10:07:00Z"}
```

**Error behavior**:

| Condition | Response |
|-----------|----------|
| Lines already reconciled | `{"error": "lines already reconciled"}` |
| Account mismatch | `{"error": "account mismatch: cannot reconcile these lines"}` |
| Odoo API failure | `{"error": "<api error>"}` — executor retries |

---

## Logging (All Tools)

Every tool call produces a `vault/Logs/` entry via `sentinel.logger.write_log_entry`
with all 6 required fields:

| Field | Value |
|-------|-------|
| `timestamp` | ISO 8601 UTC |
| `action_type` | tool name (e.g. `odoo_create_invoice_draft`) |
| `source_path` | source vault proposal path or Odoo URL |
| `dest_path` | destination vault path or Odoo model |
| `outcome` | `success` \| `failure` |
| `details` | tool name, Odoo record ID returned (or error), partner name |
