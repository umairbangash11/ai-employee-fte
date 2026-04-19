# Implementation Plan: Gold Phase 2 — Odoo Accounting Integration

**Branch**: `012-odoo-accounting` | **Date**: 2026-04-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/012-odoo-accounting/spec.md`

## Summary

Build the Odoo accounting integration code foundation: a connection + read
layer, three draft-action modules (invoice, payment, reconciliation), an
approval-gate executor, and a vault writer — all wired together through an
Odoo MCP server. Every Odoo write is approval-gated via
`vault/Pending_Approval/odoo/` → `vault/Approved/odoo/`. No new external
packages are required; the implementation uses Python stdlib `xmlrpc.client`
for the Odoo connection and the already-installed `mcp>=1.0`, `watchdog`,
`pyyaml`, and `python-dotenv`.

---

## Technical Context

**Language/Version**: Python 3.12 (project standard)
**Primary Dependencies**: `xmlrpc.client` (stdlib — Odoo XML-RPC API),
`mcp>=1.0` (already installed), `watchdog>=6.0` (already installed),
`pyyaml>=6.0` (already installed), `python-dotenv>=1.0` (already installed)
**New packages required**: None
**Storage**: Local filesystem — `vault/` directory tree; Odoo Community instance
**Testing**: pytest (already installed); minimal validation only per spec intent
**Target Platform**: Linux (WSL2) — same as existing system
**Performance Goals**: Read operations complete in under 3 seconds on a
local network Odoo instance; executor cycle completes in under 10 seconds
per approved action
**Constraints**: All Odoo writes are approval-gated — no direct write path
permitted; credentials in `.env` only; no new SpecifyPlus modifications
**Scale/Scope**: Single Odoo instance, single vault; accounting module handles
hundreds of invoices/payments

---

## Constitution Check

*Gate: Must pass before Phase 0. All 12 principles evaluated.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | ✅ PASS | All processing local; Odoo API is an authorized external action, not a core dependency |
| II. Canonical Folder Structure | ✅ PASS | Uses `Accounting/`, `Pending_Approval/odoo/`, `Approved/odoo/`, `Done/odoo/`, `Needs_Action/odoo/`, `Logs/` — all canonical |
| III. Tiered Scope | ✅ PASS | Gold Phase 2 only; Phase 1 confirmed complete 2026-04-15 |
| IV. Safety-First Execution | ✅ PASS | All Odoo writes preceded by proposal in `Pending_Approval/`; no direct write path in any module |
| V. Ralph Wiggum Loop | ✅ PASS | Executor retries 3× on Odoo API failure before routing to `Needs_Action/odoo/` |
| VI. HITL and Approval Gates | ✅ PASS | Human-only transition from `Pending_Approval/` to `Approved/`; no self-approval in any code path |
| VII. Credential and Secrets Isolation | ✅ PASS | `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` in `.env` only; never in vault files |
| VIII. Agent Skills and MCP Orchestration | ✅ PASS | All Odoo operations exposed via `odoo_mcp/server.py`; no ad-hoc direct API calls in drafter/executor |
| IX. Audit Logging | ✅ PASS | Every operation writes a 6-field log entry to `vault/Logs/` via `sentinel.logger` |
| X. Graceful Degradation | ✅ PASS | Missing Odoo credentials → skip cycle + log, no orchestrator crash; Odoo unreachable → Ralph Wiggum Loop |
| XI. Gold-Tier Phased Development | ✅ PASS | Phase 2 only; Phase 1 explicitly closed before this spec began |
| XII. Gold Scope Boundary Enforcement | ✅ PASS | No Phase 3–5 content; no SpecifyPlus or `.claude/` modifications |

**Gate result: PASS — all 12 principles satisfied. No violations.**

---

## Phase 0: Research

### Findings

**Decision 1: Odoo connection protocol**
- **Chosen**: Python stdlib `xmlrpc.client` with Odoo's XML-RPC 2 endpoint.
  - Auth: `http://<host>/xmlrpc/2/common` — `authenticate(db, user, api_key, {})` → returns `uid`
  - Data: `http://<host>/xmlrpc/2/object` — `execute_kw(db, uid, api_key, model, method, args, kwargs)`
