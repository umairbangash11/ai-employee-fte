# Data Model: Error Recovery & Process Resilience

**Feature**: 015-error-recovery-resilience
**Date**: 2026-04-20

---

## 1. Core Entities

### 1.1 ResilienceError (Exception Base)

The unified exception hierarchy for all subsystems.

```python
@dataclass
class ResilienceError(Exception):
    """Base exception for all resilience-aware errors."""

    # Required fields
    error_code: str          # ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>
    category: FailureCategory
    message: str             # Human-readable, operator-actionable

    # Optional context
    retryable: bool = True
    context: dict = field(default_factory=dict)
    source_item: Optional[Path] = None
    subsystem: Optional[str] = None

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
```

### 1.2 FailureCategory (Enum)

Categorization of failure types with associated retry policies.

```python
class FailureCategory(str, Enum):
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"    # Retryable: exponential backoff
    SESSION_EXPIRED = "SESSION_EXPIRED"         # Retryable: after re-auth
    RATE_LIMITED = "RATE_LIMITED"               # Retryable: after cooldown
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID" # Not retryable
    DATA_MALFORMED = "DATA_MALFORMED"           # Not retryable
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE" # Conditional
    EXTERNAL_SERVICE_DOWN = "EXTERNAL_SERVICE_DOWN" # Retryable: circuit breaker
    INTERNAL_ERROR = "INTERNAL_ERROR"           # Not retryable
```

### 1.3 RetryPolicy (Configuration)

Policy for retry behavior per failure category.

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3           # Constitution Principle V
    base_delay: float = 1.0         # Seconds
    backoff_multiplier: float = 2.0 # Exponential
    max_delay: float = 30.0         # Cap
    jitter_range: float = 0.5       # 0-500ms random
    retryable_categories: set[FailureCategory] = field(default_factory=lambda: {
        FailureCategory.TRANSIENT_NETWORK,
        FailureCategory.SESSION_EXPIRED,
        FailureCategory.RATE_LIMITED,
        FailureCategory.EXTERNAL_SERVICE_DOWN,
    })
```

### 1.4 FailureLog (Log Entry)

Structured log entry for failures written to `/Logs/`.

```python
@dataclass
class FailureLog:
    """Represents a failure log entry in the vault."""

    # Identity
    log_id: str              # <timestamp>-failure-<subsystem>-<slug>
    timestamp: datetime      # ISO 8601

    # Classification
    subsystem: str           # gmail_watcher, linkedin_publisher, etc.
    failure_category: FailureCategory
    error_code: str          # ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>

    # Retry state
    retry_count: int         # 0-3
    is_final_failure: bool   # True if max retries exhausted

    # Context
    source_item: Optional[str]  # Path to triggering item
    error_message: str          # Human-readable
    stack_trace: Optional[str]  # Only for INTERNAL_ERROR
    context: dict               # Additional key-value pairs

    # Resolution
    action_taken: str           # retry | routed_to_needs_action | logged_and_continued

    def to_yaml_frontmatter(self) -> str:
        """Generate YAML frontmatter for Markdown file."""
        ...

    def to_markdown(self) -> str:
        """Generate complete Markdown file content."""
        ...
```

**File naming**: `YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md`

**Example output**:
```yaml
---
log_id: "2026-04-20T12-30-00-failure-gmail_watcher-oauth-refresh"
timestamp: "2026-04-20T12:30:00Z"
action_type: failure_record
subsystem: gmail_watcher
failure_category: SESSION_EXPIRED
error_code: "ERR_GMAIL_SESSION_TOKEN_REFRESH"
retry_count: 3
is_final_failure: true
source_item: null
error_message: "OAuth token refresh failed after 3 attempts"
context:
  token_age_hours: 168
  refresh_endpoint: "https://oauth2.googleapis.com/token"
action_taken: routed_to_needs_action
---

## Failure Details

OAuth token refresh failed after 3 attempts.

## Recovery Action

