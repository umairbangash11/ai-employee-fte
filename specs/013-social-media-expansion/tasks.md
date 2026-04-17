# Tasks: Gold Phase 3 — Social Media Expansion

**Input**: Design documents from `specs/013-social-media-expansion/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/social-drafters.md ✅

**Organization**: Tasks grouped by user story — each story is independently testable.
**Tests**: No dedicated test files requested in spec; verification steps embedded in each user story phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[US#]**: Which user story this task belongs to (traceability to spec.md)

---

## Phase 1: Setup

**Purpose**: Package scaffolding and entry-point registration. Unblocks all subsequent phases.

- [x] T001 Create `src/social_drafters/` package with empty `src/social_drafters/__init__.py` skeleton
- [x] T002 Register `instagram-executor` and `x-executor` CLI entry points in `pyproject.toml` under `[project.scripts]`

---

## Phase 2: Foundational — `social_drafters` Shared Module

**Purpose**: Shared draft-writing infrastructure required by ALL three platform publishers. **MUST complete before any user story begins.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [P] Implement slug constructor in `src/social_drafters/slugger.py` — `make_slug(platform, content) -> str` producing `<platform>-<YYYYMMDD>-<first-5-content-words>` with collision counter suffix
- [x] T004 [P] Implement frontmatter builder in `src/social_drafters/frontmatter.py` — `build_frontmatter(platform, content, dest_path, **kwargs) -> dict` producing canonical schema: `type: pending_action`, `action_type: publish_post`, `platform`, `status: awaiting_approval`, `source_path`, `dest_path`, `captured_at`, `content_preview` (first 100 chars); include `image_path` for instagram/x and `char_count` + optional `warning: exceeds_char_limit` for x
- [x] T005 Implement vault directory bootstrapper in `src/social_drafters/vault.py` — `ensure_vault_dirs(vault_path, platform) -> None` creating `Pending_Approval/<platform>/`, `Approved/<platform>/`, `Done/<platform>/`, `Needs_Action/<platform>/`; idempotent
- [x] T006 Implement `draft_post()` in `src/social_drafters/drafter.py` — `draft_post(platform, content, vault_path, **kwargs) -> Path`; validates non-empty content and valid platform; calls T003, T004, T005; writes YAML frontmatter + `## Content` body; appends counter suffix on collision; raises `ValueError` on empty content or unknown platform (depends on T003, T004, T005)
- [x] T007 Export public API in `src/social_drafters/__init__.py` — `from social_drafters.drafter import draft_post`, `from social_drafters.slugger import make_slug`, `from social_drafters.vault import ensure_vault_dirs` (depends on T003–T006)
- [x] T008 Add `src/social_drafters/__main__.py` CLI entry — `python -m social_drafters <platform> "<content>" [--image-path PATH]` that calls `draft_post()` and prints the written path; reads `VAULT_PATH` from env
- [x] T009 Update `src/facebook_publisher/parser.py` to accept both `type: approval_request` (legacy) and `type: pending_action` (new canonical) in `validate_frontmatter()`; likewise accept both `action_type: publish_facebook_post` and `action_type: publish_post` — backward-compatible dual-schema support

**Checkpoint**: `python -m social_drafters facebook "hello world"` writes a valid file to `vault/Pending_Approval/facebook/<slug>.md` with `type: pending_action`. `facebook_publisher` executor can process this file from `vault/Approved/facebook/`.

---

## Phase 3: User Story 1 — Facebook Draft-First Publishing (Priority: P1) 🎯 MVP

**Goal**: Complete Facebook draft → `Pending_Approval/facebook/` → human approval → executor publishes → `Done/facebook/` lifecycle using social_drafters + existing executor.

**Independent Test**: Run `python -m social_drafters facebook "Test post content"`. Confirm file in `vault/Pending_Approval/facebook/` with all 7 required frontmatter fields. Move file to `vault/Approved/facebook/`. Run `python -m facebook_publisher run --once`. Confirm file moves to `vault/Done/facebook/` with `status: published` and a log entry in `vault/Logs/`.

