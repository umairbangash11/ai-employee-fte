# Tasks: Gold Phase 2 — Odoo Accounting Integration

**Feature**: `012-odoo-accounting` | **Branch**: `012-odoo-accounting` | **Date**: 2026-04-15
**Input**: `specs/012-odoo-accounting/spec.md`, `plan.md`, `data-model.md`, `contracts/odoo-tools.md`
**Prerequisites**: Gold Phase 1 complete ✅, Constitution v3.0.0 ✅, `vault_mcp/` pattern available

**Tests**: Minimal only — `test_vault_writer.py` (5 tests). Spec explicitly excludes testing-heavy scope.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: Maps to user story from spec.md (US1–US5)
- Exact file paths included in every task

---

## Phase 1: Setup (Package Scaffolding)

**Purpose**: Initialize the two new packages and CLI wiring so all subsequent modules
have importable homes. Must complete before any source code is written.

- [x] T001 Create package scaffolding: `src/odoo_mcp/__init__.py` and `src/odoo_accounting/__init__.py` (empty inits with module docstrings) and `tests/unit/odoo_accounting/__init__.py`
- [x] T002 [P] Add CLI entry points to `pyproject.toml`: `odoo-mcp = "odoo_mcp.__main__:main"` and `odoo-executor = "odoo_accounting.executor:main"`
- [x] T003 [P] Add Odoo env vars to `.env_example`: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` with placeholder values and comments (no real credentials)

**Checkpoint**: `PYTHONPATH=src python3 -c "import odoo_mcp; import odoo_accounting; print('ok')"` succeeds

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be
implemented. `config.py` provides the OdooConfig used by every module.
`client.py` provides the XML-RPC connection used by server.py and all drafters.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create `src/odoo_accounting/config.py`: `OdooConfig` dataclass (`url`, `db`, `user`, `api_key`, `vault_path`, `reconcile_batch_limit`) and `load_odoo_config() -> OdooConfig` that reads env vars via `python-dotenv` and raises `OdooConfigError` if any required var is missing
- [x] T005 Create `src/odoo_mcp/client.py`: `OdooConnection` dataclass, `OdooConnectionError(Exception)`, `connect(url, db, user, api_key) -> OdooConnection` (auth via `/xmlrpc/2/common`), `read_records(conn, model, domain, fields, limit) -> OdooReadResult`, `create_record(conn, model, values) -> int` (called only from executor post-approval)

**Checkpoint**: 
- `PYTHONPATH=src python3 -c "from odoo_accounting.config import OdooConfig; print('ok')"` passes
- `PYTHONPATH=src python3 -c "from odoo_mcp.client import connect, OdooConnectionError; print('ok')"` passes

---

## Phase 3: User Story 1 — Odoo Connection and Read Operations (Priority: P1) 🎯 MVP

**Goal**: Expose all three read operations as MCP tools (no approval gate).
A human operator can call `odoo_get_invoices`, `odoo_get_partners`,
`odoo_get_unreconciled` via the MCP server and receive structured data.
Connection failures follow the Ralph Wiggum Loop and log to `vault/Logs/`.

**Independent Test**: Configure Odoo credentials in `.env`, start the MCP server via
`python -m odoo_mcp`, call a read tool, and verify structured invoice data is returned.
No vault write required — read path is independently verifiable.

- [x] T006 [US1] Create `src/odoo_mcp/server.py`: FastMCP server with 6 Odoo tools. Read tools (`odoo_get_invoices`, `odoo_get_partners`, `odoo_get_unreconciled`) call `read_records()`. Write tools (`odoo_create_invoice_draft`, `odoo_create_payment_draft`, `odoo_reconcile_payment`) call `create_record()` — executor-only, never called externally. All tools log to `vault/Logs/` via `sentinel.logger.write_log_entry` with all 6 required fields.
- [x] T007 [US1] Create `src/odoo_mcp/__main__.py`: entrypoint `main()` that loads `OdooConfig`, calls `connect()`, and starts the FastMCP server via stdio. Handles `OdooConfigError` and `OdooConnectionError` with logged failure and clean exit.

**Checkpoint**: `PYTHONPATH=src python3 -c "from odoo_mcp.server import create_server; print('ok')"` passes

---

## Phase 4: User Story 2 — Invoice Draft Creation and Approval Gate (Priority: P1)

**Goal**: A complete draft-to-approval-to-execution cycle for invoice creation.
The `vault_writer` module becomes the central write point for all vault artifacts.
`invoice_drafter` produces a proposal in `Pending_Approval/odoo/` without touching Odoo.
The executor (built in US5) will later close the cycle — US2 delivers the draft half.

**Independent Test**: Call `draft_invoice_proposal()` with fixture data; verify the
draft appears in `vault/Pending_Approval/odoo/` with `type: pending_action`,
`action_type: create_invoice`, `status: awaiting_approval`. Verify nothing is
written to Odoo. Run `pytest tests/unit/odoo_accounting/ -v` — all 5 tests pass.

- [x] T008 [US2] Create `src/odoo_accounting/vault_writer.py`: `write_proposal(proposal_data, config) -> Path`, `write_accounting_record(odoo_id, proposal_path, config) -> Path`, `move_to_done(proposal_path, config) -> Path`, `move_to_needs_action(proposal_path, reason, config) -> Path`. All writes use `_safe_resolve()` path guard (path must be under `config.vault_path`). All parent directories created with `mkdir(parents=True, exist_ok=True)`. Duplicate slug gets counter suffix — never overwrites.
- [x] T009 [P] [US2] Write `tests/unit/odoo_accounting/test_vault_writer.py` (5 tests): `test_proposal_written_to_pending_approval`, `test_proposal_frontmatter_complete` (all required YAML fields: `type`, `action_type`, `status`, `source_path`, `dest_path`, `captured_at`, `odoo_partner`, `odoo_payload`), `test_accounting_record_written_to_accounting_dir`, `test_move_to_done`, `test_path_outside_vault_rejected`
- [x] T010 [US2] Create `src/odoo_accounting/invoice_drafter.py`: `draft_invoice_proposal(conn, partner_id, lines, config) -> Path`. Reads partner name via `read_records` (model `res.partner`), builds `OdooProposalFile` dict with `action_type: create_invoice`, calls `vault_writer.write_proposal()`, calls `sentinel.logger.write_log_entry()` with 6 fields. Returns path to written proposal.

**Checkpoint**: `PYTHONPATH=src pytest tests/unit/odoo_accounting/ -v` — all 5 tests pass

---

## Phase 5: User Story 3 — Payment Preparation Draft and Approval Gate (Priority: P2)

**Goal**: Apply the same draft-gate pattern from US2 to outbound payment flows.
`payment_drafter` produces a payment proposal in `Pending_Approval/odoo/` with
`action_type: prepare_payment`. Nothing registers in Odoo without approval.

**Independent Test**: Call `draft_payment_proposal()` with a fixture vendor and amount;
verify the draft appears in `vault/Pending_Approval/odoo/` with `action_type:
prepare_payment`. Verify nothing is registered in Odoo.

- [x] T011 [US3] Create `src/odoo_accounting/payment_drafter.py`: `draft_payment_proposal(conn, partner_id, amount, invoice_ref, config) -> Path`. Reads partner name via `read_records`, builds `OdooProposalFile` with `action_type: prepare_payment`, calls `vault_writer.write_proposal()`, logs to `vault/Logs/`. Returns path to written proposal.

**Checkpoint**: `PYTHONPATH=src python3 -c "from odoo_accounting.payment_drafter import draft_payment_proposal; print('ok')"` passes

---

## Phase 6: User Story 4 — Reconciliation Draft Actions (Priority: P2)

**Goal**: Detect unreconciled invoice-payment pairs in Odoo and generate one
reconciliation proposal per pair. Handles the empty-result case with a summary log.
Configurable batch limit (default: 20) guards against large reconciliation queues.

**Independent Test**: Call `scan_and_draft_reconciliation()` on a test Odoo instance
with known unreconciled items; verify a reconciliation proposal appears in
`vault/Pending_Approval/odoo/` with `action_type: reconcile_payment` per pair.
Call with no unreconciled items; verify a summary log entry is written with
`outcome: success, details: no items to reconcile`.

- [x] T012 [US4] Create `src/odoo_accounting/reconciliation.py`: `scan_and_draft_reconciliation(conn, config) -> list[Path]`. Calls `read_records` on model `account.move.line` with domain `[('reconciled','=',False),('account_id.reconcile','=',True),('balance','!=',0)]`. For each pair (up to `config.reconcile_batch_limit`): builds `OdooProposalFile` with `action_type: reconcile_payment`, calls `vault_writer.write_proposal()`. If no pairs: writes summary log entry (`outcome: success`, `details: no items to reconcile`). Returns list of proposal paths written.

**Checkpoint**: `PYTHONPATH=src python3 -c "from odoo_accounting.reconciliation import scan_and_draft_reconciliation; print('ok')"` passes

---

## Phase 7: User Story 5 — Accounting Vault Lifecycle and Executor (Priority: P3)

**Goal**: Close the approval loop. The executor watches `vault/Approved/odoo/` via
a watchdog Observer. On detection of an `.md` file, it reads the proposal, calls the
appropriate MCP write tool (via `odoo_mcp.client.create_record`), applies the
Ralph Wiggum Loop (3 attempts), writes accounting confirmation to `vault/Accounting/`,
moves the source file to `Done/odoo/` on success or `Needs_Action/odoo/` after
exhaustion. Executor performs a startup scan for pre-existing `Approved/` files
before starting the Observer (mitigates missed-event race).

**Independent Test**: Place a fixture proposal file in `vault/Approved/odoo/`. Start the
executor. Verify: `vault/Accounting/<slug>.md` is created with `type: accounting_record`,
the source file moves to `vault/Done/odoo/`, and a `vault/Logs/` entry is written with
`outcome: success`. Test failure path: place a broken proposal and verify it routes to
`vault/Needs_Action/odoo/` after 3 retries with `outcome: failure` log entry.

- [x] T013 [US5] Create `src/odoo_accounting/executor.py`: `OdooApprovalHandler(FileSystemEventHandler)` with `on_created(event)` that reads the proposal (`action_type`, `odoo_payload`), routes to `_execute_invoice` / `_execute_payment` / `_execute_reconciliation`, applies Ralph Wiggum Loop (up to 3 attempts), calls `vault_writer.write_accounting_record` + `move_to_done` + log on success, or `move_to_needs_action` + log (outcome: failure) on exhaustion. `run_executor(config)` creates `vault/Approved/odoo/` and all required subdirs, runs startup scan for pre-existing `.md` files in `Approved/odoo/`, registers Observer, runs until interrupted. `main()` entrypoint: loads `OdooConfig`, calls `run_executor(config)`.

**Checkpoint**: `PYTHONPATH=src python3 -c "from odoo_accounting.executor import OdooApprovalHandler, run_executor; print('ok')"` passes

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Phase 2 close gate (FR-014) — update the Odoo MCP contract stub
written during Phase 1 with finalized tool names, schemas, and approval gate
documentation. Done last, after implementation is validated.

- [x] T014 Update `specs/gold/phase-1/contracts/odoo-mcp.md`: replace stub content with finalized tool names, input/output schemas, and approval gate documentation from `specs/012-odoo-accounting/contracts/odoo-tools.md`. Add note that write tools are executor-only post-approval (FR-014 close gate).

**Checkpoint**: `specs/gold/phase-1/contracts/odoo-mcp.md` no longer contains stub placeholder content; all 6 tools documented with full I/O schemas.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup         → no dependencies; start immediately
Phase 2: Foundational  → depends on Phase 1 (T001 package dirs must exist)
Phase 3: US1           → depends on Phase 2 (T005 client.py must be complete)
Phase 4: US2           → depends on Phase 2 (T004 config.py) + Phase 3 (T006 server.py for log pattern)
Phase 5: US3           → depends on Phase 4 (T008 vault_writer.py must be complete)
Phase 6: US4           → depends on Phase 4 (T008 vault_writer.py) and Phase 3 (T006 for read call)
Phase 7: US5           → depends on ALL phases 3–6 (executor wires everything together)
Phase 8: Polish        → depends on Phase 7 (finalize contract after implementation validated)
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|-----------|-----------------|
| US1 (P1) — Read | T005 client.py | Phase 2 complete |
| US2 (P1) — Invoice Draft | T004 config, T006 server | Phase 3 complete |
| US3 (P2) — Payment Draft | T008 vault_writer | Phase 4 complete |
| US4 (P2) — Reconciliation | T008 vault_writer, T006 server | Phase 4 complete |
| US5 (P3) — Executor | US1+US2+US3+US4 | Phase 6 complete |

### Within Each Phase

- T002 and T003 are parallelizable (different files, no mutual dependency)
- T004 and T005 are sequential (T004 must complete before T005 for import)
- T009 (test file) and T010 (invoice_drafter) are parallelizable against each other; both depend on T008 (vault_writer)

---

## Parallel Execution Examples

### Phase 1 Setup (run together)

```bash
# These 3 tasks can run in parallel:
Task T001: Create __init__.py files
Task T002: Update pyproject.toml entry points
Task T003: Update .env_example
```

### Phase 4 US2 (tests + drafter in parallel after vault_writer)

```bash
# After T008 vault_writer is complete, run in parallel:
Task T009: Write test_vault_writer.py
Task T010: Write invoice_drafter.py
```

### Phase 5 + Phase 6 (after Phase 4 complete)

```bash
# US3 and US4 can run in parallel (different files, shared vault_writer):
Task T011: Write payment_drafter.py  [US3]
Task T012: Write reconciliation.py   [US4]
```

---

## Implementation Strategy

### MVP First (US1 + US2 only)

1. Complete Phase 1: Setup (T001, T002, T003)
2. Complete Phase 2: Foundational (T004, T005)
3. Complete Phase 3: US1 — Read (T006, T007)
4. Complete Phase 4: US2 — Invoice Draft (T008, T009, T010)
5. **STOP and VALIDATE**: `pytest tests/unit/odoo_accounting/ -v` — 5 tests pass
6. Manual test: trigger invoice draft, verify file in `Pending_Approval/odoo/`

### Full Phase 2 Delivery

1. MVP (steps 1–5 above)
2. Add US3 (T011) → payment draft verified
3. Add US4 (T012) → reconciliation draft verified
4. Add US5 (T013) → executor closes the full approval loop
5. Phase 8 Polish (T014) → contract updated, FR-014 gate closed

---

## Task Summary

| Phase | Tasks | Story | Description |
|-------|-------|-------|-------------|
| Phase 1 | T001–T003 | Setup | Package scaffolding, pyproject, .env_example |
| Phase 2 | T004–T005 | Foundational | config.py, client.py (XML-RPC) |
| Phase 3 | T006–T007 | US1 (P1) | MCP server + entrypoint (read tools live) |
| Phase 4 | T008–T010 | US2 (P1) | vault_writer + tests + invoice_drafter |
| Phase 5 | T011 | US3 (P2) | payment_drafter |
| Phase 6 | T012 | US4 (P2) | reconciliation scanner |
| Phase 7 | T013 | US5 (P3) | executor (watchdog + Ralph Wiggum Loop) |
| Phase 8 | T014 | Polish | odoo-mcp.md contract update (FR-014) |

**Total**: 14 tasks | **New source files**: 9 | **Test files**: 1 | **Updated files**: 2

---

## Notes

- `[P]` = parallelizable; different files with no dependency on an incomplete task in the same phase
- `[US?]` label maps each task to its user story for traceability
- Tests are minimal by spec intent: only `test_vault_writer.py` (5 tests on write + frontmatter)
- All Odoo writes go through `vault_writer.py` — single write point, single place to audit
- The executor (`T013`) is the only code that moves files from `Approved/` → `Done/` or `Needs_Action/`
- No self-approval path exists anywhere — the `Pending_Approval/ → Approved/` transition is human-only
- Commit after each phase checkpoint; don't batch multiple phases before committing
