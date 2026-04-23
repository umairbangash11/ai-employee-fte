# Specification: Gold Phase 5 — Error Recovery / Process Resilience

**Feature Branch**: `015-error-recovery-resilience`
**Date**: 2026-04-19
**Status**: Draft
**Priority**: P1 (Core Reliability)

---

## 1. Overview

### 1.1 Context

The AI Employee system comprises multiple autonomous processes: watchers (gmail, whatsapp), publishers (facebook, instagram, x, linkedin), approval flows (hitl_approval), and reporting (briefing_generator). These processes currently lack unified error handling, structured retry logic, and graceful degradation patterns. When a process fails—due to network issues, expired sessions, missing credentials, or malformed data—the failure mode varies inconsistently across subsystems.

Constitution Principle V (Ralph Wiggum Loop) mandates retry logic with a maximum of 3 attempts before routing to `/Needs_Action`, but implementation is inconsistent. This phase creates a unified resilience layer.

### 1.2 Problem Statement

**Operator pain points:**
- Processes fail silently or crash without actionable logs
- No consistent retry behavior across subsystems
- Session expiration (Playwright, OAuth) requires manual intervention
- Failed work items are not reliably routed to recovery queues
- No watchdog mechanism to detect and restart failed processes
- Error logs lack structure, making debugging difficult

**System gaps:**
- Retry logic exists in some modules but not uniformly
- Exception hierarchies are defined per-module without shared patterns
- No circuit breaker for external API rate limiting
- No health check endpoints for process monitoring
- No aggregated failure dashboard or notification

### 1.3 Measurable Outcomes

| Outcome | Metric | Target |
|---------|--------|--------|
| Retry coverage | Subsystems with Ralph Wiggum Loop | 7/7 (100%) |
| Silent failure elimination | Failures with structured log entry | 100% |
| Recovery routing | Failed items routed to Needs_Action | 100% |
| Process restart | Processes auto-restart after transient failure | <60s recovery |
| Operator visibility | Clear failure state in status command | All subsystems |

---

## 2. Functional Requirements

### FR-001: Unified Exception Hierarchy

The system MUST define a shared exception hierarchy that all subsystems inherit from.

**Acceptance Criteria:**
- A base `ResilienceError` class is defined in a shared module
- All subsystems inherit from domain-specific subclasses
- Each exception carries: error_code, category, retryable flag, context dict
- Exception messages are operator-actionable

### FR-002: Failure Categories

The system MUST categorize failures into distinct types with associated retry policies.

**Categories:**

| Category | Description | Retryable | Example |
|----------|-------------|-----------|---------|
| `TRANSIENT_NETWORK` | Network timeout, DNS failure | Yes (exponential backoff) | API request timeout |
| `SESSION_EXPIRED` | OAuth/browser session invalid | Yes (after re-auth) | Playwright cookie expired |
| `RATE_LIMITED` | API quota exceeded | Yes (after cooldown) | Gmail API 429 |
| `CREDENTIALS_INVALID` | Missing or bad credentials | No | VAULT_PATH not set |
| `DATA_MALFORMED` | Invalid input data | No | Bad YAML frontmatter |
| `RESOURCE_UNAVAILABLE` | File/path not found | Conditional | Vault directory missing |
| `EXTERNAL_SERVICE_DOWN` | 3rd party unavailable | Yes (with circuit breaker) | Facebook API 503 |
| `INTERNAL_ERROR` | Unexpected code exception | No | Unhandled exception |

**Acceptance Criteria:**
- Each failure is assigned exactly one category
- Retry policy is determined by category
- Category is included in all log entries

### FR-003: Ralph Wiggum Loop Implementation

The system MUST implement Constitution Principle V consistently across all subsystems.

**Retry Sequence:**
1. **Attempt 1**: Execute as planned
2. **Attempt 2**: Wait `base_delay * 2`, re-read context, retry
3. **Attempt 3**: Wait `base_delay * 4`, simplify approach, retry
4. **After 3 failures**: Log failure, route to `/Needs_Action/<source>/failed/`

**Configuration:**
- `base_delay`: 1 second (default)
- `max_retries`: 3 (fixed per constitution)
- `backoff_multiplier`: 2 (exponential)
- `jitter`: 0-500ms random (prevent thundering herd)

**Acceptance Criteria:**
- All 7 subsystems use the shared retry utility
- Retry count and delays are logged for each attempt
- Non-retryable exceptions skip retry and route immediately

### FR-004: Graceful Degradation

The system MUST degrade gracefully when dependencies fail, continuing to operate with reduced functionality.

