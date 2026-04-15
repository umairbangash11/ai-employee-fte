# Tasks: Gold Phase 1 — Cross-Domain Integration Foundation

**Input**: Design documents from `specs/011-gold-phase-1-foundation/`
**Branch**: `gold-phase` | **Date**: 2026-04-15
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story. No new external packages are required
— stdlib only (`pathlib`, `re`, `dataclasses`, `datetime`).

**Silver Baseline** (DO NOT regress):
- Passing: 121 tests
- Failing: 3 tests (pre-existing `facebook_publisher` failures — unrelated to Silver)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to user story from spec.md (US1–US5)

---

## Phase 1: Setup

**Purpose**: Confirm directory structure and Silver test baseline before any changes.

- [x] T001 Create `tests/unit/sentinel/__init__.py` (empty) if it does not exist
- [x] T002 Record Silver test baseline: run `PYTHONPATH=src pytest tests/unit/ -v --tb=short 2>&1 | tail -10` and confirm 121 pass / 3 fail (pre-existing facebook_publisher)

**Checkpoint**: Baseline confirmed — no changes made yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No shared blocking infrastructure required beyond Phase 1. All user
stories operate on independent files and modules. Proceed directly to US1.

**⚠️ CRITICAL**: Complete Phase 1 before any user story work begins.

---

## Phase 3: User Story 1 — Unified Vault Routing (Priority: P1) 🎯 MVP

**Goal**: All captured items from every watcher land in the correct canonical
vault location with complete YAML frontmatter (all 7 required fields present).

**Independent Test**: Run `PYTHONPATH=src pytest tests/unit/whatsapp_watcher/ -v`
and confirm all tests pass. Then inspect a sample WhatsApp output file and
confirm `subject:` field is present alongside `chat_name:`.

### Implementation for User Story 1

- [x] T003 [US1] Add `subject` field to `build_frontmatter()` in `src/whatsapp_watcher/writer.py` (set to value of `chat_name`; retain existing `chat_name` field for backward compatibility)
- [x] T004 [US1] Verify `src/router/parser.py` has no field assumptions that conflict with the new `subject` field (read-only check, no code change if clean)
- [x] T005 [US1] Run `PYTHONPATH=src pytest tests/unit/whatsapp_watcher/ -v` — all existing tests must pass

**Checkpoint**: WhatsApp files now emit all 7 required frontmatter fields. US1 independently verified.

---

## Phase 4: User Story 2 — Vault State Boundary Validation (Priority: P1)

**Goal**: A boundary audit tool exists that scans all typed canonical vault
directories and reports files whose `type` frontmatter field does not match
the expected type for that directory.

**Independent Test**: Run `PYTHONPATH=src pytest tests/unit/sentinel/test_vault_audit.py -v`
— all 5 tests pass. Then run `PYTHONPATH=src python3 -c "from pathlib import Path; from sentinel.vault_audit import run_vault_audit; r = run_vault_audit(Path('vault')); print('passed:', r.passed)"` against the real vault.

### Implementation for User Story 2

- [x] T006 [US2] Create `src/sentinel/vault_audit.py` — implement `BoundaryViolation` dataclass with fields: `file_path`, `directory`, `expected_type`, `actual_type`
- [x] T007 [US2] Add `BoundaryAuditReport` dataclass to `src/sentinel/vault_audit.py` with fields: `vault_path`, `scanned_at`, `directories_checked`, `files_checked`, `violations`, `passed`
- [x] T008 [US2] Implement `run_vault_audit(vault_path: Path) -> BoundaryAuditReport` in `src/sentinel/vault_audit.py` — scan 4 typed directories (`Needs_Action/plans/` → `runtime_plan`, `Approved/` → `execution_plan`, `Pending_Approval/` → `pending_action`, `Needs_Action/drafts/` → `draft_reply`); skip missing dirs; skip individual file OSErrors non-blocking
- [x] T009 [US2] Write `tests/unit/sentinel/test_vault_audit.py` — 5 tests: `test_clean_vault_passes`, `test_wrong_type_detected`, `test_missing_type_field_detected`, `test_nonexistent_dir_skipped`, `test_report_fields_complete`
- [x] T010 [US2] Run `PYTHONPATH=src pytest tests/unit/sentinel/test_vault_audit.py -v` — all 5 tests must pass

**Checkpoint**: `vault_audit.py` module is complete, tested, and importable. US2 independently verified.

---

