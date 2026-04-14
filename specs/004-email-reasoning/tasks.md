# Tasks: Email Reasoning Layer

**Input**: Design documents from `/specs/004-email-reasoning/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Unit tests included per component (requested in plan.md phases).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## User Stories (from spec.md)

| Story | Title | Priority |
|-------|-------|----------|
| US1 | Actionable Email Creates Task | P1 |
| US2 | Promotional Email Does Not Create Task | P1 |
| US3 | Multi-Step Email Creates Plan | P2 |
| US4 | Original Email Files Unchanged | P1 |
| US5 | Idempotent Processing | P2 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package structure and project initialization

- [x] T001 Create `src/email_reasoner/` package directory
- [x] T002 Create `src/email_reasoner/__init__.py` with version 0.1.0
- [x] T003 [P] Add email-reasoner entry point to pyproject.toml scripts section
- [x] T004 [P] Add dependencies (openai, pyyaml, python-frontmatter, pydantic, click, python-dotenv) to pyproject.toml
- [x] T005 [P] Update .env.example with OPENAI_API_KEY placeholder
- [x] T006 [P] Update .gitignore to exclude `.watcher-state/reasoner.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and configuration that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models

- [x] T007 [P] Create `src/email_reasoner/models.py` with EmailFile dataclass
- [x] T008 [P] Create ClassificationResult Pydantic model in `src/email_reasoner/models.py`
- [x] T009 [P] Create TaskFile dataclass in `src/email_reasoner/models.py`
- [x] T010 [P] Create PlanFile dataclass in `src/email_reasoner/models.py`
- [x] T011 [P] Create ReasonerState dataclass in `src/email_reasoner/models.py`
- [x] T012 [P] Create ProcessedEmail dataclass in `src/email_reasoner/models.py`

### Configuration

- [x] T013 Create `src/email_reasoner/config.py` with ReasonerConfig dataclass
- [x] T014 Add vault_path, dry_run, limit, state_path, verbose options to ReasonerConfig
- [x] T015 Implement config loading from environment variables (VAULT_PATH, OPENAI_API_KEY)

### Scanner Module

- [x] T016 Create `src/email_reasoner/scanner.py` module
- [x] T017 Implement `scan_inbox(inbox_path: Path) -> list[Path]` to find all .md files
- [x] T018 Implement `parse_email_file(path: Path) -> EmailFile | None` with frontmatter parsing
- [x] T019 Handle missing frontmatter gracefully (return None + log warning)
- [x] T020 Handle missing message_id (return None + log warning)
- [x] T021 Handle empty body (return EmailFile with empty body field)
- [x] T022 Implement wikilink generation method in EmailFile model

### State Management

- [x] T023 Create `src/email_reasoner/state.py` module
- [x] T024 Implement `load_state(path: Path) -> ReasonerState` (load or create new)
- [x] T025 Implement `save_state(state: ReasonerState, path: Path)` to persist JSON
- [x] T026 Implement `is_processed(state: ReasonerState, message_id: str) -> bool`
- [x] T027 Implement `mark_processed(state: ReasonerState, message_id: str, classification: str, task_file: str | None)`
- [x] T028 Create `.watcher-state/` directory if missing in state.py

### Unit Tests for Foundational

- [x] T029 [P] Create `tests/test_scanner.py` with tests for scan_inbox and parse_email_file
- [x] T030 [P] Create `tests/test_state.py` with tests for load_state, save_state, is_processed
- [x] T031 [P] Create `tests/test_models.py` with tests for model serialization/validation

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Actionable Email Creates Task (Priority: P1) 🎯 MVP

**Goal**: When an actionable email exists in Inbox, the reasoner creates a task file in /Needs_Action/tasks/

**Independent Test**: Place a job-related email in `/Inbox/email/`, run reasoner, verify task file appears in `/Needs_Action/tasks/`

### Classifier Implementation (Core for US1)

