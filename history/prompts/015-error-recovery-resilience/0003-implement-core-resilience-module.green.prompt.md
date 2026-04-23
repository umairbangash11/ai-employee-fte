---
id: "0003"
title: Implement Core Resilience Module
stage: green
date: 2026-04-21
surface: agent
model: claude-opus-4-5-20251101
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, exceptions, retry, circuit-breaker, health, cli]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/resilience/__init__.py
  - src/resilience/exceptions.py
  - src/resilience/exit_codes.py
  - src/resilience/retry.py
  - src/resilience/failed_routing.py
  - src/resilience/logger.py
  - src/resilience/health.py
  - src/resilience/circuit_breaker.py
  - src/resilience/cli/__init__.py
  - src/resilience/cli/status.py
  - src/resilience/cli/recover.py
  - pyproject.toml
  - specs/015-error-recovery-resilience/tasks.md
tests:
  - Manual import verification passed
  - sentinel-status CLI verified
  - sentinel-recover CLI verified
---

## Prompt

/sp.implement

Continue implementation of 015-error-recovery-resilience feature from tasks.md. Resume from Phase 3 (T011-T016) retry utilities through Phase 9 (CLI commands).

## Response snapshot

Successfully implemented the core resilience module (Phases 1-9) with the following components:

### Phase 1-2: Foundation (T001-T010)
- Created `src/resilience/` package structure
- Implemented `FailureCategory` enum with 8 failure categories
- Implemented `ResilienceError` base exception with error_code, category, message, retryable, context fields
- Created 8 convenience exception subclasses (TransientNetworkError, SessionExpiredError, etc.)
- Implemented `is_retryable()` helper function
- Implemented `ExitCode` enum (SUCCESS=0, RECOVERABLE=1, CONFIGURATION=2, FATAL=3)
- Implemented `exit_with_code()` function

### Phase 3: Retry Utilities (T011-T016)
- Implemented `RetryPolicy` dataclass with configurable backoff parameters
- Implemented `calculate_delay()` with exponential backoff and jitter
- Implemented `@retry_with_backoff` decorator for sync functions
- Implemented `@async_retry_with_backoff` decorator for async functions
- Implemented `ralph_wiggum_loop()` per Constitution Principle V (3-attempt pattern)
- Implemented `async_ralph_wiggum_loop()` async variant

### Phase 4: Failed Item Routing (T017-T022)
- Implemented `FailedItemWrapper` dataclass with to_markdown() and from_markdown() methods
- Implemented `route_to_failed_queue()` to move failed items to Needs_Action/<source>/failed/
- Implemented `get_failed_items()` to list all failed items
- Implemented `recover_failed_item()` to restore items to original location

### Phase 5: Structured Failure Logging (T023-T026)
- Implemented `FailureLogEntry` dataclass per FR-005 schema
- Implemented `write_failure_log()` with YAML frontmatter and sections
- Implemented filename pattern: YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md
- Implemented `get_failure_logs()` for log retrieval with filters

### Phase 6: Health Management (T027-T033)
- Implemented `HealthState` enum (HEALTHY, DEGRADED, UNHEALTHY)
- Implemented `CircuitState` enum (CLOSED, OPEN, HALF_OPEN)
- Implemented `HealthStatus` dataclass with JSON serialization
- Implemented `HealthManager` class with record_success(), record_failure(), heartbeat()
- Implemented health file persistence to .watcher-state/<subsystem>_health.json
- Implemented `read_all_health_files()` and `compute_aggregate_status()`

### Phase 7: Circuit Breaker (T034-T040)
- Implemented `CircuitBreaker` dataclass with configurable thresholds
- Implemented automatic OPEN → HALF_OPEN transition after recovery_timeout
- Implemented `execute()` and `execute_async()` methods
- Implemented `CircuitOpenError` exception class

### Phase 8-9: CLI Commands (T041-T058)
- Created `src/resilience/cli/` package
- Implemented `sentinel-status` command with table/JSON output and exit codes
- Implemented `sentinel-recover` command with list, retry, retry-all, purge subcommands
- Added entry points to pyproject.toml

## Outcome

- Impact: Core resilience module fully implemented (T001-T058 complete)
- Tests: Manual import verification passed, both CLI commands functional
- Files: 12 files created/modified
- Next prompts: Subsystem integration (T059-T111), end-to-end testing
- Reflection: Clean separation of concerns; each module is independently testable

## Evaluation notes (flywheel)

- Failure modes observed: None - implementation proceeded smoothly
- Graders run and results (PASS/FAIL): Manual verification PASS
- Prompt variant (if applicable): Standard /sp.implement
- Next experiment (smallest change to try): Add unit tests before subsystem integration
