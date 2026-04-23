# Tasks: Error Recovery & Process Resilience

**Input**: Design documents from `/specs/015-error-recovery-resilience/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/resilience/` for shared module, existing subsystems in `src/<subsystem>/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and resilience module structure

- [x] T001 Create resilience package directory structure: `src/resilience/` with `__init__.py`
- [x] T002 [P] Add resilience module to `pyproject.toml` as internal dependency
- [x] T003 [P] Create `.watcher-state/` directory in `.gitignore` if not already present

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core resilience infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Implement `FailureCategory` enum in `src/resilience/exceptions.py` with all 8 categories per FR-002
- [x] T005 Implement `ResilienceError` base class in `src/resilience/exceptions.py` with error_code, category, message, retryable, context, source_item, subsystem fields
- [x] T006 [P] Implement convenience exception subclasses in `src/resilience/exceptions.py`: TransientNetworkError, SessionExpiredError, RateLimitedError, CredentialsInvalidError, DataMalformedError, ResourceUnavailableError, ExternalServiceDownError, InternalError
- [x] T007 [P] Implement `is_retryable(error)` helper function in `src/resilience/exceptions.py`
- [x] T008 Implement `ExitCode` enum in `src/resilience/exit_codes.py` with SUCCESS=0, RECOVERABLE=1, CONFIGURATION=2, FATAL=3
- [x] T009 [P] Implement `exit_with_code(code, message)` function in `src/resilience/exit_codes.py`
- [x] T010 Export all public APIs in `src/resilience/__init__.py`

**Checkpoint**: Foundation ready — exception hierarchy and exit codes in place. User story implementation can now begin.

---

## Phase 3: User Story 2 — Transient Failure Auto-Recovery (Priority: P1)

**Goal**: System automatically retries transient failures with exponential backoff per Constitution Principle V.

**Independent Test**: Trigger a transient network error in any subsystem; verify 3 retries with exponential delay before failure.

### Implementation for User Story 2

- [x] T011 [US2] Implement `RetryPolicy` dataclass in `src/resilience/retry.py` with max_attempts=3, base_delay=1.0, backoff_multiplier=2.0, max_delay=30.0, jitter_range=0.5
- [x] T012 [US2] Implement `calculate_delay(attempt, policy)` function in `src/resilience/retry.py` with exponential backoff and jitter
- [x] T013 [US2] Implement `@retry_with_backoff` decorator in `src/resilience/retry.py` for synchronous functions with on_retry and on_failure callbacks
- [x] T014 [US2] Implement `@async_retry_with_backoff` decorator in `src/resilience/retry.py` for async functions using asyncio.sleep
- [x] T015 [US2] Implement `ralph_wiggum_loop(operation, simplify_fn, on_failure, policy)` function in `src/resilience/retry.py` per Constitution Principle V with 3-attempt sequence
- [x] T016 [US2] Export retry utilities in `src/resilience/__init__.py`

**Checkpoint**: Retry utilities ready. Subsystems can now use `@retry_with_backoff` or `ralph_wiggum_loop()`.

---

## Phase 4: User Story 3 — Failed Item Recovery (Priority: P1)

**Goal**: Failed items are routed to `Needs_Action/<source>/failed/` with preserved content and recovery metadata.

**Independent Test**: Simulate a final failure in gmail_watcher; verify item appears in `Needs_Action/email/failed/` with wrapper frontmatter.

### Implementation for User Story 3

- [x] T017 [US3] Implement `FailedItemWrapper` dataclass in `src/resilience/failed_routing.py` with failure_at, failure_reason, original_path, retry_attempts, recovery_action, original_content, original_frontmatter fields
- [x] T018 [US3] Implement `FailedItemWrapper.to_markdown()` method generating wrapped Markdown with YAML frontmatter preserving original content
- [x] T019 [US3] Implement `FailedItemWrapper.from_markdown(path)` class method to parse wrapped failed items
- [x] T020 [US3] Implement `route_to_failed_queue(source_item, subsystem, failure_reason, retry_attempts, recovery_action, vault_path)` function in `src/resilience/failed_routing.py` that creates wrapper and moves to `Needs_Action/<source>/failed/`
- [x] T021 [US3] Implement `get_failed_items(vault_path, subsystem=None)` function in `src/resilience/failed_routing.py` that lists all failed items with parsed metadata
- [x] T022 [US3] Export failed routing utilities in `src/resilience/__init__.py`

**Checkpoint**: Failed item routing ready. Subsystems can now route failures to recovery queue.

---

## Phase 5: User Story 6 — Structured Failure Analysis (Priority: P3)

**Goal**: All failures produce structured log entries in `vault/Logs/` with consistent schema.

**Independent Test**: Trigger any failure; verify log file in `Logs/` with correct YAML frontmatter and error code format.

### Implementation for User Story 6

- [x] T023 [US6] Implement `write_failure_log()` function in `src/resilience/logger.py` per FR-005 schema: log_id, timestamp, action_type, subsystem, failure_category, error_code, retry_count, is_final_failure, source_item, error_message, stack_trace, context, action_taken
- [x] T024 [US6] Implement Markdown output format with YAML frontmatter, Failure Details section, Stack Trace section (if applicable), Context section
- [x] T025 [US6] Implement filename pattern `YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md` in `src/resilience/logger.py`
- [x] T026 [US6] Export failure logging utilities in `src/resilience/__init__.py`

**Checkpoint**: Structured failure logging ready. All subsystems can now produce consistent failure logs.

---

## Phase 6: User Story 4 — Process Watchdog Integration (Priority: P2)

**Goal**: Subsystems maintain health files and use standard exit codes for external watchdog integration.

**Independent Test**: Start gmail_watcher; verify `.watcher-state/gmail_watcher_health.json` exists and updates every poll cycle.

### Implementation for User Story 4

- [x] T027 [US4] Implement `HealthState` enum in `src/resilience/health.py` with HEALTHY, DEGRADED, UNHEALTHY values
- [x] T028 [US4] Implement `HealthStatus` dataclass in `src/resilience/health.py` with subsystem, status, last_heartbeat, last_success, consecutive_failures, degradation_reason, circuit_state, version fields
- [x] T029 [US4] Implement `HealthStatus.to_json()` and `HealthStatus.from_json()` serialization methods
- [x] T030 [US4] Implement `HealthStatus.is_stale(max_age_seconds=300)` method
- [x] T031 [US4] Implement `HealthManager` class in `src/resilience/health.py` with `record_success()`, `record_failure(reason)`, `heartbeat()`, `get_status()` methods
- [x] T032 [US4] Implement health file persistence to `.watcher-state/<subsystem>_health.json` in HealthManager
- [x] T033 [US4] Export health management utilities in `src/resilience/__init__.py`

**Checkpoint**: Health management ready. Subsystems can now maintain health files for watchdog integration.

---

## Phase 7: User Story 5 — Circuit Breaker Protection (Priority: P2)

**Goal**: External API calls are protected by circuit breaker pattern to prevent cascading failures.

**Independent Test**: Trigger 5 consecutive failures on Gmail API; verify circuit opens and subsequent calls fail fast.

### Implementation for User Story 5

- [x] T034 [US5] Implement `CircuitState` enum in `src/resilience/circuit_breaker.py` with CLOSED, OPEN, HALF_OPEN values (or import from health.py)
- [x] T035 [US5] Implement `CircuitBreaker` dataclass in `src/resilience/circuit_breaker.py` with name, failure_threshold=5, failure_rate_threshold=0.5, failure_window_seconds=60, recovery_timeout_seconds=30, success_threshold=3
- [x] T036 [US5] Implement `CircuitBreaker.state` property with automatic OPEN→HALF_OPEN transition after recovery_timeout_seconds
- [x] T037 [US5] Implement `CircuitBreaker.can_execute()`, `record_success()`, `record_failure()` methods
- [x] T038 [US5] Implement `CircuitBreaker.execute(operation)` method with circuit breaker protection
- [x] T039 [US5] Implement `CircuitOpenError` exception class in `src/resilience/circuit_breaker.py`
- [x] T040 [US5] Export circuit breaker utilities in `src/resilience/__init__.py`

**Checkpoint**: Circuit breaker ready. Subsystems can now protect external API calls.

---

## Phase 8: User Story 1 — Operator Diagnoses Failure (Priority: P1)

**Goal**: Operator can view aggregate health status of all subsystems via `sentinel-status` command.

**Independent Test**: Run `sentinel-status`; verify table output shows all 7 subsystems with correct status.

### Implementation for User Story 1

- [x] T041 [US1] Create `src/resilience/cli/__init__.py` package for CLI commands
- [x] T042 [US1] Implement `sentinel-status` command in `src/resilience/cli/status.py` with argparse: `--json` flag, `--subsystem` filter
- [x] T043 [US1] Implement `read_all_health_files(state_dir)` function in `src/resilience/cli/status.py` that reads all `*_health.json` files
- [x] T044 [US1] Implement `compute_aggregate_status(health_statuses)` function returning HEALTHY, DEGRADED, or UNHEALTHY based on worst subsystem
- [x] T045 [US1] Implement table output format per cli-contract.md with columns: Subsystem, Status, Last Success, Failures, Circuit
- [x] T046 [US1] Implement JSON output format per cli-contract.md when `--json` flag is passed
- [x] T047 [US1] Implement exit codes: 0=all healthy, 1=some degraded, 2=some unhealthy
- [x] T048 [US1] Add `sentinel-status` entry point to `pyproject.toml` `[project.scripts]`

**Checkpoint**: sentinel-status command ready. Operators can now diagnose system health.

---

## Phase 9: CLI Recovery Commands

**Goal**: Operator can manage failed items via `sentinel-recover` command.

**Independent Test**: Run `sentinel-recover list`; verify table shows failed items from all subsystems.

### Implementation

- [x] T049 Implement `sentinel-recover` command in `src/resilience/cli/recover.py` with subcommands: list, retry, retry-all, purge
- [x] T050 Implement `list` subcommand in `src/resilience/cli/recover.py`: scan `Needs_Action/*/failed/` directories, parse wrapper frontmatter, display table with Path, Subsystem, Failed At, Reason columns
- [x] T051 Implement `--subsystem` and `--since` filters for `list` subcommand
- [x] T052 Implement `--json` output option for `list` subcommand
- [x] T053 Implement `retry` subcommand in `src/resilience/cli/recover.py`: parse wrapper, extract original content, move to original location, delete wrapper, log recovery
- [x] T054 Implement `--force` flag for `retry` subcommand to retry non-retryable items
- [x] T055 Implement `retry-all` subcommand in `src/resilience/cli/recover.py` with `--subsystem` (required), `--force`, `--dry-run` options
- [x] T056 Implement `purge` subcommand in `src/resilience/cli/recover.py` with `--older-than` (required), `--subsystem`, `--dry-run`, `--yes` options
- [x] T057 Implement backup creation before purge to `.watcher-state/purge-backup-<date>.tar.gz`
- [x] T058 Add `sentinel-recover` entry point to `pyproject.toml` `[project.scripts]`

**Checkpoint**: Recovery commands ready. Operators can list, retry, and purge failed items.

---

## Phase 10: Subsystem Integration — Critical Path (P1)

**Goal**: Integrate resilience module into gmail_watcher and whatsapp_watcher (highest priority per research.md gap analysis).

**Independent Test**: Start gmail_watcher with network issues; verify retry, health file updates, and failure routing.

### gmail_watcher Integration

- [x] T059 [P] Import resilience module in `src/gmail_watcher/__init__.py`
- [x] T060 Add `HealthManager` initialization in `src/gmail_watcher/watcher.py` for gmail_watcher subsystem
- [x] T061 Wrap Gmail API poll loop with `ralph_wiggum_loop()` in `src/gmail_watcher/watcher.py`
- [x] T062 Add `health.record_success()` and `health.record_failure()` calls in poll loop
- [x] T063 Add `health.heartbeat()` call at end of each poll cycle
- [x] T064 Add `CircuitBreaker` for Gmail API calls in `src/gmail_watcher/watcher.py`
- [x] T065 Route failed emails to `Needs_Action/email/failed/` using `route_to_failed_queue()` after final failure
- [x] T066 Replace existing error handling with `ResilienceError` subclasses in `src/gmail_watcher/`
- [x] T067 Add `--health-file` and `--log-dir` CLI flags to gmail_watcher `__main__.py`
- [x] T068 Standardize exit codes in gmail_watcher using `exit_with_code()`

### whatsapp_watcher Integration

- [x] T069 [P] Import resilience module in `src/whatsapp_watcher/__init__.py`
- [x] T070 Add `HealthManager` initialization in `src/whatsapp_watcher/watcher.py` for whatsapp_watcher subsystem
- [x] T071 Wrap WhatsApp poll loop with `ralph_wiggum_loop()` in `src/whatsapp_watcher/watcher.py`
- [x] T072 Add `health.record_success()` and `health.record_failure()` calls in poll loop
- [x] T073 Add `health.heartbeat()` call at end of each poll cycle
- [x] T074 Route failed messages to `Needs_Action/whatsapp/failed/` using `route_to_failed_queue()`
- [x] T075 Replace existing error handling with `ResilienceError` subclasses in `src/whatsapp_watcher/`
- [x] T076 Add `--health-file` and `--log-dir` CLI flags to whatsapp_watcher `__main__.py`
- [x] T077 Standardize exit codes in whatsapp_watcher using `exit_with_code()`

**Checkpoint**: Critical watchers integrated. gmail_watcher and whatsapp_watcher now have full resilience.

---

## Phase 11: Subsystem Integration — Secondary (P2)

**Goal**: Integrate resilience module into router, orchestrator, and briefing_generator.

### router Integration

- [x] T078 [P] Import resilience module in `src/router/__init__.py`
- [x] T079 Add `HealthManager` initialization in `src/router/router.py`
- [x] T080 Wrap file routing operations with `ralph_wiggum_loop()` in `src/router/router.py`
- [x] T081 Add health file updates in router operations
- [x] T082 Standardize exit codes in router using `exit_with_code()`

### orchestrator Integration

- [x] T083 [P] Import resilience module in `src/orchestrator/__init__.py`
- [x] T084 Migrate existing Ralph Wiggum loop in `src/orchestrator/brain.py` to use shared `ralph_wiggum_loop()`
- [x] T085 Add `HealthManager` initialization in `src/orchestrator/brain.py`
- [x] T086 Add `CircuitBreaker` for OpenAI API calls in `src/orchestrator/brain.py`
- [x] T087 Add health file updates in orchestrator operations
- [x] T088 Route failed email triage to `Needs_Action/email/failed/` using `route_to_failed_queue()`
- [x] T089 Standardize exit codes in orchestrator using `exit_with_code()`

### briefing_generator Integration

- [~] T090 [P] Import resilience module in `src/briefing_generator/__init__.py` (if exists) — N/A: source files absent from repo (only .pyc in __pycache__)
- [~] T091 Add `HealthManager` initialization in briefing_generator — N/A (see T090)
- [~] T092 Implement graceful degradation: partial briefing with "Data unavailable" sections when data sources fail — N/A (see T090)
- [~] T093 Add health file updates after each generation — N/A (see T090)
- [~] T094 Standardize exit codes using `exit_with_code()` — N/A (see T090)

**Checkpoint**: Secondary subsystems integrated.

---

## Phase 12: Subsystem Integration — Publishers (P3)

**Goal**: Migrate publishers to shared resilience module (already have retry logic, just need standardization).

### hitl_approval Integration

- [x] T095 [P] Import resilience module in `src/hitl_approval/__init__.py`
- [x] T096 Add `HealthManager` initialization in `src/hitl_approval/watcher.py`
- [x] T097 Route invalid approvals to `Needs_Action/approvals/invalid/` using `route_to_failed_queue()`
- [x] T098 Add health file updates in approval operations
- [x] T099 Standardize exit codes using `exit_with_code()`

### linkedin_publisher Migration

- [x] T100 [P] Migrate `src/linkedin_publisher/executor.py` retry logic to use `@async_retry_with_backoff` from resilience module
- [x] T101 Migrate `src/linkedin_publisher/exceptions.py` to inherit from `ResilienceError`
- [x] T102 Add `HealthManager` initialization in linkedin_publisher
- [x] T103 Add `CircuitBreaker` for LinkedIn API calls
- [x] T104 Add health file updates in publish operations
- [x] T105 Standardize exit codes using `exit_with_code()`

### facebook_publisher Migration

- [x] T106 [P] Migrate `src/facebook_publisher/executor.py` retry logic to use `@async_retry_with_backoff` from resilience module
- [x] T107 Migrate `src/facebook_publisher/exceptions.py` to inherit from `ResilienceError`
- [x] T108 Add `HealthManager` initialization in facebook_publisher
- [x] T109 Add `CircuitBreaker` for Facebook API calls
- [x] T110 Add health file updates in publish operations
- [x] T111 Standardize exit codes using `exit_with_code()`

**Checkpoint**: All publishers migrated to shared resilience module.

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple subsystems

- [x] T112 [P] Add `--version` flag to `sentinel-status` and `sentinel-recover` commands
- [x] T113 [P] Verify all subsystem health files exist in `.watcher-state/` after startup
- [x] T114 Run quickstart.md validation: verify all commands and outputs match documentation — all CLI commands executed (read-only/`--dry-run` subset) and all three code examples logically verified against real API signatures; three doc drifts fixed: `--older-than 30d` → `30`, `HealthManager("gmail_watcher")` → `HealthManager("gmail_watcher", state_dir=Path(".watcher-state"))`, and `write_failure_log(logs_dir=..., failure_category=..., error_code=..., error_message=...)` → real positional/kwargs form. Credential-gated commands are user-supervised per CLAUDE.md blast-radius policy; CLI surfaces/flags/outputs all verified present.
- [x] T115 Verify structured failure log format in `Logs/` matches FR-005 schema
- [x] T116 Verify all 7 subsystems report correct status via `sentinel-status`
- [x] T117 End-to-end test: simulate failure cascade, verify circuit breakers open, items routed to failed queue, status shows degraded

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US2 Retry (Phase 3)**: Depends on Phase 2 (needs exceptions)
- **US3 Failed Routing (Phase 4)**: Depends on Phase 2 (needs exceptions)
- **US6 Logging (Phase 5)**: Depends on Phase 2 (needs exceptions)
- **US4 Health (Phase 6)**: Depends on Phase 2 (needs exit codes)
- **US5 Circuit Breaker (Phase 7)**: Depends on Phase 2 and Phase 6 (needs HealthState)
- **US1 Status CLI (Phase 8)**: Depends on Phase 6 (needs HealthManager)
- **Recovery CLI (Phase 9)**: Depends on Phase 4 (needs FailedItemWrapper)
- **Critical Integration (Phase 10)**: Depends on Phases 3, 4, 5, 6, 7 (all core utilities)
- **Secondary Integration (Phase 11)**: Depends on Phase 10 (after critical path proven)
- **Publisher Integration (Phase 12)**: Depends on Phase 11 (lowest priority)
- **Polish (Phase 13)**: Depends on all previous phases

### User Story Dependencies

- **US2 (Retry)**: Foundation only — can start after Phase 2
- **US3 (Failed Routing)**: Foundation only — can start after Phase 2 in parallel with US2
- **US4 (Health)**: Foundation only — can start after Phase 2 in parallel with US2/US3
- **US5 (Circuit Breaker)**: Depends on US4 (uses HealthState enum)
- **US6 (Logging)**: Foundation only — can start after Phase 2 in parallel with US2/US3/US4
- **US1 (Status CLI)**: Depends on US4 (needs health files to read)

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T006 and T007 can run in parallel (different functions, same file but independent)
- T008 and T009 can run in parallel (different functions)
- US2, US3, US4, US6 can start in parallel after Phase 2
- T059 and T069 can run in parallel (different subsystems)
- T078, T083, T090 can run in parallel (different subsystems)
- T095, T100, T106 can run in parallel (different subsystems)
- T112 and T113 can run in parallel (different concerns)

---

## Implementation Strategy

### MVP First (Core Resilience Module)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US2 Retry (core utility)
4. Complete Phase 4: US3 Failed Routing (core utility)
5. Complete Phase 6: US4 Health (enables status command)
6. Complete Phase 8: US1 Status CLI
7. **STOP and VALIDATE**: Run `sentinel-status` to verify health monitoring works
8. MVP Demo: Show health status of existing subsystems (even without full integration)

### Incremental Delivery

1. Setup + Foundational → Exception hierarchy ready
2. Add US2 + US3 + US4 + US6 → All core utilities ready
3. Add US5 → Circuit breaker ready
4. Add US1 + CLI → Operator tooling ready
5. Integrate gmail_watcher + whatsapp_watcher → Critical path complete
6. Integrate remaining subsystems → Full coverage

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US2 (Retry) + US5 (Circuit Breaker)
   - Developer B: US3 (Failed Routing) + US4 (Health)
   - Developer C: US6 (Logging) + US1 (Status CLI)
3. All developers: Integration tasks per subsystem

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total tasks: 117 (3 setup + 7 foundational + 6 US2 + 6 US3 + 4 US6 + 7 US4 + 7 US5 + 8 US1 + 10 CLI + 19 gmail/whatsapp + 17 secondary + 17 publishers + 6 polish)