- [x] T010 [US1] Verify `social_drafters.draft_post("facebook", content, vault_path)` writes `vault/Pending_Approval/facebook/<slug>.md` with correct frontmatter: `type: pending_action`, `action_type: publish_post`, `platform: facebook`, `status: awaiting_approval`, `source_path`, `dest_path`, `captured_at`, `content_preview`
- [ ] T011 [US1] Verify `facebook_publisher` executor detects and processes a canonical-schema file from `vault/Approved/facebook/` — confirm `Done/facebook/` receives file with `status: published` and `vault/Logs/` receives a 6-field log entry
- [ ] T012 [US1] Verify failure path: block Facebook network access, run executor against `vault/Approved/facebook/` — confirm Ralph Wiggum Loop (3 retries) exhausts and file routes to `vault/Needs_Action/facebook/` with `status: failed` and `retry_count: 3`

**Checkpoint**: Full Facebook lifecycle functional end-to-end. social_drafters ↔ facebook_publisher integration confirmed.

---

## Phase 4: User Story 2 — Instagram Draft-First Publishing (Priority: P1)

**Goal**: Full `instagram_publisher` package implementing config → models → executor pattern; lifecycle from `Pending_Approval/instagram/` through `Done/instagram/`.

**Independent Test**: Run `python -m social_drafters instagram "Caption text" --image-path /path/to/img.jpg`. Confirm file in `vault/Pending_Approval/instagram/` with `image_path` in frontmatter. Move to `vault/Approved/instagram/`. Run `python -m instagram_publisher run --once`. Confirm executor publishes to Instagram and moves file to `vault/Done/instagram/` with `status: published`.

- [x] T013 [US2] Create `src/instagram_publisher/__init__.py` with package-level exports for `InstagramPublisher`, `InstagramPublisherConfig`
- [x] T014 [P] [US2] Implement `src/instagram_publisher/config.py` — `InstagramPublisherConfig` dataclass with `vault_path`, `session_path`, `headless`, `poll_interval`, `detection_mode`, `publish_timeout`, `retry_attempts`, `retry_delay`; properties for `approved_dir`, `done_dir`, `needs_action_dir`, `pending_approval_dir`, `logs_dir`, `storage_state_path`; `from_env()` classmethod reading `VAULT_PATH`, `INSTAGRAM_SESSION_PATH`, `INSTAGRAM_HEADLESS`, `INSTAGRAM_POLL_INTERVAL`, `INSTAGRAM_DETECTION_MODE`
- [x] T015 [P] [US2] Implement `src/instagram_publisher/exceptions.py` — `SessionExpiredError`, `PublishTimeoutError`, `SelectorNotFoundError`, `ImageNotFoundError`, `FrontmatterValidationError` (mirror `facebook_publisher/exceptions.py`; add `ImageNotFoundError`)
- [x] T016 [P] [US2] Implement `src/instagram_publisher/models.py` — `ApprovedPost` (adds `image_path: str | None` field), `PublishResult`, `ExecutionState` (mirror `facebook_publisher/models.py`)
- [x] T017 [P] [US2] Implement `src/instagram_publisher/utils.py` — `ensure_directory`, `read_frontmatter`, `write_frontmatter`, `move_file`, `format_timestamp` (direct mirror of `facebook_publisher/utils.py`)
- [x] T018 [US2] Implement `src/instagram_publisher/parser.py` — `parse_approved_post()` reads canonical schema (`type: pending_action`, `action_type: publish_post`, `platform: instagram`); validates `image_path` file existence if field is non-empty, raising `ImageNotFoundError`; extracts caption from `## Content` body (depends on T015, T016, T017)
- [x] T019 [US2] Implement `src/instagram_publisher/selectors.py` — `SELECTORS` dict for Instagram Web DOM elements (new post button, caption textarea, share button, confirmation), `URLS` dict (`instagram.com/`), `TIMEOUTS` dict (page_load, element_wait, post_confirm)
- [x] T020 [US2] Implement `src/instagram_publisher/handlers.py` — `update_frontmatter_published(file_path, post_url, duration_ms)` and `update_frontmatter_failed(file_path, error, error_type, retry_count)` (mirror `facebook_publisher/handlers.py`)
- [x] T021 [US2] Implement `src/instagram_publisher/state.py` — `ExecutionState` load/save to `.watcher-state/instagram/publisher.json` (mirror `facebook_publisher/state.py`)
- [x] T022 [US2] Implement `src/instagram_publisher/logger.py` — `write_log_entry(config, action_type, source_path, dest_path, outcome, details)` delegating to `sentinel.logger.write_log_entry` (mirror `facebook_publisher/logger.py`)
- [x] T023 [US2] Implement `src/instagram_publisher/executor.py` — `InstagramPublisher` class with `initialize()` loading `storage_state.json` session, `publish(post)` navigating Instagram Web via Playwright, uploading caption + image, confirming post; calls `ensure_vault_dirs` at startup; implements Ralph Wiggum Loop (3 attempts with `retry_delay` back-off); calls `handlers.update_frontmatter_published/failed`; writes log via `logger.write_log_entry` on every attempt (depends on T014–T022)
- [x] T024 [US2] Implement `src/instagram_publisher/detector.py` — `ApprovalFileHandler(FileSystemEventHandler)` watching `vault/Approved/instagram/` for `on_created`/`on_moved` events triggering `executor.publish()`; `poll_approved_dir()` fallback for poll mode (mirror `facebook_publisher/detector.py`)
- [x] T025 [US2] Implement `src/instagram_publisher/__main__.py` — `click` CLI with `auth` (headed browser → export `storage_state.json`), `run` (watchdog watch mode), `poll` (interval polling) subcommands; reads config via `InstagramPublisherConfig.from_env()` (mirror `facebook_publisher/__main__.py`)
- [x] T026 [US2] Verify end-to-end Instagram lifecycle: `draft_post("instagram", caption, vault_path, image_path="tests/fixtures/test.jpg")` → `Pending_Approval/instagram/` → move to `Approved/instagram/` → `python -m instagram_publisher run --once` → `Done/instagram/` with `status: published` + 6-field log entry in `Logs/`

