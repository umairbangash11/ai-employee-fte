# Research: Error Recovery & Process Resilience

**Feature**: 015-error-recovery-resilience
**Date**: 2026-04-20
**Status**: Complete

---

## Summary

The codebase has established foundations for error handling and retry logic but lacks **unified patterns and consistency** across subsystems. Ralph Wiggum Loop (Constitution Principle V) is implemented in orchestrator and publishers but not universally.

---

## 1. Existing Retry Logic Implementations

### 1.1 Orchestrator (brain.py)

**Location**: `src/orchestrator/brain.py:259-341`

Pattern:
- **Attempt 1**: Execute as planned
- **Attempt 2**: Re-read context, sleep 1.0s, retry
- **Attempt 3**: Fallback approach (assume needs reply)
- **After 3 failures**: Log to `/Logs` with full error context

```python
for attempt in range(1, 4):
    try:
        content = filepath.read_text(encoding="utf-8")
        classification = classify_email(self.client, self.model, content)
        return
    except Exception as e:
        last_error = e
        if attempt < 3:
            print(f"  Retry {attempt}/3 failed: {e}")
            time.sleep(1.0 * attempt)
            continue
```

**Decision**: Extract to shared `retry.py` utility.

### 1.2 LinkedIn Publisher

**Location**: `src/linkedin_publisher/executor.py:305-368`

Pattern:
- Async-aware retry with `publish_with_retry(content, max_attempts=3)`
- Calls `is_retryable_error()` to skip retry for permanent failures
- `_adjust_for_retry(attempt)` between attempts

**Decision**: Generalize async retry pattern for reuse.

### 1.3 Facebook Publisher

**Location**: `src/facebook_publisher/executor.py:367-435`

Pattern:
- Same structure as LinkedIn
- Calls `_adjust_for_retry(attempt)` with browser refresh/reinit

**Decision**: Merge with LinkedIn pattern into shared utility.

---

## 2. Exception Hierarchies

### 2.1 Current State

| Subsystem | Base Class | Retryable Flag | Actionable Message |
|-----------|------------|----------------|-------------------|
| linkedin_publisher | `LinkedInPublishError` | Yes | Yes |
| facebook_publisher | `FacebookPublishError` | No | Yes |
| router | `RouterError` | No | Yes |
| hitl_approval | `HITLApprovalError` | No | Yes |

### 2.2 Design Decision

Create unified hierarchy:

```python
# src/resilience/exceptions.py

class ResilienceError(Exception):
    """Base for all subsystem errors."""
    category: str  # TRANSIENT_NETWORK, SESSION_EXPIRED, etc.
    retryable: bool
    error_code: str
    context: dict

class TransientNetworkError(ResilienceError):
    category = "TRANSIENT_NETWORK"
    retryable = True

class SessionExpiredError(ResilienceError):
    category = "SESSION_EXPIRED"
    retryable = True  # After re-auth

class RateLimitedError(ResilienceError):
    category = "RATE_LIMITED"
    retryable = True  # After cooldown

class CredentialsInvalidError(ResilienceError):
    category = "CREDENTIALS_INVALID"
    retryable = False

class DataMalformedError(ResilienceError):
    category = "DATA_MALFORMED"
    retryable = False

class ResourceUnavailableError(ResilienceError):
    category = "RESOURCE_UNAVAILABLE"
    retryable = False  # Conditional

class ExternalServiceDownError(ResilienceError):
    category = "EXTERNAL_SERVICE_DOWN"
    retryable = True  # With circuit breaker

class InternalError(ResilienceError):
    category = "INTERNAL_ERROR"
    retryable = False
```

**Rationale**: Enables consistent retry policy determination across all subsystems.
**Alternatives Considered**: Keep per-subsystem hierarchies (rejected: inconsistent behavior).

---

## 3. Logging Infrastructure

### 3.1 Current Patterns

| Subsystem | Format | Location | Quality |
|-----------|--------|----------|---------|
| sentinel | Markdown + YAML | `/Logs/` | Simple |
| linkedin_publisher | JSON lines | `/Logs/linkedin/` | Excellent |
| facebook_publisher | JSON lines | `/Logs/facebook/` | Excellent |
| hitl_approval | JSON lines | `/Logs/approvals/` | Excellent |

### 3.2 Design Decision

Create unified failure logger:

```python
# src/resilience/logger.py

def write_failure_log(
    logs_dir: Path,
    subsystem: str,
    failure_category: str,
    error_code: str,
    error_message: str,
    retry_count: int,
    is_final_failure: bool,
    source_item: Optional[Path],
    context: dict,
    action_taken: str,
    stack_trace: Optional[str] = None
) -> Path:
    """Write structured failure log to Logs/ as Markdown with YAML frontmatter."""
```

**Rationale**: Markdown format for Obsidian compatibility (Constitution constraint).
**Alternatives Considered**: JSON-only (rejected: Obsidian requires Markdown).

---

## 4. Missing Components

### 4.1 Health Files

**Current State**: Not implemented.

**Design Decision**: Each subsystem maintains heartbeat file:

