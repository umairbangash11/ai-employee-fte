# MCP Contract: Odoo Integration (Stub)

**Domain**: `odoo`
**Phase**: Gold Phase 2 (stub — tools TBD)
**Status**: Planned — not yet implemented
**Requires approval**: Yes (all Odoo writes are external actions)

---

## Overview

The Odoo MCP server will provide tools for interacting with the Odoo ERP system
(accounting, invoicing, CRM). All tools that create or modify Odoo records are
**external actions** and MUST require human approval via the
`Pending_Approval/odoo/` → `Approved/odoo/` gate before execution.

Read-only queries (fetching invoice status, customer records) do not require
approval.

---

## Planned Tools (Phase 2 scope — names and schemas TBD)

| Tool | Description | Requires Approval |
|------|-------------|-------------------|
| `odoo_get_invoice_status` | Read invoice status for a given invoice ID | No |
| `odoo_create_invoice` | Create a draft invoice in Odoo | Yes |
| `odoo_post_invoice` | Post (confirm) a draft invoice | Yes |
| `odoo_get_customer` | Look up a customer record | No |
| `odoo_create_contact` | Create a new contact in Odoo | Yes |

*Tool names and parameters will be finalized in the Gold Phase 2 spec.*

---

## Approval Gate

All write tools (approval required = Yes):

1. Orchestrator writes a proposed action to `vault/Pending_Approval/odoo/<id>.md`
   with `status: awaiting_approval` and `type: pending_action`.
2. Human reviews the proposal in `Pending_Approval/odoo/`.
3. Human moves the file to `vault/Approved/odoo/`.
4. Orchestrator detects the file in `Approved/odoo/`, executes the Odoo action,
   and logs the result to `vault/Logs/`.

---

## Error Behavior

| Condition | Response |
|-----------|----------|
| Odoo API unreachable | Log failure; follow Ralph Wiggum retry (3 attempts); route to `Needs_Action/` |
| Authentication failure | Log error with `outcome: failure`; alert human via `Needs_Action/` |
| Invalid input | Reject before write; log validation error |
| Approval gate bypassed | Reject; log boundary violation |

---

## Notes

- Odoo credentials will be stored in `.env` (never in code).
- Connection details: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`.
- Phase 2 spec will define full input/output schemas for each tool.
