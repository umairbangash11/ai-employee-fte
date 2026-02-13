# Tasks: Vault Sentinel

**Input**: Design documents from `/specs/001-vault-sentinel/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli-contract.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/sentinel/` and `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, package structure, and dependencies

- [x] T001 Create project directory structure: `src/sentinel/`, `tests/unit/`, `tests/integration/` per plan.md
- [x] T002 Create `pyproject.toml` with Python 3.12 requirement, `watchdog>=6.0` dependency, and `sentinel` package entry point (`python -m sentinel`)
- [x] T003 [P] Create `src/sentinel/__init__.py` with package version constant
- [x] T004 [P] Create `tests/conftest.py` with shared pytest fixtures (tmp vault directory with all 5 canonical folders)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared modules that ALL user stories depend on. MUST complete before any story begins.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Implement log entry writer in `src/sentinel/logger.py`: function `write_log_entry(logs_dir, action_type, source_path, dest_path, file_size, outcome, details)` that creates a Markdown file with YAML frontmatter in `Logs/` per data-model.md LogEntry format. Filename pattern: `YYYY-MM-DDTHH-MM-SS_<action>_<filename>.md`
- [x] T006 [P] Implement execution plan writer in `src/sentinel/planner.py`: function `write_execution_plan(approved_dir, action, source, destination, rollback, expected_outcome)` that creates a Markdown file with YAML frontmatter in `Approved/` per data-model.md ExecutionPlan format. Filename pattern: `YYYY-MM-DDTHH-MM-SS_plan_<action>_<filename>.md`
- [x] T007 Implement CLI entry point in `src/sentinel/__main__.py`: use argparse with two subcommands `init` (with `--vault-path` argument, default `.`) and `watch` (with `--vault-path` and `--poll-interval` arguments) per contracts/cli-contract.md. Wire `init` to `vault.init_vault()` and `watch` to `watcher.start_watching()`. Handle exit codes 0, 1, 2 as specified in the contract.

**Checkpoint**: Foundation ready — logger, planner, and CLI scaffolding in place.

---

## Phase 3: User Story 1 — Initialize Vault Structure (Priority: P1) MVP

**Goal**: User runs `python -m sentinel init` to create the 5 canonical folders idempotently.

**Independent Test**: Run `python -m sentinel init --vault-path /tmp/test-vault` on an empty directory, verify all 5 folders exist. Run again, verify no errors and no data loss.

### Implementation for User Story 1

- [x] T008 [US1] Implement vault initialization in `src/sentinel/vault.py`: function `init_vault(vault_path)` that creates `Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs` directories using `os.makedirs(exist_ok=True)`. Return a dict with `created` and `existing` folder lists. Raise `ValueError` if `vault_path` does not exist. Raise `PermissionError` if not writable.
- [x] T009 [US1] Implement `validate_vault(vault_path)` in `src/sentinel/vault.py`: check that all 5 canonical folders exist, return `True`/`False`. Used by `watch` command to verify initialization before starting.
- [x] T010 [US1] Wire `init` subcommand in `src/sentinel/__main__.py`: call `vault.init_vault()`, print created/existing folders to stdout per CLI contract, handle errors to stderr, set exit code 1 on failure.

**Checkpoint**: `python -m sentinel init` works end-to-end. Vault structure is ready for Sentinel.

---

## Phase 4: User Story 2 — Sentinel Watches Inbox (Priority: P2)

**Goal**: Sentinel watches `Inbox/` for new `.txt`/`.pdf` files, writes execution plan to `Approved/`, moves file to `Needs_Action/`, and logs action to `Logs/`.

**Independent Test**: Start Sentinel, drop `test.txt` into `Inbox/`, verify within 10 seconds: file in `Needs_Action/`, plan in `Approved/`, log in `Logs/`, file gone from `Inbox/`.

### Implementation for User Story 2

- [x] T011 [US2] Implement file stability checker in `src/sentinel/watcher.py`: function `wait_for_stability(filepath, timeout=30, check_interval=0.1, stable_duration=0.5)` that polls file size until unchanged for `stable_duration` seconds. Return `True` if stable, `False` on timeout or file disappearance. Per research.md R2.
- [x] T012 [US2] Implement file mover with retry logic in `src/sentinel/mover.py`: function `move_file(source_path, needs_action_dir, approved_dir, logs_dir)` that: (1) writes execution plan via `planner.write_execution_plan()`, (2) moves file via `shutil.move()`, (3) writes log via `logger.write_log_entry()`. Implement Ralph Wiggum retry loop (3 attempts with progressive simplification per plan.md D2). On final failure, log error and write failure description to `Needs_Action/` for human review.
- [x] T013 [US2] Implement watchdog event handler in `src/sentinel/watcher.py`: class `InboxHandler(FileSystemEventHandler)` with `on_created()` that filters for `.txt`/`.pdf` extensions (case-insensitive), calls `wait_for_stability()`, then delegates to `mover.move_file()`. Ignore directories and unsupported extensions.
- [x] T014 [US2] Implement `start_watching(vault_path, poll_interval)` in `src/sentinel/watcher.py`: validate vault via `vault.validate_vault()`, create watchdog `Observer` on `Inbox/` directory, register `InboxHandler`, print startup message per CLI contract, run until `KeyboardInterrupt` (SIGINT). Handle graceful shutdown.
- [x] T015 [US2] Wire `watch` subcommand in `src/sentinel/__main__.py`: call `watcher.start_watching()`, handle `KeyboardInterrupt` for clean exit (code 0), vault-not-initialized error (code 1), unrecoverable errors (code 2). Print status messages per CLI contract.

**Checkpoint**: Full Sentinel pipeline works: detect → plan → move → log. All `.txt`/`.pdf` files triaged, unsupported extensions ignored.

---

## Phase 5: User Story 3 — Handle Naming Conflicts (Priority: P3)

**Goal**: When moving a file to `Needs_Action/` and a file with the same name exists, deduplicate with incrementing `_N` suffix.

**Independent Test**: Place `report.txt` in `Needs_Action/` manually, drop another `report.txt` into `Inbox/`, verify it appears as `report_1.txt` in `Needs_Action/` with correct log entry noting the rename.

### Implementation for User Story 3

- [x] T016 [US3] Implement filename deduplication in `src/sentinel/mover.py`: function `deduplicate_filename(dest_dir, filename)` that checks if `filename` exists in `dest_dir`; if so, tries `name_1.ext`, `name_2.ext`, ... up to `_999`; if all taken, falls back to `name_<timestamp>.ext`. Return the resolved filename. Per plan.md D4.
- [x] T017 [US3] Integrate deduplication into `move_file()` in `src/sentinel/mover.py`: call `deduplicate_filename()` before `shutil.move()`, pass the resolved destination to the execution plan and log entry. Include rename details in the log entry's `details` field when a conflict was resolved.

**Checkpoint**: All three user stories functional. Naming conflicts resolved without data loss.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T018 [P] Add `--version` flag to CLI in `src/sentinel/__main__.py` printing package version from `__init__.py`
- [x] T019 [P] Validate quickstart.md end-to-end: run through all steps in `specs/001-vault-sentinel/quickstart.md` and verify outputs match
- [x] T020 Review all Markdown output files (logs, plans) for Obsidian compatibility: YAML frontmatter validity, no broken wikilinks, renders correctly in Obsidian preview

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (needs CLI scaffolding from T007)
- **US2 (Phase 4)**: Depends on Phase 2 (needs logger T005, planner T006, CLI T007) and Phase 3 (needs `validate_vault` from T009)
- **US3 (Phase 5)**: Depends on Phase 4 (extends `mover.py` from T012)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependency on other stories.
- **US2 (P2)**: Depends on US1 (`validate_vault` function). Core sentinel behavior.
- **US3 (P3)**: Depends on US2 (extends `move_file` with dedup). Naming conflict handling.

### Within Each User Story

- Foundation modules (logger, planner) before story implementation
- Vault module before watcher module
- Mover module before watcher integration
- CLI wiring as final task in each story

### Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T005 and T006 can run in parallel (logger and planner are independent)
- T008 and T009 can be developed together (same file, but logically sequential)
- T018 and T019 and T020 can run in parallel (independent concerns)

---

## Parallel Example: Phase 2

```bash
# Launch foundational modules in parallel:
Task: "Implement log entry writer in src/sentinel/logger.py"       # T005
Task: "Implement execution plan writer in src/sentinel/planner.py" # T006

