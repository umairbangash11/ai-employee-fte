# Tasks: Facebook Post Execution

**Input**: Design documents from `/specs/008-facebook-post-execution/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- All tasks include exact file paths

## User Stories Reference (from spec.md)

| ID | Title | Priority |
|----|-------|----------|
| US1 | Publish Approved Facebook Post | P1 |
| US2 | Handle Publication Failure | P1 |
| US3 | Detect Approved Files | P1 |
| US4 | CLI Manual Trigger | P2 |
| US5 | Move to Done After Success | P1 |
| US6 | One-Time Session Authentication | P1 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package structure and configuration

- [ ] T001 Create `src/facebook_publisher/` package directory structure
- [ ] T002 [P] Create `src/facebook_publisher/__init__.py` with package exports
- [ ] T003 [P] Create `src/facebook_publisher/exceptions.py` with custom exceptions (FacebookPublishError, SessionExpiredError, FrontmatterValidationError, DetectionError)
- [ ] T004 [P] Create `src/facebook_publisher/config.py` with configuration class (vault_path, timeouts, session_path, poll_interval)
- [ ] T005 Add facebook-publisher entry point to `pyproject.toml`
- [ ] T006 [P] Create `tests/unit/facebook_publisher/` directory structure
- [ ] T007 [P] Create `tests/integration/facebook_publisher/` directory structure

**Completion condition**: All directories exist, `python -c "from facebook_publisher import *"` succeeds, entry point defined in pyproject.toml.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create `src/facebook_publisher/models.py` with ApprovedPost dataclass (file_path, content, frontmatter, created_at, visibility)
- [ ] T009 [P] Create `src/facebook_publisher/models.py` with PublishResult dataclass (success, post_url, error, error_type, retry_count, timestamp)
- [ ] T010 [P] Create `src/facebook_publisher/models.py` with ExecutionState dataclass (processed_hashes, last_run, stats)
- [ ] T011 Create `src/facebook_publisher/utils.py` with ensure_directory() function to create vault directories
- [ ] T012 [P] Create `src/facebook_publisher/utils.py` with move_file() function for file movement between vault folders
- [ ] T013 [P] Create `src/facebook_publisher/utils.py` with compute_content_hash() function for SHA-256 hash (16 chars)
- [ ] T014 Create `src/facebook_publisher/selectors.py` with SELECTORS dict containing Facebook DOM selectors with fallbacks

**Completion condition**: All models importable, utils functions tested manually, selectors defined.

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 3 - Detect Approved Files (Priority: P1)

**Goal**: Detect files in `/Approved/facebook/` within 30 seconds

**Independent Test**: Place a file in `/Approved/facebook/`, verify callback is triggered within 30 seconds

### Implementation for User Story 3

- [ ] T015 [US3] Create `src/facebook_publisher/detector.py` with FacebookApprovedDetector class skeleton
- [ ] T016 [US3] Implement `scan_existing()` in detector.py — return all .md files sorted by mtime (oldest first)
- [ ] T017 [US3] Implement `_is_valid_approved_file()` in detector.py — validate path is in /Approved/facebook/ and is .md
- [ ] T018 [US3] Implement watcher mode using watchdog Observer in detector.py
- [ ] T019 [US3] Implement poll mode fallback in detector.py (30-second intervals)
- [ ] T020 [US3] Implement `start()` and `stop()` methods in detector.py
- [ ] T021 [US3] Add safety boundary check — reject files from /Pending_Approval/facebook/

**Completion condition**: `FacebookApprovedDetector` detects new .md files in /Approved/facebook/ within 30 seconds, ignores other directories.

---

## Phase 4: User Story 1 - Publish Approved Facebook Post (Priority: P1)

**Goal**: Publish approved posts to Facebook via Playwright

**Independent Test**: Place valid approved file, run executor, verify post appears on Facebook

**Depends on**: Phase 2 (models), Phase 3 (detector)

### Implementation for User Story 1

- [ ] T022 [US1] Create `src/facebook_publisher/parser.py` with parse_frontmatter() function
- [ ] T023 [US1] Implement frontmatter validation in parser.py — check required fields (type, action_type, status, target.platform, target.visibility)
- [ ] T024 [US1] Implement extract_content() in parser.py — extract from `## Content Preview` section or full body
- [ ] T025 [US1] Create `src/facebook_publisher/executor.py` with FacebookPublisher class skeleton
- [ ] T026 [US1] Implement `initialize()` in executor.py — launch browser with storage_state if exists
- [ ] T027 [US1] Implement `is_authenticated()` in executor.py — check if Facebook feed page loads
- [ ] T028 [US1] Implement `_click_new_post()` in executor.py — click "What's on your mind?" using SELECTORS
- [ ] T029 [US1] Implement `_enter_content()` in executor.py — type post content into editor
- [ ] T030 [US1] Implement `_set_visibility()` in executor.py — set public/friends/only_me
- [ ] T031 [US1] Implement `_click_post_button()` in executor.py — click Post button
- [ ] T032 [US1] Implement `_wait_for_success()` in executor.py — detect post success indicator
- [ ] T033 [US1] Implement `_extract_post_url()` in executor.py — extract Facebook post URL if possible
- [ ] T034 [US1] Implement `publish_post()` in executor.py — orchestrate full publish workflow
- [ ] T035 [US1] Implement `close()` in executor.py — save storage_state and close browser