- **Rationale**: `xmlrpc.client` is stdlib (zero new dependencies), Odoo Community ships
  XML-RPC enabled by default, and the pattern is battle-tested. JSON-RPC is an
  alternative but requires `requests` and offers no functional advantage for this scope.
- **Alternatives considered**: `odoorpc` library (rejected — extra dependency, not in
  pyproject.toml, no advantage for read/write operations); JSON-RPC (rejected — requires
  `requests` package)

**Decision 2: Odoo models and methods**
- **Invoice draft**: model `account.move`, `create` with `{move_type: out_invoice, state: draft, partner_id, invoice_line_ids}`
- **Payment draft**: model `account.payment`, `create` with `{partner_id, amount, payment_type: outbound, state: draft, ref}`
- **Reconciliation scan**: model `account.move.line`, `search_read` with domain
  `[('reconciled','=',False),('account_id.reconcile','=',True),('balance','!=',0)]`
- **Read open invoices**: model `account.move`, `search_read` with
  domain `[('move_type','=','out_invoice'),('state','=','posted'),('payment_state','!=','paid')]`
- **Read partner**: model `res.partner`, `search_read`
- **Rationale**: These are standard Odoo Community models. `account.move` is the
  unified invoice/bill model introduced in Odoo 13+. All Odoo Community versions
  from v13 onward are covered.

**Decision 3: Executor trigger mechanism**
- **Chosen**: Reuse the existing `watchdog` Observer pattern (already in project
  for `sentinel/watcher.py`). The executor registers a `FileSystemEventHandler`
  on `vault/Approved/odoo/` and processes `.md` files on creation events.
- **Rationale**: Matches the project's established event-driven pattern. No polling
  delays; events are near-instantaneous on local filesystem. No new mechanism needed.
- **Alternatives considered**: Polling loop (rejected — introduces latency, wastes CPU);
  inotify directly (rejected — Linux-only, over-engineering for local scope)

**Decision 4: Module layout — two packages**
- **Chosen**: Two new packages:
  - `src/odoo_mcp/` — MCP server exposing Odoo tools (follows `vault_mcp/` pattern)
  - `src/odoo_accounting/` — accounting action modules (drafters, executor, vault writer)
- **Rationale**: Separation of concerns matches existing project structure. The MCP
  server is the external-boundary layer; the accounting modules are the business logic.
  Keeping them separate makes each independently testable and replaceable.
- **Alternatives considered**: Single `src/odoo/` package (rejected — conflates MCP
  boundary with business logic; harder to test the MCP layer independently)

**Decision 5: Proposal file slug generation**
- **Chosen**: `<YYYYMMDD-HHMMSS>-<action_type>-<partner_slug>.md` format, consistent
  with existing vault file naming conventions (see `sentinel/logger.py`).
- **Rationale**: Matches existing file naming patterns; lexicographically sortable;
  human-readable in vault directory listing.

**Decision 6: MCP contract update**
- **Chosen**: Update `specs/gold/phase-1/contracts/odoo-mcp.md` at Phase 2 close
  (FR-014). Final tool names and schemas are defined in this plan and finalized
  after implementation.
- **Rationale**: FR-014 requires the contract be updated with finalized schemas.
  Doing it as a Phase 2 close gate prevents contract drift.

**Output**: All 6 decisions resolved. No NEEDS CLARIFICATION items remain.

---

## Phase 1: Design & Contracts

### Data Model

See [`data-model.md`](./data-model.md).

**OdooConnection**:

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | Odoo instance URL (from `ODOO_URL` env) |
| `db` | `str` | Odoo database name (from `ODOO_DB` env) |
| `uid` | `int` \| `None` | Authenticated user ID (populated after `authenticate()`) |
| `api_key` | `str` | API key (from `ODOO_API_KEY` env — never logged) |

**OdooReadResult**:

| Field | Type | Description |
|-------|------|-------------|
| `record_type` | `str` | One of: `invoice`, `partner`, `payment`, `reconciliation_pair` |
| `odoo_id` | `int` \| `None` | Odoo record ID (None for lists) |
| `records` | `list[dict]` | Raw field data returned from Odoo |
| `fetched_at` | `str` | ISO 8601 timestamp |
| `error` | `str` \| `None` | Error message if read failed; `None` on success |

**OdooProposalFile** (written to `Pending_Approval/odoo/<slug>.md`):

