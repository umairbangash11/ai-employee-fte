# Tasks: Human-in-the-Loop Approval System

**Feature**: 005-hitl-approval
**Phase**: 3 — HITL + Approval Workflow Hardening
**Input**: `specs/005-hitl-approval/plan.md`, `phase-3/spec.md`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- All file paths are exact

---

## Phase 1: Setup (Package Foundation)

**Purpose**: Create hitl_approval package structure and dependencies

- [x] T001 Create package directory at `src/hitl_approval/__init__.py` with version 0.1.0
- [x] T002 [P] Create exceptions module at `src/hitl_approval/exceptions.py` with DuplicateApprovalError, InvalidFrontmatterError
- [x] T003 [P] Add hitl-approval dependencies to `pyproject.toml`: pyyaml>=6.0, watchdog>=6.0, click>=8.0
- [x] T004 [P] Add hitl-approval CLI entry point to `pyproject.toml`: hitl-approval = "hitl_approval.__main__:cli"

**Completion**: Package importable, `pip install -e .` succeeds

---

## Phase 2: Foundational (Core Models & Utilities)

**Purpose**: Base models and directory utilities that all user stories depend on

- [x] T005 Create ApprovalRequest dataclass in `src/hitl_approval/models.py` with all fields from plan section 2.2
- [x] T006 [P] Create ApprovalState dataclass in `src/hitl_approval/models.py` for hash registry (created_hashes, last_updated)
- [x] T007 [P] Create config module at `src/hitl_approval/config.py` with HITLConfig dataclass (vault_path, state_path)
- [x] T008 Create directory utilities in `src/hitl_approval/utils.py`: ensure_approval_dirs(vault_path) creates all approval subdirs
- [x] T009 [P] Create slug generation utility in `src/hitl_approval/utils.py`: generate_slug(text, max_len=50)
- [x] T010 [P] Create filename generation utility in `src/hitl_approval/utils.py`: generate_approval_filename(action_type, slug)

**Completion**: `from hitl_approval.models import ApprovalRequest` succeeds, directories created on first run

---

## Phase 3: User Story 1 - Reasoning Layer Creates Approval Request (Priority: P1)

**Goal**: Reasoning layer creates approval request files instead of executing actions

**Independent Test**: Trigger reasoning layer with reply email, verify file in `/Pending_Approval/email/`

### Implementation for US1

- [x] T011 [US1] Create frontmatter generator in `src/hitl_approval/writer.py`: generate_frontmatter(request: ApprovalRequest) → str
- [x] T012 [US1] Create body generator in `src/hitl_approval/writer.py`: generate_body(request: ApprovalRequest) → str
- [x] T013 [US1] Create hash generator in `src/hitl_approval/writer.py`: compute_approval_hash(request) → str (SHA256)
- [x] T014 [US1] Create state loader in `src/hitl_approval/state.py`: load_approval_state(state_path) → ApprovalState
- [x] T015 [US1] Create state saver in `src/hitl_approval/state.py`: save_approval_state(state, state_path)
- [x] T016 [US1] Create duplicate checker in `src/hitl_approval/state.py`: is_duplicate(state, hash) → bool
- [x] T017 [US1] Create main writer function in `src/hitl_approval/writer.py`: create_approval_request(request, vault_path) → Path
- [x] T018 [US1] Add _requires_approval() method to `src/email_reasoner/engine.py` detecting reply/send/forward actions
- [x] T019 [US1] Add _detect_action_type() method to `src/email_reasoner/engine.py` returning send_email_reply|send_email_followup
- [x] T020 [US1] Integrate approval creation in `src/email_reasoner/engine.py:_process_email()` for actions requiring approval

**Completion**: Email needing reply creates file in `/Pending_Approval/email/`, no direct execution

### Tests for US1

- [x] T021 [P] [US1] Unit test for frontmatter generation in `tests/test_approval_writer.py`
- [x] T022 [P] [US1] Unit test for body generation in `tests/test_approval_writer.py`
- [x] T023 [P] [US1] Unit test for duplicate detection in `tests/test_approval_state.py`
- [x] T024 [US1] Integration test: reasoner creates approval file in `tests/test_approval_integration.py`

**Checkpoint**: US1 complete — reasoning layer creates approval files instead of executing

---

## Phase 4: User Story 2 - Human Approves Action via File Move (Priority: P1)

**Goal**: Watcher detects file moved to /Approved/ and logs the approval

**Independent Test**: Create file in /Pending_Approval/email/, move to /Approved/email/, verify log entry

### Implementation for US2

