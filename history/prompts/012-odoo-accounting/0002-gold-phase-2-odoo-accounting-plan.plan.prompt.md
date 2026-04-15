---
id: "0002"
title: "Gold Phase 2 Odoo Accounting Plan"
stage: plan
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 012-odoo-accounting
branch: 012-odoo-accounting
user: Umair Ahmad
command: /sp.plan
labels: ["plan", "gold-phase-2", "odoo", "mcp", "xmlrpc", "approval-gate"]
links:
  spec: specs/012-odoo-accounting/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/012-odoo-accounting/plan.md
  - specs/012-odoo-accounting/data-model.md
  - specs/012-odoo-accounting/contracts/odoo-tools.md
tests:
  - tests/unit/odoo_accounting/test_vault_writer.py (planned in Task 12)
---

## Prompt

/sp.plan (no additional user input — plan generated from specs/012-odoo-accounting/spec.md)

## Response snapshot

Generated plan with 6 research decisions resolved, constitution check 12/12 PASS, and 15 implementation tasks across two new packages:

- `src/odoo_mcp/` — FastMCP server with 6 tools (3 read, 3 write-post-approval) using stdlib `xmlrpc.client`
- `src/odoo_accounting/` — 7 modules: config, vault_writer, invoice_drafter, payment_drafter, reconciliation, executor (watchdog on Approved/odoo/), __init__

Key decisions: XML-RPC over JSON-RPC (no new deps), `account.move` for invoices (Odoo 13+), watchdog Observer for executor trigger, startup scan for pre-existing Approved/ files, reconcile batch limit of 20.

Phase 1 artifacts: data-model.md (6 entities), contracts/odoo-tools.md (6 tools with full I/O schemas), CLAUDE.md updated with 012-odoo-accounting tech.

## Outcome

- ✅ Impact: Full implementation plan ready; 15 tasks defined; 0 new packages required; all 12 constitution principles pass
- 🧪 Tests: 1 minimal test file planned (test_vault_writer.py — 5 tests on vault write + frontmatter validation)
- 📁 Files: plan.md, data-model.md, contracts/odoo-tools.md, CLAUDE.md updated
- 🔁 Next prompts: `/sp.tasks` to generate dependency-ordered tasks.md
- 🧠 Reflection: Implementation-first focus correctly kept test scope minimal. Executor startup-scan risk (missing pre-existing files) caught and mitigated in risks section. Reconcile batch limit added as a configurable safeguard.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): constitution check 12/12 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.tasks to validate task granularity matches implementation-first intent
