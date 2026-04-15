# Tasks: Runtime Plan Generation

**Input**: Design documents from `specs/010-runtime-plan-gen/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅
**Branch**: `010-runtime-plan-gen` | **Date**: 2026-04-14

**Organization**: Tasks grouped by user story for independent implementation and testing.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test package structure before any implementation begins.

- [x] T001 Create `tests/unit/orchestrator/__init__.py` (empty file — makes orchestrator a test package)

**Checkpoint**: `PYTHONPATH=src pytest tests/unit/orchestrator/ --collect-only` runs without import errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create `plan_writer.py` module — the standalone writer function that all user stories depend on. No user story work can begin until this is complete.

**⚠️ CRITICAL**: All three user stories depend on this module existing and being importable.

- [x] T002 Implement `_safe_slug(subject: str) -> str` helper in `src/orchestrator/plan_writer.py` — sanitises subject to `[a-z0-9-]`, max 40 chars, strip leading/trailing hyphens
- [x] T003 Implement `_deduplicate_path(plans_dir: Path, filename: str) -> Path` helper in `src/orchestrator/plan_writer.py` — appends `_1`, `_2` etc. if file already exists
- [x] T004 Implement `write_runtime_plan(plans_dir, source_filename, email_meta, classification) -> Path | None` in `src/orchestrator/plan_writer.py` — writes YAML frontmatter + 6 body sections; catches `OSError`; returns `Path` or `None`
- [x] T005 Verify module is importable: `PYTHONPATH=src python3 -c "from orchestrator.plan_writer import write_runtime_plan; print('ok')"`

**Checkpoint**: Import succeeds, no syntax errors. `write_runtime_plan` function exists and is callable.

---

## Phase 3: User Story 1 — Plan Created for Actionable Email (Priority: P1) 🎯 MVP

**Goal**: When `write_runtime_plan()` is called with `needs_reply=True`, it creates a plan file at the correct vault location with all required fields.

**Independent Test**: `PYTHONPATH=src pytest tests/unit/orchestrator/test_plan_writer.py -v` — all tests pass.

### Tests for User Story 1

- [x] T006 [US1] Write `test_plan_created_for_actionable_email` in `tests/unit/orchestrator/test_plan_writer.py` — call with `needs_reply=True`, assert file exists at `plans_dir/`
- [x] T007 [US1] Write `test_all_required_fields_present` in `tests/unit/orchestrator/test_plan_writer.py` — parse frontmatter from written file, assert all 7 fields present: `type`, `status`, `created_at`, `source_file`, `requires_approval`, `email_sender`, `email_subject`
- [x] T008 [US1] Write `test_correct_vault_location` in `tests/unit/orchestrator/test_plan_writer.py` — assert plan file path is inside `Needs_Action/plans/` (not `Approved/`, not `Inbox/`)
- [x] T009 [US1] Write `test_expected_markdown_structure` in `tests/unit/orchestrator/test_plan_writer.py` — read file content, assert all 6 sections present: `# Triage Plan`, `## Objective`, `## Source Context`, `## Action Steps`, `## Approval Requirement`, `## Status`
- [x] T010 [US1] Write `test_standard_action_steps_for_reply_needed` in `tests/unit/orchestrator/test_plan_writer.py` — assert file contains the 3 standard checkboxes: `Review the AI-generated draft reply`, `Edit the draft as needed`, `Approve by moving to Approved/email/`

**Checkpoint**: `PYTHONPATH=src pytest tests/unit/orchestrator/test_plan_writer.py::test_plan_created_for_actionable_email tests/unit/orchestrator/test_plan_writer.py::test_all_required_fields_present tests/unit/orchestrator/test_plan_writer.py::test_correct_vault_location tests/unit/orchestrator/test_plan_writer.py::test_expected_markdown_structure tests/unit/orchestrator/test_plan_writer.py::test_standard_action_steps_for_reply_needed -v` — all 5 pass.

---

## Phase 4: User Story 2 — No Plan Created for Non-Actionable Email (Priority: P2)

**Goal**: The plan writer is called by the orchestrator only on the `needs_reply=True` path. Non-actionable emails never trigger plan creation. This is a caller-side contract enforced in `brain.py`.

**Independent Test**: `PYTHONPATH=src python3 -c "from orchestrator.brain import InboxTriageHandler; print('ok')"` — import succeeds with `plans_dir` attribute present.

### Implementation for User Story 2

- [x] T011 [US2] Add `self.plans_dir = self.needs_action_dir / "plans"` to `InboxTriageHandler.__init__` in `src/orchestrator/brain.py`
- [x] T012 [US2] Add `from orchestrator.plan_writer import write_runtime_plan` import to `src/orchestrator/brain.py`
- [x] T013 [US2] In `_route_reply_needed()` in `src/orchestrator/brain.py`, insert `write_runtime_plan(self.plans_dir, ...)` call after `write_execution_plan()` and before `shutil.move()` — wrap in try/except, log warning on `None` return
- [x] T014 [US2] Verify import chain: `PYTHONPATH=src python3 -c "from orchestrator.brain import InboxTriageHandler; print('ok')"`
- [x] T015 [US2] Confirm `write_runtime_plan` is ONLY called inside `_route_reply_needed()` — not in `_route_no_reply()` or other paths: `PYTHONPATH=src grep -n "write_runtime_plan" src/orchestrator/brain.py` should show exactly one call site

**Checkpoint**: brain.py imports cleanly, `plans_dir` attribute exists on handler, `write_runtime_plan` called only on reply-needed path.

---

## Phase 5: User Story 3 — Plan Writer Independently Testable (Priority: P2)

**Goal**: Full unit test suite for `plan_writer.py` runs without OpenAI, watcher loop, or vault filesystem. All edge cases covered.