**Completion condition**: `FacebookPublisher.publish_post()` successfully posts text to Facebook and returns PublishResult with post_url.

---

## Phase 5: User Story 2 - Handle Publication Failure (Priority: P1)

**Goal**: Preserve failed files with error metadata, implement retry logic

**Independent Test**: Simulate network failure, verify file remains in /Approved/ with error frontmatter

**Depends on**: Phase 4 (executor)

### Implementation for User Story 2

- [ ] T036 [US2] Implement `_adjust_for_retry()` in executor.py — adjust timeouts and selectors per attempt
- [ ] T037 [US2] Implement `publish_with_retry()` in executor.py — 3 attempts with Ralph Wiggum Loop
- [ ] T038 [US2] Create `src/facebook_publisher/handlers.py` with update_frontmatter_failed() function
- [ ] T039 [US2] Implement failure frontmatter update — set status=failed, last_error, last_attempt_at, retry_count
- [ ] T040 [US2] Implement file preservation logic — failed files remain in /Approved/facebook/

**Completion condition**: After 3 failed publish attempts, file remains in /Approved/facebook/ with error metadata in frontmatter.

---

## Phase 6: User Story 5 - Move to Done After Success (Priority: P1)

**Goal**: Move published files to /Done/facebook/ with updated frontmatter

**Independent Test**: After successful publish, verify file exists in /Done/ with correct frontmatter

**Depends on**: Phase 4 (executor)

### Implementation for User Story 5

- [ ] T041 [US5] Implement update_frontmatter_published() in handlers.py — set status=published, published_at, executed_by, facebook_post_url
- [ ] T042 [US5] Implement move_to_done() in handlers.py — move file from /Approved/ to /Done/facebook/
- [ ] T043 [US5] Ensure /Done/facebook/ directory is created if not exists

**Completion condition**: Successfully published files are moved to /Done/facebook/ with updated frontmatter.

---

## Phase 7: User Story 6 - One-Time Session Authentication (Priority: P1)

**Goal**: Provide headed browser auth flow for initial Facebook login

**Independent Test**: Run `facebook-publish auth`, complete login, verify session file created

**Depends on**: Phase 4 (executor)

### Implementation for User Story 6

- [ ] T044 [US6] Implement `run_auth_flow()` in executor.py — launch headed browser to facebook.com
- [ ] T045 [US6] Implement auth flow detection — wait for feed page to confirm login success
- [ ] T046 [US6] Implement session save — save storage_state to .watcher-state/facebook/storage_state.json
- [ ] T047 [US6] Implement session expiry detection — return SessionExpiredError with actionable message