| YAML field | Value |
|------------|-------|
| `type` | `pending_action` |
| `action_type` | `create_invoice` \| `prepare_payment` \| `reconcile_payment` |
| `status` | `awaiting_approval` |
| `source_path` | trigger file path that initiated the draft |
| `dest_path` | `Pending_Approval/odoo/<slug>.md` |
| `captured_at` | ISO 8601 |
| `odoo_partner` | partner name string |
| `odoo_payload` | JSON-serialized action payload (partner_id, amounts, lines) |

**OdooApprovedAction** (read from `Approved/odoo/<slug>.md`):

Same schema as OdooProposalFile; `status` field is `approved` after human promotion.
The executor reads `odoo_payload` and `action_type` to reconstruct the Odoo call.

**OdooAccountingRecord** (written to `Accounting/<slug>.md` after execution):

| YAML field | Value |
|------------|-------|
| `type` | `accounting_record` |
| `action_type` | same as the executed proposal |
| `status` | `executed` |
| `odoo_id` | Odoo record ID returned by the API |
| `source_proposal` | path to the original `Pending_Approval/` file |
| `executed_at` | ISO 8601 |

**OdooLogEntry** (written to `Logs/` via `sentinel.logger.write_log_entry`):

| Field | Value |
|-------|-------|
| `timestamp` | ISO 8601 |
| `action_type` | e.g. `odoo_read_invoices`, `odoo_create_invoice`, `odoo_execute_approved` |
| `source_path` | source file or `ODOO_URL` for reads |
| `dest_path` | destination vault path or Odoo model |
| `outcome` | `success` \| `failure` \| `partial` |
| `details` | human-readable description including Odoo record ID or error |

### Integration Points Diagram

```
Gmail / Email Triage
     │
     │ email triggers "create invoice" action
     │
     ▼
OdooAccountingOrchestrator (executor.py)
     │
     ├── reads from: odoo_mcp.server (via MCP tools)
     │       │
     │       ├── odoo_get_invoices()
     │       ├── odoo_get_partners()
     │       └── odoo_get_unreconciled()
     │           ↓
     │       odoo_mcp.client (xmlrpc.client)
     │           ↓
     │       Odoo Community instance
     │
     ├── writes to:
     │   invoice_drafter.py → vault/Pending_Approval/odoo/<slug>.md
     │   payment_drafter.py → vault/Pending_Approval/odoo/<slug>.md
     │   reconciliation.py  → vault/Pending_Approval/odoo/<slug>.md
     │
     │
HUMAN OPERATOR (vault/Pending_Approval/odoo/)
     │  moves file to vault/Approved/odoo/
     ▼
executor.py (watchdog on vault/Approved/odoo/)
     │
     ├── reads proposal from Approved/odoo/<slug>.md
     ├── calls odoo_mcp.server write tools:
     │       ├── odoo_create_invoice_draft()
     │       ├── odoo_create_payment_draft()
     │       └── odoo_reconcile_payment()
     │           ↓
     │       odoo_mcp.client → Odoo Community
     │
     ├── on success:
     │   vault_writer.py → vault/Accounting/<slug>.md (confirmation)
     │   shutil.move     → vault/Done/odoo/<slug>.md
     │   logger.write_log_entry → vault/Logs/
     │
     └── on failure (after 3 retries):
         shutil.move     → vault/Needs_Action/odoo/<slug>.md
         logger.write_log_entry → vault/Logs/ (outcome: failure)
```

### Module Breakdown

**Module 1 — `src/odoo_mcp/client.py`** (NEW)

Responsibility: Establish and maintain the Odoo XML-RPC connection; expose
low-level read and write methods.

```
connect(url, db, user, api_key) -> OdooConnection
    - authenticates via /xmlrpc/2/common
    - returns OdooConnection with uid populated
    - raises OdooConnectionError on failure

read_records(conn, model, domain, fields) -> OdooReadResult
    - calls execute_kw(search_read)
    - returns OdooReadResult

create_record(conn, model, values) -> int
    - calls execute_kw(create)
    - returns new Odoo record ID
    - ONLY called from executor after approval

OdooConnectionError(Exception)  — raised when auth fails or server unreachable
```

**Module 2 — `src/odoo_mcp/server.py`** (NEW)

Responsibility: FastMCP server exposing 6 Odoo tools. Read tools have no
approval gate. Write tools are called ONLY from the executor after approval.

