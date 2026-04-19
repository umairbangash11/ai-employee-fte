---
id: "0003"
title: "Gold Phase 2 Odoo Accounting Tasks"
stage: tasks
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 012-odoo-accounting
branch: 012-odoo-accounting
user: Umair Ahmad
command: /sp.tasks
labels: ["tasks", "gold-phase-2", "odoo", "xmlrpc", "mcp", "approval-gate", "watchdog"]
links:
  spec: specs/012-odoo-accounting/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/012-odoo-accounting/tasks.md
tests:
  - tests/unit/odoo_accounting/test_vault_writer.py (planned in T009)
---

## Prompt

/sp.tasks (no additional user input — tasks generated from specs/012-odoo-accounting/plan.md and spec.md)

## Response snapshot

Generated `specs/012-odoo-accounting/tasks.md` with 14 tasks across 8 phases, mapping all 15 plan tasks to 5 spec user stories:

- **Phase 1 (Setup, T001–T003)**: Package scaffolding for `src/odoo_mcp/`, `src/odoo_accounting/`, `tests/unit/odoo_accounting/`; pyproject.toml entry points; .env_example Odoo vars
- **Phase 2 (Foundational, T004–T005)**: `config.py` (OdooConfig + load_odoo_config) and `client.py` (OdooConnection, connect, read_records, create_record via xmlrpc.client)
- **Phase 3 (US1 P1, T006–T007)**: `server.py` (FastMCP 6 tools, 3 read + 3 write-post-approval) and `__main__.py` entrypoint
- **Phase 4 (US2 P1, T008–T010)**: `vault_writer.py` (central write point with path guard), `test_vault_writer.py` (5 tests), `invoice_drafter.py`
- **Phase 5 (US3 P2, T011)**: `payment_drafter.py`
- **Phase 6 (US4 P2, T012)**: `reconciliation.py` (scan + batch limit)
- **Phase 7 (US5 P3, T013)**: `executor.py` (watchdog Observer + startup scan + Ralph Wiggum Loop)
- **Phase 8 (Polish, T014)**: Update `specs/gold/phase-1/contracts/odoo-mcp.md` (FR-014 close gate)

Parallel opportunities identified: T002/T003 (Phase 1), T009/T010 (Phase 4 after vault_writer), T011/T012 (Phase 5+6 in parallel).

MVP scope: Phases 1–4 (US1 + US2) deliver a complete read + invoice-draft cycle independently testable.

## Outcome

- ✅ Impact: 14 tasks defined; 8 phases; 5 user stories covered; parallel execution identified; MVP scope (US1+US2) isolated; FR-014 close gate tracked as T014
- 🧪 Tests: 1 test file planned (test_vault_writer.py — 5 tests on vault write + frontmatter validation, per T009)
- 📁 Files: specs/012-odoo-accounting/tasks.md
- 🔁 Next prompts: `/sp.implement` to execute all 14 tasks
- 🧠 Reflection: Implementation-first focus correctly maintained — only 1 test file, no TDD overhead. Executor startup scan (Risk 2 from plan) correctly surfaced in T013 description. FR-014 contract update correctly positioned as Phase 8 (Polish) close gate rather than mixed in with implementation. T009 and T010 correctly marked parallelizable within Phase 4 (different files, both depend on T008 vault_writer).

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): format validation — all 14 tasks follow checklist format (checkbox + ID + optional [P] + optional [US?] + description with file path)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.implement to validate task granularity matches implementation-first intent
