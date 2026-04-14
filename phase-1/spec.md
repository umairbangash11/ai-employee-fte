# Phase 1 Specification: Gmail API Migration

**Phase**: 1 — Gmail API Migration
**Branch**: `003-gmail-api-oauth`
**Created**: 2026-03-03
**Status**: Draft
**Constitution**: v2.0.0 (Principles VII, VIII)

---

## 1. Definition of Done

Phase 1 is complete when ALL of the following conditions are met:

### 1.1 Gmail API Watcher Module Exists

- [ ] Module exists at `src/gmail_watcher/watcher.py`
- [ ] Module can authenticate with Gmail API using OAuth 2.0
- [ ] Module can fetch unread messages from Gmail inbox
- [ ] Module exports a `main()` function callable as CLI entry point

### 1.2 Action File Generation

- [ ] Watcher creates `.md` files in `<VAULT_PATH>/Needs_Action/email/` for urgent emails
- [ ] Watcher creates `.md` files in `<VAULT_PATH>/Inbox/email/` for normal emails
- [ ] Files use the canonical frontmatter schema (see Section 3)
- [ ] Filename pattern: `{YYYYMMDD-HHMMSS}_{subject_slug}.md`

### 1.3 Deduplication

- [ ] Processed message IDs are persisted to `.watcher-state/gmail-api.json`
- [ ] State file is stored OUTSIDE the Obsidian vault
- [ ] Duplicate emails are skipped on subsequent polls
- [ ] State survives process restarts

### 1.4 Conservative Polling

- [ ] Default poll interval is 120 seconds minimum (`GMAIL_POLL_INTERVAL`)
- [ ] Exponential backoff on transient errors (network, rate limit)
- [ ] Maximum 3 retries per poll cycle (Ralph Wiggum Loop)
- [ ] After 3 failures, log to `/Logs/` and continue

### 1.5 Dry-Run Mode

- [ ] `--dry-run` flag prints which emails would be captured
- [ ] Dry-run does NOT write `.md` files to vault
- [ ] Dry-run does NOT modify Gmail state (no mark-as-read, no label changes)
- [ ] Dry-run does NOT update deduplication state

### 1.6 Documentation

- [ ] `docs/gmail-api-setup.md` exists with OAuth setup instructions
- [ ] Required environment variables documented
- [ ] Google Cloud Console setup steps documented
- [ ] Troubleshooting section for common errors

---

## 2. File and Module Plan

### 2.1 New Modules (to be created)

| Path | Purpose |
|------|---------|
| `src/gmail_watcher/__init__.py` | Package init, exports version |
| `src/gmail_watcher/auth.py` | OAuth 2.0 authentication flow |
| `src/gmail_watcher/watcher.py` | Gmail API polling and email extraction |
| `src/gmail_watcher/writer.py` | Markdown file generation with frontmatter |
| `src/gmail_watcher/state.py` | Deduplication state persistence |
| `src/gmail_watcher/__main__.py` | CLI entry point with `main()` |

### 2.2 Token and State Storage (OUTSIDE vault)

| Path | Purpose | Git Status |
|------|---------|------------|
| `secrets/gmail/credentials.json` | OAuth client config (from Google Cloud) | `.gitignore` |
| `secrets/gmail/token.json` | User OAuth tokens (access + refresh) | `.gitignore` |
| `.watcher-state/gmail-api.json` | Deduplication registry (message IDs) | `.gitignore` |

**Security Constraint**: These paths MUST be outside `<VAULT_PATH>` and MUST be in `.gitignore`.

### 2.3 CLI Surface

```
gmail-watcher [OPTIONS]

Options:
  --vault-path PATH      Path to Obsidian vault (default: VAULT_PATH env or ".")
  --credentials PATH     Path to OAuth credentials.json (default: secrets/gmail/credentials.json)
  --token PATH           Path to OAuth token.json (default: secrets/gmail/token.json)
  --state PATH           Path to dedup state file (default: .watcher-state/gmail-api.json)
  --interval SECONDS     Poll interval in seconds (default: 120, min: 60)
  --once                 Poll once and exit (no loop)
  --dry-run              Preview mode: no file writes, no state updates
  --auth                 Run OAuth flow to create/refresh token, then exit
  --version              Show version and exit
  --help                 Show this help and exit
```

---

## 3. Frontmatter Schema

All generated `.md` files MUST use this YAML frontmatter (compatible with existing router):