| Tool | Type | Description |
|------|------|-------------|
| `odoo_get_invoices` | Read | List open/posted invoices |
| `odoo_get_partners` | Read | List partner records by query |
| `odoo_get_unreconciled` | Read | List unreconciled invoice-payment pairs |
| `odoo_create_invoice_draft` | Write (post-approval only) | Create draft invoice in Odoo |
| `odoo_create_payment_draft` | Write (post-approval only) | Create draft payment in Odoo |
| `odoo_reconcile_payment` | Write (post-approval only) | Apply invoice-payment reconciliation |

**Module 3 — `src/odoo_accounting/config.py`** (NEW)

Responsibility: Load and validate Odoo configuration from `.env`.

```
OdooConfig dataclass:
    url: str          # ODOO_URL
    db: str           # ODOO_DB
    user: str         # ODOO_USER
    api_key: str      # ODOO_API_KEY
    vault_path: Path  # VAULT_PATH

load_odoo_config() -> OdooConfig
    - reads env vars via python-dotenv
    - raises OdooConfigError if any required var is missing
```

**Module 4 — `src/odoo_accounting/invoice_drafter.py`** (NEW)

Responsibility: Reads open invoices from Odoo (via MCP client), builds an
invoice draft proposal, writes it to `vault/Pending_Approval/odoo/`.

```
draft_invoice_proposal(
    conn: OdooConnection,
    partner_id: int,
    lines: list[dict],   # [{product, qty, price}]
    config: OdooConfig
) -> Path
    - reads partner name from Odoo
    - builds OdooProposalFile
    - writes to vault/Pending_Approval/odoo/<slug>.md
    - logs to vault/Logs/
    - returns path to written file
```

**Module 5 — `src/odoo_accounting/payment_drafter.py`** (NEW)

Responsibility: Builds a payment preparation proposal and writes it to
`vault/Pending_Approval/odoo/`.

```
draft_payment_proposal(
    conn: OdooConnection,
    partner_id: int,
    amount: float,
    invoice_ref: str,
    config: OdooConfig
) -> Path
    - reads vendor/partner name from Odoo
    - builds OdooProposalFile with action_type: prepare_payment
    - writes to vault/Pending_Approval/odoo/<slug>.md
    - logs to vault/Logs/
    - returns path to written file
```

**Module 6 — `src/odoo_accounting/reconciliation.py`** (NEW)

Responsibility: Reads unreconciled invoice-payment pairs from Odoo; for each
pair, writes a reconciliation proposal to `vault/Pending_Approval/odoo/`.

```
scan_and_draft_reconciliation(
    conn: OdooConnection,
    config: OdooConfig
) -> list[Path]
    - reads unreconciled pairs via odoo_get_unreconciled
    - for each pair: builds OdooProposalFile with action_type: reconcile_payment
    - writes each to vault/Pending_Approval/odoo/<slug>.md
    - if no pairs: writes summary log (outcome: success, "no items to reconcile")
    - returns list of written proposal paths
```

**Module 7 — `src/odoo_accounting/vault_writer.py`** (NEW)

Responsibility: Writes accounting vault artifacts (proposal files, confirmation
records, accounting records). Central write point for all Pending_Approval/odoo/
and Accounting/ files — ensures consistent frontmatter and directory creation.

```
write_proposal(proposal_data: dict, config: OdooConfig) -> Path
    - builds YAML frontmatter + body
    - writes to vault/Pending_Approval/odoo/<slug>.md
    - ensures parent dirs exist

write_accounting_record(odoo_id: int, proposal_path: Path, config: OdooConfig) -> Path
    - writes confirmation to vault/Accounting/<slug>.md
    - type: accounting_record, status: executed

move_to_done(proposal_path: Path, config: OdooConfig) -> Path
    - moves file from vault/Approved/odoo/ to vault/Done/odoo/
    - returns new path

move_to_needs_action(proposal_path: Path, reason: str, config: OdooConfig) -> Path
    - moves file from vault/Approved/odoo/ to vault/Needs_Action/odoo/
    - returns new path
```

**Module 8 — `src/odoo_accounting/executor.py`** (NEW)

Responsibility: Watches `vault/Approved/odoo/` for new `.md` files (watchdog
Observer). On detection, reads the proposal, executes via Odoo MCP tools,
handles retries, logs, and moves files to Done/ or Needs_Action/.