**Checkpoint**: Full Instagram lifecycle functional. Image validation, Ralph Wiggum Loop, and log entry verified.

---

## Phase 5: User Story 3 — X Draft-First Publishing (Priority: P1)

**Goal**: Full `x_publisher` package; lifecycle from `Pending_Approval/x/` through `Done/x/`; `char_count` and over-280 `warning` field verified in drafter.

**Independent Test**: Run `python -m social_drafters x "Short post"`. Confirm `char_count: 10` in frontmatter, no `warning` field. Run with content >280 chars — confirm `char_count: N` and `warning: exceeds_char_limit` in frontmatter. Move to `Approved/x/`. Run `python -m x_publisher run --once`. Confirm `Done/x/` + log entry.

- [x] T027 [US3] Create `src/x_publisher/__init__.py` with package-level exports for `XPublisher`, `XPublisherConfig`
- [x] T028 [P] [US3] Implement `src/x_publisher/config.py` — `XPublisherConfig` dataclass; `from_env()` reading `VAULT_PATH`, `X_SESSION_PATH`, `X_HEADLESS`, `X_POLL_INTERVAL`, `X_DETECTION_MODE`; properties for `approved_dir`, `done_dir`, `needs_action_dir`, `pending_approval_dir`, `logs_dir`, `storage_state_path`
- [x] T029 [P] [US3] Implement `src/x_publisher/exceptions.py` — `SessionExpiredError`, `PublishTimeoutError`, `SelectorNotFoundError`, `CharLimitError`, `FrontmatterValidationError`
- [x] T030 [P] [US3] Implement `src/x_publisher/models.py` — `ApprovedPost` (with `char_count: int | None` field extracted from frontmatter), `PublishResult`, `ExecutionState`
- [x] T031 [P] [US3] Implement `src/x_publisher/utils.py` — `ensure_directory`, `read_frontmatter`, `write_frontmatter`, `move_file`, `format_timestamp` (direct mirror of `facebook_publisher/utils.py`)
- [x] T032 [US3] Implement `src/x_publisher/parser.py` — `parse_approved_post()` validates canonical schema; extracts `char_count` from frontmatter into `ApprovedPost.char_count`; logs advisory warning if `char_count > 280` but does NOT block execution (depends on T029, T030, T031)
- [x] T033 [US3] Implement `src/x_publisher/selectors.py` — `SELECTORS` dict for X Web DOM elements (compose tweet button, text area, post button, confirmation), `URLS` dict (`x.com/home`), `TIMEOUTS` dict
- [x] T034 [US3] Implement `src/x_publisher/handlers.py` — `update_frontmatter_published()` and `update_frontmatter_failed()` (mirror `facebook_publisher/handlers.py`)
- [x] T035 [US3] Implement `src/x_publisher/state.py` — `ExecutionState` load/save to `.watcher-state/x/publisher.json`
- [x] T036 [US3] Implement `src/x_publisher/logger.py` — `write_log_entry()` wrapper delegating to `sentinel.logger.write_log_entry`
- [x] T037 [US3] Implement `src/x_publisher/executor.py` — `XPublisher` class with `initialize()` loading `storage_state.json`, `publish(post)` navigating X Web, entering text, clicking Post, waiting for confirmation; calls `ensure_vault_dirs` at startup; Ralph Wiggum Loop; `handlers.update_frontmatter_published/failed`; `logger.write_log_entry` on every attempt (depends on T028–T036)
- [x] T038 [US3] Implement `src/x_publisher/detector.py` — `ApprovalFileHandler(FileSystemEventHandler)` for `vault/Approved/x/`; poll mode fallback (mirror `facebook_publisher/detector.py`)
- [x] T039 [US3] Implement `src/x_publisher/__main__.py` — `click` CLI with `auth`, `run`, `poll` subcommands; `XPublisherConfig.from_env()` (mirror `facebook_publisher/__main__.py`)
- [x] T040 [US3] Verify end-to-end X lifecycle including over-limit draft: `draft_post("x", long_content, vault_path)` → confirm `char_count: N` and `warning: exceeds_char_limit` in `Pending_Approval/x/` → edit content → move to `Approved/x/` → `python -m x_publisher run --once` → `Done/x/` + log entry

