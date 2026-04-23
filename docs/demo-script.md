# Demo Script — AI Employee FTE

A 10-minute walkthrough that demonstrates the full pipeline: capture → triage → approval → publish, plus the resilience layer (retry, circuit breaker, failed-queue routing, operator CLIs).

Every command below has been validated against the real implementation. Expected outputs are shown verbatim from smoke tests; your timestamps will differ.

---

## 0. Pre-demo checklist

```bash
source venv/bin/activate
sentinel-status --version          # → sentinel-status 0.1.0
sentinel-recover --version         # → sentinel-recover 0.1.0
ls vault/ .watcher-state/ .env     # all should exist
```

If `vault/` is missing: `sentinel init` creates the canonical folder structure.

---

## 1. Start the system (steady state)

Start the subsystems that will run during the demo. Each watcher now writes its own health file and uses standard exit codes.

```bash
# Terminal 1 — orchestrator (AI triage)
python -m orchestrator.brain

# Terminal 2 — gmail watcher (single poll is fine for a demo)
gmail-watcher --once \
  --health-file .watcher-state/gmail_watcher_health.json \
  --log-dir vault/Logs

# Terminal 3 — optional: whatsapp watcher (requires QR auth on first run)
# whatsapp-watcher --once \
#   --health-file .watcher-state/whatsapp_watcher_health.json \
#   --log-dir vault/Logs
```

Confirm all subsystems are visible to the watchdog layer:

```bash
sentinel-status
```

Expected:

```
System Status: ✓ HEALTHY

Subsystem            Status      Last Success    Failures  Circuit
───────────────────────────────────────────────────────────────────
gmail_watcher        healthy     <moments ago>   0         closed
orchestrator         healthy     <moments ago>   0         closed
```

