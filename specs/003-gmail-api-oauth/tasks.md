# Tasks: Gmail API Migration (Phase 1)

**Input**: Design documents from `/specs/003-gmail-api-oauth/` and `/phase-1/spec.md`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete)
**Branch**: `003-gmail-api-oauth`
**Constitution**: v2.0.0

**Tests**: Manual acceptance tests only (6 tests defined in spec). No automated unit tests requested.

**Organization**: Tasks grouped by user story mapped from spec's acceptance tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and package structure

- [ ] T001 Create `src/gmail_watcher/` directory structure
- [ ] T002 Create package init file at `src/gmail_watcher/__init__.py` with version
- [ ] T003 [P] Create empty module stubs: `auth.py`, `watcher.py`, `writer.py`, `state.py`
- [ ] T004 [P] Create `secrets/gmail/` directory (outside vault, add to .gitignore)
- [ ] T005 [P] Create `.watcher-state/` directory (outside vault, add to .gitignore)
- [ ] T006 Verify package is importable: `python -c "import gmail_watcher"`

**Checkpoint**: Package structure ready, all module files exist (empty stubs)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Fix malformed `[project.scripts]` section in `pyproject.toml`
- [ ] T008 Add Gmail API dependencies to `pyproject.toml`: google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib
- [ ] T009 Run `pip install -e .` to install updated dependencies
- [ ] T010 [P] Create `src/gmail_watcher/models.py` with EmailMessage and Attachment dataclasses per data-model.md
- [ ] T011 [P] Create `src/gmail_watcher/config.py` with SentinelConfig dataclass for CLI args and env vars
- [ ] T012 Verify existing `sentinel.logger` module is importable for logging integration

**Checkpoint**: Foundation ready - dependencies installed, base models defined

---

## Phase 3: User Story 1 - OAuth Authentication (Priority: P1) MVP

**Goal**: User can authenticate with Gmail via OAuth 2.0 and store token securely

**Independent Test**: Run `gmail-watcher --auth`, complete OAuth flow in browser, verify `secrets/gmail/token.json` exists with chmod 600

### Implementation for User Story 1

- [ ] T013 [US1] Implement `load_credentials()` in `src/gmail_watcher/auth.py` to load token from file
- [ ] T014 [US1] Implement `run_oauth_flow()` in `src/gmail_watcher/auth.py` using InstalledAppFlow
- [ ] T015 [US1] Implement `save_token()` in `src/gmail_watcher/auth.py` with chmod 600 permission
- [ ] T016 [US1] Implement `refresh_if_expired()` in `src/gmail_watcher/auth.py` for auto-refresh
- [ ] T017 [US1] Create CLI skeleton in `src/gmail_watcher/__main__.py` with argparse and `main()` function
- [ ] T018 [US1] Implement `--auth` flag handler in `__main__.py` that runs OAuth flow
- [ ] T019 [US1] Add error handling for missing `credentials.json` with actionable message
- [ ] T020 [US1] Manual test: Run `python -m gmail_watcher --auth` and verify token creation

**Checkpoint**: OAuth authentication works end-to-end. Token stored securely.

---

## Phase 4: User Story 2 - Email Capture (Priority: P1) MVP

**Goal**: Unread emails are fetched from Gmail API and written as Markdown files

**Independent Test**: Run `gmail-watcher --once`, verify `.md` files created in `/Inbox/email/` with correct frontmatter

### Implementation for User Story 2

- [ ] T021 [US2] Implement `build_service()` in `src/gmail_watcher/watcher.py` to create Gmail API service
- [ ] T022 [US2] Implement `fetch_unread_messages()` in `src/gmail_watcher/watcher.py` using messages.list + messages.get
- [ ] T023 [US2] Implement `get_header()` helper in `src/gmail_watcher/watcher.py` for header extraction
- [ ] T024 [US2] Implement `get_message_body()` in `src/gmail_watcher/watcher.py` with recursive multipart handling
- [ ] T025 [US2] Implement `get_attachments()` in `src/gmail_watcher/watcher.py` for attachment metadata
- [ ] T026 [US2] Implement `parse_message()` in `src/gmail_watcher/watcher.py` to convert API response to EmailMessage
- [ ] T027 [P] [US2] Implement `generate_filename()` in `src/gmail_watcher/writer.py` with timestamp+slug pattern
- [ ] T028 [P] [US2] Implement `generate_frontmatter()` in `src/gmail_watcher/writer.py` per spec Section 3
- [ ] T029 [US2] Implement `generate_body()` in `src/gmail_watcher/writer.py` with email template
- [ ] T030 [US2] Implement `write_email_file()` in `src/gmail_watcher/writer.py` combining frontmatter + body
- [ ] T031 [US2] Implement `--once` flag handler in `__main__.py` that polls once and exits
- [ ] T032 [US2] Integrate watcher with auth in `__main__.py`: load credentials → build service → fetch → write
- [ ] T033 [US2] Manual test: Run `python -m gmail_watcher --once --vault-path <VAULT>` and verify file creation

