# Implementation Plan: Error Recovery & Process Resilience

**Branch**: `015-error-recovery-resilience` | **Date**: 2026-04-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-error-recovery-resilience/spec.md`

## Summary

Build a unified resilience layer for all 7 subsystems (gmail_watcher, whatsapp_watcher, facebook_publisher, instagram_publisher, x_publisher, briefing_generator, hitl_approval). Implements Constitution Principle V (Ralph Wiggum Loop) consistently, adds shared exception hierarchy with failure categorization, circuit breaker for external APIs, health file management for watchdog integration, and CLI commands for status monitoring and failed item recovery.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: None (pure Python, reuses existing watchdog/playwright/openai)
**Storage**: Local filesystem (JSON for health files, Markdown for logs)
**Testing**: pytest (using existing test infrastructure)
**Target Platform**: Linux (WSL2), macOS (secondary)
**Project Type**: Single project — shared module at `src/resilience/`
**Performance Goals**: Health file writes <100ms, circuit breaker checks O(1)
**Constraints**: Constitution Principle V mandates 3 retries, async sleep for non-blocking
**Scale/Scope**: 7 subsystems, moderate error rate (<10 failures/hour expected)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | PASS | All resilience operations are local filesystem |
| II. Canonical Folders | PASS | Failed items route to `Needs_Action/<source>/failed/` |
| III. Tiered Scope | PASS | This is Gold Tier work; all Silver Tier complete |
| IV. Safety-First | PASS | Execution plans written before moves per existing pattern |
| V. Ralph Wiggum Loop | PASS | Implementing uniformly across all 7 subsystems |
| VI. Silver Tier Autonomy | N/A | Not applicable to resilience layer |
| VII. Phased Development | PASS | Gold Phase 5 scope only |
| VIII. Gmail API Migration | N/A | Gmail already migrated to API |
| Audit Trail | PASS | All failures logged to `/Logs/` as structured Markdown |
| Obsidian Compat | PASS | All logs use YAML frontmatter + Markdown |
| No Secrets | PASS | No credentials in health files or logs |

**Post-design re-check**: PASS — no violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/015-error-recovery-resilience/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── cli-contract.md  # CLI interface contract
│   └── resilience-api.md # Module API contract
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── resilience/                    # NEW: Shared resilience module
│   ├── __init__.py               # Package exports
│   ├── exceptions.py             # Unified exception hierarchy (FR-001, FR-002)
│   ├── retry.py                  # Ralph Wiggum loop + decorators (FR-003)
│   ├── logger.py                 # Structured failure logging (FR-005)
│   ├── health.py                 # Health file management (FR-007)
│   ├── circuit_breaker.py        # Circuit breaker pattern (FR-009)
│   ├── exit_codes.py             # Standard exit codes (FR-007)
│   └── failed_routing.py         # Failed item wrapper + routing (FR-006)
│
├── gmail_watcher/                 # UPDATE: Add resilience integration
├── whatsapp_watcher/              # UPDATE: Add resilience integration
├── facebook_publisher/            # UPDATE: Migrate to shared retry
├── instagram_publisher/           # UPDATE: Migrate to shared retry
├── linkedin_publisher/            # UPDATE: Migrate to shared retry
├── orchestrator/                  # UPDATE: Migrate to shared retry
├── hitl_approval/                 # UPDATE: Add resilience integration
└── ...

tests/
├── unit/
│   ├── test_resilience_exceptions.py
│   ├── test_resilience_retry.py
│   ├── test_resilience_health.py
│   └── test_resilience_circuit_breaker.py
├── integration/
│   └── test_resilience_subsystems.py
└── conftest.py
```

**Structure Decision**: Single shared module at `src/resilience/` provides utilities that all subsystems import. This ensures consistent behavior and allows centralized updates.

## Design Decisions

### D1: Shared Exception Hierarchy

All subsystems inherit from `ResilienceError` base class with:
- `error_code`: ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>
- `category`: One of 8 failure categories per FR-002
- `retryable`: Boolean determined by category

**Rationale**: Enables `is_retryable(error)` check to work uniformly.
**Alternative Rejected**: Keep per-subsystem exceptions (inconsistent retry behavior).

### D2: Retry as Decorator + Function

Provide both decorator (`@retry_with_backoff`) for simple cases and function (`ralph_wiggum_loop`) for complex workflows requiring simplification fallback.

**Rationale**: Different subsystems have different complexity needs.
**Alternative Rejected**: Decorator-only (can't support simplify_fn pattern).

### D3: Health Files as JSON

Health status persisted to `.watcher-state/<subsystem>_health.json` as JSON, not Markdown.

**Rationale**: Health files are for machine consumption (watchdogs); JSON is easier to parse.
**Alternative Rejected**: Markdown (overkill for watchdog integration).

### D4: Circuit Breaker per External API

Separate circuit breaker instances for: Gmail API, OpenAI API, LinkedIn API, Facebook API, Instagram API, X API.

**Rationale**: Isolate failures — Gmail being down shouldn't affect Facebook publishing.
**Alternative Rejected**: Single global circuit (cascading false positives).

### D5: Failed Item Wrapper Format

Failed items wrapped with YAML frontmatter containing failure metadata, preserving original content below.

**Rationale**: Original content preserved for manual recovery; metadata enables recovery commands.
**Alternative Rejected**: JSON sidecar files (complicates vault structure).

## Complexity Tracking

> No violations detected — no entries needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

## Implementation Phases

### Phase 1: Core Resilience Module

Build `src/resilience/` with all utilities:
- exceptions.py
- retry.py
- logger.py
- health.py
- circuit_breaker.py
- exit_codes.py
- failed_routing.py

### Phase 2: CLI Commands

Implement `sentinel-status` and `sentinel-recover` commands per cli-contract.md.

### Phase 3: Subsystem Integration (Priority Order)

1. **gmail_watcher** — Add retry loop, health file, circuit breaker (P1)
2. **whatsapp_watcher** — Add retry loop, health file (P1)
3. **router** — Add retry loop, health file (P2)
4. **orchestrator** — Migrate to shared retry, add health file (P3)
5. **briefing_generator** — Add health file, graceful degradation (P3)
6. **hitl_approval** — Add health file, failed routing (P4)
7. **linkedin_publisher** — Migrate to shared retry (P5)
8. **facebook_publisher** — Migrate to shared retry (P5)

### Phase 4: Testing & Documentation

- Unit tests for all resilience module components
- Integration tests for subsystem retry behavior
- Update quickstart.md with real output examples

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing subsystems | Additive changes only; preserve existing APIs |
| Inconsistent adoption | Shared utilities with clear contracts |
| Health files become stale | Timestamp validation in status command |
| Retry loops overwhelm services | Exponential backoff + circuit breaker + jitter |
| Failed queue grows unbounded | Recovery command + purge capability |

## Dependencies

### Internal Dependencies
- `sentinel.logger` — existing logging infrastructure (wrap, don't replace)
- Per-subsystem exception classes — refactor to inherit from `ResilienceError`

### External Dependencies
- None (all local implementation)

### Blocking Dependencies
- All 7 target subsystems must exist and be functional

## Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| All subsystems use shared retry | Code review | 7/7 |
| Failures produce structured logs | Manual test | 100% |
| Failed items routed correctly | Manual test | 100% |
| Status shows all subsystems | CLI test | Complete output |
| Circuit breaker functional | Load test | Opens at threshold |
| Health files updated | File timestamp | <5 min freshness |
| Exit codes correct | Process test | Per schema |
| Recovery commands work | CLI test | All functional |