**Completion condition**: `facebook-publish auth` opens headed browser, user can login, session persists for headless use.

---

## Phase 8: Audit Logging (Cross-cutting)

**Goal**: Log all publish attempts to /Logs/facebook/

**Depends on**: Phase 2 (models)

### Implementation

- [ ] T048 Create `src/facebook_publisher/logger.py` with FacebookLogger class
- [ ] T049 Implement `log_event()` in logger.py — write JSON line to daily log file
- [ ] T050 [P] Implement event types: detected, validated, publishing, published, failed, moved_to_done, moved_to_needs_action, duplicate_skipped
- [ ] T051 Implement daily rotation path logic — /Logs/facebook/facebook-YYYYMMDD.log
- [ ] T052 Ensure /Logs/facebook/ directory is created if not exists

**Completion condition**: All publish events are logged to /Logs/facebook/ as JSON lines.

---

## Phase 9: State Management (Cross-cutting)

**Goal**: Track processed files for idempotency

**Depends on**: Phase 2 (models, utils)

### Implementation

- [ ] T053 Create `src/facebook_publisher/state.py` with PublisherState class
- [ ] T054 Implement `load()` in state.py — load from .watcher-state/facebook/publisher.json
- [ ] T055 Implement `save()` in state.py — persist to .watcher-state/facebook/publisher.json
- [ ] T056 Implement `is_duplicate()` in state.py — check if content hash exists
- [ ] T057 Implement `add_hash()` in state.py — add processed hash to state
- [ ] T058 Implement `update_stats()` in state.py — increment published/failed/skipped counters

**Completion condition**: Duplicate content is detected and skipped, stats are tracked.

---

## Phase 10: User Story 4 - CLI Manual Trigger (Priority: P2)

**Goal**: CLI commands for manual control

**Independent Test**: Run CLI commands and verify expected behavior

**Depends on**: All previous phases

### Implementation for User Story 4

- [ ] T059 [US4] Create `src/facebook_publisher/__main__.py` with Click CLI group
- [ ] T060 [US4] Implement `cli()` group with --vault-path and --headless/--headed options
- [ ] T061 [US4] Implement `run` command — process all approved posts (one-shot)
- [ ] T062 [US4] Implement `watch` command — continuous monitoring mode
- [ ] T063 [US4] Implement `list` command — show pending approved posts
- [ ] T064 [US4] Implement `status` command — show last run statistics from state file
- [ ] T065 [US4] Implement `auth` command — run headed auth flow

**Completion condition**: All CLI commands work as documented: run, watch, list, status, auth.

---

## Phase 11: Integration (Orchestration)

**Goal**: Wire all components together

**Depends on**: All previous phases

### Implementation

- [ ] T066 Create process_file() function in __main__.py — orchestrate detect→parse→validate→publish→move→log
- [ ] T067 Implement invalid frontmatter handling — move to /Needs_Action/facebook/ with error
- [ ] T068 Implement duplicate detection flow — skip and log "duplicate_skipped"
- [ ] T069 Wire detector callback to process_file() in watch command
- [ ] T070 Implement graceful shutdown handling for watch command (Ctrl+C)

**Completion condition**: End-to-end flow works: file detected → parsed → published → moved → logged.

---

## Phase 12: Testing

**Goal**: Unit and integration tests

### Unit Tests

- [ ] T071 [P] Create `tests/unit/facebook_publisher/test_models.py` — test ApprovedPost, PublishResult validation
- [ ] T072 [P] Create `tests/unit/facebook_publisher/test_parser.py` — test frontmatter parsing and content extraction
- [ ] T073 [P] Create `tests/unit/facebook_publisher/test_detector.py` — test file detection and safety boundary
- [ ] T074 [P] Create `tests/unit/facebook_publisher/test_state.py` — test hash tracking and state persistence
- [ ] T075 [P] Create `tests/unit/facebook_publisher/test_logger.py` — test log event format and daily rotation
- [ ] T076 [P] Create `tests/unit/facebook_publisher/test_utils.py` — test file move and hash computation

