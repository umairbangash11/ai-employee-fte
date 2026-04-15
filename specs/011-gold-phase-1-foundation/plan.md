# Implementation Plan: Gold Phase 1 — Cross-Domain Integration Foundation

**Branch**: `011-gold-phase-1-foundation` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/011-gold-phase-1-foundation/spec.md`

## Summary

Audit, validate, and correct the five integration boundaries required before
Gold Phase 2 work begins: (1) vault routing correctness, (2) vault state
boundary enforcement, (3) MCP orchestration contract documentation, (4) Silver
regression validation, and (5) log completeness. The deliverables are three
narrow code fixes (logger frontmatter, WhatsApp frontmatter, router log),
one new module (`vault_audit.py`), and a set of MCP contract Markdown
documents. No new end-user features are added.

## Technical Context

**Language/Version**: Python 3.12 (existing project language)
**Primary Dependencies**: stdlib only (`pathlib`, `re`, `dataclasses`,
`datetime`) — no new packages required
**Storage**: Local filesystem — `vault/` directory tree
**Testing**: pytest (already installed); all new tests in `tests/unit/`
**Target Platform**: Linux (WSL2) — same as existing system
**Performance Goals**: Audit scan of a vault with 1,000 files MUST complete
in under 5 seconds; all validation is offline (no network calls)
**Constraints**: All changes MUST be backward-compatible; existing Silver tests
MUST continue to pass; audit tool is read-only (no vault mutations)
**Scale/Scope**: Single-machine vault; typical vault has hundreds of files

## Constitution Check

*Gate: Must pass before Phase 0. All 12 principles evaluated.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | ✅ PASS | All work is local filesystem — no external calls in any deliverable |
| II. Canonical Folder Structure | ✅ PASS | Phase 1 enforces and validates the canonical structure; no directories renamed or bypassed |
| III. Tiered Scope | ✅ PASS | Gold Phase 1 work — ratified tier; scoped to `specs/gold/phase-1/` |
| IV. Safety-First Execution | ✅ PASS | Audit tool is read-only; any code fixes write to non-critical fields only; no file moves without execution plans |
| V. Ralph Wiggum Loop | ✅ PASS | Existing retry loops preserved; audit tool failure is non-blocking |
| VI. HITL and Approval Gates | ✅ PASS | No external actions in Phase 1; audit reports require human review before any remediation |
| VII. Credential and Secrets Isolation | ✅ PASS | No credentials involved; audit tool reads frontmatter only |
| VIII. Agent Skills and MCP Orchestration | ✅ PASS | MCP contract documents are the primary Phase 1 MCP deliverable; existing vault MCP server unchanged |
| IX. Audit Logging | ✅ PASS | Fixing log completeness (logger frontmatter gaps) is a primary deliverable |
| X. Graceful Degradation | ✅ PASS | Audit tool failures are non-blocking; partial audit results are still returned |
| XI. Gold-Tier Phased Development | ✅ PASS | Phase 1 only; no Phase 2–5 content touched |
| XII. Gold Scope Boundary Enforcement | ✅ PASS | No Odoo, social, briefing, or reliability work; all changes scoped to Phase 1 spec |

**Gate result: PASS — all 12 principles satisfied. No violations.**

## Phase 0: Research

### Findings

**Decision 1: Source field value normalization**
- **Chosen**: Retain `source: gmail-api` in Gmail files (not `source: gmail`).
  Add a constitution note that `source` values are sub-variants
  (`gmail-api`, `whatsapp`, `filesystem`) — all are valid. Do NOT change
  existing Gmail files or break existing tests.
- **Rationale**: `gmail-api` is more specific and accurately reflects the
  transport mechanism. Changing it would break existing router tests (which
  match on `source: gmail-api`). The spec requirement is that `source` is
  present — not that it has a specific value.
- **Alternatives**: Normalize to `source: gmail` (rejected — breaks 6 router
  tests; `gmail-api` is more accurate)

**Decision 2: WhatsApp `subject` field**
- **Chosen**: Add `subject` field to WhatsApp frontmatter as a copy of
  `chat_name`. This satisfies FR-003 (all captured items MUST have a
  `subject` field) without removing `chat_name` (backward-compatible).
- **Rationale**: WhatsApp messages do not have a literal "subject". The
  closest semantic equivalent is the chat name. Existing WhatsApp consumers
  that use `chat_name` continue to work.
- **Alternatives**: Use first line of message body as subject (rejected —
  unpredictable; chat_name is stable)

**Decision 3: Logger frontmatter field alignment**
- **Chosen**: Fix `sentinel/logger.py` to use `action_type:` (not `action:`)
  in YAML frontmatter, and promote `source_path` and `dest_path` from
  Markdown body to YAML frontmatter fields. This satisfies FR-009 (all 6
  required log fields in frontmatter).
- **Rationale**: FR-009 and Constitution Principle IX both require `action_type`,
  `source_path`, and `dest_path` as named fields. The current `action:` key
  is a typo-level divergence from the rest of the system (router uses
  `action_type:`). Promoting path fields to frontmatter enables programmatic
  audit of log files.
- **Alternatives**: Keep existing format and update FR-009 (rejected —
  FR-009 is a spec contract)

**Decision 4: Router log `details` field**
- **Chosen**: Add `details:` field to `router/router.py`'s `_write_routing_log`
  function with a human-readable summary of matched rules.
- **Rationale**: FR-009 requires all 6 fields. The router log currently
  omits `details`. Adding matched rules as details is the natural content.
- **Alternatives**: Omit `details` from log requirement for the router
  (rejected — FR-009 is spec contract; all flows must comply)

**Decision 5: Vault boundary audit tool location**
- **Chosen**: New standalone module `src/sentinel/vault_audit.py` — a
  pure-function audit tool callable from CLI and from tests.
- **Rationale**: Follows the existing `sentinel/` pattern (logger, mover,
  planner are all standalone). Independently testable without running the
  full orchestrator. Exposes `run_vault_audit(vault_path) -> BoundaryAuditReport`.
- **Alternatives**: Add to `brain.py` (rejected — brain.py is the orchestrator,
  not an audit tool; would complicate testing); new top-level module (rejected
  — sentinel/ already houses vault utilities)

**Decision 6: MCP contracts format**
- **Chosen**: Markdown documents in `specs/gold/phase-1/contracts/` — one file
  per integration domain. Each document specifies: tool name, description,
  input parameters, output format, approval gate requirement, error behavior.
  This is documentation, not code.
- **Rationale**: FR-008 requires contracts to be documented before Phase 1
  closes. Markdown contracts are readable by both humans and future AI agents.
  Code implementation of Odoo/social MCP tools is Phase 2/3 work.
- **Alternatives**: OpenAPI YAML (rejected — overkill for local tools;
  harder to read in Obsidian vault)

**Decision 7: Silver regression test baseline**
- **Chosen**: The Silver baseline is the current passing test count: 121 tests
  pass, 3 fail (all in `facebook_publisher`). The 3 pre-existing failures are
  unrelated to Silver-tier features and are NOT regressions introduced by
  Phase 1. Phase 1 must not increase the failure count.
- **Rationale**: The 3 failures (`test_publish_result_defaults`,
  `test_execution_state_from_empty_dict`, `test_execution_state_defaults`)
  all relate to `datetime.utcnow()` deprecation warnings in the Facebook
  publisher module — a pre-existing issue. Silver tier does not include
  Facebook publishing.
- **Alternatives**: Fix the 3 pre-existing failures as part of Phase 1
  (rejected — out of Phase 1 scope; those tests relate to Facebook publisher
  which is a pre-Silver artifact, not a Silver deliverable)

**Output**: All 7 decisions resolved. No NEEDS CLARIFICATION items remain.

## Phase 1: Design & Contracts

### Data Model

See [`data-model.md`](./data-model.md).

**VaultRoute**:

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Source identifier (`gmail-api`, `whatsapp`, `filesystem`) |
| `urgency` | `"normal"` \| `"urgent"` | Urgency level from frontmatter |
| `destination_dir` | `Path` | Canonical destination (`Inbox/<source>/` or `Needs_Action/<source>/`) |

**BoundaryAuditReport**:

| Field | Type | Description |
|-------|------|-------------|
| `vault_path` | `Path` | Vault root scanned |
| `scanned_at` | `str` | ISO 8601 timestamp |
| `directories_checked` | `int` | Count of canonical directories scanned |
| `files_checked` | `int` | Total files inspected |
| `violations` | `list[BoundaryViolation]` | Files whose `type` mismatches directory expectation |
| `passed` | `bool` | `True` if `violations` is empty |

**BoundaryViolation**:

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `Path` | Path to the offending file |
| `directory` | `str` | Canonical directory name |
| `expected_type` | `str` | Expected `type` value for this directory |
| `actual_type` | `str` \| `None` | Actual `type` value found (or `None` if missing) |

**MCPContract**:

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | MCP tool identifier |
| `domain` | `str` | Integration domain (`vault`, `odoo`, `social`, `briefing`) |
| `description` | `str` | Human-readable purpose |
| `inputs` | `list[str]` | Parameter names and types |
| `outputs` | `str` | Return value description |
| `requires_approval` | `bool` | Whether human approval gate is required |
| `error_behavior` | `str` | What happens on failure |

**LogEntry** (aligned to FR-009):

| Field | Type | Notes |
|-------|------|-------|
| `timestamp` | `str` | ISO 8601 — already present |
| `action_type` | `str` | Rename from `action:` — **gap to fix** |
| `source_path` | `str` | Promote from body to frontmatter — **gap to fix** |
| `dest_path` | `str` | Promote from body to frontmatter — **gap to fix** |
| `outcome` | `str` | Already present |
| `details` | `str` | Already present in sentinel logger; **gap in router log** |

### Integration Points Diagram

```
Gmail Watcher                   WhatsApp Watcher
     │                                │
     │ write_email_file()             │ write_message_file()
     │ → Inbox/email/ or             │ → Inbox/whatsapp/ or
     │   Needs_Action/email/         │   Needs_Action/whatsapp/
     │ (source: gmail-api) ✅        │ + ADD subject field ← FIX
     │                                │
     └────────────────┬───────────────┘
                      │
              Router (route_inbox)
              Inbox/email/ → Needs_Action/email/
              (add details field) ← FIX
                      │
              Orchestrator (brain.py)
              _process_email()
              → write_execution_plan()  (Approved/)
              → write_runtime_plan()    (Needs_Action/plans/)
              → shutil.move()           (Needs_Action/drafts/)
              → write_draft_reply()     (Needs_Action/drafts/)
              → write_log_entry()  ← FIX action_type + paths in frontmatter
                      │
              Vault MCP Server
              list_files / read_file / write_file
              → logs operation ← verify logged
                      │
              BoundaryAuditReport ← NEW MODULE
              scans all canonical dirs
              reports type mismatches