**Checkpoint**: Full X lifecycle functional. char_count field, warning field, and log entry verified.

---

## Phase 6: User Story 4 — Shared Social Post Vault Lifecycle (Priority: P2)

**Goal**: Confirm all three platforms share the canonical lifecycle schema and produce zero vault boundary violations.

**Independent Test**: Run complete draft-to-done cycle for each platform. Inspect all files at every stage. Run `vault_audit.py`. Zero violations.

- [x] T041 [US4] Verify every file produced across all three platform lifecycles contains all 7 required frontmatter fields: `type`, `platform`, `action_type`, `status`, `source_path`, `dest_path`, `captured_at` — inspect `Pending_Approval/`, `Done/`, `Needs_Action/` output files
- [ ] T042 [US4] Run `vault_audit.py` boundary scan — confirm zero violations reported across `Pending_Approval/facebook/`, `Pending_Approval/instagram/`, `Pending_Approval/x/` (SC-005)
- [x] T043 [US4] Verify `ensure_vault_dirs` bootstrapping — delete `Pending_Approval/instagram/`, `Approved/instagram/`, `Done/instagram/`, `Needs_Action/instagram/`; start `python -m instagram_publisher run --once`; confirm all 4 dirs recreated automatically without manual intervention (FR-007)

**Checkpoint**: Zero boundary violations. All lifecycle files carry complete frontmatter. Directory bootstrapping confirmed.

---

## Phase 7: User Story 5 — Publisher Architecture Consistency (Priority: P3)

**Goal**: Confirm `instagram_publisher/` and `x_publisher/` are structurally identical to `facebook_publisher/`; confirm `social_drafters` is the sole source of frontmatter logic.

**Independent Test**: `ls src/instagram_publisher/ src/x_publisher/ src/facebook_publisher/` — module counts match. Grep for inline frontmatter dicts in publisher packages — zero hits outside `social_drafters`.

- [x] T044 [US5] Verify `src/instagram_publisher/` contains all 12 modules: `__init__.py`, `__main__.py`, `config.py`, `models.py`, `executor.py`, `handlers.py`, `parser.py`, `selectors.py`, `detector.py`, `state.py`, `utils.py`, `exceptions.py`, `logger.py` (13 files — same as `facebook_publisher/`)
- [x] T045 [US5] Verify `src/x_publisher/` contains all 13 modules matching `facebook_publisher/` inventory
- [x] T046 [US5] Verify zero duplicated frontmatter construction: `grep -r "pending_action\|awaiting_approval\|captured_at" src/facebook_publisher/ src/instagram_publisher/ src/x_publisher/` — confirm no inline frontmatter dict building; all frontmatter produced exclusively by `social_drafters.frontmatter.build_frontmatter()`

**Checkpoint**: Architecture consistency confirmed. social_drafters is the sole frontmatter authority.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Credential isolation, graceful degradation, and env documentation.