# Then sequentially:
Task: "Implement CLI entry point in src/sentinel/__main__.py"      # T007 (depends on T005, T006)
```

## Parallel Example: Phase 4

```bash
# T011 must complete first (stability checker)
Task: "Implement file stability checker in src/sentinel/watcher.py"  # T011

# Then T012 can start (uses logger + planner from Phase 2):
Task: "Implement file mover with retry in src/sentinel/mover.py"    # T012

# Then T013 + T014 sequentially (both in watcher.py):
Task: "Implement watchdog event handler in src/sentinel/watcher.py"  # T013
Task: "Implement start_watching in src/sentinel/watcher.py"          # T014

# Finally wire CLI:
Task: "Wire watch subcommand in src/sentinel/__main__.py"            # T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T007)
3. Complete Phase 3: User Story 1 (T008–T010)
4. **STOP and VALIDATE**: Run `python -m sentinel init`, verify 5 folders created
5. Demo-ready: vault initialization works

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (init) → Test independently → MVP!
3. Add US2 (watch) → Test independently → Core value delivered
4. Add US3 (dedup) → Test independently → Data safety complete
5. Polish → Production-ready

---

## Silver Tier: Gmail Sentinel (added 2026-02-12)

**Purpose**: Playwright-based Gmail monitoring per Constitution Principle VI and WatcherInfrastructure skill.