```

### Module Breakdown

**Module 1 — `src/sentinel/vault_audit.py`** (NEW)

Responsibility: Scan canonical vault directories, compare each file's
`type` frontmatter field against the expected type for that directory,
return a `BoundaryAuditReport`.

Expected type table (hardcoded):

| Directory | Expected `type` value |
|-----------|-----------------------|
| `Needs_Action/plans/` | `runtime_plan` |
| `Approved/` | `execution_plan` |
| `Pending_Approval/` | `pending_action` |
| `Needs_Action/drafts/` | `draft_reply` |

Other canonical directories (`Inbox/`, `Done/`, `Logs/`, `Briefings/`,
`Accounting/`, `Plans/`, `Signals/`, `Updates/`, `In_Progress/`) are scanned
for presence but do not have mandatory `type` constraints — their contents
are heterogeneous by design.

Public interface:

```
run_vault_audit(vault_path: Path) -> BoundaryAuditReport
    - creates BoundaryAuditReport
    - for each typed directory: scan .md files, parse frontmatter, check type
    - non-blocking: OSError on individual files is logged and skipped
    - returns report with passed=True if violations is empty
```

**Module 2 — `src/sentinel/logger.py`** (MODIFY — gap fixes only)

Changes:
- Rename YAML frontmatter key `action:` → `action_type:`
- Add `source_path:` and `dest_path:` as YAML frontmatter fields
  (in addition to retaining them in the body for human readability)
- `file_size` field promoted to frontmatter for completeness

Existing callers (`brain.py`, `mover.py`) are unaffected — same function
signature, same parameters.

**Module 3 — `src/router/router.py`** (MODIFY — gap fix only)

Change: Add `details:` field to `_write_routing_log()` containing the
matched rules as a human-readable string.

**Module 4 — `src/whatsapp_watcher/writer.py`** (MODIFY — gap fix only)

Change: Add `subject:` field to `build_frontmatter()` output, set to the
value of `chat_name`. Existing `chat_name` field is retained for backward
compatibility.

**Module 5 — `specs/gold/phase-1/contracts/`** (NEW — documentation only)

MCP contract documents:
- `vault-mcp.md` — documents existing `list_files`, `read_file`, `write_file` tools
- `odoo-mcp.md` — stub contract for Phase 2 Odoo integration
- `social-mcp.md` — stub contract for Phase 3 social publishing
- `briefing-mcp.md` — stub contract for Phase 4 CEO briefing generation

Each document follows the MCPContract entity schema above.

### Project Structure

```text
specs/011-gold-phase-1-foundation/
├── spec.md
├── plan.md              ← this file
├── data-model.md        ← Phase 1 output
├── contracts/           ← MCP contract stubs (documentation only)
│   ├── vault-mcp.md
│   ├── odoo-mcp.md
│   ├── social-mcp.md
│   └── briefing-mcp.md
└── tasks.md             ← /sp.tasks output (not yet created)