**Degradation Scenarios:**

| Scenario | Degraded Behavior |
|----------|-------------------|
| Gmail API unavailable | Log error, skip poll cycle, retry next interval |
| WhatsApp session expired | Log warning, pause polling, emit status:degraded |
| Vault path invalid | Refuse to start, log actionable error |
| OpenAI API down | Queue items for later reasoning, log skip |
| Briefing data incomplete | Generate partial briefing with "Data unavailable" sections |
| Publisher session expired | Queue item to Needs_Action, emit re-auth required |

**Acceptance Criteria:**
- No process crashes due to single dependency failure
- Degraded state is visible in status output
- Recovery is automatic when dependency returns

### FR-005: Structured Failure Logging

The system MUST log all failures with a consistent structured schema.

**Log Entry Schema:**

```yaml
---
log_id: "<timestamp>-<action>-<slug>"
timestamp: "<ISO 8601>"
action_type: failure_record
subsystem: gmail_watcher | whatsapp_watcher | facebook_publisher | ...
failure_category: TRANSIENT_NETWORK | SESSION_EXPIRED | ...
error_code: "ERR_<SUBSYSTEM>_<CODE>"
retry_count: 0-3
is_final_failure: true | false
source_item: "<path to triggering item, if any>"
error_message: "<human-readable description>"
stack_trace: "<optional, only for INTERNAL_ERROR>"
context:
  <additional key-value pairs>
action_taken: retry | routed_to_needs_action | logged_and_continued
---
```

**Acceptance Criteria:**
- All failures produce a log entry in `vault/Logs/`
- Log files are named: `YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md`
- Stack traces are included only for unexpected exceptions

### FR-006: Failed Item Routing

The system MUST route failed work items to a recoverable location.

**Routing Rules:**

| Failure Type | Destination |
|--------------|-------------|
| Watcher item failed to parse | `Needs_Action/<source>/failed/` |
| Publisher failed after 3 retries | `Needs_Action/<platform>/failed/` |
| Approval validation failed | `Needs_Action/approvals/invalid/` |
| Briefing generation failed | `Needs_Action/briefings/failed/` |

**Failed Item Wrapper:**

When routing a failed item, the system MUST create a wrapper file with:
- Original content preserved
- Failure frontmatter added:
  ```yaml
  failure_at: "<ISO timestamp>"
  failure_reason: "<category>: <message>"
  original_path: "<where it came from>"
  retry_attempts: 3
  recovery_action: "<suggested fix>"
  ```

**Acceptance Criteria:**
- Failed items are never silently dropped
- Original content is preserved for manual recovery
- Recovery action suggestion is included when possible

### FR-007: Watchdog / Process Health

The system MUST support external watchdog monitoring via status files and exit codes.

**Health Indicators:**

Each subsystem MUST maintain a heartbeat file:
- Location: `.watcher-state/<subsystem>_health.json`
- Updated: Every poll cycle or significant operation
- Content:
  ```json
  {
    "subsystem": "gmail_watcher",
    "status": "healthy | degraded | unhealthy",
    "last_heartbeat": "<ISO timestamp>",
    "last_success": "<ISO timestamp>",
    "consecutive_failures": 0,
    "degradation_reason": null | "<description>",
    "version": "0.1.0"
  }
  ```

**Exit Codes:**

| Code | Meaning | Restart Policy |
|------|---------|----------------|
| 0 | Clean shutdown | No restart |
| 1 | Recoverable error | Restart with backoff |
| 2 | Configuration error | No restart (manual fix needed) |
| 3 | Fatal error | No restart (investigation needed) |

**Acceptance Criteria:**
- Health files are updated every poll cycle
- Exit codes follow the defined schema
- Status command reads health files to show aggregate state

### FR-008: Status Command Enhancement

The system MUST provide operator-visible failure states via status commands.

**Enhanced Status Output:**

```
System Status: DEGRADED
════════════════════════

Subsystem          Status      Last Success    Failures
─────────────────────────────────────────────────────────
gmail_watcher      healthy     2 min ago       0
whatsapp_watcher   degraded    15 min ago      3
facebook_publisher healthy     5 min ago       0
instagram_publisher unhealthy  2 hours ago     12
x_publisher        healthy     8 min ago       0
briefing_generator healthy     1 day ago       0
hitl_approval      healthy     30 sec ago      0

Degraded: whatsapp_watcher - Session expired, re-auth required
Unhealthy: instagram_publisher - API rate limited, cooldown 45 min
```

