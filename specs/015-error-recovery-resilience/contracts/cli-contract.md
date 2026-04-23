# CLI Contract: Error Recovery Commands

**Feature**: 015-error-recovery-resilience
**Date**: 2026-04-20

---

## 1. sentinel-status

Display aggregate health status of all subsystems.

### Usage

```bash
sentinel-status [--json] [--subsystem <name>]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output JSON instead of table | False |
| `--subsystem` | Filter to specific subsystem | All |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All subsystems healthy |
| 1 | One or more subsystems degraded |
| 2 | One or more subsystems unhealthy |

### Output (Table)

```
System Status: DEGRADED
════════════════════════

Subsystem            Status      Last Success    Failures  Circuit
───────────────────────────────────────────────────────────────────
gmail_watcher        healthy     2 min ago       0         closed
whatsapp_watcher     degraded    15 min ago      3         half-open
facebook_publisher   healthy     5 min ago       0         closed
instagram_publisher  unhealthy   2 hours ago     12        open
x_publisher          healthy     8 min ago       0         closed
briefing_generator   healthy     1 day ago       0         n/a
hitl_approval        healthy     30 sec ago      0         n/a

Issues:
  whatsapp_watcher: Session expired, re-auth required
  instagram_publisher: API rate limited, cooldown 45 min remaining
```

### Output (JSON)

```json
{
  "aggregate_status": "degraded",
  "timestamp": "2026-04-20T12:30:00Z",
  "subsystems": [
    {
      "name": "gmail_watcher",
      "status": "healthy",
      "last_heartbeat": "2026-04-20T12:28:00Z",
      "last_success": "2026-04-20T12:28:00Z",
      "consecutive_failures": 0,
      "circuit_state": "closed",
      "degradation_reason": null
    }
  ],
  "issues": [
    {
      "subsystem": "whatsapp_watcher",
      "status": "degraded",
      "reason": "Session expired, re-auth required"
    }
  ]
}
```

---

## 2. sentinel-recover

Manage failed items in recovery queues.

### Usage

```bash
sentinel-recover <command> [options]
```

### Commands

#### list

List failed items awaiting recovery.

```bash
sentinel-recover list [--subsystem <name>] [--since <date>] [--json]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--subsystem` | Filter by source subsystem | All |
| `--since` | Only items after this date (ISO 8601) | None |
| `--json` | Output JSON instead of table | False |

**Output (Table):**

```
Failed Items: 5 total
═════════════════════

Path                                          Subsystem    Failed At           Reason
──────────────────────────────────────────────────────────────────────────────────────
Needs_Action/email/failed/email-123.md        gmail        2026-04-20 11:30    SESSION_EXPIRED
Needs_Action/email/failed/email-456.md        gmail        2026-04-20 11:32    DATA_MALFORMED
Needs_Action/instagram/failed/post-001.md     instagram    2026-04-20 10:15    RATE_LIMITED
Needs_Action/whatsapp/failed/msg-789.md       whatsapp     2026-04-19 22:00    SESSION_EXPIRED
Needs_Action/approvals/invalid/approval-x.md  hitl         2026-04-19 18:45    DATA_MALFORMED
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | Success (even if no items) |
| 1 | Error reading failed queues |

---

#### retry

Retry a specific failed item.

```bash
sentinel-recover retry <file-path> [--force]
```

**Arguments:**

| Argument | Description | Required |
|----------|-------------|----------|
| `file-path` | Path to failed item | Yes |

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Retry even if not retryable | False |

**Behavior:**

1. Parse wrapper frontmatter to get original path
2. Extract original content
3. Move to original location (e.g., `Inbox/email/`)
4. Delete wrapper from failed queue
5. Log recovery attempt to `Logs/`

**Output:**

```
Retrying: Needs_Action/email/failed/email-123.md
  Original path: Inbox/email/email-123.md
  Failure reason: SESSION_EXPIRED: OAuth token refresh failed
  Moving to: Inbox/email/email-123.md
  Success: Item queued for reprocessing
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | Item successfully queued |
| 1 | Item not found or parse error |
| 2 | Item not retryable (use --force) |

---

#### retry-all

Retry all failed items for a subsystem.

```bash
sentinel-recover retry-all --subsystem <name> [--force] [--dry-run]
```

**Options:**

| Option | Description | Default |
|--------|-------------|----------|
| `--subsystem` | Target subsystem (required) | - |
| `--force` | Retry non-retryable items | False |
| `--dry-run` | Show what would be retried | False |

**Output:**

```
Retrying all failed items for: gmail_watcher

Processing 3 items...
  [1/3] email-123.md → Inbox/email/ ... OK
  [2/3] email-456.md → Inbox/email/ ... SKIP (not retryable: DATA_MALFORMED)
  [3/3] email-789.md → Inbox/email/ ... OK

Summary: 2 retried, 1 skipped, 0 failed
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | All retryable items processed |
| 1 | Some items failed to retry |

---

#### purge

Purge old failed items.

```bash
sentinel-recover purge --older-than <duration> [--subsystem <name>] [--dry-run] [--yes]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--older-than` | Duration (e.g., `30d`, `7d`, `24h`) | Required |
| `--subsystem` | Filter by subsystem | All |
| `--dry-run` | Show what would be purged | False |
| `--yes` | Skip confirmation prompt | False |

**Output:**

```
Purging failed items older than 30 days...

Found 12 items to purge:
  Needs_Action/email/failed/email-001.md (45 days old)
  Needs_Action/email/failed/email-002.md (38 days old)
  ...

Are you sure? This cannot be undone. [y/N]: y

Purged 12 items. Backup created at: .watcher-state/purge-backup-2026-04-20.tar.gz
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | Purge completed |
| 1 | Error during purge |
| 2 | User cancelled |

---

## 3. Module Entry Points

Each subsystem MUST support these flags for resilience integration:

### Common Options

```bash
python -m <subsystem> [--health-file <path>] [--log-dir <path>]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--health-file` | Path to write health JSON | `.watcher-state/<subsystem>_health.json` |
| `--log-dir` | Directory for failure logs | `vault/Logs/` |

### Exit Codes (All Subsystems)

| Code | Meaning | PM2/systemd Action |
|------|---------|-------------------|
| 0 | Clean shutdown (SIGINT) | No restart |
| 1 | Recoverable error | Restart with backoff |
| 2 | Configuration error | No restart |
| 3 | Fatal error | No restart |

---

## 4. Error Response Format

All CLI errors MUST follow this format:

```
Error: [ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>] <message>

Details:
  <key>: <value>
  ...

Suggested action:
  <actionable recovery step>
```

**Example:**

```
Error: [ERR_GMAIL_SESSION_TOKEN_REFRESH] OAuth token refresh failed

Details:
  subsystem: gmail_watcher
  category: SESSION_EXPIRED
  retry_count: 3
  last_attempt: 2026-04-20T12:30:00Z

Suggested action:
  Re-authenticate with Gmail: python -m gmail_watcher --reauth
```