src/
└── sentinel/
    ├── logger.py        ← MODIFY: frontmatter gap fixes
    ├── vault_audit.py   ← NEW: boundary audit module
    └── [existing files unchanged]

src/
└── router/
    └── router.py        ← MODIFY: add details field to routing log

src/
└── whatsapp_watcher/
    └── writer.py        ← MODIFY: add subject field to frontmatter

tests/
└── unit/
    └── sentinel/
        ├── __init__.py  ← NEW (if not exists)
        └── test_vault_audit.py  ← NEW: boundary audit tests
```

**Total diff surface**: 1 new module, 3 modified modules, 4 new contract
documents, 1 new test file. Minimal.

## Implementation Sequence

### Task 1 — Fix `sentinel/logger.py` frontmatter fields

In `write_log_entry()`, update the YAML frontmatter block:
- Change `action: {action_type}` → `action_type: {action_type}`
- Add `source_path: "{source_path}"` to YAML block
- Add `dest_path: "{dest_path}"` to YAML block

Retain body lines as-is (human-readable `**From**`, `**To**` remain).

**Verify**: `PYTHONPATH=src python3 -c "from sentinel.logger import write_log_entry; print('ok')"`
and inspect a generated log file to confirm all 6 fields present in frontmatter.

### Task 2 — Fix `router/router.py` routing log details field

In `_write_routing_log()`, add `details: "Routed by rules: {matched_rules}"` to
the YAML frontmatter block.

**Verify**: `PYTHONPATH=src pytest tests/unit/router/ -v` — all existing tests pass.

### Task 3 — Fix `whatsapp_watcher/writer.py` subject field

In `build_frontmatter()`, add `"subject": message.chat_name` to the returned
dict (after the existing `chat_name` field).

**Verify**: `PYTHONPATH=src pytest tests/unit/whatsapp_watcher/ -v` — all existing tests pass.

### Task 4 — Create `src/sentinel/vault_audit.py`

Implement `run_vault_audit(vault_path)` with `BoundaryAuditReport` and
`BoundaryViolation` dataclasses. Scan the 4 typed directories. Return
`passed=True` if zero violations.

**Verify**: `PYTHONPATH=src python3 -c "from sentinel.vault_audit import run_vault_audit; print('ok')"`

### Task 5 — Write unit tests for `vault_audit.py`

In `tests/unit/sentinel/test_vault_audit.py`, cover:
- `test_clean_vault_passes` — no type violations → `passed=True`
- `test_wrong_type_detected` — file with wrong type → `passed=False`, violation recorded
- `test_missing_type_field_detected` — file with no `type` field → violation recorded
- `test_nonexistent_dir_skipped` — missing canonical dir → no error, dir skipped
- `test_report_fields_complete` — all BoundaryAuditReport fields populated

**Verify**: `PYTHONPATH=src pytest tests/unit/sentinel/test_vault_audit.py -v` — all pass.

### Task 6 — Write MCP contract documents

Create `specs/gold/phase-1/contracts/`:
- `vault-mcp.md` — fully specified (existing tools)
- `odoo-mcp.md` — stub (Phase 2 scope; tools TBD)
- `social-mcp.md` — stub (Phase 3 scope; tools TBD)
- `briefing-mcp.md` — stub (Phase 4 scope; tools TBD)

**Verify**: All 4 files exist, vault-mcp.md specifies all 3 existing tools.

### Task 7 — Run Silver regression suite

Run `PYTHONPATH=src pytest tests/unit/ -v --tb=short` and verify:
- Total passing tests ≥ 121 (baseline)
- Total failing tests ≤ 3 (only the pre-existing facebook_publisher failures)
- All orchestrator, router, vault_mcp, and whatsapp_watcher tests pass

**Verify**: `PYTHONPATH=src pytest tests/unit/ -v --tb=short 2>&1 | tail -5`

### Task 8 — Run vault boundary audit against real vault

Run the boundary audit against `vault/` and verify `passed=True`.

**Verify**: `PYTHONPATH=src python3 -c "from pathlib import Path; from sentinel.vault_audit import run_vault_audit; r = run_vault_audit(Path('vault')); print('passed:', r.passed, '| violations:', len(r.violations))"`

## Failure Handling

| Failure scenario | System response |
|-----------------|-----------------|
| Routing mismatch (file lands in wrong dir) | Boundary audit flags it as violation; audit report routes to `Needs_Action/plans/` for human review; triage continues |
| Boundary violation detected by audit | `BoundaryAuditReport.passed = False`; violation list written to `Needs_Action/plans/` as a triage plan; system continues operating |
| Missing log fields | Phase 1 Task 1 fixes this gap; post-fix, any missing fields produce a test failure before merge |
| MCP bypass attempt | MCP server enforces path safety via `_safe_resolve()`; any path escaping vault root raises `ValueError` and is logged; operation rejected |
| Audit tool fails (OSError on individual file) | Individual file is skipped and error noted in `BoundaryAuditReport.violations`; other files continue to be scanned |
| Silver test regression | Tasks 1–3 changes are backward-compatible by design; if a test fails, the specific change causing it is reverted before phase closes |

All failure paths follow Ralph Wiggum Loop (Constitution Principle V):
try → retry with adjusted context → simplify → route to `Needs_Action` for
human review after 3 failures.

## Complexity Tracking

No constitution violations. No complexity justifications required.

## Risks

1. **Logger frontmatter change affects existing log consumers**: Any code
   that reads log files and expects `action:` (not `action_type:`) will
   break. Mitigation: grep the codebase for `log\["action"\]` or `action:`
   before merging; update any consumers found.
2. **WhatsApp `subject` field conflicts with parser**: The email parser
   (`router/parser.py`) may read WhatsApp files and expect specific fields.
   Mitigation: check router parser for field assumptions before Task 3.
3. **Pre-existing 3 Facebook publisher failures**: Must not be confused with
   Phase 1 regressions. Mitigation: document baseline (121 pass, 3 fail) in
   tasks.md and verify count before and after each change.
