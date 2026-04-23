# Troubleshooting Guide

Field guide for the AI Employee FTE system, organized by symptom. For each issue: quick diagnosis → root cause(s) → fix.

First-aid command for any weirdness: **`sentinel-status`**. It aggregates the health of all 7 subsystems and tells you where to look.

---

## Gmail auth issues

### Symptom: `CredentialsInvalidError: Gmail OAuth token refresh failed`

Root cause: the refresh token in `secrets/gmail/token.json` has been revoked, expired, or never existed.

Fix:

```bash
# Re-run the OAuth flow — opens a browser
gmail-watcher --auth

# Verify the new token
ls -la secrets/gmail/token.json

# Confirm the watcher can now start
gmail-watcher --once
```

Exit code after this path: **2** (CONFIGURATION) — not retryable, requires human action. PM2/systemd will NOT auto-restart on exit 2, which is intentional.

### Symptom: `HTTP 401/403` from Gmail API

- **401**: token is invalid. Same fix as above (`gmail-watcher --auth`).
- **403**: Gmail API isn't enabled on the GCP project, or the scopes don't match. Go to [Google Cloud Console](https://console.cloud.google.com/), verify Gmail API is enabled for the project tied to `credentials.json`, and confirm the OAuth consent screen includes `gmail.readonly` (or broader) scope.

### Symptom: `credentials.json` not found

Root cause: no OAuth credentials have been downloaded.

Fix: follow [`docs/gmail-api-setup.md`](gmail-api-setup.md) to create a Desktop OAuth client, download the JSON, save to `secrets/gmail/credentials.json`.

---

## WhatsApp session issues

### Symptom: `SessionExpiredError: WhatsApp Web session expired`

Root cause: WhatsApp Web's persistent session cookies have aged out. This happens after ~2 weeks of inactivity or when WhatsApp forces a re-auth.

Fix:

```bash
python -m whatsapp_watcher --auth
# Opens a headed browser. Scan the QR code with your phone.
# After auth, session cookies are persisted in .watcher-state/whatsapp/
```

The resilience layer categorizes this as `SESSION_EXPIRED` and exits with code **1** (RECOVERABLE). A watchdog can restart the watcher after the operator re-authenticates, without needing to flip a flag.

### Symptom: `QRTimeoutError: QR authentication timed out`

Root cause: the QR code window expired before the phone scanned it.

Fix: same as above — re-run `--auth` and scan more quickly. QR windows are short (~20s default per Playwright).

### Symptom: Watcher hangs, no messages captured, no obvious error

Run `sentinel-status --subsystem whatsapp_watcher --json` — check `consecutive_failures` and `last_heartbeat`.

- `last_heartbeat` older than 5 minutes → subsystem is stuck (heartbeat is the liveness signal). Check Playwright is healthy: `ls .watcher-state/whatsapp/` for a populated browser profile.
- `consecutive_failures` growing → selectors may have drifted (WhatsApp Web UI changed). Inspect the most recent `vault/Logs/*_failure_whatsapp_watcher_*.md` for the specific selector that failed.

---

## No logs appearing in `vault/Logs/`

### Symptom: `ls vault/Logs/*_failure_*.md` → no matches, but failures are occurring

Possible root causes (in order of likelihood):

1. **`--log-dir` flag pointing elsewhere.** Each watcher defaults to `./vault/Logs` but can be redirected. Confirm the invocation:
   ```bash
   ps aux | grep gmail_watcher
   # If the process line includes --log-dir <other>, logs are there instead
   ```

2. **The failure path never called `write_failure_log`.** Some subsystems log per-poll success/failure to health files but only write structured failure logs on final failure or route-to-failed. If you're seeing DEGRADED in `sentinel-status` but no `vault/Logs/` entries, the failures are still retryable and haven't hit a "terminal" log point.

3. **Filesystem permission / wrong CWD.** Watcher was launched from a directory where `vault/Logs/` isn't writable. Fix: start with an absolute `--log-dir`.

4. **No failures have actually happened.** Expected output of `sentinel-status` is healthy → there are no logs because there are no failures. This is fine.

### Symptom: Logs appear in unexpected format

If a log file lacks the FR-005 frontmatter, it was written by the legacy per-subsystem logger (`sentinel.logger.write_log_entry`, used by the orchestrator for non-failure actions). `*_failure_*.md` files use the resilience schema; other log files use the older schema.

---

## Circuit breaker stuck OPEN

### Symptom: `sentinel-status` shows `circuit_state: open` and it stays that way

The breaker transitions OPEN → HALF_OPEN automatically after `recovery_timeout_seconds=30`. If the state is stuck, one of:

1. **The process restarted and the breaker reset to CLOSED but failures are immediate.** Breaker state is in-process; it does not persist across restarts. If `sentinel-status` shows OPEN, check `last_heartbeat` — if older than 5 min, the process is probably dead. Restart it (PM2/systemd will do this on exit 1).

2. **The downstream service is genuinely still down.** The HALF_OPEN probe attempts one call; if that call fails, the breaker jumps back to OPEN for another `recovery_timeout_seconds`. This is working as intended.

3. **Circuit state on the health file is stale.** The health file's `circuit_state` is updated via `health.set_circuit_state(circuit.state)` at specific points in each subsystem. If the subsystem isn't calling this after every breaker transition, the health file can lag reality. Fix: restart the subsystem.

Force-reset the breaker (emergency, discards failure history):

```bash
# Stop the subsystem first (Ctrl+C / PM2 stop).
# Edit the health file:
python -c "
import json
from pathlib import Path
p = Path('.watcher-state/gmail_watcher_health.json')
data = json.loads(p.read_text())
data['circuit_state'] = 'closed'
data['consecutive_failures'] = 0
data['status'] = 'healthy'
p.write_text(json.dumps(data, indent=2))
"
# Restart the subsystem — it will load the reset state.
```

Prefer letting the breaker time out naturally (30s).

---

## Failed queue handling

### Symptom: `Needs_Action/<source>/failed/` is filling up

Not necessarily a bug — this is the quarantine queue working. Review with:

```bash
sentinel-recover list                          # all failed items
sentinel-recover list --subsystem gmail_watcher
sentinel-recover list --since "7 days ago"     # recent only
sentinel-recover list --json | jq .            # for scripts
```

### Symptom: Retrying an item fails immediately

```bash
sentinel-recover retry Needs_Action/email/failed/<filename>
```

If that raises `not retryable`, the wrapper's `error_code` indicates a non-retryable category (credentials, data malformed, internal error). Either:

- Fix the root cause (e.g. `gmail-watcher --auth` for credentials) and retry with `--force`:
  ```bash
  sentinel-recover retry Needs_Action/email/failed/<file> --force
  ```
- Or treat the item as lost — inspect the content manually, then delete the wrapper.

### Symptom: Can't find the original content after routing

The wrapper **contains** the original content (frontmatter + body preserved). `sentinel-recover retry` extracts and restores it. Don't delete wrappers until you've either retried or confirmed the content isn't needed.

Emergency recovery (if wrappers were bulk-deleted): the most recent `purge` created `.watcher-state/purge-backup-<date>.tar.gz` — extract to restore.

---

## `sentinel-status` not showing subsystems

### Symptom: `sentinel-status` returns `No subsystems found.`

Root cause: no `*_health.json` files exist in `.watcher-state/`.

Diagnosis:

```bash
ls .watcher-state/*_health.json    # if this is empty, the watchers never wrote health
```

Reasons `.json` files might be missing:

1. **Watchers have never been started under the new resilience pipeline.** Each subsystem writes its health file on the first `heartbeat()`. If you just installed/integrated the resilience layer, start any subsystem once:
   ```bash
   gmail-watcher --once
   ```
   Then re-run `sentinel-status`.

2. **Watchers are writing to a different state dir.** Check `--state` / `--health-file` flags or `VAULT_PATH` env var. Make sure they point to the same directory `sentinel-status` reads from. Default is `.watcher-state/` relative to the invocation CWD.

3. **Permission issue.** `.watcher-state/` exists but the watcher process can't write to it. Check owner/perms:
   ```bash
   ls -la .watcher-state/
   ```

### Symptom: Some but not all expected subsystems visible

Each subsystem writes its health file only after its first heartbeat. Subsystems that haven't been started yet will simply not appear. Start them and re-check.

### Symptom: `sentinel-status` reports a subsystem but `last_heartbeat` is stale

`HealthStatus.is_stale(max_age_seconds=300)` treats heartbeats older than 5 minutes as stale. A stale heartbeat means the process is dead, wedged, or paused. Check:

```bash
ps aux | grep <subsystem>
```

If the process isn't running, your watchdog (PM2/systemd) should have restarted it — check the watchdog's logs. If the process IS running but heartbeat is stale, the poll loop is blocked somewhere (check recent `vault/Logs/` entries for that subsystem).

---

## Exit code reference

When debugging a crashed subsystem, the exit code is the fastest classifier:

| Exit | Meaning | What to do |
|------|---------|------------|
| 0 | Clean shutdown / no work | Nothing — watchdog may restart depending on policy |
| 1 | Recoverable error (transient network, rate limit, session expiry) | Watchdog should restart with backoff. Check `vault/Logs/` for specifics. |
| 2 | Configuration error (credentials, missing resource) | Fix the config. Do NOT auto-restart — that will just burn cycles. |
| 3 | Fatal / unhandled error | Investigate `vault/Logs/` and the stack trace. Likely a bug. |

Check the last exit code of a watcher started under PM2:

```bash
pm2 show gmail-watcher | grep -i exit
```

Or in an ad-hoc shell:

```bash
gmail-watcher --once; echo $?
```

---

## When in doubt

Collect this snapshot before asking for help:

```bash
sentinel-status --json > /tmp/status.json
ls -la .watcher-state/
ls vault/Logs/*_failure_*.md 2>/dev/null | tail -5
tail -n 50 vault/Logs/$(ls -t vault/Logs/*_failure_*.md 2>/dev/null | head -1) 2>/dev/null
```

Those four commands cover (1) aggregate health, (2) state directory contents, (3) recent failure logs, (4) the most recent failure in detail — enough to diagnose ~90% of operational issues.