```
OdooApprovalHandler(FileSystemEventHandler):
    on_created(event):
        - reads proposal file (action_type, odoo_payload)
        - routes to _execute_invoice / _execute_payment / _execute_reconciliation
        - Ralph Wiggum Loop: up to 3 attempts
        - on success: vault_writer.write_accounting_record + move_to_done + log
        - on exhausted: move_to_needs_action + log (outcome: failure)

run_executor(config: OdooConfig):
    - creates Observer, registers OdooApprovalHandler on vault/Approved/odoo/
    - also initializes required subdirs via vault_writer
    - runs until interrupted
```

**Module 9 — `src/odoo_mcp/__main__.py`** (NEW)

Entrypoint for the Odoo MCP server. Loads config, creates OdooConnection,
starts FastMCP server via stdio.

**Module 10 — `specs/gold/phase-1/contracts/odoo-mcp.md`** (UPDATE at close)

Update with finalized tool names, input/output schemas, and approval gate
documentation per FR-014. Updated after implementation is validated.

### Project Structure

```text
specs/012-odoo-accounting/
├── spec.md
├── plan.md              ← this file
├── data-model.md        ← Phase 1 output
├── contracts/           ← MCP tool contracts (see below)
│   └── odoo-tools.md
└── tasks.md             ← /sp.tasks output (not yet created)

src/
└── odoo_mcp/            ← NEW: Odoo MCP server (follows vault_mcp/ pattern)
    ├── __init__.py
    ├── __main__.py      ← CLI entrypoint: odoo-mcp
    ├── client.py        ← XML-RPC connection + read/write methods
    └── server.py        ← FastMCP server with 6 Odoo tools

src/
└── odoo_accounting/     ← NEW: accounting action modules
    ├── __init__.py
    ├── config.py        ← OdooConfig from .env
    ├── invoice_drafter.py
    ├── payment_drafter.py
    ├── reconciliation.py
    ├── vault_writer.py
    └── executor.py      ← watchdog on vault/Approved/odoo/

src/sentinel/
    └── logger.py        ← REUSE: write_log_entry (no changes)

tests/unit/
└── odoo_accounting/     ← minimal tests (import checks + vault writer)
    ├── __init__.py
    └── test_vault_writer.py   ← vault write + frontmatter validation
```

**Total diff surface**: 2 new packages (9 new source files), 1 updated contract
document, 1 new test file, 1 pyproject.toml entry point addition.

---

## Implementation Sequence

### Task 1 — Create `src/odoo_mcp/client.py`

Implement `OdooConnection` dataclass, `OdooConnectionError`, `connect()`,
`read_records()`, and `create_record()` using `xmlrpc.client`.

**Verify**: `PYTHONPATH=src python3 -c "from odoo_mcp.client import connect; print('ok')"`

### Task 2 — Create `src/odoo_mcp/server.py`

Implement FastMCP server with 6 tools. Read tools call `read_records()`.
Write tools call `create_record()` — note these are only invoked by the executor,
not by the MCP server accepting external calls without gating.

**Verify**: `PYTHONPATH=src python3 -c "from odoo_mcp.server import create_server; print('ok')"`

### Task 3 — Create `src/odoo_mcp/__init__.py` and `__main__.py`

Entrypoint loads `OdooConfig`, calls `connect()`, starts FastMCP stdio server.

### Task 4 — Create `src/odoo_accounting/config.py`

`OdooConfig` dataclass + `load_odoo_config()`. Raises `OdooConfigError` if
any of `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` is missing.

**Verify**: `PYTHONPATH=src python3 -c "from odoo_accounting.config import OdooConfig; print('ok')"`

### Task 5 — Create `src/odoo_accounting/vault_writer.py`

`write_proposal()`, `write_accounting_record()`, `move_to_done()`,
`move_to_needs_action()`. All writes go through `_safe_resolve()` (import from
`vault_mcp.server` or re-implement the identical guard). All parent directories
created with `mkdir(parents=True, exist_ok=True)`.

**Verify**: `PYTHONPATH=src pytest tests/unit/odoo_accounting/test_vault_writer.py -v`

### Task 6 — Create `src/odoo_accounting/invoice_drafter.py`

`draft_invoice_proposal()` — reads partner, builds proposal dict, calls
`vault_writer.write_proposal()`, calls `sentinel.logger.write_log_entry()`.