```yaml
---
source: gmail-api
message_id: "<Gmail API message ID>"
captured_at: "2026-03-03T14:30:00Z"
sender: "John Doe <john@example.com>"
subject: "Meeting tomorrow"
urgency: normal
starred: false
important: false
status: unread
tags: [inbox, gmail]
---

## Email Body

<email body content here, sanitized>

## Attachments

- [ ] attachment: filename.pdf (not downloaded)
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Always `gmail-api` |
| `message_id` | string | Yes | Gmail API message ID (for dedup) |
| `captured_at` | ISO8601 | Yes | UTC timestamp when captured |
| `sender` | string | Yes | Format: `"Name <email>"` |
| `subject` | string | Yes | Email subject (default: `(no subject)`) |
| `urgency` | enum | Yes | `normal` or `urgent` |
| `starred` | bool | Yes | True if starred in Gmail |
| `important` | bool | Yes | True if marked important |
| `status` | string | Yes | Always `unread` at capture time |
| `tags` | list | Yes | Default: `[inbox, gmail]` |

### Urgency Routing Rules

| Condition | Urgency | Destination |
|-----------|---------|-------------|
| `starred: true` | `urgent` | `/Needs_Action/email/` |
| `important: true` | `urgent` | `/Needs_Action/email/` |
| Neither | `normal` | `/Inbox/email/` |

---

## 4. pyproject.toml Changes

### 4.1 Dependencies to Add

```toml
[project]
dependencies = [
    # ... existing deps ...
    "google-api-python-client>=2.100.0",
    "google-auth>=2.23.0",
    "google-auth-httplib2>=0.2.0",
    "google-auth-oauthlib>=1.1.0",
]
```

### 4.2 Entry Point to Add

```toml
[project.scripts]
sentinel = "sentinel.__main__:main"
gmail-watcher = "gmail_watcher.__main__:main"
```

**Entry Point Safety Rule**: The `gmail-watcher` script entry MUST NOT be added until `src/gmail_watcher/__main__.py` exists and contains a working `main()` function.

### 4.3 Dependencies to Remove

- `playwright` — No longer needed for Gmail (remains for WhatsApp if present)

**Note**: The current `pyproject.toml` has a malformed `[project.scripts]` section that needs to be fixed as part of implementation.

---

## 5. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_PATH` | No | `.` | Path to Obsidian vault root |
| `GMAIL_POLL_INTERVAL` | No | `120` | Seconds between polls (min: 60) |
| `GMAIL_CREDENTIALS_PATH` | No | `secrets/gmail/credentials.json` | OAuth client config |
| `GMAIL_TOKEN_PATH` | No | `secrets/gmail/token.json` | OAuth user token |
| `GMAIL_STATE_PATH` | No | `.watcher-state/gmail-api.json` | Dedup state file |

**Removed Variables** (no longer needed):
- `GMAIL_EMAIL` — Replaced by OAuth
- `GMAIL_PASSWORD` — Replaced by OAuth

---

## 6. Non-Goals (Explicitly Out of Scope)

| Item | Reason |
|------|--------|
| WhatsApp changes | Separate feature, not Phase 1 |
| MCP server implementation | Future phase |
| Gmail Pub/Sub push notifications | Polling is acceptable for Phase 1 |
| Sending/replying to emails | Read-only watcher only |
| Modifying Gmail labels | Read-only scope only |
| Marking emails as read | Read-only scope only |
| Downloading attachments | Lists only; no download in Phase 1 |
| HTML email rendering | Plain text extraction only |

---

## 7. Acceptance Tests (Manual)

### Test 1: OAuth Authentication

**Objective**: Verify OAuth flow creates valid token.

**Prerequisites**:
- Google Cloud project with Gmail API enabled
- OAuth 2.0 credentials downloaded to `secrets/gmail/credentials.json`

**Steps**:
1. Delete `secrets/gmail/token.json` if it exists
2. Run: `gmail-watcher --auth`
3. Browser opens to Google OAuth consent page
4. Grant permissions (gmail.readonly scope)
5. Browser redirects; CLI shows "Authentication successful"

**Expected Result**:
- [ ] `secrets/gmail/token.json` exists
- [ ] File contains `access_token`, `refresh_token`, `expiry`
- [ ] File permissions are `600` (owner only)

---

### Test 2: Single Email Capture

**Objective**: Verify unread email generates exactly one `.md` file.

**Prerequisites**:
- Valid OAuth token exists
- At least 1 unread email in Gmail inbox

**Steps**:
1. Note the current file count in `<VAULT>/Inbox/email/`
2. Run: `gmail-watcher --once --vault-path <VAULT>`
3. Check `<VAULT>/Inbox/email/` for new file

**Expected Result**:
- [ ] Exactly 1 new `.md` file created per unread email
- [ ] File has correct frontmatter (source: gmail-api)
- [ ] File has correct sender, subject, captured_at
- [ ] Body contains email content

---

### Test 3: Deduplication

**Objective**: Verify duplicate emails are not created on re-run.

**Prerequisites**:
- Test 2 completed successfully
- Same unread email still in Gmail