```json
// .watcher-state/<subsystem>_health.json
{
  "subsystem": "gmail_watcher",
  "status": "healthy | degraded | unhealthy",
  "last_heartbeat": "2026-04-20T12:30:00Z",
  "last_success": "2026-04-20T12:15:00Z",
  "consecutive_failures": 0,
  "degradation_reason": null,
  "version": "0.1.0"
}
```

**Rationale**: Enables external watchdog integration (PM2, systemd).

### 4.2 Circuit Breaker

**Current State**: Not implemented.

**Design Decision**: Implement for external API calls:

- Gmail API
- OpenAI API
- Publisher APIs (LinkedIn, Facebook, Instagram, X)

**Pattern**:
- CLOSED → OPEN: 5 consecutive failures OR 50% failure rate in 60s
- OPEN → HALF-OPEN: After 30s cooldown
- HALF-OPEN → CLOSED: 3 consecutive successes

**Rationale**: Prevents cascading failures and wasted API quota.

### 4.3 Exit Codes

**Current State**: Inconsistent.

**Design Decision**: Standardize:

| Code | Meaning | Restart Policy |
|------|---------|----------------|
| 0 | Clean shutdown | No restart |
| 1 | Recoverable error | Restart with backoff |
| 2 | Configuration error | No restart |
| 3 | Fatal error | No restart |

---

## 5. Subsystem Coverage Analysis

| Subsystem | Has Retry | Has Exceptions | Has Logger | Has Health | Gap Priority |
|-----------|-----------|----------------|------------|------------|--------------|
| gmail_watcher | No | Basic | No | No | P1 (Critical) |
| whatsapp_watcher | No | Basic | No | No | P1 (Critical) |
| router | No | Yes | No | No | P2 (High) |
| orchestrator | Yes | Basic | Yes | No | P3 (Medium) |
| briefing_generator | Partial | Basic | No | No | P3 (Medium) |
| hitl_approval | No | Yes | Yes | No | P4 (Low) |
| linkedin_publisher | Yes | Yes | Yes | No | P5 (Low) |
| facebook_publisher | Yes | Yes | Yes | No | P5 (Low) |

---

## 6. Technology Decisions

### 6.1 Retry Utility

**Decision**: Create synchronous and asynchronous retry decorators.

```python
# src/resilience/retry.py

@retry_with_backoff(max_attempts=3, base_delay=1.0, backoff_multiplier=2)
def some_operation():
    ...

@async_retry_with_backoff(max_attempts=3, base_delay=1.0, backoff_multiplier=2)
async def some_async_operation():
    ...

def ralph_wiggum_loop(operation, simplify_fn=None, on_failure=None):
    """Constitution Principle V implementation."""
```

**Rationale**: Decorators for simple cases; function for complex workflows.

### 6.2 Failed Item Routing

**Decision**: Route to `Needs_Action/<source>/failed/` with wrapper:

```yaml
---
failure_at: "2026-04-20T12:30:00Z"
failure_reason: "SESSION_EXPIRED: OAuth token refresh failed"
original_path: "/Inbox/email/email-123.md"
retry_attempts: 3
recovery_action: "Re-authenticate with Gmail, then retry with sentinel-recover"
---

[Original content preserved below]
```

**Rationale**: Preserves original content; provides actionable recovery steps.

---

## 7. File Structure

```
src/resilience/
├── __init__.py           # Package exports
├── exceptions.py         # Unified exception hierarchy
├── retry.py              # Ralph Wiggum loop + decorators
├── logger.py             # Structured failure logging
├── health.py             # Heartbeat + health file management
├── circuit_breaker.py    # Circuit breaker pattern
├── exit_codes.py         # Standard exit codes
└── failed_routing.py     # Failed item routing utilities
```

---

## 8. Reuse Summary

| Source | Target | Transformation |
|--------|--------|----------------|
| linkedin_publisher/executor.py retry logic | resilience/retry.py | Extract, generalize |
| linkedin_publisher/exceptions.py is_retryable_error | resilience/exceptions.py | Generalize to category-based |
| linkedin_publisher/logger.py JSON format | resilience/logger.py | Keep JSON + Markdown hybrid |
| sentinel/logger.py Markdown format | resilience/logger.py | Use for failure logs |
| facebook_publisher/executor.py _adjust_for_retry | resilience/retry.py | Extract as hook pattern |

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing subsystems | Additive changes only; preserve existing APIs |
| Inconsistent adoption | Shared utilities with clear contracts + migration guide |
| Health files become stale | Timestamp validation in status command |
| Retry loops overwhelm services | Exponential backoff + circuit breaker + jitter |

---

## 10. Conclusion

**NEEDS CLARIFICATION items resolved:**
- Retry pattern: Extract from LinkedIn/Facebook → unified `retry.py`
- Exception hierarchy: New shared base with category-based retryability
- Health monitoring: JSON files in `.watcher-state/`
- Circuit breaker: Standard pattern with configurable thresholds
- Exit codes: 0/1/2/3 schema per spec

**Ready for Phase 1 design.**