- [x] T025 [US2] Create ApprovalLogger class in `src/hitl_approval/logger.py` with log_event() method
- [x] T026 [US2] Implement log file path generation in `src/hitl_approval/logger.py`: get_log_path(logs_path) → Path
- [x] T027 [US2] Implement JSON lines log writing in `src/hitl_approval/logger.py`: _write_log_entry(entry: dict)
- [x] T028 [US2] Create ApprovalEventHandler class in `src/hitl_approval/watcher.py` extending FileSystemEventHandler
- [x] T029 [US2] Implement on_created() handler in `src/hitl_approval/watcher.py` for /Approved/ directory
- [x] T030 [US2] Implement _is_approved_path() helper in `src/hitl_approval/watcher.py`
- [x] T031 [US2] Implement _handle_approval() in `src/hitl_approval/watcher.py` calling logger.log_event()
- [x] T032 [US2] Create ApprovalWatcher class in `src/hitl_approval/watcher.py` with start()/stop() methods
- [x] T033 [US2] Wire up Observer to watch /Approved/email/ and /Approved/linkedin/ in ApprovalWatcher.start()

**Completion**: Moving file to /Approved/ creates log entry with "approved" event

### Tests for US2

- [x] T034 [P] [US2] Unit test for ApprovalLogger.log_event() in `tests/test_approval_logger.py`
- [x] T035 [P] [US2] Unit test for JSON lines format validation in `tests/test_approval_logger.py`
- [x] T036 [US2] Integration test: file move to Approved creates log in `tests/test_approval_watcher.py`

**Checkpoint**: US2 complete — approvals are detected and logged

---

## Phase 5: User Story 3 - Human Rejects Action via File Move (Priority: P1)

**Goal**: Watcher detects file moved to /Rejected/ and logs the rejection

**Independent Test**: Create file in /Pending_Approval/linkedin/, move to /Rejected/linkedin/, verify log entry

### Implementation for US3

- [x] T037 [US3] Implement on_created() handler extension for /Rejected/ directory in `src/hitl_approval/watcher.py`
- [x] T038 [US3] Implement _is_rejected_path() helper in `src/hitl_approval/watcher.py`
- [x] T039 [US3] Implement _handle_rejection() in `src/hitl_approval/watcher.py` calling logger.log_event()
- [x] T040 [US3] Wire up Observer to also watch /Rejected/email/ and /Rejected/linkedin/ in ApprovalWatcher.start()

**Completion**: Moving file to /Rejected/ creates log entry with "rejected" event

### Tests for US3

- [x] T041 [P] [US3] Unit test for rejection path detection in `tests/test_approval_watcher.py`
- [x] T042 [US3] Integration test: file move to Rejected creates log in `tests/test_approval_watcher.py`

**Checkpoint**: US3 complete — rejections are detected and logged

---

## Phase 6: User Story 4 - CLI Lists Pending Approvals (Priority: P2)

**Goal**: Operator can list all pending approval requests via CLI

**Independent Test**: Create 3 approval files, run `hitl-approval list`, verify all 3 shown

### Implementation for US4

- [x] T043 [US4] Create CLI entry point in `src/hitl_approval/__main__.py` with click group and options
- [x] T044 [US4] Implement `list` command in `src/hitl_approval/__main__.py` scanning /Pending_Approval/
- [x] T045 [US4] Create approval file parser in `src/hitl_approval/validator.py`: parse_approval_file(path) → dict
- [x] T046 [US4] Implement list output formatting: action_type, target, created_at, summary
- [x] T047 [US4] Handle empty state: "No pending approvals" message
- [x] T048 [US4] Implement `show` command in `src/hitl_approval/__main__.py` displaying full approval details
- [x] T049 [US4] Implement `stats` command in `src/hitl_approval/__main__.py` showing counts by status/type

**Completion**: `hitl-approval list` shows all pending approvals with correct format

### Tests for US4

- [x] T050 [P] [US4] Unit test for approval file parsing in `tests/test_approval_validator.py`
- [x] T051 [US4] CLI test for list command in `tests/test_approval_cli.py`
- [x] T052 [US4] CLI test for empty state message in `tests/test_approval_cli.py`

**Checkpoint**: US4 complete — CLI shows pending approvals

---

## Phase 7: User Story 5 - Approval Request Includes Rollback Strategy (Priority: P2)

**Goal**: Every approval request includes rollback_strategy field

**Independent Test**: Create approval request, verify rollback_strategy present in frontmatter

### Implementation for US5

- [x] T053 [US5] Add rollback_strategy validation to ApprovalRequest model in `src/hitl_approval/models.py`
- [x] T054 [US5] Add rollback_strategy to frontmatter template in `src/hitl_approval/writer.py`
- [x] T055 [US5] Add rollback_strategy to body Risk Assessment section in `src/hitl_approval/writer.py`
- [x] T056 [US5] Implement frontmatter validator in `src/hitl_approval/validator.py`: validate_frontmatter(data) → bool