**Verify**: `PYTHONPATH=src python3 -c "from odoo_accounting.invoice_drafter import draft_invoice_proposal; print('ok')"`

### Task 7 — Create `src/odoo_accounting/payment_drafter.py`

`draft_payment_proposal()` — same pattern as invoice drafter.

### Task 8 — Create `src/odoo_accounting/reconciliation.py`

`scan_and_draft_reconciliation()` — reads unreconciled pairs, writes one
proposal per pair, handles empty case with summary log.

### Task 9 — Create `src/odoo_accounting/executor.py`

`OdooApprovalHandler` (watchdog `FileSystemEventHandler`) + `run_executor()`.
Ralph Wiggum Loop (3 attempts). On success: `vault_writer.write_accounting_record`
+ `move_to_done` + log. On failure: `move_to_needs_action` + log.

**Verify**: `PYTHONPATH=src python3 -c "from odoo_accounting.executor import OdooApprovalHandler; print('ok')"`

### Task 10 — Create `src/odoo_accounting/__init__.py`

Empty init with module docstring.

### Task 11 — Create `specs/012-odoo-accounting/contracts/odoo-tools.md`

MCP tool contract document for this feature's 6 tools, following the
`vault-mcp.md` contract format from Phase 1.

### Task 12 — Write `tests/unit/odoo_accounting/test_vault_writer.py`

Tests for `write_proposal()` and `write_accounting_record()`:
- `test_proposal_written_to_pending_approval`
- `test_proposal_frontmatter_complete` (all required YAML fields present)
- `test_accounting_record_written_to_accounting_dir`
- `test_move_to_done`
- `test_path_outside_vault_rejected`

**Verify**: `PYTHONPATH=src pytest tests/unit/odoo_accounting/ -v` — all pass.

### Task 13 — Update `pyproject.toml`

Add CLI entry points:
- `odoo-mcp = "odoo_mcp.__main__:main"`
- `odoo-executor = "odoo_accounting.executor:main"`

### Task 14 — Update `.env_example`

Add `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` with placeholder values
and comments. Never commit real credentials.

### Task 15 — Update `specs/gold/phase-1/contracts/odoo-mcp.md`

Replace stub content with final tool names, input/output schemas, and approval
gate documentation per FR-014. Done at Phase 2 close, after Task 12 validates
the implementation.

---

## Failure Handling

| Failure scenario | System response |
|-----------------|-----------------|
| Odoo server unreachable on read | `OdooConnectionError` raised; executor catches it; log failure + route to `Needs_Action/odoo/` after 3 retries |
| Missing credentials in `.env` | `OdooConfigError` on startup; log error; skip Odoo operations for this cycle; orchestrator continues |
| Proposal file already exists (duplicate slug) | `vault_writer` appends counter suffix; never overwrites |
| Write tool called without prior approval file | Not possible — write tools only called from `executor.py` on detection of a file in `Approved/odoo/` |
| Vault write failure after Odoo write succeeds | Odoo result logged immediately after execution; vault write failure logged separately; no Odoo rollback |
| Human promotes and rejects same file simultaneously | Executor acts on whichever triggers `on_created`; logs a conflict warning for the duplicate |

All failure paths follow Ralph Wiggum Loop (Constitution Principle V):
attempt 1 → attempt 2 (retry with adjusted context) → attempt 3 (simplify) →
route to `Needs_Action/odoo/` after exhaustion.

---

## Complexity Tracking

No constitution violations. No complexity justifications required.

---

## Risks

1. **Odoo XML-RPC version differences**: Odoo Community versions 13+ use
   `account.move` for invoices (not the older `account.invoice`). Mitigation:
   implementation targets Odoo 14+ (current Community LTS). The client module
   documents the minimum supported version.
2. **Executor misses a file written before it starts**: If a file is moved to
   `Approved/odoo/` before the executor's watchdog starts, it will not be
   processed. Mitigation: executor performs a startup scan of `Approved/odoo/`
   for existing `.md` files before starting the Observer, processing any found.
3. **Large reconciliation batches**: If hundreds of unreconciled pairs exist,
   the reconciliation scanner writes hundreds of proposal files. Mitigation:
   scanner applies a configurable batch limit (default: 20 proposals per run)
   with a summary log for remaining items.