## Phase 5: User Story 3 — MCP Orchestration Boundary Enforcement (Priority: P2)

**Goal**: MCP contract documents exist for all current vault tools and all
planned Gold-tier external integrations, stored in `specs/gold/phase-1/contracts/`.

**Independent Test**: Confirm all 4 contract files exist and `vault-mcp.md`
specifies all 3 existing vault tools (`list_files`, `read_file`, `write_file`)
with complete input/output/error schemas.

### Implementation for User Story 3

- [x] T011 [US3] Create directory `specs/gold/phase-1/contracts/` (and parent `specs/gold/phase-1/` if needed)
- [x] T012 [US3] Create `specs/gold/phase-1/contracts/vault-mcp.md` — fully specify existing tools: `list_files` (input: path, output: file list, no approval gate), `read_file` (input: path, output: content, no approval gate), `write_file` (input: path + content, output: confirmation, no approval gate); include error behavior for path escaping vault root
- [x] T013 [P] [US3] Create `specs/gold/phase-1/contracts/odoo-mcp.md` — Phase 2 stub: tool names TBD, domain: `odoo`, requires_approval: true, error_behavior: route to `Needs_Action/`
- [x] T014 [P] [US3] Create `specs/gold/phase-1/contracts/social-mcp.md` — Phase 3 stub: domain: `social`, requires_approval: true, covers Facebook/Instagram/X post publishing
- [x] T015 [P] [US3] Create `specs/gold/phase-1/contracts/briefing-mcp.md` — Phase 4 stub: domain: `briefing`, requires_approval: false (read-only generation), covers CEO briefing generation

**Checkpoint**: All 4 MCP contract files exist. vault-mcp.md is fully specified. US3 independently verified.

---

## Phase 6: User Story 4 — Silver Compatibility Regression Check (Priority: P2)

**Goal**: All Silver-tier unit tests pass after Phase 3–5 changes. Zero
regressions introduced by any Gold Phase 1 modification.

**Independent Test**: Run full unit suite and compare pass/fail count against
the Phase 1 baseline (≥ 121 pass, ≤ 3 fail).

### Implementation for User Story 4

- [x] T016 [US4] Run `PYTHONPATH=src pytest tests/unit/ -v --tb=short` — confirm passing ≥ 121, failing ≤ 3 (pre-existing facebook_publisher failures only); if any new failures appear, diagnose and fix before proceeding

**Checkpoint**: Silver regression baseline confirmed post-US1/US2/US3 changes. US4 independently verified.

---

## Phase 7: User Story 5 — Log Completeness Audit (Priority: P3)

**Goal**: Every automated action produces a log entry in `vault/Logs/` containing
all 6 required YAML frontmatter fields: `timestamp`, `action_type`, `source_path`,
`dest_path`, `outcome`, `details`.

**Independent Test**: Run `PYTHONPATH=src pytest tests/unit/ -v --tb=short` after
all fixes — all Silver tests still pass. Then inspect a log entry produced by the
orchestrator and confirm all 6 fields appear in the YAML frontmatter block.

### Implementation for User Story 5

- [x] T017 [US5] Grep codebase for `log["action"]` and `action:` in log-reading code: `grep -r 'action[^_]' src/ --include="*.py"` — identify any consumer of the old `action:` key before changing it
- [x] T018 [US5] Fix `src/sentinel/logger.py` `write_log_entry()`: rename YAML key `action:` → `action_type:`, add `source_path:` and `dest_path:` as YAML frontmatter fields (retain body lines `**From**` / `**To**` for human readability)
- [x] T019 [US5] Fix `src/router/router.py` `_write_routing_log()`: add `details:` field to YAML frontmatter containing matched rules as a human-readable string (e.g. `"Routed by rules: {matched_rules}"`)
- [x] T020 [US5] Run `PYTHONPATH=src pytest tests/unit/router/ -v` — all existing router tests must pass after the `details` field addition
- [x] T021 [US5] Run `PYTHONPATH=src pytest tests/unit/orchestrator/ -v` — all orchestrator tests must pass after the `action_type` rename

**Checkpoint**: All 6 required log fields now present in frontmatter for all emitters. US5 independently verified.

---

## Phase 8: Polish & End-to-End Validation

**Purpose**: Full regression sweep and live vault audit after all changes land.