**Acceptance Criteria:**
- `sentinel-status` command shows all subsystems
- Degraded/unhealthy subsystems show reason
- Output is parseable for scripting (JSON option)

### FR-009: Circuit Breaker for External APIs

The system MUST implement circuit breaker pattern for external service calls.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Circuit tripped, requests fail fast without calling service
- **HALF-OPEN**: Testing recovery, limited requests allowed

**Thresholds:**
- Open after: 5 consecutive failures OR 50% failure rate in 60s window
- Half-open after: 30 seconds in open state
- Close after: 3 consecutive successes in half-open

**Acceptance Criteria:**
- Gmail API, OpenAI API, and publisher APIs use circuit breaker
- Circuit state is logged on transitions
- Circuit state is visible in status output

### FR-010: Recovery Queue Processing

The system SHOULD support manual or automated retry of failed items.

**Recovery Commands:**

```bash
# List failed items
sentinel-recover list [--subsystem <name>]

# Retry a specific failed item
sentinel-recover retry <file-path>

# Retry all failed items for a subsystem
sentinel-recover retry-all --subsystem <name>

# Purge old failed items (>30 days)
sentinel-recover purge --older-than 30d
```

**Acceptance Criteria:**
- Failed items can be listed with failure reason
- Retry moves item back to original queue
- Purge requires confirmation for destructive action

---

## 3. Non-Functional Requirements

### NFR-001: Performance

- Retry delays MUST NOT block the main event loop (async sleep)
- Health file writes MUST complete in <100ms
- Circuit breaker state checks MUST be O(1)

### NFR-002: Reliability

- Failure logging MUST be atomic (no partial writes)
- Health files MUST survive process restart (persisted to disk)
- Retry state MUST NOT be lost on process restart

### NFR-003: Observability

- All subsystems MUST log at DEBUG level for troubleshooting
- ERROR level logs MUST be operator-actionable
- Log rotation SHOULD be supported (configurable max log files)

### NFR-004: Security

- Stack traces MUST NOT include credentials or tokens
- Health files MUST NOT contain sensitive data
- Failed item wrappers MUST NOT expose auth secrets

---

## 4. User Stories

### US1: Operator Diagnoses Failure (P1)

**As** an operator,
**I want** clear visibility into which subsystems are failing and why,
**So that** I can take corrective action without reading code.

**Acceptance Criteria:**
- [ ] `sentinel-status` shows all subsystem health
- [ ] Degraded/unhealthy states include actionable reason
- [ ] Status is available even when processes are down (reads health files)

### US2: Transient Failure Auto-Recovery (P1)

**As** the system,
**I want** to automatically retry transient failures,
**So that** temporary network issues don't require manual intervention.

**Acceptance Criteria:**
- [ ] Network timeouts retry with exponential backoff
- [ ] Session expirations trigger re-auth attempt before retry
- [ ] Rate limits wait appropriate cooldown before retry
- [ ] Successful retry clears failure counter

### US3: Failed Item Recovery (P1)

**As** an operator,
**I want** failed items routed to a known location with context,
**So that** I can manually fix and reprocess them.

**Acceptance Criteria:**
- [ ] Failed items are in `Needs_Action/<source>/failed/`
- [ ] Wrapper includes failure reason and suggested action
- [ ] Original content is fully preserved
- [ ] `sentinel-recover list` shows failed items

### US4: Process Watchdog Integration (P2)

**As** an operator using PM2 or systemd,
**I want** processes to exit with correct codes and maintain health files,
**So that** external watchdogs can manage restart and alerting.

**Acceptance Criteria:**
- [ ] Exit codes follow defined schema
- [ ] Health files are updated every poll cycle
- [ ] Stale health files (>5 min) indicate crashed process
- [ ] PM2/systemd can restart based on exit code

### US5: Circuit Breaker Protection (P2)

**As** the system,
**I want** to stop calling failing external services,
**So that** I don't waste resources and can fail fast.

**Acceptance Criteria:**
- [ ] Circuit opens after threshold failures
- [ ] Open circuit returns error immediately
- [ ] Circuit tests recovery after cooldown
- [ ] Circuit state is logged and visible in status

### US6: Structured Failure Analysis (P3)

**As** a developer,
**I want** consistent structured failure logs,
**So that** I can analyze failure patterns and improve reliability.

**Acceptance Criteria:**
- [ ] All failures produce structured log entry
- [ ] Logs can be parsed programmatically (YAML frontmatter)
- [ ] Error codes are unique per subsystem/failure type
- [ ] Context includes relevant debugging info

