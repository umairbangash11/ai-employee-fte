# Data Model: Gold Phase 2 — Odoo Accounting Integration

**Feature**: `012-odoo-accounting` | **Date**: 2026-04-15

---

## Entities

### OdooConnection

Runtime state for an active Odoo XML-RPC session.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `url` | `str` | `ODOO_URL` env | Base URL of Odoo instance |
| `db` | `str` | `ODOO_DB` env | Odoo database name |
| `uid` | `int \| None` | Returned by `authenticate()` | `None` before connection |
| `api_key` | `str` | `ODOO_API_KEY` env | Used as password for API calls; never logged |

**State transitions**: `disconnected` → (authenticate) → `connected` → (connection error) → `disconnected`

---

### OdooReadResult

Data returned from a read operation against Odoo.

| Field | Type | Description |
|-------|------|-------------|
| `record_type` | `str` | One of: `invoice`, `partner`, `payment`, `reconciliation_pair` |
| `odoo_id` | `int \| None` | Single record ID (None for list results) |
| `records` | `list[dict]` | Raw field values returned from Odoo |
| `fetched_at` | `str` | ISO 8601 timestamp |
| `error` | `str \| None` | Error message on failure; `None` on success |

---

### OdooProposalFile

Vault file written to `vault/Pending_Approval/odoo/<slug>.md`.
Represents a proposed Odoo write action awaiting human approval.

**Filename pattern**: `<YYYYMMDD-HHMMSS>-<action_type>-<partner_slug>.md`

**YAML frontmatter**:

| Field | Value |
|-------|-------|
| `type` | `pending_action` |
| `action_type` | `create_invoice` \| `prepare_payment` \| `reconcile_payment` |
| `status` | `awaiting_approval` |
| `source_path` | trigger file path (email or plan that initiated the draft) |
| `dest_path` | `Pending_Approval/odoo/<slug>.md` (this file's path) |
| `captured_at` | ISO 8601 timestamp |
| `odoo_partner` | human-readable partner name |
| `odoo_payload` | JSON-serialized action payload (partner_id, amounts, lines, refs) |

**Body**: Human-readable summary of the proposed action including partner name,
amounts, and description. Written for human review — no credentials.

---

### OdooApprovedAction

Vault file in `vault/Approved/odoo/<slug>.md`. Same schema as OdooProposalFile;
`status` field reflects approval state at time of execution.

The executor reads `action_type` and `odoo_payload` to reconstruct the Odoo
API call. The file is moved to `Done/odoo/` after successful execution.

---

### OdooAccountingRecord

Confirmation record written to `vault/Accounting/<slug>.md` after successful
execution.

**YAML frontmatter**:

| Field | Value |
|-------|-------|
| `type` | `accounting_record` |
| `action_type` | same as the executed proposal |
| `status` | `executed` |
| `odoo_id` | Odoo record ID returned by the create/reconcile call |
| `source_proposal` | relative path to the original `Pending_Approval/odoo/<slug>.md` |
| `executed_at` | ISO 8601 timestamp |
| `dest_path` | `Accounting/<slug>.md` (this file's path) |
| `outcome` | `success` |

**Body**: Confirmation summary: what was created/reconciled in Odoo,
Odoo record ID, and link back to the original proposal.

---

### OdooLogEntry

Log record written to `vault/Logs/` via `sentinel.logger.write_log_entry`.
Produced for every accounting operation (reads, draft writes, executions,
failures, retries).

| Field | Required | Description |
|-------|----------|-------------|
| `timestamp` | ✅ | ISO 8601 datetime |
| `action_type` | ✅ | e.g. `odoo_read_invoices`, `odoo_create_invoice`, `odoo_executor_success`, `odoo_executor_failure` |
| `source_path` | ✅ | Source file path or Odoo URL for reads |
| `dest_path` | ✅ | Destination vault path or Odoo model name |
| `outcome` | ✅ | `success` \| `failure` \| `partial` |
| `details` | ✅ | Human-readable description with Odoo record ID, error, or rule summary |

---

### OdooConfig

Runtime configuration loaded from `.env`.

| Field | Env Var | Required | Description |
|-------|---------|----------|-------------|
| `url` | `ODOO_URL` | ✅ | Odoo instance base URL |
| `db` | `ODOO_DB` | ✅ | Odoo database name |
| `user` | `ODOO_USER` | ✅ | Odoo login username |
| `api_key` | `ODOO_API_KEY` | ✅ | Odoo API key (used as password in XML-RPC) |
| `vault_path` | `VAULT_PATH` | ✅ | Local vault root directory |
| `reconcile_batch_limit` | `ODOO_RECONCILE_BATCH` | optional | Max proposals per reconciliation scan (default: 20) |

---

## Vault Directory Map

| Directory | Contains | Required `type` field |
|-----------|----------|-----------------------|
| `vault/Accounting/` | Executed accounting confirmations | `accounting_record` |
| `vault/Pending_Approval/odoo/` | Unapproved Odoo write proposals | `pending_action` |
| `vault/Approved/odoo/` | Human-approved Odoo write proposals | `pending_action` (executor reads them here) |
| `vault/Done/odoo/` | Executed + moved proposals | `pending_action` |
| `vault/Needs_Action/odoo/` | Failed or error proposals | any (moved from Approved/ on failure) |
| `vault/Logs/` | All operation log entries | (sentinel logger format) |

---

## State Transition: Proposal Lifecycle

```
[trigger: email / scan]
        │
        ▼
  invoice_drafter.py / payment_drafter.py / reconciliation.py
        │  write_proposal()
        ▼
vault/Pending_Approval/odoo/<slug>.md   [status: awaiting_approval]
        │
        │  HUMAN OPERATOR moves file
        ▼
vault/Approved/odoo/<slug>.md           [status: awaiting_approval → executor reads]
        │
        │  executor.py OdooApprovalHandler.on_created()
        │
        ├── success (≤3 attempts)
        │       ├── write vault/Accounting/<slug>.md  [type: accounting_record]
        │       ├── move → vault/Done/odoo/<slug>.md
        │       └── write vault/Logs/ entry [outcome: success]
        │
        └── failure (after 3 attempts)
                ├── move → vault/Needs_Action/odoo/<slug>.md
                └── write vault/Logs/ entry [outcome: failure]
```
