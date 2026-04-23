# Quickstart: Error Recovery & Process Resilience

**Feature**: 015-error-recovery-resilience
**Date**: 2026-04-20

---

## Prerequisites

- Python 3.12+
- Existing AI Employee installation with subsystems operational
- Vault directory initialized with canonical folders

---

## Installation

```bash
# From repository root
source venv/bin/activate

# Install resilience module (after implementation)
pip install -e .
```

---

## Quick Verification

### 1. Check System Health

```bash
# View aggregate health of all subsystems
sentinel-status

# Expected output (healthy system):
# System Status: HEALTHY
# ════════════════════════
#
# Subsystem            Status      Last Success    Failures  Circuit
# ───────────────────────────────────────────────────────────────────
# gmail_watcher        healthy     2 min ago       0         closed
# whatsapp_watcher     healthy     3 min ago       0         closed
# ...
```

### 2. Verify Health Files Exist

```bash
# Health files should exist for each running subsystem
ls -la .watcher-state/*_health.json

# Expected output:
# -rw-r--r-- 1 user user 256 Apr 20 12:30 .watcher-state/gmail_watcher_health.json
# -rw-r--r-- 1 user user 256 Apr 20 12:30 .watcher-state/whatsapp_watcher_health.json
# ...
```

### 3. Test Retry Logic

```bash
# Start any watcher and introduce a transient failure
# The watcher should retry 3 times with exponential backoff

# Check logs for retry entries
ls vault/Logs/*failure*.md
```

---

## Using the Resilience Module in Code

### Basic Retry Decorator

```python
from resilience import retry_with_backoff
from resilience.exceptions import TransientNetworkError

@retry_with_backoff(max_attempts=3, base_delay=1.0)
def fetch_data():
    # This will be retried on transient errors
    response = requests.get("https://api.example.com/data")
    if response.status_code == 503:
        raise TransientNetworkError("Service unavailable")
    return response.json()
```

### Ralph Wiggum Loop (Constitution Principle V)

```python
from pathlib import Path

from resilience import ralph_wiggum_loop
from resilience.logger import write_failure_log

def process_email(email_path):
    def primary_operation():
        content = email_path.read_text()
        return classify_email(content)

    def simplified_fallback():
        # Attempt 3: assume needs reply
        return {"action": "needs_reply", "confidence": 0.5}

    def on_failure(error, attempt, is_final):
        print(f"Attempt {attempt}/3 failed: {error}")
        if is_final:
            # `write_failure_log` derives failure_category / error_code /
            # error_message from the exception itself (a ResilienceError
            # carries all three). Non-ResilienceError exceptions fall back
            # to INTERNAL_ERROR with a synthesized error_code.
            write_failure_log(
                error=error,
                subsystem="email_reasoner",
                action_type="classify_email",
                log_dir=Path("vault/Logs"),
                retry_count=attempt,
                is_final_failure=True,
                source_item=email_path,
                action_taken="routed_to_needs_action",
            )

    return ralph_wiggum_loop(
        operation=primary_operation,
        simplify_fn=simplified_fallback,
        on_failure=on_failure,
    )
```

### Health File Management

```python
from pathlib import Path

from resilience.health import HealthManager

# Initialize health manager for your subsystem.
# `state_dir` is REQUIRED — it's where the `<subsystem>_health.json` file
# is persisted and where external watchdogs (sentinel-status, PM2, systemd)
# read from.
health = HealthManager("gmail_watcher", state_dir=Path(".watcher-state"))

# In your polling loop
while True:
    try:
        # Poll for new emails
        emails = poll_gmail()
        health.record_success()

    except Exception as e:
        health.record_failure(str(e))

    # Heartbeat to indicate process is alive
    health.heartbeat()
    time.sleep(poll_interval)
```

### Circuit Breaker for External APIs

```python
from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError

# Create circuit breaker for Gmail API
gmail_circuit = CircuitBreaker(
    name="gmail_api",
    failure_threshold=5,
    recovery_timeout_seconds=30,
)

def call_gmail_api():
    try:
        return gmail_circuit.execute(lambda: gmail_service.users().messages().list(...))
    except CircuitOpenError:
        # Circuit is open, fail fast
        raise TransientNetworkError("Gmail API circuit is open, try again later")
```

---

## Recovery Commands

### List Failed Items

```bash
# List all failed items
sentinel-recover list

# Filter by subsystem
sentinel-recover list --subsystem gmail_watcher

# JSON output for scripting
sentinel-recover list --json
```

### Retry Failed Items

```bash
# Retry a specific item
sentinel-recover retry Needs_Action/email/failed/email-123.md

# Retry all items for a subsystem
sentinel-recover retry-all --subsystem gmail_watcher

# Dry run (see what would be retried)
sentinel-recover retry-all --subsystem gmail_watcher --dry-run
```

### Purge Old Items

```bash
# Purge items older than 30 days (value is an integer number of days)
sentinel-recover purge --older-than 30

# Dry run first
sentinel-recover purge --older-than 30 --dry-run
```

---

## Monitoring Integration

### PM2 Configuration

```json
{
  "apps": [
    {
      "name": "gmail-watcher",
      "script": "python",
      "args": "-m gmail_watcher",
      "restart_delay": 5000,
      "exp_backoff_restart_delay": 100,
      "max_restarts": 10,
      "autorestart": true,
      "watch": false
    }
  ]
}
```

### systemd Service

```ini
[Unit]
Description=Gmail Watcher
After=network.target

[Service]
Type=simple
ExecStart=/path/to/venv/bin/python -m gmail_watcher
Restart=on-failure
RestartSec=5
Environment=VAULT_PATH=/path/to/vault

[Install]
WantedBy=multi-user.target
```

---

## Exit Codes Reference

| Code | Meaning | Watchdog Action |
|------|---------|-----------------|
| 0 | Clean shutdown | No restart |
| 1 | Recoverable error | Restart with backoff |
| 2 | Configuration error | No restart |
| 3 | Fatal error | No restart |

---

## Troubleshooting

### Health File Missing

```bash
# Check if subsystem is running
ps aux | grep gmail_watcher

# Check state directory permissions
ls -la .watcher-state/
```

### Circuit Breaker Stuck Open

```bash
# Check circuit state
sentinel-status --subsystem gmail_watcher

# Circuit will automatically move to HALF_OPEN after 30 seconds
# Wait and check again
```

### Failed Items Not Being Processed

```bash
# Ensure watchers are processing the Inbox
tail -f vault/Logs/*.md

# Check for permission issues
ls -la Needs_Action/email/failed/
```

---

## Next Steps

1. Run `sentinel-status` to verify all subsystems are healthy
2. Trigger a test failure to verify retry logic works
3. Check that failed items appear in `Needs_Action/<source>/failed/`
4. Use `sentinel-recover list` to view failed items
5. Use `sentinel-recover retry` to test recovery workflow