- [ ] T032 [US1] Create `src/email_reasoner/classifier.py` module
- [ ] T033 [US1] Implement OpenAI client initialization with OPENAI_API_KEY
- [ ] T034 [US1] Define SYSTEM_PROMPT constant for email classification
- [ ] T035 [US1] Define user prompt template for classification
- [ ] T036 [US1] Implement `classify_email(email: EmailFile) -> ClassificationResult`
- [ ] T037 [US1] Enable JSON mode with response_format={"type": "json_object"}
- [ ] T038 [US1] Parse LLM response to ClassificationResult Pydantic model
- [ ] T039 [US1] Implement confidence threshold check (low → informational fallback)
- [ ] T040 [US1] Implement retry with backoff per Ralph Wiggum Loop (3 attempts)
- [ ] T041 [US1] Handle API errors gracefully (fallback to informational)
- [ ] T042 [US1] Implement body truncation to 4000 tokens for long emails

### Writer Implementation (Task Generation)

- [ ] T043 [US1] Create `src/email_reasoner/writer.py` module
- [ ] T044 [US1] Implement `generate_task_filename(action: str, timestamp: datetime) -> str`
- [ ] T045 [US1] Implement `generate_task_frontmatter(email: EmailFile, result: ClassificationResult) -> str`
- [ ] T046 [US1] Implement `generate_task_body(email: EmailFile, result: ClassificationResult) -> str`
- [ ] T047 [US1] Implement `write_task_file(task: TaskFile, vault_path: Path) -> Path`
- [ ] T048 [US1] Create `/Needs_Action/tasks/` directory if missing

### Engine (Minimal for US1)

- [ ] T049 [US1] Create `src/email_reasoner/engine.py` module
- [ ] T050 [US1] Implement `ReasonerEngine` class with config injection
- [ ] T051 [US1] Implement `run()` method: scan → classify → write task for actionable
- [ ] T052 [US1] Integrate scanner, classifier, writer, state modules
- [ ] T053 [US1] Log classification decisions to console (verbose mode)

### Unit Tests for US1

- [ ] T054 [P] [US1] Create `tests/test_classifier.py` with mock OpenAI responses
- [ ] T055 [P] [US1] Create `tests/test_writer.py` with tests for task file generation

**Checkpoint**: Actionable emails now create tasks. Run AT-01 to verify.

---

## Phase 4: User Story 2 - Promotional Email Does Not Create Task (Priority: P1)

**Goal**: Promotional/marketing emails are classified but do NOT generate task files

**Independent Test**: Place a promotional email in `/Inbox/email/`, run reasoner, verify NO task file created

### Classification Enhancement

- [ ] T056 [US2] Ensure classifier correctly identifies promotional patterns in SYSTEM_PROMPT
- [ ] T057 [US2] Verify ClassificationResult.creates_task returns False for promotional
- [ ] T058 [US2] Add promotional classification examples to classifier tests

### Engine Enhancement

- [ ] T059 [US2] Update engine to skip task creation when classification != actionable
- [ ] T060 [US2] Log skipped emails with classification reason

### Tests for US2

- [ ] T061 [P] [US2] Add promotional email test case to `tests/test_classifier.py`
- [ ] T062 [P] [US2] Add integration test for promotional email in `tests/test_engine.py`

**Checkpoint**: Promotional emails classified but no task created. Run AT-02 to verify.

---

## Phase 5: User Story 3 - Multi-Step Email Creates Plan (Priority: P2)

**Goal**: Complex actionable emails with multiple steps create both task AND plan files

**Independent Test**: Place a multi-step request email, run reasoner, verify both task in `/Needs_Action/tasks/` and plan in `/Plans/`

### Writer Enhancement (Plan Generation)

- [ ] T063 [US3] Implement `generate_plan_filename(title: str, timestamp: datetime) -> str` in writer.py
- [ ] T064 [US3] Implement `generate_plan_frontmatter(email: EmailFile, result: ClassificationResult, task_path: str) -> str`
- [ ] T065 [US3] Implement `generate_plan_body(result: ClassificationResult) -> str` with checkbox steps
- [ ] T066 [US3] Implement `write_plan_file(plan: PlanFile, vault_path: Path) -> Path`
- [ ] T067 [US3] Create `/Plans/` directory if missing
- [ ] T068 [US3] Link plan to task via wikilink in related_task field