1. Check network connectivity
2. Re-run Gmail OAuth flow: `python -m gmail_watcher --reauth`
3. Verify credentials in `.env`
```

### 1.5 HealthStatus (Health File)

Health status file for watchdog integration.

```python
@dataclass
class HealthStatus:
    """Subsystem health status persisted to .watcher-state/."""

    subsystem: str               # gmail_watcher, etc.
    status: HealthState          # healthy | degraded | unhealthy
    last_heartbeat: datetime     # Updated every poll cycle
    last_success: datetime       # Last successful operation
    consecutive_failures: int    # Reset on success
    degradation_reason: Optional[str]  # Why degraded/unhealthy
    circuit_state: Optional[CircuitState]  # CLOSED | OPEN | HALF_OPEN
    version: str                 # Package version

    def to_json(self) -> str:
        """Serialize to JSON for file storage."""
        ...

    @classmethod
    def from_json(cls, data: str) -> "HealthStatus":
        """Deserialize from JSON file."""
        ...

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if heartbeat is older than threshold."""
        ...
```

**File location**: `.watcher-state/<subsystem>_health.json`

### 1.6 CircuitBreaker (State Machine)

Circuit breaker for external API protection.

```python
@dataclass
class CircuitBreaker:
    """Circuit breaker state machine."""

    name: str                    # e.g., "gmail_api"
    state: CircuitState          # CLOSED | OPEN | HALF_OPEN

    # Thresholds
    failure_threshold: int = 5           # Open after N failures
    failure_rate_threshold: float = 0.5  # Or 50% failure rate
    failure_window_seconds: int = 60     # In this time window
    recovery_timeout_seconds: int = 30   # Time in OPEN before HALF_OPEN
    success_threshold: int = 3           # Successes to close from HALF_OPEN

    # Current state
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None

    def record_success(self) -> None:
        """Record successful call."""
        ...

    def record_failure(self) -> None:
        """Record failed call."""
        ...

    def can_execute(self) -> bool:
        """Check if call should proceed."""
        ...

    def get_state(self) -> CircuitState:
        """Get current state with automatic transitions."""
        ...


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Reject all calls
    HALF_OPEN = "half_open" # Testing recovery
```

### 1.7 FailedItemWrapper (Recovery Queue)

Wrapper for items routed to failed queue.

```python
@dataclass
class FailedItemWrapper:
    """Wrapper for failed items in Needs_Action/<source>/failed/."""

    # Failure metadata
    failure_at: datetime
    failure_reason: str          # <category>: <message>
    original_path: Path
    retry_attempts: int
    recovery_action: str         # Suggested fix

    # Original content
    original_content: str
    original_frontmatter: Optional[dict]

    def to_markdown(self) -> str:
        """Generate wrapped Markdown file."""
        ...

    @classmethod
    def from_markdown(cls, path: Path) -> "FailedItemWrapper":
        """Parse wrapped failed item."""
        ...
```

**File location**: `Needs_Action/<source>/failed/<original-filename>`

---

## 2. Enums

### 2.1 HealthState

```python
class HealthState(str, Enum):
    HEALTHY = "healthy"       # Operating normally
    DEGRADED = "degraded"     # Partial functionality
    UNHEALTHY = "unhealthy"   # Not functioning
```

### 2.2 ActionTaken

```python
class ActionTaken(str, Enum):
    RETRY = "retry"                           # Will retry
    ROUTED_TO_NEEDS_ACTION = "routed_to_needs_action"  # Sent to failed queue
    LOGGED_AND_CONTINUED = "logged_and_continued"      # Non-blocking failure
```

### 2.3 ExitCode

```python
class ExitCode(IntEnum):
    SUCCESS = 0              # Clean shutdown
    RECOVERABLE = 1          # Restart with backoff
    CONFIGURATION = 2        # No restart (manual fix)
    FATAL = 3                # No restart (investigation)
```

---

## 3. Relationships

```
ResilienceError
    └── FailureCategory (1:1)
    └── RetryPolicy (N:1, via category)

FailureLog
    └── FailureCategory (1:1)
    └── Subsystem (N:1)
    └── FailedItemWrapper (1:1, optional)

HealthStatus
    └── Subsystem (1:1)
    └── CircuitBreaker (1:1, optional)

CircuitBreaker
    └── External API (1:1)
```

---

## 4. State Transitions

### 4.1 Retry State Machine

```
┌─────────────┐    success    ┌───────────┐
│  ATTEMPT_1  │──────────────▶│  SUCCESS  │
└──────┬──────┘               └───────────┘
       │ failure
       ▼
┌─────────────┐    success    ┌───────────┐
│  ATTEMPT_2  │──────────────▶│  SUCCESS  │
└──────┬──────┘               └───────────┘
       │ failure + sleep(2s)
       ▼
┌─────────────┐    success    ┌───────────┐
│  ATTEMPT_3  │──────────────▶│  SUCCESS  │
└──────┬──────┘               └───────────┘
       │ failure + sleep(4s)
       ▼
┌─────────────┐    route      ┌───────────────────┐
│ FINAL_FAIL  │──────────────▶│ NEEDS_ACTION/fail │
└─────────────┘               └───────────────────┘
```

### 4.2 Health State Machine

```
┌─────────┐   1 failure   ┌──────────┐   3+ failures   ┌───────────┐
│ HEALTHY │──────────────▶│ DEGRADED │────────────────▶│ UNHEALTHY │
└────┬────┘               └────┬─────┘                 └─────┬─────┘
     │                         │                             │
     │◀────────────────────────┘◀────────────────────────────┘
     │              success (consecutive_failures = 0)
```

---

## 5. Validation Rules

### 5.1 Error Code Format

```
ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>
```

- `SUBSYSTEM`: GMAIL, WHATSAPP, FACEBOOK, INSTAGRAM, X, BRIEFING, HITL, SENTINEL, RESILIENCE
- `CATEGORY`: NETWORK, SESSION, RATE, CREDS, DATA, RESOURCE, SERVICE, INTERNAL
- `DETAIL`: Specific error (e.g., TIMEOUT, EXPIRED, REFRESH, PARSE)

### 5.2 Health File Validation

- `last_heartbeat` must be within 5 minutes of current time (else stale)
- `consecutive_failures` must be non-negative
- `status` must match `consecutive_failures` thresholds:
  - 0 failures → healthy
  - 1-2 failures → degraded
  - 3+ failures → unhealthy

### 5.3 Circuit Breaker Validation

- `failure_count` resets after `failure_window_seconds`
- `opened_at` must be set when `state == OPEN`
- `success_threshold` successes in HALF_OPEN → CLOSED

---

## 6. Storage Locations

| Entity | Location | Format |
|--------|----------|--------|
| FailureLog | `vault/Logs/` | Markdown + YAML frontmatter |
| HealthStatus | `.watcher-state/<subsystem>_health.json` | JSON |
| CircuitBreaker | `.watcher-state/<api>_circuit.json` | JSON |
| FailedItemWrapper | `Needs_Action/<source>/failed/` | Markdown |