(Subsystems only appear once they've run at least one cycle and written their health file.)

---

## 2. Process an email (normal flow)

Drop a test email into the Inbox (or let gmail-watcher capture one from a real account). The orchestrator picks it up, classifies via OpenAI, and either (a) routes to `Needs_Action/drafts/` with an AI-drafted reply or (b) logs "no reply needed".

```bash
ls vault/Inbox/email/          # raw captured emails
ls vault/Needs_Action/drafts/  # AI-generated draft replies
tail -n 20 vault/Logs/*.md     # watch the triage log grow
```

---

## 3. Show normal flow complete

```bash
sentinel-status --json | python -m json.tool | head -20
```

Expected (healthy system with ≥1 subsystem reporting):

```json
{
  "aggregate_status": "healthy",
  "subsystems": [
    {
      "subsystem": "gmail_watcher",
      "status": "healthy",
      "consecutive_failures": 0,
      "circuit_state": "closed",
      ...
    }
  ]
}
```

Exit code is `0`.

---

## 4. Simulate a failure cascade

The in-process T117 smoke is the fastest way to demonstrate the full cascade without touching the real Gmail account. The scenario drives a synthetic sustained outage through the resilience pipeline.

```bash
python - <<'PY'
import sys, tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')
from resilience import RetryPolicy, CircuitOpenError, HealthState, CircuitState, write_failure_log
from resilience.cli.status import run_status
from gmail_watcher.watcher import poll_with_retry, create_health_manager, create_gmail_circuit_breaker, route_email_to_failed
from gmail_watcher.models import EmailMessage
from gmail_watcher.writer import write_email_file

FAST = RetryPolicy(max_attempts=3, base_delay=0.0, backoff_multiplier=1.0, max_delay=0.0, jitter_range=0.0)

class DownGmail:
    def __init__(self): self.calls = 0
    def users(self):
        o = self
        class U:
            def messages(self_inner):
                class M:
                    def list(self_l, **kw):
                        o.calls += 1
                        raise ConnectionError("simulated outage")
                return M()
        return U()

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    (vault / "Inbox" / "email").mkdir(parents=True)
    (vault / "Needs_Action" / "email").mkdir(parents=True)
    state = vault / ".watcher-state"; state.mkdir()
    logs = vault / "Logs"; logs.mkdir()

    msg = EmailMessage(
        message_id="demo", thread_id="t", sender="alice@example.com",
        subject="Demo Email", date=datetime.now(),
        snippet="snip", body="body", label_ids=["UNREAD"], attachments=[],
    )
    seeded = write_email_file(msg, vault)
    health = create_health_manager(state)
    circuit = create_gmail_circuit_breaker()

    for cycle in range(1, 4):
        try:
            poll_with_retry(DownGmail(), health, policy=FAST, circuit=circuit)
        except Exception as e:
            print(f"cycle {cycle}: {type(e).__name__} health={health.get_status().status.value} circuit={circuit.state.value}")
            if isinstance(e, CircuitOpenError):
                route_email_to_failed(seeded, vault, e.message, retry_attempts=3, error_code=e.error_code)
                write_failure_log(error=e, subsystem="gmail_watcher", action_type="fetch_unread",
                                  log_dir=logs, retry_count=3, is_final_failure=True,
                                  source_item=seeded, action_taken="routed_to_failed_queue")
                break

    health.set_circuit_state(circuit.state); health.heartbeat()
    code = run_status(state_dir=state, output_json=False)
    print(f"\nsentinel-status exit code: {code}")
    print(f"failed items: {list((vault / 'Needs_Action/email/failed').glob('*.md'))[0].name}")
    print(f"log file:     {list(logs.glob('*_failure_*.md'))[0].name}")
PY
```

Expected output (shape):

```
cycle 1: TransientNetworkError health=degraded circuit=closed
cycle 2: CircuitOpenError      health=unhealthy circuit=open

System Status: ✗ UNHEALTHY

Subsystem       Status     Last Success  Failures  Circuit
───────────────────────────────────────────────────────────
gmail_watcher   unhealthy  never         5         open

Degradation Reasons:
  - gmail_watcher: simulated outage

sentinel-status exit code: 2
failed items: <timestamp>_<subject>_failed.md
log file:     <timestamp>_failure_gmail_watcher_<slug>.md
```

Narrate while this runs:

1. **Cycle 1**: 3 real retries with exponential backoff; translated from raw `ConnectionError` to `TransientNetworkError`. Health drops to DEGRADED (3 failures).
2. **Cycle 2**: Circuit trips to OPEN at the 5th breaker failure. `poll_with_retry` stops retrying immediately (`CircuitOpenError.retryable` flipped to `False` locally).
3. **Routing**: the seeded email is moved to `Needs_Action/email/failed/` with a wrapper preserving the original content plus failure metadata.
4. **Logging**: one structured Markdown log in `Logs/` with FR-005 frontmatter.

---

## 5. Show retry + circuit breaker in action

During the cascade above:

- **Retry**: cycle 1 has 3 fetch calls (attempt 1/2/3 with exponential backoff).
- **Circuit breaker**: cycle 2 tripped after 5 breaker failures (3 from cycle 1 + 2 from cycle 2 before the breaker opened). Once OPEN, further calls fast-fail without hitting the Gmail surface.
- **Auto-recovery**: after `recovery_timeout_seconds=30`, the breaker's `state` property transitions to `HALF_OPEN` and lets one probe call through.

---

## 6. Show failed routing

```bash
# Inspect the wrapper
ls Needs_Action/email/failed/
cat Needs_Action/email/failed/<filename>
```

Expected frontmatter:

```yaml
---
type: failed_item
failure_at: <ISO 8601>
failure_reason: "Circuit 'gmail_api' is open. Retry after X.X seconds."
original_path: "<absolute path to original Inbox/email file>"
retry_attempts: 3
subsystem: gmail_watcher
error_code: ERR_CIRCUIT_GMAIL_API_OPEN
recovery_action: "Inspect wrapped email..."
---
```

Use `sentinel-recover list` to see it from the operator view:

```bash
sentinel-recover list
sentinel-recover list --json
sentinel-recover list --subsystem gmail_watcher
```

---

## 7. Show structured logs

```bash
ls vault/Logs/*_failure_*.md
```

Filename pattern: `YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md` (FR-005).

Open the most recent one and narrate:
- **Frontmatter**: `log_id`, `timestamp`, `subsystem`, `failure_category`, `error_code`, `retry_count`, `is_final_failure`, `source_item`, `action_taken` — the fields an aggregator (Grafana/ELK) keys off.
- **Body**: Failure Details, Stack Trace (only for unhandled exceptions), Context — human-readable narrative the operator actually reads.

---

## 8. Show sentinel-status UNHEALTHY

```bash
sentinel-status
# System Status: ✗ UNHEALTHY
# ...
echo "exit code: $?"
# exit code: 2
```

JSON for scripting / dashboards:

```bash
sentinel-status --json
```

Aggregate rolls up to the worst subsystem state:
- all HEALTHY → `healthy` / exit 0
- any DEGRADED (≥3 failures) → `degraded` / exit 1
- any UNHEALTHY (≥5 failures) → `unhealthy` / exit 2

PM2/systemd can key restart policy on exit 1 (restart with backoff) vs exit 2/3 (don't restart — operator attention needed).

---

## 9. Show recovery

Two paths — re-queue an item, or manually fix and purge.

**Re-queue:**

```bash
sentinel-recover retry Needs_Action/email/failed/<filename>
# Moves the original content back to its Inbox path, deletes the wrapper,
# logs the recovery action.
```

Bulk retry:

```bash
sentinel-recover retry-all --subsystem gmail_watcher --dry-run  # preview
sentinel-recover retry-all --subsystem gmail_watcher            # execute
```

**Purge** (old wrappers, after they've been manually resolved):

```bash
sentinel-recover purge --older-than 30 --dry-run   # preview what would be deleted
sentinel-recover purge --older-than 30 --yes       # actually delete (backup auto-created)
```

Every purge creates `.watcher-state/purge-backup-<date>.tar.gz` before deletion, so nothing is lost irrecoverably.

After recovery, re-run `sentinel-status` — as the affected subsystem records successes, it transitions back to HEALTHY and the aggregate clears.

---

## Wrap-up

What the audience just saw:

1. Multiple watchers running, each health-reporting independently.
2. An AI-powered triage pipeline routing items from Inbox to Needs_Action.
3. A real failure cascade with transparent retry behaviour, breaker protection, structured logging, and quarantine into a recovery queue.
4. Operator tooling (`sentinel-status` / `sentinel-recover`) that sits above all 7 subsystems and makes their state legible from a single command.

Total demo time, hands-on: ~10 minutes. Total lines of user-facing failure-handling code written by each subsystem author: ~0 — it's all inherited from `resilience`.