**Checkpoint**: Email capture works. Single poll creates Markdown files in vault.

---

## Phase 5: User Story 3 - Deduplication (Priority: P2)

**Goal**: Previously captured emails are skipped on subsequent polls

**Independent Test**: Run watcher twice with same unread email, verify no duplicate file created

### Implementation for User Story 3

- [ ] T034 [US3] Implement `load_state()` in `src/gmail_watcher/state.py` to load or create empty JSON
- [ ] T035 [US3] Implement `save_state()` in `src/gmail_watcher/state.py` to persist to disk
- [ ] T036 [US3] Implement `is_captured()` in `src/gmail_watcher/state.py` to check if message_id exists
- [ ] T037 [US3] Implement `mark_captured()` in `src/gmail_watcher/state.py` to add message_id with timestamp
- [ ] T038 [US3] Integrate state with poll loop in `__main__.py`: load state → filter duplicates → save state
- [ ] T039 [US3] Add CLI output showing "Skipped N already captured" when duplicates detected
- [ ] T040 [US3] Manual test: Run watcher twice, verify no duplicate files and state file contains message IDs

**Checkpoint**: Deduplication works. State persists across restarts.

---

## Phase 6: User Story 4 - Dry-Run Mode (Priority: P2)

**Goal**: Preview which emails would be captured without writing files or updating state

**Independent Test**: Run `gmail-watcher --once --dry-run`, verify no files created, state unchanged

### Implementation for User Story 4

- [ ] T041 [US4] Add `--dry-run` flag to argparse in `__main__.py`
- [ ] T042 [US4] Modify `write_email_file()` in `writer.py` to accept `dry_run` parameter and skip write
- [ ] T043 [US4] Modify state save logic to skip when `dry_run=True`
- [ ] T044 [US4] Add CLI output "Would capture: <subject>" in dry-run mode
- [ ] T045 [US4] Manual test: Run with `--dry-run`, verify no vault changes and no state updates

**Checkpoint**: Dry-run mode works. No side effects when flag is set.

---

## Phase 7: User Story 5 - Urgent Email Routing (Priority: P2)

**Goal**: Starred/important emails route to `/Needs_Action/email/` instead of `/Inbox/email/`

**Independent Test**: Star an email in Gmail, run watcher, verify file in `/Needs_Action/email/` with `urgency: urgent`

### Implementation for User Story 5

- [ ] T046 [US5] Add `is_starred` and `is_important` detection in `parse_message()` from labelIds
- [ ] T047 [US5] Implement `determine_destination()` in `writer.py` to return Needs_Action or Inbox path
- [ ] T048 [US5] Update `generate_frontmatter()` to include `starred`, `important`, and computed `urgency` fields
- [ ] T049 [US5] Integrate `determine_destination()` into `write_email_file()` for routing
- [ ] T050 [US5] Manual test: Star an unread email, run watcher, verify routing to Needs_Action

**Checkpoint**: Urgency routing works. Starred/important emails go to Needs_Action.

---

## Phase 8: User Story 6 - Error Recovery (Priority: P3)

**Goal**: Transient errors trigger retry with backoff; failures are logged with actionable messages

**Independent Test**: Corrupt token.json, run watcher, verify error logged to `/Logs/` with fix instructions

### Implementation for User Story 6

- [ ] T051 [US6] Implement `poll_with_retry()` in `__main__.py` with 3 retries and exponential backoff
- [ ] T052 [US6] Add transient error detection (network timeout, rate limit 429)
- [ ] T053 [US6] Integrate `sentinel.logger.write_log_entry()` for error logging to `/Logs/`
- [ ] T054 [US6] Add actionable error messages per spec: auth failure → run --auth, network → check connection
- [ ] T055 [US6] Manual test: Corrupt token.json, run watcher, verify log entry with actionable message

**Checkpoint**: Error recovery works. Ralph Wiggum Loop implemented.

---

## Phase 9: CLI Completion & Poll Loop

**Purpose**: Complete CLI with all flags and continuous polling

- [ ] T056 Add `--vault-path` flag with VAULT_PATH env var fallback in `__main__.py`
- [ ] T057 Add `--credentials`, `--token`, `--state` path flags in `__main__.py`
- [ ] T058 Add `--interval` flag with 120s default and 60s minimum validation in `__main__.py`
- [ ] T059 Add `--version` flag displaying version from `__init__.py`
- [ ] T060 Implement `run_poll_loop()` in `__main__.py` with interval sleep between polls
- [ ] T061 Add graceful shutdown on Ctrl+C with cleanup message
- [ ] T062 Manual test: Run `python -m gmail_watcher --interval 60` and verify continuous polling