- [x] T022 [P] Run complete Silver regression suite: `PYTHONPATH=src pytest tests/unit/ -v --tb=short` — final count must be ≥ 121 pass / ≤ 3 fail
- [x] T023 [P] Run vault boundary audit against real vault: `PYTHONPATH=src python3 -c "from pathlib import Path; from sentinel.vault_audit import run_vault_audit; r = run_vault_audit(Path('vault')); print('passed:', r.passed, '| violations:', len(r.violations))"` — verify `passed: True`
- [x] T024 Inspect a log file in `vault/Logs/` (or generate one via orchestrator) and verify all 6 fields (`timestamp`, `action_type`, `source_path`, `dest_path`, `outcome`, `details`) appear in the YAML frontmatter — SC-005 sign-off

**Checkpoint**: Gold Phase 1 complete. All 6 success criteria (SC-001 through SC-006) met.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: N/A — no shared blocking infra; proceed to Phase 3 after Phase 1
- **Phase 3 (US1)**: Depends on Phase 1 only
- **Phase 4 (US2)**: Depends on Phase 1 only — independent of US1 (different files)
- **Phase 5 (US3)**: Depends on Phase 1 only — documentation only, no code dependencies
- **Phase 6 (US4)**: Depends on Phases 3, 4, 5 — regression check must happen after all changes
- **Phase 7 (US5)**: Depends on Phase 6 passing — changes to logger/router after Silver confirmed
- **Phase 8 (Polish)**: Depends on all Phases 3–7 complete

### User Story Dependencies

- **US1 (P1)**: Start after Phase 1 — modifies `src/whatsapp_watcher/writer.py` only
- **US2 (P1)**: Start after Phase 1 — creates new `src/sentinel/vault_audit.py` and tests; no conflict with US1
- **US3 (P2)**: Start after Phase 1 — documentation only; can run in parallel with US1 and US2
- **US4 (P2)**: Depends on US1 + US2 + US3 complete
- **US5 (P3)**: Depends on US4 (Silver baseline re-confirmed); modifies `logger.py` + `router.py`

### Parallel Opportunities

- **US1 + US2 + US3** can all run in parallel (different files, no dependencies between them)
- Within US3, T013 + T014 + T015 (stub contracts) can run in parallel
- **T022 + T023** in Phase 8 can run in parallel (different operations)

---

## Parallel Example: US1, US2, US3 (all Phase 1 → Phase 3/4/5)

```bash
# After Phase 1 Setup completes, launch all three in parallel:

# Stream A — US1: WhatsApp frontmatter fix
# T003: Fix build_frontmatter() in src/whatsapp_watcher/writer.py
# T004: Verify router/parser.py compatibility
# T005: pytest tests/unit/whatsapp_watcher/

# Stream B — US2: Vault audit module
# T006–T008: Create src/sentinel/vault_audit.py
# T009: Write tests/unit/sentinel/test_vault_audit.py
# T010: pytest tests/unit/sentinel/test_vault_audit.py

# Stream C — US3: MCP contract docs (no code, pure docs)
# T011: Create specs/gold/phase-1/contracts/
# T012: vault-mcp.md
# T013+T014+T015: odoo/social/briefing stubs
```

---

## Implementation Strategy

### MVP (US1 + US2 first)

1. Complete Phase 1: Setup (T001–T002)
2. Complete US1 in parallel with US2 (T003–T010)
3. **STOP and VALIDATE**: Both user stories independently verified
4. Add US3 documentation (T011–T015) — can overlap with step 2
5. Run US4 regression check (T016)
6. Complete US5 log fixes (T017–T021)
7. Final polish and validation (T022–T024)

### Total Tasks: 24

| Phase | Tasks | Count |
|-------|-------|-------|
| Setup | T001–T002 | 2 |
| US1 (P1) | T003–T005 | 3 |
| US2 (P1) | T006–T010 | 5 |
| US3 (P2) | T011–T015 | 5 |
| US4 (P2) | T016 | 1 |
| US5 (P3) | T017–T021 | 5 |
| Polish | T022–T024 | 3 |
| **Total** | | **24** |

---

## Notes

- [P] tasks touch different files — safe to parallelize
- Silver baseline (121 pass / 3 fail) must be confirmed at T002 and re-confirmed at T016 and T022
- The 3 pre-existing failures (`facebook_publisher`) are NOT regressions — document and skip
- `vault_audit.py` is read-only — it never mutates vault files
- All logger changes (T018) are backward-compatible: body lines retained; only YAML frontmatter keys change
- `specs/gold/phase-1/contracts/` is documentation; it does not affect any runtime path
- Commit after each phase checkpoint to keep the diff surface minimal