### Engine Enhancement

- [ ] T069 [US3] Update engine to check `result.is_multi_step` after classification
- [ ] T070 [US3] Call write_plan_file when is_multi_step is True
- [ ] T071 [US3] Log plan creation with step count

### Tests for US3

- [ ] T072 [P] [US3] Add multi-step classification test to `tests/test_classifier.py`
- [ ] T073 [P] [US3] Add plan generation test to `tests/test_writer.py`

**Checkpoint**: Multi-step emails create task + plan. Run AT-03 to verify.

---

## Phase 6: User Story 4 - Original Email Files Unchanged (Priority: P1)

**Goal**: The reasoning layer MUST NOT modify, move, or delete original email files

**Independent Test**: Run reasoner on emails, verify original files unchanged (same content, path, timestamp)

### Read-Only Verification

- [ ] T074 [US4] Audit scanner.py to ensure read-only operations on email files
- [ ] T075 [US4] Audit engine.py to ensure no modification/deletion of source files
- [ ] T076 [US4] Add explicit comment in engine.py documenting read-only guarantee

### Tests for US4

- [ ] T077 [P] [US4] Create integration test that checksums email files before/after reasoner run
- [ ] T078 [P] [US4] Verify file timestamps unchanged after processing

**Checkpoint**: Original emails preserved. Run AT-04 to verify.

---

## Phase 7: User Story 5 - Idempotent Processing (Priority: P2)

**Goal**: Running reasoner multiple times on same emails produces no duplicates

**Independent Test**: Run reasoner twice on same email set, verify single task file only

### State Integration

- [ ] T079 [US5] Integrate state.is_processed() check in engine before classification
- [ ] T080 [US5] Call state.mark_processed() after successful task creation
- [ ] T081 [US5] Save state after each email processed (not just at end)
- [ ] T082 [US5] Use message_id from email frontmatter as deduplication key

### Tests for US5

- [ ] T083 [P] [US5] Create integration test that runs engine twice on same emails
- [ ] T084 [P] [US5] Verify second run processes 0 emails
- [ ] T085 [P] [US5] Verify task count unchanged after second run

**Checkpoint**: Idempotent processing verified. Run AT-05 to verify.

---

## Phase 8: CLI Implementation

**Purpose**: Complete CLI with all options per spec

### CLI Entry Point

- [ ] T086 Create `src/email_reasoner/__main__.py` with Click
- [ ] T087 Add `--vault-path` option (override VAULT_PATH env)
- [ ] T088 Add `--dry-run` flag (preview classifications without file writes)
- [ ] T089 Add `--limit N` option (process at most N emails)
- [ ] T090 Add `--state` path override for reasoner.json location
- [ ] T091 Add `--verbose` flag for detailed classification output
- [ ] T092 Add `--version` flag showing version from __init__.py
- [ ] T093 Add `--help` with usage documentation
- [ ] T094 Load OPENAI_API_KEY from environment with python-dotenv
- [ ] T095 Handle missing API key with clear error message

### Dry-Run Mode