- [x] T021 [P] Add `playwright>=1.40` and `python-dotenv>=1.0` to `pyproject.toml` dependencies
- [x] T022 [P] Add `.watcher-state/` to `.gitignore`
- [x] T023 Create `src/sentinels/__init__.py` package with version constant
- [x] T024 Implement `src/sentinels/gmail_watcher.py`: `GmailWatcher` class with Playwright login, unread scraping, Markdown emission with standard YAML frontmatter, hash-based deduplication via `.watcher-state/gmail.json`, Ralph Wiggum retry loop, urgency routing (`/Inbox/email/` vs `/Needs_Action/email/`), and logging to `/Logs`
- [x] T025 [P] Create `.env.example` documenting `GMAIL_EMAIL`, `GMAIL_PASSWORD`, `VAULT_PATH`, `GMAIL_POLL_INTERVAL`, `GMAIL_HEADLESS`
- [x] T026 Add `gmail-sentinel` entry point to `pyproject.toml` `[project.scripts]`
- [x] T027 Verify syntax, utility functions (`compute_email_hash`, `sanitize_filename`), Markdown output format, deduplication, and urgency routing

**Checkpoint**: Gmail Sentinel ready for end-to-end testing with a live Gmail account.

---

## Silver Tier: Logic Orchestrator (added 2026-02-12)

**Purpose**: AI-powered email triage with Anthropic Claude API and draft reply generation.

- [x] T028 [P] Add `anthropic>=0.40` to `pyproject.toml` dependencies
- [x] T029 [P] Add `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` to `.env.example`
- [x] T030 Create `src/orchestrator/__init__.py` package with version constant
- [x] T031 Implement `src/orchestrator/brain.py`: `InboxTriageHandler(FileSystemEventHandler)` with watchdog monitoring of `vault/Inbox/` (recursive), `parse_email_frontmatter()` for YAML extraction, `classify_email()` calling Claude API with Assistant persona, `write_draft_reply()` generating Obsidian-compatible draft in `Needs_Action/drafts/`, Ralph Wiggum retry loop, execution plan to `Approved/` before moves, logging to `Logs/`
- [x] T032 Add `brain` entry point to `pyproject.toml` `[project.scripts]`
- [x] T033 Verify syntax, frontmatter parsing, draft reply output, handler instantiation, and IDE diagnostics

**Checkpoint**: Logic Orchestrator ready for end-to-end testing with OpenAI API key.

---

## Silver Tier: Orchestrator SDK Swap (added 2026-02-12)

**Purpose**: Refactor Logic Orchestrator from Anthropic SDK to OpenAI SDK with gpt-4o.

- [x] T034 Replace `import anthropic` with `from openai import OpenAI` in `src/orchestrator/brain.py`
- [x] T035 Rewrite `classify_email()` to use `client.chat.completions.create()` with system/user message format
- [x] T036 Update `load_config()` to read `OPENAI_API_KEY` and `OPENAI_MODEL` (default: `gpt-4o`)
- [x] T037 Update `InboxTriageHandler.__init__` and `start_brain()` type hints and defaults
- [x] T038 [P] Replace `anthropic>=0.40` with `openai>=1.0` in `pyproject.toml`
- [x] T039 [P] Update `.env.example` with `OPENAI_API_KEY` and `OPENAI_MODEL`
- [x] T040 Verify zero Anthropic references remain, syntax valid, all utility checks pass, 0 IDE diagnostics

**Checkpoint**: Orchestrator uses OpenAI gpt-4o. All vault routing logic unchanged.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total tasks: 40 (4 setup + 3 foundational + 3 US1 + 5 US2 + 2 US3 + 3 polish + 7 Gmail + 6 Orchestrator + 7 SDK Swap)