- [x] T047 [P] Add Instagram and X env vars to `.env.example`: `INSTAGRAM_SESSION_PATH`, `INSTAGRAM_HEADLESS`, `INSTAGRAM_POLL_INTERVAL`, `INSTAGRAM_DETECTION_MODE`, `X_SESSION_PATH`, `X_HEADLESS`, `X_POLL_INTERVAL`, `X_DETECTION_MODE`
- [x] T048 [P] Verify `.gitignore` contains `.watcher-state/` entry — confirm Instagram and X session state cannot be committed (Constitution Principle VII, FR-009)
- [ ] T049 Verify graceful degradation: unset `INSTAGRAM_SESSION_PATH` in env, run `python -m instagram_publisher run --once` — confirm log entry with `outcome: failure` written to `vault/Logs/`; orchestrator does NOT raise uncaught exception (FR-010, SC-006)
- [ ] T050 Verify Ralph Wiggum Loop across all 3 platforms: for each platform, create an `Approved/` file and block network access; confirm after 3 retries the file routes to `Needs_Action/<platform>/` with `retry_count: 3` and `status: failed` in frontmatter (FR-005, Constitution Principle V)

**Checkpoint**: Gold Phase 3 complete. All 6 success criteria (SC-001 through SC-006) met.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user story phases**
- **Phase 3 (US1 Facebook)**: Depends on Phase 2 complete — Facebook executor already exists, only verification tasks
- **Phase 4 (US2 Instagram)**: Depends on Phase 2 complete — can run in parallel with Phase 3
- **Phase 5 (US3 X)**: Depends on Phase 2 complete — can run in parallel with Phases 3 and 4
- **Phase 6 (US4 Vault Lifecycle)**: Depends on Phases 3, 4, 5 complete
- **Phase 7 (US5 Architecture)**: Depends on Phases 4 and 5 complete — can overlap with Phase 6
- **Phase 8 (Polish)**: Depends on Phases 6 and 7 complete

### User Story Dependencies

- **US1 (Facebook, P1)**: Depends only on Foundational (Phase 2)
- **US2 (Instagram, P1)**: Depends only on Foundational (Phase 2) — independent of US1
- **US3 (X, P1)**: Depends only on Foundational (Phase 2) — independent of US1 and US2
- **US4 (Vault Lifecycle, P2)**: Depends on US1 + US2 + US3 all complete
- **US5 (Architecture, P3)**: Depends on US2 + US3 complete

### Within Each User Story

- Package scaffold (config, models, exceptions, utils) before parser and executor
- Parser before executor (executor imports parser)
- Executor before detector (detector imports executor)
- Detector before __main__ (entry point wires them)

### Parallel Opportunities

- **T003 and T004** (slugger, frontmatter): fully parallel — different files, no dependencies
- **T014, T015, T016, T017** (Instagram config, exceptions, models, utils): all parallel — no inter-deps
- **T028, T029, T030, T031** (X config, exceptions, models, utils): all parallel — no inter-deps
- **Phases 3, 4, 5** can all proceed simultaneously once Phase 2 is done
- **T047 and T048** (env.example + gitignore): parallel — different files

---

## Parallel Example: Phase 2 Foundational

```text
# Launch T003 and T004 simultaneously (different files, no deps):
Task T003: Implement src/social_drafters/slugger.py
Task T004: Implement src/social_drafters/frontmatter.py

# Then sequentially:
T005 → T006 → T007 → T008 → T009
```

## Parallel Example: User Stories 1, 2, 3

```text
# After Phase 2 completes, all three can proceed in parallel:
Thread A: Phase 3 (US1 verification tasks T010–T012)
Thread B: Phase 4 (US2 Instagram T013–T026)
Thread C: Phase 5 (US3 X T027–T040)
```

---

## Implementation Strategy

### MVP First (Facebook lifecycle only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (social_drafters + facebook parser update)
3. Complete Phase 3: US1 verification
4. **STOP and VALIDATE**: `draft_post("facebook", ...) → Approved → Done` works end-to-end
5. Proceed to Instagram and X once Facebook lifecycle is confirmed

### Incremental Delivery

1. Phase 1 + 2 → social_drafters shared module ready
2. Phase 3 → Facebook full loop confirmed (MVP)
3. Phase 4 → Instagram publisher live
4. Phase 5 → X publisher live
5. Phase 6 + 7 → Vault audit + architecture check
6. Phase 8 → Polish and env documentation

---

## Notes

- [P] tasks = different files, no mutual dependencies within the phase
- [US#] label maps task to spec.md user story for traceability
- Facebook executor reuse: `facebook_publisher/executor.py` is NOT modified — only `parser.py` gets a backward-compat update (T009)
- `social_drafters` has zero imports from publisher packages — pure write-path module
- All Playwright sessions use `storage_state.json` pattern (proven by updated `linkedin_publisher` on this branch)
- Commit after each phase checkpoint — each phase is a logical, independently releasable increment
