# Tasks: WhatsApp Watcher — Message Ingestion

**Input**: Design documents from `/specs/007-whatsapp-watcher/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Unit and integration tests included as requested in spec.md Test Scenarios section.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Exact file paths included in descriptions

## Path Conventions

- **Single project**: `src/whatsapp_watcher/` at repository root
- **Tests**: `tests/unit/whatsapp_watcher/`, `tests/integration/whatsapp_watcher/`

---

## Phase 1: Setup (Module Skeleton)

**Purpose**: Initialize whatsapp_watcher module structure

- [ ] T001 Create module directory `src/whatsapp_watcher/` with `__init__.py`
- [ ] T002 [P] Create CLI entrypoint skeleton in `src/whatsapp_watcher/__main__.py` with argparse (--auth, --dry-run, --once flags)
- [ ] T003 [P] Create `.watcher-state/whatsapp/` directory structure and add to `.gitignore` if not present

**Completion Condition**: Module is importable via `python -m whatsapp_watcher --help` and shows available flags.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement `src/whatsapp_watcher/config.py` with WatcherConfig dataclass loading from environment (VAULT_PATH, WHATSAPP_POLL_INTERVAL, WHATSAPP_URGENCY_KEYWORDS, WHATSAPP_PAGE_TIMEOUT)
- [ ] T005 [P] Implement `src/whatsapp_watcher/models.py` with WhatsAppMessage, WhatsAppConversation, DeduplicationState, CapturedMessageFile dataclasses per data-model.md
- [ ] T006 [P] Implement `src/whatsapp_watcher/selectors.py` with Selectors class containing all WhatsApp Web DOM selectors (CHAT_LIST, CHAT_ITEM, UNREAD_BADGE, MESSAGE_TEXT, etc.)
- [ ] T007 Create test directory structure: `tests/unit/whatsapp_watcher/` and `tests/integration/whatsapp_watcher/` with `__init__.py` files

**Completion Condition**: `from whatsapp_watcher.config import load_config` and `from whatsapp_watcher.models import WhatsAppMessage` work without import errors. pytest discovers test directories.

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Headless WhatsApp Message Capture (Priority: P1) 🎯 MVP

**Goal**: Silently monitor WhatsApp Web via Playwright, capture unread messages as Markdown files to `/Inbox/whatsapp/`

**Independent Test**: Run watcher with valid session, verify messages from unread conversations appear as markdown files in `/Inbox/whatsapp/`

### Tests for User Story 1

- [ ] T008 [P] [US1] Unit test for WhatsAppMessage model validation in `tests/unit/whatsapp_watcher/test_models.py`
- [ ] T009 [P] [US1] Unit test for hash computation (deterministic SHA-256) in `tests/unit/whatsapp_watcher/test_models.py`

### Implementation for User Story 1

- [ ] T010 [US1] Implement `src/whatsapp_watcher/session.py` with `create_headless_session(session_path: Path) -> BrowserContext` function that loads storage_state.json and returns Playwright context
- [ ] T011 [US1] Implement `src/whatsapp_watcher/session.py` with `validate_session(context: BrowserContext) -> bool` function that checks for QR code vs main interface
- [ ] T012 [US1] Implement `src/whatsapp_watcher/scraper.py` with `get_unread_conversations(page: Page) -> list[dict]` function that finds conversations with unread badges
- [ ] T013 [US1] Implement `src/whatsapp_watcher/scraper.py` with `extract_messages(page: Page, chat_element) -> list[WhatsAppMessage]` function that extracts message data
- [ ] T014 [US1] Implement `src/whatsapp_watcher/writer.py` with `generate_filename(message: WhatsAppMessage) -> str` function using pattern `{YYYY-MM-DD}-{chat_slug}-{HHMMSS}.md`
- [ ] T015 [US1] Implement `src/whatsapp_watcher/writer.py` with `generate_frontmatter(message: WhatsAppMessage, captured_at: datetime) -> str` function with all 12 required YAML fields
- [ ] T016 [US1] Implement `src/whatsapp_watcher/writer.py` with `generate_body(message: WhatsAppMessage) -> str` function with header, metadata, and content sections
- [ ] T017 [US1] Implement `src/whatsapp_watcher/writer.py` with `write_message_file(message: WhatsAppMessage, vault_path: Path, dry_run: bool) -> Path | None` function that writes to `/Inbox/whatsapp/`
- [ ] T018 [US1] Wire poll loop in `src/whatsapp_watcher/__main__.py`: load session → get_unread_conversations → extract_messages → write_message_file → sleep(poll_interval)

**Completion Condition**: Running `python -m whatsapp_watcher` with valid session captures unread messages to `/Inbox/whatsapp/` as Markdown files with correct frontmatter.

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 - One-Time QR Code Authentication (Priority: P1)

**Goal**: Provide `--auth` flag to open headed browser for QR code scanning, persist session for subsequent headless operation

**Independent Test**: Delete `.watcher-state/whatsapp/`, run `--auth`, scan QR, verify session persists and subsequent polls work headlessly

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit test for session path validation in `tests/unit/whatsapp_watcher/test_session.py`

### Implementation for User Story 2

- [ ] T020 [US2] Implement `src/whatsapp_watcher/session.py` with `create_auth_session(session_path: Path, timeout: int) -> bool` function that opens headed browser, waits for QR scan, saves storage_state.json
- [ ] T021 [US2] Add auth mode handler in `src/whatsapp_watcher/__main__.py`: if --auth flag, call create_auth_session() and exit
- [ ] T022 [US2] Add session existence check in `src/whatsapp_watcher/__main__.py`: if no session file, print "No session found. Run `whatsapp-watcher --auth` first." and exit(1)

**Completion Condition**: Running `python -m whatsapp_watcher --auth` opens headed browser, QR scan persists session, subsequent `python -m whatsapp_watcher` runs headlessly.

**Checkpoint**: User Stories 1 AND 2 work independently

---

## Phase 5: User Story 3 - Urgent Message Routing (Priority: P2)

**Goal**: Route messages containing urgency keywords to `/Needs_Action/whatsapp/` instead of `/Inbox/whatsapp/`

**Independent Test**: Send "URGENT" message, trigger poll, verify message appears in `/Needs_Action/whatsapp/` with `urgency: urgent` frontmatter

### Tests for User Story 3

- [ ] T023 [P] [US3] Unit test for `is_urgent()` function (case-insensitive matching) in `tests/unit/whatsapp_watcher/test_writer.py`
- [ ] T024 [P] [US3] Unit test for `determine_destination()` routing logic in `tests/unit/whatsapp_watcher/test_writer.py`

### Implementation for User Story 3

- [ ] T025 [US3] Implement `src/whatsapp_watcher/writer.py` with `is_urgent(body: str, keywords: list[str]) -> bool` function for case-insensitive keyword matching
- [ ] T026 [US3] Implement `src/whatsapp_watcher/writer.py` with `determine_destination(message: WhatsAppMessage, vault_path: Path, keywords: list[str]) -> Path` function returning `/Inbox/whatsapp/` or `/Needs_Action/whatsapp/`
- [ ] T027 [US3] Update `write_message_file()` to use `determine_destination()` for routing
- [ ] T028 [US3] Update `generate_filename()` to include "URGENT" suffix for urgent messages

**Completion Condition**: Messages containing "URGENT", "ASAP", etc. are routed to `/Needs_Action/whatsapp/` with `urgency: urgent` in frontmatter.

**Checkpoint**: User Stories 1, 2, AND 3 work independently

---

## Phase 6: User Story 4 - Deduplication Across Restarts (Priority: P2)

**Goal**: Prevent duplicate message files using persistent hash registry

**Independent Test**: Poll once to capture message, stop watcher, restart, poll again — verify same message is not written twice

### Tests for User Story 4

- [ ] T029 [P] [US4] Unit test for `load_state()` and `save_state()` functions in `tests/unit/whatsapp_watcher/test_state.py`
- [ ] T030 [P] [US4] Unit test for `is_captured()` and `mark_captured()` functions in `tests/unit/whatsapp_watcher/test_state.py`
- [ ] T031 [P] [US4] Unit test for state file corruption recovery in `tests/unit/whatsapp_watcher/test_state.py`

### Implementation for User Story 4

- [ ] T032 [US4] Implement `src/whatsapp_watcher/state.py` with `load_state(path: Path) -> DeduplicationState` function that loads JSON or returns empty state if missing/corrupt
- [ ] T033 [US4] Implement `src/whatsapp_watcher/state.py` with `save_state(state: DeduplicationState, path: Path) -> None` function that persists state to JSON
- [ ] T034 [US4] Implement `src/whatsapp_watcher/state.py` with `is_captured(state: DeduplicationState, hash: str) -> bool` function
- [ ] T035 [US4] Implement `src/whatsapp_watcher/state.py` with `mark_captured(state: DeduplicationState, hash: str) -> None` function
- [ ] T036 [US4] Update poll loop in `__main__.py`: load_state before loop, check is_captured before write, call mark_captured after write, save_state after each cycle

**Completion Condition**: Same message polled twice results in only one file. Restart preserves dedup state.

**Checkpoint**: User Stories 1-4 work independently

---

## Phase 7: User Story 5 - Group Chat Message Capture (Priority: P2)

**Goal**: Capture messages from group chats with group name and sender in metadata

**Independent Test**: Send message in group, trigger poll, verify message has `chat_type: group` and both `sender` and `chat_name` in frontmatter

### Tests for User Story 5

- [ ] T037 [P] [US5] Unit test for `detect_chat_type()` function in `tests/unit/whatsapp_watcher/test_scraper.py`
- [ ] T038 [P] [US5] Unit test for group message filename generation (includes sender) in `tests/unit/whatsapp_watcher/test_writer.py`

### Implementation for User Story 5

- [ ] T039 [US5] Implement `src/whatsapp_watcher/scraper.py` with `detect_chat_type(page: Page) -> str` function that returns "individual" or "group"
- [ ] T040 [US5] Update `extract_messages()` to detect group chats using GROUP_ICON selector and extract MESSAGE_AUTHOR for sender
- [ ] T041 [US5] Update `generate_filename()` to include sender slug for group messages: `{date}-{chat_slug}-{sender_slug}-{time}.md`

**Completion Condition**: Group chat messages have `chat_type: group`, `chat_name` (group name), and `sender` (message author) correctly populated.

**Checkpoint**: User Stories 1-5 work independently

---

## Phase 8: User Story 6 - Error Logging with Actionable Messages (Priority: P3)

**Goal**: Log errors to vault with clear remediation steps

**Independent Test**: Corrupt session, run watcher, verify error log entry with "Run `whatsapp-watcher --auth` to re-authenticate"

### Tests for User Story 6

- [ ] T042 [P] [US6] Unit test for `get_log_path()` returning daily log path in `tests/unit/whatsapp_watcher/test_logger.py`
- [ ] T043 [P] [US6] Unit test for `log_error()` entry format in `tests/unit/whatsapp_watcher/test_logger.py`

### Implementation for User Story 6

- [ ] T044 [US6] Implement `src/whatsapp_watcher/logger.py` with `get_log_path(vault_path: Path, date: datetime) -> Path` function returning `<VAULT_PATH>/Logs/whatsapp-watcher-<YYYY-MM-DD>.md`
- [ ] T045 [US6] Implement `src/whatsapp_watcher/logger.py` with `ensure_log_file(log_path: Path) -> None` function that creates file with frontmatter if missing
- [ ] T046 [US6] Implement `src/whatsapp_watcher/logger.py` with `log_poll_start(log_path: Path, timestamp: datetime) -> None` function
- [ ] T047 [US6] Implement `src/whatsapp_watcher/logger.py` with `log_poll_result(log_path: Path, timestamp: datetime, messages_found: int, new_captures: int, duplicates_skipped: int, urgent_count: int, results: list[dict]) -> None` function
- [ ] T048 [US6] Implement `src/whatsapp_watcher/logger.py` with `log_error(log_path: Path, timestamp: datetime, error_type: str, attempt: int, message: str, action: str) -> None` function with actionable remediation
- [ ] T049 [US6] Add logging calls in `__main__.py` poll loop: log_poll_start, log_poll_result, log_error for exceptions
- [ ] T050 [US6] Implement Ralph Wiggum retry wrapper with 3-attempt escalating strategy, logging each attempt

**Completion Condition**: All poll cycles logged to daily log file. Errors include actionable messages (session expired → "Run --auth").

**Checkpoint**: All 6 User Stories work independently

---

## Phase 9: Integration Tests

**Purpose**: End-to-end validation of complete flows

- [ ] T051 [P] Integration test for end-to-end capture flow (mock Playwright) in `tests/integration/whatsapp_watcher/test_end_to_end.py`
- [ ] T052 [P] Integration test for deduplication (process same message twice → one file) in `tests/integration/whatsapp_watcher/test_end_to_end.py`
- [ ] T053 [P] Integration test for urgency routing (keyword → Needs_Action) in `tests/integration/whatsapp_watcher/test_end_to_end.py`
- [ ] T054 Integration test for session recovery (corrupt state → fresh start) in `tests/integration/whatsapp_watcher/test_end_to_end.py`

**Completion Condition**: `pytest tests/integration/whatsapp_watcher/` passes all tests.

---

## Phase 10: Polish & CLI Finalization

**Purpose**: Final CLI wiring and pyproject.toml entry

- [ ] T055 Add `whatsapp-watcher` console script entry to `pyproject.toml` under `[project.scripts]`
- [ ] T056 Add media type detection in `src/whatsapp_watcher/scraper.py` with `extract_media_info(message_element) -> tuple[bool, str | None]` function
- [ ] T057 Update `extract_messages()` to call `extract_media_info()` and populate `has_media`, `media_type` fields
- [ ] T058 Add media placeholders in `generate_body()`: "[Image attached]", "[Video attached]", "[Voice note attached]", "[Document: filename]"
- [ ] T059 Run all unit tests: `pytest tests/unit/whatsapp_watcher/ -v`
- [ ] T060 Run all integration tests: `pytest tests/integration/whatsapp_watcher/ -v`

**Completion Condition**: `whatsapp-watcher --help` works from command line. All pytest tests pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (P1): Core capture - no story dependencies
  - US2 (P1): Auth flow - no story dependencies (can run parallel with US1)
  - US3 (P2): Urgency routing - depends on US1 writer.py existing
  - US4 (P2): Deduplication - depends on US1 poll loop existing
  - US5 (P2): Group chats - depends on US1 scraper.py existing
  - US6 (P3): Logging - depends on US1 poll loop existing
- **Integration Tests (Phase 9)**: Depends on US1-US6 completion
- **Polish (Phase 10)**: Depends on all user stories and tests

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
```
T005 (models.py) | T006 (selectors.py) | T007 (test dirs)
```

**Within Phase 3 (US1)**:
```
T008 (test_models) | T009 (test hash)
```

**User Stories can run in parallel after Foundational**:
```
US1 (T010-T018) + US2 (T020-T022) can proceed simultaneously
```

**Within Phase 6 (US4)**:
```
T029 (test load/save) | T030 (test is/mark) | T031 (test corruption)
```

**Within Phase 9 (Integration)**:
```
T051 | T052 | T053 (all integration tests are independent)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Headless capture)
4. Complete Phase 4: User Story 2 (QR authentication)
5. **STOP and VALIDATE**: Test US1 + US2 independently
6. Demo ready: User can auth via QR and capture messages headlessly

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 + US2 → Test independently → **MVP Demo**
3. Add US3 (Urgency) → Test independently → Urgent routing works
4. Add US4 (Dedup) → Test independently → No duplicates
5. Add US5 (Groups) → Test independently → Groups supported
6. Add US6 (Logging) → Test independently → Full audit trail
7. Integration tests + Polish → Production ready

---

## Summary

| Phase | Task Count | User Story | Priority |
|-------|------------|------------|----------|
| Setup | 3 | — | — |
| Foundational | 4 | — | — |
| US1: Headless Capture | 11 | US1 | P1 |
| US2: QR Authentication | 4 | US2 | P1 |
| US3: Urgency Routing | 6 | US3 | P2 |
| US4: Deduplication | 8 | US4 | P2 |
| US5: Group Chats | 5 | US5 | P2 |
| US6: Error Logging | 10 | US6 | P3 |
| Integration Tests | 4 | — | — |
| Polish | 6 | — | — |
| **Total** | **61** | | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Manual hackathon test scenarios in spec.md for final validation
