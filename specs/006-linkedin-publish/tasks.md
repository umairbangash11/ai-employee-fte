# Tasks: LinkedIn Publish Execution

**Feature**: 006-linkedin-publish
**Input**: Design documents from `/specs/006-linkedin-publish/`
**Prerequisites**: spec.md (approved), plan.md (approved)
**Phase**: 4 — LinkedIn Publish Execution

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Priority | Description |
|-------|----------|-------------|
| US1 | P1 | Publish Approved LinkedIn Post |
| US2 | P1 | Handle Publication Failure |
| US3 | P1 | Detect Approved Files |
| US4 | P2 | CLI Manual Trigger |
| US5 | P1 | Move to Done After Success |

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create package structure and configure dependencies

- [ ] T001 Create `src/linkedin_publisher/` package directory structure
- [ ] T002 Create `src/linkedin_publisher/__init__.py` with package exports
- [ ] T003 [P] Add playwright, click, pyyaml to dependencies in pyproject.toml
- [ ] T004 [P] Add `linkedin-publish` CLI entry point to pyproject.toml scripts section
- [ ] T005 [P] Add `.watcher-state/linkedin/` to .gitignore

**Completion**: Package installable, entry point registered

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration & Exceptions

- [ ] T006 Create `src/linkedin_publisher/config.py` with LinkedInPublisherConfig dataclass (vault_path, session_path, headless, poll_interval)
- [ ] T007 [P] Create `src/linkedin_publisher/exceptions.py` with custom exceptions (InvalidFrontmatterError, PublishError, AuthenticationError, DuplicatePostError)

### Models

- [ ] T008 Create `src/linkedin_publisher/models.py` with ApprovedPost dataclass (file_path, content, frontmatter, created_at)
- [ ] T009 [P] Add PublishResult dataclass to `src/linkedin_publisher/models.py` (success, post_url, error, error_type, retry_count, timestamp)
- [ ] T010 [P] Add ExecutionState dataclass to `src/linkedin_publisher/models.py` (processed_hashes, last_run, total_published, total_failed)

### Utilities

- [ ] T011 Create `src/linkedin_publisher/utils.py` with ensure_directory() function (creates /Done/linkedin/, /Logs/linkedin/, /Needs_Action/linkedin/ if missing)
- [ ] T012 [P] Add move_file_to_done() function to `src/linkedin_publisher/utils.py`
- [ ] T013 [P] Add move_file_to_needs_action() function to `src/linkedin_publisher/utils.py`
- [ ] T014 [P] Add update_frontmatter() function to `src/linkedin_publisher/utils.py` (reads file, updates YAML frontmatter fields, writes back)

**Checkpoint**: Core models, config, exceptions, and utilities ready

---

## Phase 3: User Story 3 - Detect Approved Files (Priority: P1)

**Goal**: Detect files in `/Approved/linkedin/` within 30 seconds

**Independent Test**: Place file in `/Approved/linkedin/`, verify callback triggered within 30 seconds

**Why First**: Detection triggers all other stories; foundation for processing pipeline

### Parser Module