---

## 5. Scope Boundaries

### In Scope

- Unified exception hierarchy and error codes
- Ralph Wiggum Loop implementation for all 7 subsystems
- Structured failure logging to `vault/Logs/`
- Failed item routing to `Needs_Action/<source>/failed/`
- Health file generation for watchdog integration
- Enhanced status command with aggregate health
- Circuit breaker for external API calls
- Recovery queue listing and retry commands
- Exit code standardization

### Out of Scope

- Cloud deployment or container orchestration (Platinum tier)
- Distributed tracing or centralized logging
- Alerting/notification system (email, Slack, etc.)
- Web dashboard for monitoring
- Automatic scaling or load balancing
- Database-backed retry queues
- Message broker integration

---

## 6. Subsystem Coverage

### 6.1 gmail_watcher

**Failure Points:**
- OAuth token refresh failure
- Gmail API rate limiting (429)
- Network timeout during poll
- Malformed email data

**Resilience Requirements:**
- Circuit breaker on Gmail API
- Token refresh retry with exponential backoff
- Graceful skip of malformed emails (log and continue)
- Health file: `.watcher-state/gmail_watcher_health.json`

**Exit Criteria:**
- [ ] All failure categories handled
- [ ] Ralph Wiggum Loop implemented
- [ ] Health file maintained
- [ ] Failures logged with ERR_GMAIL_* codes

### 6.2 whatsapp_watcher

**Failure Points:**
- Playwright session/cookie expiration
- Browser crash or timeout
- Selector changes (DOM updates)
- Network interruption

**Resilience Requirements:**
- Session health check before each poll
- Re-authentication flow for expired sessions
- Selector fallback chains (multiple selectors per element)
- Health file: `.watcher-state/whatsapp_watcher_health.json`

**Exit Criteria:**
- [ ] Session expiration detected and flagged
- [ ] Re-auth prompt surfaced to operator
- [ ] Partial scrape failures don't crash process
- [ ] Health file reflects session validity

### 6.3 facebook_publisher

**Failure Points:**
- Session expiration (Playwright)
- Post creation timeout
- Rate limiting by Facebook
- Content policy rejection

**Resilience Requirements:**
- Pre-flight session validation
- Post timeout with configurable limit
- Circuit breaker on Facebook API
- Content rejection routed to failed queue with reason
- Health file: `.watcher-state/facebook_publisher_health.json`

**Exit Criteria:**
- [ ] Session status checked before publish attempt
- [ ] Failed posts in `Needs_Action/facebook/failed/`
- [ ] Content rejections include Facebook's error message
- [ ] Rate limits trigger circuit breaker

### 6.4 instagram_publisher

**Failure Points:**
- Session expiration (Playwright)
- Image upload failure
- Rate limiting
- Content policy rejection

**Resilience Requirements:**
- Same as facebook_publisher (shared patterns)
- Image validation before upload attempt
- Health file: `.watcher-state/instagram_publisher_health.json`

**Exit Criteria:**
- [ ] Image validation prevents known-bad uploads
- [ ] Failed posts in `Needs_Action/instagram/failed/`
- [ ] Session expiration triggers re-auth prompt

### 6.5 x_publisher

**Failure Points:**
- Session expiration (Playwright)
- Tweet character limit exceeded
- Rate limiting (X/Twitter strict limits)
- Media upload failure

**Resilience Requirements:**
- Content validation (character count) before attempt
- Strict rate limit awareness (15 tweets/15 min window)
- Health file: `.watcher-state/x_publisher_health.json`

**Exit Criteria:**
- [ ] Character limit validated pre-flight
- [ ] Rate limits tracked and respected
- [ ] Failed tweets in `Needs_Action/x/failed/`

### 6.6 briefing_generator

**Failure Points:**
- Vault path invalid
- Reader file parse failures
- Writer output failures
- Missing optional data sources

**Resilience Requirements:**
- Vault path validation at startup
- Per-file retry for reader failures (already implemented)
- Partial briefing generation with "Data unavailable" sections
- Health file: `.watcher-state/briefing_generator_health.json`

**Exit Criteria:**
- [ ] Invalid vault path exits with code 2
- [ ] Partial data produces partial briefing
- [ ] All data failures logged to `data_gaps`
- [ ] Health file updated on each generation

### 6.7 hitl_approval

**Failure Points:**
- Approval file validation failure
- Executor subsystem failure (delegated action)
- File system permission errors
- Concurrent approval race conditions