**Independent Test**: `PYTHONPATH=src pytest tests/unit/orchestrator/ -v` — all tests pass.

### Tests for User Story 3

- [x] T016 [US3] Write `test_filename_deduplication` in `tests/unit/orchestrator/test_plan_writer.py` — call `write_runtime_plan()` twice with identical subject in same `plans_dir`; assert two distinct files created (second gets `_1` suffix)
- [x] T017 [US3] Write `test_error_classification_uses_fallback_steps` in `tests/unit/orchestrator/test_plan_writer.py` — call with `needs_reply=False` (error/fallback); assert file contains `Human review required — automated classification failed` and `Inspect the source email` checkboxes
- [x] T018 [US3] Write `test_write_failure_returns_none` in `tests/unit/orchestrator/test_plan_writer.py` — pass a read-only directory as `plans_dir`; assert `None` returned and no exception propagates
- [x] T019 [US3] Write `test_plans_dir_created_if_missing` in `tests/unit/orchestrator/test_plan_writer.py` — pass a non-existent subdirectory as `plans_dir`; assert the directory is created and file written successfully
- [x] T020 [US3] Write `test_requires_approval_always_true` in `tests/unit/orchestrator/test_plan_writer.py` — parse frontmatter from written plan file, assert `requires_approval: true` regardless of classification input
- [x] T021 [US3] Run full suite: `PYTHONPATH=src pytest tests/unit/orchestrator/ -v` — all tests pass, no OpenAI calls, no watcher started

**Checkpoint**: All 7+ unit tests pass. Suite completes in under 5 seconds. No mocking of OpenAI required.

---

## Phase 6: End-to-End Validation

**Purpose**: Validate plan file creation, correct vault location, expected markdown structure, and end-to-end runtime flow against the real vault path.

- [x] T022 Create `vault/Needs_Action/plans/` directory if it does not exist: `mkdir -p vault/Needs_Action/plans/`
- [x] T023 Run end-to-end smoke test — manually invoke `write_runtime_plan()` with real vault path and mock classification:
  ```bash
  PYTHONPATH=src python3 -c "
  from pathlib import Path
  from orchestrator.plan_writer import write_runtime_plan
  plans_dir = Path('vault/Needs_Action/plans')
  result = write_runtime_plan(
      plans_dir=plans_dir,
      source_filename='test-email.md',
      email_meta={'sender': 'test@example.com', 'subject': 'Re: Project Update', 'source': 'gmail', 'urgency': 'normal'},
      classification={'needs_reply': True, 'reason': 'Requires a reply', 'draft': 'Dear test...'}
  )
  print('Plan written to:', result)
  "
  ```
- [x] T024 Validate vault location: `ls vault/Needs_Action/plans/` — plan file appears in correct directory (NOT in `Approved/`, `Inbox/`, or `Done/`)
- [x] T025 Validate markdown structure: open the generated plan file and confirm all 6 sections are present and readable as Markdown with correct heading levels
- [x] T026 Validate YAML frontmatter: confirm all 7 frontmatter fields are present (`type`, `status`, `created_at`, `source_file`, `requires_approval`, `email_sender`, `email_subject`) with correct values
- [x] T027 Validate action steps: confirm the 3 standard checkboxes are present and use `- [ ]` format

**Checkpoint**: Plan file exists at `vault/Needs_Action/plans/`, all 6 sections present, all 7 frontmatter fields correct, checkboxes use `- [ ]` syntax.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (plan_writer.py must exist)
- **User Story 2 (Phase 4)**: Depends on Phase 2 and Phase 3 (brain.py integrates with plan_writer)
- **User Story 3 (Phase 5)**: Depends on Phase 2; can run in parallel with Phase 3 after T005
- **E2E Validation (Phase 6)**: Depends on all phases complete

### Parallel Opportunities

- T002, T003 in Phase 2 can run in parallel (different functions, same file — no conflict if done sequentially within file)
- T006–T010 in Phase 3 (test writing) can all be written in parallel — different test functions, same file
- T016–T020 in Phase 5 (test writing) can all be written in parallel
- T024–T027 in Phase 6 validation can run in parallel (read-only checks)

---

## Parallel Example: Phase 3 Test Writing

```bash
# Write all US1 tests together (different test functions, same file):
Task: "test_plan_created_for_actionable_email"
Task: "test_all_required_fields_present"
Task: "test_correct_vault_location"
Task: "test_expected_markdown_structure"
Task: "test_standard_action_steps_for_reply_needed"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T005)
3. Complete Phase 3: US1 tests + run to confirm pass (T006–T010)
4. **STOP and VALIDATE**: `PYTHONPATH=src pytest tests/unit/orchestrator/ -v`
5. US1 is the minimum deliverable — plan files are created with correct structure

### Incremental Delivery

1. T001 → T005: Foundation ready
2. T006–T010: US1 tests pass — plan creation verified
3. T011–T015: brain.py integration — non-actionable path confirmed clean
4. T016–T021: full edge-case coverage
5. T022–T027: E2E against real vault — Silver tier gap closed

---

## Notes

- No OpenAI dependency in any test — all tests use `tmp_path` fixtures and real filesystem writes
- `write_runtime_plan()` is called ONLY from `_route_reply_needed()` — never from `_route_no_reply()`
- `plans_dir` is distinct from `drafts_dir` — plans go to `Needs_Action/plans/`, drafts to `Needs_Action/drafts/`
- `requires_approval: true` is hardcoded — never derived from classification input
- All tests use `tmp_path` (pytest fixture) — no writes to real vault during unit tests
- E2E validation (Phase 6) is the only phase that writes to the real vault