**Completion**: All approval files contain rollback_strategy, validation fails without it

### Tests for US5

- [x] T057 [P] [US5] Unit test for rollback_strategy validation in `tests/test_approval_models.py`
- [x] T058 [US5] Unit test for frontmatter validation in `tests/test_approval_validator.py`

**Checkpoint**: US5 complete — rollback strategy present in all approvals

---

## Phase 8: Edge Cases & Safety

**Purpose**: Handle edge cases from spec section "Edge Cases"

- [x] T059 Implement duplicate prevention in `src/hitl_approval/writer.py`: raise DuplicateApprovalError if hash exists
- [x] T060 [P] Log "abandoned" event when file deleted from /Pending_Approval/ in `src/hitl_approval/watcher.py`
- [x] T061 [P] Add invalid frontmatter handling in `src/hitl_approval/validator.py`: log error, return None
- [x] T062 Add "created" event logging in `src/hitl_approval/writer.py` after successful file creation

**Completion**: All edge cases handled per spec

---

## Phase 9: Orchestrator Integration (LinkedIn)

**Purpose**: LinkedIn post approval via orchestrator

- [x] T063 Create request_linkedin_post_approval() function in `src/hitl_approval/writer.py`
- [x] T064 [P] Add LinkedIn action type constants in `src/hitl_approval/models.py`: ACTION_TYPE_LINKEDIN_POST
- [x] T065 Document orchestrator integration point in `src/orchestrator/brain.py` (comment only, no implementation)

**Completion**: LinkedIn approval requests can be created programmatically

---

## Phase 10: Polish & Documentation

**Purpose**: Final cleanup and documentation

- [x] T066 [P] Add docstrings to all public functions in `src/hitl_approval/` modules
- [x] T067 [P] Update `phase-3/README.md` with completion status
- [x] T068 Run all tests and verify passing: `pytest tests/test_approval_*.py -v`

**Completion**: All tests pass, documentation complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US1)**: Depends on Phase 2 — Core approval creation
- **Phase 4 (US2)**: Depends on Phase 2 — Can run parallel to US1
- **Phase 5 (US3)**: Depends on Phase 4 (extends watcher)
- **Phase 6 (US4)**: Depends on Phase 2 — Can run parallel to US1-US3
- **Phase 7 (US5)**: Depends on Phase 2 — Can run parallel to US1-US4
- **Phase 8 (Edge Cases)**: Depends on US1, US2, US3
- **Phase 9 (LinkedIn)**: Depends on Phase 2
- **Phase 10 (Polish)**: Depends on all previous phases

### Within Each Phase

- Tasks marked [P] can run in parallel
- Tasks without [P] must run sequentially in order

### Parallel Opportunities

```
After Phase 2 completes:
├── US1 (T011-T024) — Approval creation
├── US2 (T025-T036) — Approval detection (parallel)
├── US4 (T043-T052) — CLI (parallel)
├── US5 (T053-T058) — Rollback (parallel)
└── US3 (T037-T042) — Rejection (after US2)
```

---

## Task Summary

| Phase | Tasks | Story Coverage |
|-------|-------|----------------|
| Phase 1: Setup | T001-T004 | Infrastructure |
| Phase 2: Foundational | T005-T010 | Models/Utils |
| Phase 3: US1 | T011-T024 | Approval Creation |
| Phase 4: US2 | T025-T036 | Approval Detection |
| Phase 5: US3 | T037-T042 | Rejection Detection |
| Phase 6: US4 | T043-T052 | CLI Interface |
| Phase 7: US5 | T053-T058 | Rollback Strategy |
| Phase 8: Edge Cases | T059-T062 | Safety/Edge Cases |
| Phase 9: LinkedIn | T063-T065 | Orchestrator |
| Phase 10: Polish | T066-T068 | Documentation |

**Total Tasks**: 68

---

## MVP Scope (Recommended)

**Minimum Viable Product**: Phase 1 + Phase 2 + Phase 3 (US1)

- Package setup (T001-T004)
- Core models and utilities (T005-T010)
- Approval file creation (T011-T024)

**MVP Completion Condition**: Email reasoner creates approval files in `/Pending_Approval/email/` instead of executing

---

## Acceptance Test Mapping

| AT-ID | Scenario | Covered By |
|-------|----------|------------|
| AT-01 | Create email reply approval | T017-T020, T024 |
| AT-02 | Create LinkedIn post approval | T063 |
| AT-03 | Approve email action | T029-T033, T036 |
| AT-04 | Reject LinkedIn action | T037-T040, T042 |
| AT-05 | List pending approvals | T044-T047, T051 |
| AT-06 | Prevent duplicate | T059 |
| AT-07 | Invalid frontmatter | T061 |