**Steps**:
1. Note the file count in `<VAULT>/Inbox/email/`
2. Run: `gmail-watcher --once --vault-path <VAULT>`
3. Check file count again

**Expected Result**:
- [ ] No new files created (same count as before)
- [ ] CLI output shows "Skipped N already captured"
- [ ] `.watcher-state/gmail-api.json` contains message ID

---

### Test 4: Dry-Run Mode

**Objective**: Verify dry-run does not modify anything.

**Prerequisites**:
- New unread email in Gmail (not yet captured)
- Note current state of:
  - File count in `<VAULT>/Inbox/email/`
  - Contents of `.watcher-state/gmail-api.json`

**Steps**:
1. Run: `gmail-watcher --once --dry-run --vault-path <VAULT>`
2. Observe CLI output

**Expected Result**:
- [ ] CLI shows "Would capture: <subject>" for the new email
- [ ] No new `.md` file created in vault
- [ ] `.watcher-state/gmail-api.json` unchanged
- [ ] Email still shows as unread in Gmail

---

### Test 5: Urgent Email Routing

**Objective**: Verify starred/important emails route to Needs_Action.

**Prerequisites**:
- Star an unread email in Gmail (or mark as important)

**Steps**:
1. Run: `gmail-watcher --once --vault-path <VAULT>`
2. Check `<VAULT>/Needs_Action/email/` for new file

**Expected Result**:
- [ ] File created in `/Needs_Action/email/` (not `/Inbox/email/`)
- [ ] Frontmatter shows `urgency: urgent`
- [ ] Frontmatter shows `starred: true` or `important: true`

---

### Test 6: Error Recovery (Backoff)

**Objective**: Verify transient errors trigger backoff.

**Prerequisites**:
- Temporarily corrupt `secrets/gmail/token.json`

**Steps**:
1. Run: `gmail-watcher --once --vault-path <VAULT>`
2. Observe CLI output and log file

**Expected Result**:
- [ ] CLI shows authentication error
- [ ] Log entry created in `<VAULT>/Logs/` with actionable message
- [ ] Message suggests running `gmail-watcher --auth`

---

## 8. Constraints and Safety Rules

### 8.1 Constitution Compliance (v2.0.0)

| Principle | Compliance |
|-----------|------------|
| I. Local-First | Tokens stored locally, no cloud dependency for file ops |
| II. Canonical Folders | Routes to /Inbox/email/, /Needs_Action/email/, /Logs/ |
| IV. Safety-First | Read-only scope, no system-modifying actions |
| V. Ralph Wiggum Loop | 3 retries on transient errors, then log and continue |
| VII. Phased Development | Scoped to Phase 1 only |
| VIII. Gmail API Safety | OAuth 2.0, no Playwright, no passwords, conservative polling |

### 8.2 Security Requirements

- OAuth tokens MUST be stored with `chmod 600` (owner-only read/write)
- Token paths MUST be outside `<VAULT_PATH>`
- All secret paths MUST be in `.gitignore`
- Gmail API scope MUST be `gmail.readonly` only

### 8.3 Entry Point Safety

**Critical**: The `gmail-watcher` CLI entry point in `pyproject.toml` MUST NOT be added until:
1. `src/gmail_watcher/__main__.py` exists
2. The file contains a `def main():` function
3. The module is importable without errors

---

## 9. Dependencies

### 9.1 Internal Dependencies

| Module | Purpose |
|--------|---------|
| `sentinel.logger` | Write log entries to `/Logs/` |
| `sentinel.vault` | Validate vault structure |

### 9.2 External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `google-api-python-client` | >=2.100.0 | Gmail API client |
| `google-auth` | >=2.23.0 | Google authentication |
| `google-auth-httplib2` | >=0.2.0 | HTTP transport for auth |
| `google-auth-oauthlib` | >=1.1.0 | OAuth 2.0 flow |
| `python-dotenv` | >=1.0 | Environment variable loading |
| `pyyaml` | >=6.0 | YAML frontmatter generation |

---

## 10. Assumptions

1. User has a Google Cloud project with Gmail API enabled
2. User can download OAuth credentials from Google Cloud Console
3. User has Python 3.12+ installed
4. Gmail API quota (250 units/user/second) is sufficient for personal use
5. The existing `sentinel.logger` module is available and compatible
6. `.gitignore` already excludes `secrets/` and `.watcher-state/`

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| OAuth token expires | Auto-refresh using refresh_token; log actionable error if refresh fails |
| Gmail API quota exceeded | Conservative polling (120s default); exponential backoff |
| User revokes OAuth consent | Detect 401 error; prompt re-authentication via `--auth` |
| Network instability | 3-retry pattern with backoff; continue after logging |
| Large inbox (1000s of unread) | Process in batches; rate-limit file writes |

---

**End of Phase 1 Specification**