- [ ] T015 [US3] Create `src/linkedin_publisher/parser.py` with parse_approved_file() function (reads markdown file, extracts YAML frontmatter, validates required fields)
- [ ] T016 [US3] Add extract_post_content() function to `src/linkedin_publisher/parser.py` (extracts content from ## Content Preview section or full body)
- [ ] T017 [US3] Add validate_frontmatter() function to `src/linkedin_publisher/parser.py` (checks type=approval_request, action_type=publish_linkedin_post, target.platform=linkedin)

### Detector Module

- [ ] T018 [US3] Create `src/linkedin_publisher/detector.py` with LinkedInApprovedDetector class skeleton (__init__ with vault_path, mode)
- [ ] T019 [US3] Add scan_existing() method to LinkedInApprovedDetector in `src/linkedin_publisher/detector.py` (returns list of .md files sorted by mtime oldest first)
- [ ] T020 [US3] Add _is_valid_approved_file() method to LinkedInApprovedDetector in `src/linkedin_publisher/detector.py` (checks .md extension, in /Approved/linkedin/, not in /Pending_Approval/)
- [ ] T021 [US3] Add ApprovedFileHandler class to `src/linkedin_publisher/detector.py` (watchdog FileSystemEventHandler for on_created events)
- [ ] T022 [US3] Add start() method to LinkedInApprovedDetector in `src/linkedin_publisher/detector.py` (starts watchdog observer on /Approved/linkedin/)
- [ ] T023 [US3] Add stop() method to LinkedInApprovedDetector in `src/linkedin_publisher/detector.py` (stops observer gracefully)
- [ ] T024 [US3] Add poll mode support to LinkedInApprovedDetector in `src/linkedin_publisher/detector.py` (periodic directory scan fallback)

**Checkpoint**: Files in /Approved/linkedin/ are detected within 30 seconds via watcher or poll

---

## Phase 4: User Story 1 - Publish Approved LinkedIn Post (Priority: P1)

**Goal**: Publish approved posts to LinkedIn via Playwright

**Independent Test**: Place valid file in /Approved/linkedin/, run executor, verify post appears on LinkedIn

**Depends on**: US3 (detection)

### Selectors Module

- [ ] T025 [P] [US1] Create `src/linkedin_publisher/selectors.py` with SELECTORS dict (start_post_button, post_editor, post_button, post_success_indicator with fallback selectors)

### Executor Module

- [ ] T026 [US1] Create `src/linkedin_publisher/executor.py` with LinkedInPublisher class skeleton (__init__ with session_path, headless)
- [ ] T027 [US1] Add async initialize() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (launches Playwright with persistent context at .watcher-state/linkedin/session/)
- [ ] T028 [US1] Add async is_authenticated() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (navigates to linkedin.com, checks for feed presence)
- [ ] T029 [US1] Add async _click_start_post() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (clicks start post button using fallback selectors)
- [ ] T030 [US1] Add async _enter_content() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (types content into post editor)
- [ ] T031 [US1] Add async _click_post_button() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (clicks post button, waits for confirmation)
- [ ] T032 [US1] Add async _extract_post_url() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (attempts to extract new post URL from DOM)
- [ ] T033 [US1] Add async publish_post() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (orchestrates full publish flow, returns PublishResult)
- [ ] T034 [US1] Add async close() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (closes browser, saves session)

**Checkpoint**: Executor can publish text content to LinkedIn and return post URL

---

## Phase 5: User Story 2 - Handle Publication Failure (Priority: P1)

**Goal**: Preserve failed files with error metadata, support retry

**Independent Test**: Simulate network failure, verify file remains in /Approved/linkedin/ with error frontmatter

**Depends on**: US1 (executor)

### Retry Logic

- [ ] T035 [US2] Add async _adjust_for_retry() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (increases wait times, switches to fallback selectors on attempt 2-3)
- [ ] T036 [US2] Add async publish_with_retry() method to LinkedInPublisher in `src/linkedin_publisher/executor.py` (Ralph Wiggum Loop: 3 attempts with progressive simplification)

### Failure Handler

- [ ] T037 [US2] Add update_file_with_failure() function to `src/linkedin_publisher/utils.py` (updates frontmatter with status=failed, last_error, last_error_at, retry_count)
- [ ] T038 [US2] Add is_retryable_error() function to `src/linkedin_publisher/exceptions.py` (returns True for network, timeout; False for auth, invalid content)

**Checkpoint**: Failed posts remain in /Approved/linkedin/ with error metadata; unrecoverable errors move to /Needs_Action/

---

## Phase 6: User Story 5 - Move to Done After Success (Priority: P1)

**Goal**: Move published files to /Done/linkedin/, prevent re-publication

**Independent Test**: Publish post, verify file in /Done/linkedin/ with updated frontmatter

**Depends on**: US1 (executor), US2 (failure handling)

### State Module

- [ ] T039 [US5] Create `src/linkedin_publisher/state.py` with load_execution_state() function (loads from .watcher-state/linkedin/publisher.json)
- [ ] T040 [US5] Add save_execution_state() function to `src/linkedin_publisher/state.py`
- [ ] T041 [US5] Add compute_content_hash() function to `src/linkedin_publisher/state.py` (sha256 of action_type + content + source_path)
- [ ] T042 [US5] Add is_duplicate() function to `src/linkedin_publisher/state.py` (checks hash against processed_hashes)
- [ ] T043 [US5] Add add_processed_hash() function to `src/linkedin_publisher/state.py` (adds hash to state, updates total_published/total_failed)

### Success Handler

- [ ] T044 [US5] Add update_file_with_success() function to `src/linkedin_publisher/utils.py` (updates frontmatter with status=published, published_at, executed_by, linkedin_post_url, execution_log)
- [ ] T045 [US5] Add handle_publish_success() function to `src/linkedin_publisher/utils.py` (updates frontmatter, moves to /Done/linkedin/, adds hash to state)

**Checkpoint**: Published files automatically moved to /Done/linkedin/ with full audit trail

---

## Phase 7: Audit Logging (Cross-Cutting)

**Purpose**: Log all publish attempts per FR-005

### Logger Module

- [ ] T046 Create `src/linkedin_publisher/logger.py` with LinkedInLogger class skeleton (__init__ with logs_path)
- [ ] T047 Add _get_log_file() method to LinkedInLogger in `src/linkedin_publisher/logger.py` (returns /Logs/linkedin/linkedin-YYYYMMDD.log)
- [ ] T048 Add log_event() method to LinkedInLogger in `src/linkedin_publisher/logger.py` (writes JSON line with timestamp, event, file_path, details)
- [ ] T049 [P] Add log_detected() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T050 [P] Add log_publishing() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T051 [P] Add log_published() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T052 [P] Add log_failed() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T053 [P] Add log_moved_to_done() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T054 [P] Add log_moved_to_needs_action() method to LinkedInLogger in `src/linkedin_publisher/logger.py`
- [ ] T055 [P] Add log_duplicate_skipped() method to LinkedInLogger in `src/linkedin_publisher/logger.py`

**Checkpoint**: All publish lifecycle events logged to /Logs/linkedin/

---

## Phase 8: User Story 4 - CLI Manual Trigger (Priority: P2)

**Goal**: CLI for manual control of publish execution

**Independent Test**: Run `linkedin-publish list`, verify output shows pending files

**Depends on**: US3 (detection), US1 (executor), US5 (done handler)

### CLI Module

- [ ] T056 [US4] Create `src/linkedin_publisher/__main__.py` with click group (cli) and global options (--vault-path, --headless/--headed, --verbose)
- [ ] T057 [US4] Add `run` command to `src/linkedin_publisher/__main__.py` (scans /Approved/linkedin/, processes each file, displays results)
- [ ] T058 [US4] Add `list` command to `src/linkedin_publisher/__main__.py` (shows pending approved files with creation dates)
- [ ] T059 [US4] Add `status` command to `src/linkedin_publisher/__main__.py` (reads .watcher-state/linkedin/publisher.json, displays statistics)
- [ ] T060 [US4] Add `auth` command to `src/linkedin_publisher/__main__.py` (forces headed mode, navigates to LinkedIn, waits for user to complete login)
- [ ] T061 [US4] Add `watch` command to `src/linkedin_publisher/__main__.py` (starts detector, processes on callback, runs until SIGINT)

**Checkpoint**: CLI fully functional with run, list, status, auth, watch commands

---

## Phase 9: Integration & Orchestration

**Purpose**: Wire all components together

- [ ] T062 Create process_approved_file() orchestration function in `src/linkedin_publisher/executor.py` (parse → validate → check duplicate → publish → handle result → log)
- [ ] T063 Add main processing loop to `run` command in `src/linkedin_publisher/__main__.py` (scan existing → process each → summarize)
- [ ] T064 Add main processing loop to `watch` command in `src/linkedin_publisher/__main__.py` (startup scan → watch → process on callback)
- [ ] T065 Wire LinkedInLogger into all processing paths in `src/linkedin_publisher/executor.py`

**Checkpoint**: End-to-end flow functional: detect → parse → publish → move → log

---

## Phase 10: Tests

**Purpose**: Unit and integration tests

### Unit Tests

- [ ] T066 [P] Create `tests/test_linkedin_models.py` with tests for ApprovedPost, PublishResult, ExecutionState dataclasses
- [ ] T067 [P] Create `tests/test_linkedin_parser.py` with tests for parse_approved_file(), extract_post_content(), validate_frontmatter()
- [ ] T068 [P] Create `tests/test_linkedin_detector.py` with tests for scan_existing(), _is_valid_approved_file()
- [ ] T069 [P] Create `tests/test_linkedin_state.py` with tests for compute_content_hash(), is_duplicate(), load/save state
- [ ] T070 [P] Create `tests/test_linkedin_logger.py` with tests for log_event() JSON format, daily rotation path
- [ ] T071 [P] Create `tests/test_linkedin_utils.py` with tests for move_file_to_done(), move_file_to_needs_action(), update_frontmatter()

### Integration Tests

- [ ] T072 Create `tests/integration/test_linkedin_detection.py` with test for file detection within 30 seconds
- [ ] T073 [P] Create `tests/integration/test_linkedin_success_flow.py` with mocked executor testing full success path
- [ ] T074 [P] Create `tests/integration/test_linkedin_failure_flow.py` with mocked executor testing failure preservation
- [ ] T075 [P] Create `tests/integration/test_linkedin_duplicate.py` with test for duplicate content detection
- [ ] T076 Create `tests/integration/test_linkedin_cli.py` with tests for list, status, run commands

**Checkpoint**: All tests pass with >80% coverage

---

## Phase 11: Polish & Documentation

**Purpose**: Final cleanup and documentation

- [ ] T077 Add docstrings to all public functions and classes in `src/linkedin_publisher/`
- [ ] T078 Create E2E test script at `scripts/test_linkedin_e2e.sh` (manual verification checklist)
- [ ] T079 Update pyproject.toml with linkedin_publisher package metadata
- [ ] T080 Run full test suite and verify all tests pass

**Checkpoint**: Feature complete, tested, documented

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phases 3-8 (User Stories + Logging) → Phase 9-11 (Integration, Tests, Polish)
```

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|------------|----------------------|
| US3 (Detect) | Phase 2 only | - (start first) |
| US1 (Publish) | US3 | US2, US5 (after T033) |
| US2 (Failure) | US1 (T033) | US5 |
| US5 (Done) | US1 (T033) | US2 |
| US4 (CLI) | US1, US3, US5 | - (needs others first) |

### Parallel Opportunities

**Phase 2 Parallel Group**:
```
T006, T007, T008, T009, T010, T011, T012, T013, T014 (all different files)
```

**Phase 7 Logger Parallel Group**:
```
T049, T050, T051, T052, T053, T054, T055 (all log methods)
```

**Phase 10 Unit Tests Parallel Group**:
```
T066, T067, T068, T069, T070, T071 (all different test files)
```

**Phase 10 Integration Tests Parallel Group**:
```
T073, T074, T075 (independent scenarios)
```

---

## Implementation Strategy

### MVP First (Core Flow Only)

1. Phase 1: Setup (T001-T005)
2. Phase 2: Foundational (T006-T014)
3. Phase 3: Detection (T015-T024)
4. Phase 4: Executor (T025-T034)
5. Phase 5: Failure Handling (T035-T038)
6. Phase 6: Done Handler (T039-T045)
7. **VALIDATE**: Manual E2E test with real LinkedIn

### Incremental Additions

8. Phase 7: Logging (T046-T055)
9. Phase 8: CLI (T056-T061)
10. Phase 9: Integration (T062-T065)
11. Phase 10: Tests (T066-T076)
12. Phase 11: Polish (T077-T080)

---

## Task Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | T001-T005 (5) | Setup |
| 2 | T006-T014 (9) | Foundational |
| 3 | T015-T024 (10) | US3: Detection |
| 4 | T025-T034 (10) | US1: Publish |
| 5 | T035-T038 (4) | US2: Failure |
| 6 | T039-T045 (7) | US5: Done |
| 7 | T046-T055 (10) | Logging |
| 8 | T056-T061 (6) | US4: CLI |
| 9 | T062-T065 (4) | Integration |
| 10 | T066-T076 (11) | Tests |
| 11 | T077-T080 (4) | Polish |
| **Total** | **80 tasks** | |

---

## Notes

- Each task has clear completion condition (function exists, test passes, file created)
- [P] tasks can run in parallel within their phase
- Commit after each task or logical group
- Run tests after each phase completion
- Manual E2E validation after Phase 6 before proceeding

---

**End of Tasks**

**Next Step**: `/sp.implement` to execute tasks from this file