**Checkpoint**: Full CLI functional with all flags per spec Section 2.3.

---

## Phase 10: Documentation & Finalization

**Purpose**: Setup documentation and pyproject.toml entry point

- [ ] T063 [P] Create `docs/gmail-api-setup.md` with Google Cloud Console setup instructions
- [ ] T064 [P] Add OAuth credentials download steps to `docs/gmail-api-setup.md`
- [ ] T065 [P] Add environment variables documentation to `docs/gmail-api-setup.md`
- [ ] T066 [P] Add troubleshooting section to `docs/gmail-api-setup.md` for common errors
- [ ] T067 Add `gmail-watcher = "gmail_watcher.__main__:main"` to `[project.scripts]` in `pyproject.toml`
- [ ] T068 Run `pip install -e .` to register the new entry point
- [ ] T069 Verify CLI works: `gmail-watcher --version` and `gmail-watcher --help`
- [ ] T070 Run all 6 manual acceptance tests from spec Section 7

**Checkpoint**: Phase 1 complete. All acceptance tests pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3 (US1 - Auth)**: Depends on Phase 2 - MVP must start here
- **Phase 4 (US2 - Capture)**: Depends on Phase 3 (needs auth to work)
- **Phase 5 (US3 - Dedup)**: Depends on Phase 4 (needs capture to test)
- **Phase 6 (US4 - DryRun)**: Depends on Phase 4 (needs capture to modify)
- **Phase 7 (US5 - Routing)**: Depends on Phase 4 (needs capture to route)
- **Phase 8 (US6 - Errors)**: Depends on Phase 3 (needs auth to test errors)
- **Phase 9 (CLI)**: Depends on Phases 3-8 (all features must work)
- **Phase 10 (Docs)**: Depends on Phase 9 (CLI must be complete)

### User Story Dependencies

```
Phase 2 (Foundational)
       │
       ▼
Phase 3 (US1 - OAuth) ────────┐
       │                      │
       ▼                      │
Phase 4 (US2 - Capture)       │
       │                      │
       ├──────┬──────┬────────┤
       ▼      ▼      ▼        │
    US3    US4    US5         │
   (Dedup) (Dry)  (Route)     │
       │      │      │        │
       └──────┴──────┴────────┤
                              ▼
                     Phase 8 (US6 - Errors)
                              │
                              ▼
                     Phase 9 (CLI Completion)
                              │
                              ▼
                     Phase 10 (Documentation)
```

### Within Each User Story

- Core implementation before integration
- Manual test at end of each story
- Commit after each phase checkpoint

### Parallel Opportunities

- **Phase 1**: T003, T004, T005 can run in parallel
- **Phase 2**: T010, T011 can run in parallel
- **Phase 4**: T027, T028 can run in parallel
- **Phase 10**: T063, T064, T065, T066 can run in parallel
- **Phases 5, 6, 7**: Can run in parallel after Phase 4 completes (different concerns)

---

## Parallel Example: Phase 2 Foundational

```bash
# After T007 completes (fix pyproject.toml):
# Launch these in parallel:
Task: "Create EmailMessage and Attachment dataclasses in src/gmail_watcher/models.py"
Task: "Create SentinelConfig dataclass in src/gmail_watcher/config.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (OAuth)
4. Complete Phase 4: User Story 2 (Capture)
5. **STOP and VALIDATE**: Test OAuth + Capture independently
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (OAuth) → Test independently
3. Add US2 (Capture) → Test independently → **MVP Complete!**
4. Add US3 (Dedup) → Test independently
5. Add US4 (DryRun) → Test independently
6. Add US5 (Routing) → Test independently
7. Add US6 (Errors) → Test independently
8. CLI + Docs → **Phase 1 Complete!**

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1. Setup | T001-T006 (6) | Package structure |
| 2. Foundational | T007-T012 (6) | Dependencies & base models |
| 3. US1 OAuth | T013-T020 (8) | Authentication |
| 4. US2 Capture | T021-T033 (13) | Email fetching & writing |
| 5. US3 Dedup | T034-T040 (7) | Deduplication |
| 6. US4 DryRun | T041-T045 (5) | Preview mode |
| 7. US5 Routing | T046-T050 (5) | Urgency routing |
| 8. US6 Errors | T051-T055 (5) | Error recovery |
| 9. CLI | T056-T062 (7) | Full CLI |
| 10. Docs | T063-T070 (8) | Documentation |
| **Total** | **70 tasks** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable via manual acceptance tests
- Commit after each phase checkpoint
- Entry point safety: T067 (add gmail-watcher to pyproject.toml) ONLY after T017 (main() exists)