### Integration Tests

- [ ] T077 Create `tests/integration/facebook_publisher/test_e2e.py` — test full flow with mocked Playwright
- [ ] T078 [P] Add integration test for invalid frontmatter → /Needs_Action/ flow
- [ ] T079 [P] Add integration test for duplicate detection flow
- [ ] T080 [P] Add integration test for CLI commands (run, list, status)

**Completion condition**: `pytest tests/unit/facebook_publisher tests/integration/facebook_publisher` passes.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) — BLOCKS ALL USER STORIES
    ↓
┌───────────────────────────────────────────────┐
│  Phase 3 (US3: Detect) ← Must complete first  │
│       ↓                                        │
│  Phase 4 (US1: Publish)                       │
│       ↓                                        │
│  ┌─────────────────┬─────────────────┐        │
│  │ Phase 5 (US5)   │ Phase 6 (US2)   │        │
│  │ Move to Done    │ Handle Failure  │        │
│  └─────────────────┴─────────────────┘        │
│       ↓                                        │
│  Phase 7 (US6: Auth)                          │
└───────────────────────────────────────────────┘
    ↓
Phase 8 (Logging) + Phase 9 (State) — can run in parallel
    ↓
Phase 10 (US4: CLI)
    ↓
Phase 11 (Integration)
    ↓
Phase 12 (Testing)
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US3 (Detect) | Phase 2 | Phase 2 complete |
| US1 (Publish) | US3 | Phase 3 complete |
| US2 (Failure) | US1 | Phase 4 complete |
| US5 (Done) | US1 | Phase 4 complete |
| US6 (Auth) | US1 | Phase 4 complete |
| US4 (CLI) | All P1 stories | Phase 9 complete |

### Parallel Opportunities

**Within Phase 1**:
- T002, T003, T004 can run in parallel (different files)
- T006, T007 can run in parallel

**Within Phase 2**:
- T009, T010 can run in parallel (same file but different classes)
- T012, T013 can run in parallel

**Within Phase 12**:
- All unit tests (T071-T076) can run in parallel
- Integration tests T078-T080 can run in parallel

---

## Implementation Strategy

### MVP First (Core Publishing)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US3 (Detection)
4. Complete Phase 4: US1 (Publishing)
5. Complete Phase 5: US5 (Move to Done)
6. **STOP and VALIDATE**: Test core publishing flow end-to-end
7. Continue with remaining phases

### Incremental Delivery

| Milestone | Phases | Deliverable |
|-----------|--------|-------------|
| M1: Foundation | 1-2 | Package structure, models, utils |
| M2: Detection | 3 | File detection working |
| M3: Publishing | 4-5 | Core publish + done flow |
| M4: Reliability | 6-7 | Failure handling + auth |
| M5: Observability | 8-9 | Logging + state |
| M6: CLI | 10-11 | Full CLI working |
| M7: Quality | 12 | All tests passing |

---

## Task Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| 1. Setup | 7 | 5 |
| 2. Foundational | 7 | 4 |
| 3. US3 (Detect) | 7 | 0 |
| 4. US1 (Publish) | 14 | 0 |
| 5. US2 (Failure) | 5 | 0 |
| 6. US5 (Done) | 3 | 0 |
| 7. US6 (Auth) | 4 | 0 |
| 8. Logging | 5 | 1 |
| 9. State | 6 | 0 |
| 10. US4 (CLI) | 7 | 0 |
| 11. Integration | 5 | 0 |
| 12. Testing | 10 | 9 |
| **Total** | **80** | **19** |

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [USn] label maps task to specific user story for traceability
- Commit after each completed task or logical group
- Verify each phase checkpoint before proceeding
- Tests in Phase 12 use mocked Playwright — E2E with real Facebook is manual