**Resilience Requirements:**
- Strict frontmatter validation with clear errors
- Executor failure doesn't crash approval watcher
- File locking for concurrent access
- Health file: `.watcher-state/hitl_approval_health.json`

**Exit Criteria:**
- [ ] Invalid approvals routed to `Needs_Action/approvals/invalid/`
- [ ] Executor failures logged with context
- [ ] Race conditions prevented or detected
- [ ] Health file shows approval queue depth

---

## 7. Dependencies

### Internal Dependencies

- `sentinel.logger` — existing logging infrastructure
- `briefing_generator.retry` — starting point for shared retry utility
- Per-subsystem exception classes — refactor into shared hierarchy

### External Dependencies

- None (all local implementation)

### Blocking Dependencies

- Gold Phase 4 (briefing_generator) — complete (provides retry.py pattern)
- All target subsystems must exist and be functional

---

## 8. Assumptions

1. All 7 subsystems are already functional (monitoring/publishing works)
2. Vault directory structure follows constitution (Needs_Action exists)
3. Operators have access to command line for status and recovery
4. External watchdog (PM2/systemd) is configured separately
5. Log rotation is handled externally or via existing mechanisms

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Inconsistent adoption | Medium | High | Shared utilities with clear contracts |
| Retry loops overwhelm services | Low | High | Exponential backoff + circuit breaker |
| Health files become stale | Medium | Medium | Timestamp validation in status command |
| Failed queue grows unbounded | Low | Medium | Recovery command + purge capability |
| Breaking changes to existing subsystems | Medium | Medium | Additive changes, preserve existing APIs |

---

## 10. Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| All subsystems use shared retry | Code review | 7/7 |
| Failures produce structured logs | Manual test | 100% |
| Failed items routed correctly | Manual test | 100% |
| Status shows all subsystems | CLI test | Complete output |
| Circuit breaker functional | Load test | Opens at threshold |
| Health files updated | File timestamp check | <5 min freshness |
| Exit codes correct | Process termination test | Per schema |
| Recovery commands work | CLI test | All commands functional |

---

## 11. Appendices

### A. Error Code Schema

Format: `ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>`

**Examples:**
- `ERR_GMAIL_NETWORK_TIMEOUT` — Gmail API request timed out
- `ERR_WHATSAPP_SESSION_EXPIRED` — WhatsApp session cookies invalid
- `ERR_FACEBOOK_RATE_LIMITED` — Facebook API rate limit hit
- `ERR_HITL_VALIDATION_MISSING_FIELD` — Approval file missing required field
- `ERR_BRIEFING_READER_PARSE_FAILURE` — Could not parse vault file

**Subsystem Prefixes:**
- `GMAIL` — gmail_watcher
- `WHATSAPP` — whatsapp_watcher
- `FACEBOOK` — facebook_publisher
- `INSTAGRAM` — instagram_publisher
- `X` — x_publisher
- `BRIEFING` — briefing_generator
- `HITL` — hitl_approval
- `SENTINEL` — sentinel (filesystem watcher)
- `RESILIENCE` — shared resilience module

### B. Retry Timing Table

| Attempt | Delay | Cumulative | Action |
|---------|-------|------------|--------|
| 1 | 0s | 0s | Execute |
| 2 | 2s (+jitter) | ~2s | Re-read context, retry |
| 3 | 4s (+jitter) | ~6s | Simplify, retry |
| Final | — | — | Log, route to Needs_Action |

### C. Circuit Breaker State Machine

```
     ┌───────────────────────────────────────┐
     │                                       │
     ▼                                       │
┌─────────┐   failure threshold   ┌────────┐│
│ CLOSED  │──────────────────────▶│  OPEN  ││
│(normal) │                       │(reject)││
└────┬────┘                       └────┬───┘│
     │                                 │    │
     │ success                         │30s │
     │                                 │    │
     │         ┌──────────────┐        │    │
     │◀────────│  HALF-OPEN   │◀───────┘    │
     │ 3 ok    │  (testing)   │             │
     └─────────┴──────┬───────┘             │
                      │ failure             │
                      └─────────────────────┘
```

### D. Health File Example

```json
{
  "subsystem": "gmail_watcher",
  "status": "degraded",
  "last_heartbeat": "2026-04-19T12:30:00Z",
  "last_success": "2026-04-19T12:15:00Z",
  "consecutive_failures": 3,
  "degradation_reason": "OAuth token refresh failed",
  "circuit_state": "half-open",
  "version": "0.1.0"
}
```

---

**Document Version**: 1.0.0
**Created**: 2026-04-19
**Author**: Claude Code