- [ ] T096 Implement dry-run in engine (classify but don't write files)
- [ ] T097 Log what would be created in dry-run mode
- [ ] T098 [P] Create test for dry-run mode in `tests/test_engine.py`

**Checkpoint**: CLI fully functional. Run `email-reasoner --help` to verify.

---

## Phase 9: Logging & Auditability

**Purpose**: Log classification decisions for auditability per Constitution

### Logging Implementation

- [ ] T099 Implement logging to `/Logs/reasoner-YYYYMMDD.log` in engine
- [ ] T100 Log timestamp, email subject, classification, confidence, action taken
- [ ] T101 Create `/Logs/` directory if missing
- [ ] T102 Use JSON lines format for machine-readable logs

---

## Phase 10: Polish & Documentation

**Purpose**: Final documentation and cleanup

- [ ] T103 [P] Create `docs/email-reasoner-setup.md` with setup guide
- [ ] T104 [P] Update `phase-2/README.md` with Implementation Complete status
- [ ] T105 [P] Create example email files in `docs/examples/` for testing
- [ ] T106 Run all acceptance tests (AT-01 through AT-06)
- [ ] T107 Code review and cleanup

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-7)**: Depend on Foundational phase completion
- **CLI (Phase 8)**: Depends on US1 minimum (can run in parallel with US2-5)
- **Logging (Phase 9)**: Depends on engine foundation (Phase 3)
- **Polish (Phase 10)**: Depends on all user stories and CLI complete

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|------------|---------------------|
| US1 (P1) | Foundational | - |
| US2 (P1) | US1 classifier | US3, US4, US5 (after classifier done) |
| US3 (P2) | US1 writer | US2, US4, US5 |
| US4 (P1) | US1 engine | US2, US3, US5 |
| US5 (P2) | US1 state integration | US2, US3, US4 |

### Critical Path

```
Setup → Foundational → US1 → CLI → Logging → Polish
                         ↘ US2 ↘
                         ↘ US3 ↘
                         ↘ US4 ↘
                         ↘ US5 ↗
```

### Parallel Opportunities

**Phase 1 (Setup)**: T003, T004, T005, T006 can run in parallel

**Phase 2 (Foundational)**: T007-T012 (all models) can run in parallel, T029-T031 (all tests) can run in parallel

**Within Each User Story**: Test tasks marked [P] can run in parallel with each other

**Across User Stories**: After US1 classifier (T042), US2-US5 can proceed in parallel

---

## Parallel Execution Examples

### Phase 2: All Models in Parallel

```
Parallel batch:
- T007: Create EmailFile dataclass
- T008: Create ClassificationResult Pydantic model
- T009: Create TaskFile dataclass
- T010: Create PlanFile dataclass
- T011: Create ReasonerState dataclass
- T012: Create ProcessedEmail dataclass
```

### User Story Tests in Parallel

```
After US1 classifier complete:
- T054: test_classifier.py (US1)
- T061: test_classifier.py promotional case (US2)
- T072: test_classifier.py multi-step case (US3)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run AT-01 - actionable email creates task
5. Commit and demo MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Test AT-01 → **MVP Complete**
3. US2 → Test AT-02 → Promotional filtering works
4. US3 → Test AT-03 → Multi-step plans work
5. US4 → Test AT-04 → Safety verified
6. US5 → Test AT-05 → Idempotency verified
7. CLI + Logging → Full feature complete
8. Polish → Release ready

---

## Task Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Setup | 6 (T001-T006) | 4 |
| Foundational | 25 (T007-T031) | 9 |
| US1 (P1) | 24 (T032-T055) | 2 |
| US2 (P1) | 7 (T056-T062) | 2 |
| US3 (P2) | 11 (T063-T073) | 2 |
| US4 (P1) | 5 (T074-T078) | 2 |
| US5 (P2) | 7 (T079-T085) | 3 |
| CLI | 13 (T086-T098) | 1 |
| Logging | 4 (T099-T102) | 0 |
| Polish | 5 (T103-T107) | 3 |
| **Total** | **107** | **28** |

---

## Acceptance Tests Mapping

| Test ID | User Story | Tasks |
|---------|------------|-------|
| AT-01 | US1 | T032-T053 |
| AT-02 | US2 | T056-T060 |
| AT-03 | US3 | T063-T071 |
| AT-04 | US4 | T074-T076 |
| AT-05 | US5 | T079-T082 |
| AT-06 | Dry-run | T088, T096-T098 |

---

## Notes

- [P] tasks = different files, no dependencies between them
- [US#] label = maps to user story for traceability
- Each user story should be independently testable
- Commit after each task or logical group
- Run acceptance test at each checkpoint before proceeding
