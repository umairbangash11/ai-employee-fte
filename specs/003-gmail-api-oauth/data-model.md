# Data Model: Gmail API OAuth Sentinel

**Feature**: 003-gmail-api-oauth
**Date**: 2026-02-28
**Status**: Complete

## Entities

### 1. GmailCredentials

OAuth client configuration loaded from `./secrets/gmail/credentials.json`.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| client_id | string | OAuth 2.0 client ID | Google Cloud Console |
| client_secret | string | OAuth 2.0 client secret | Google Cloud Console |
| redirect_uris | list[string] | Authorized redirect URIs | Google Cloud Console |
| auth_uri | string | Google OAuth authorization endpoint | Standard |
| token_uri | string | Google OAuth token endpoint | Standard |

**File Location**: `./secrets/gmail/credentials.json`
**User Action**: User downloads from Google Cloud Console and places manually.

---

### 2. GmailToken

User's OAuth access and refresh tokens, generated after OAuth consent flow.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| token | string | OAuth access token (short-lived, ~1 hour) | OAuth flow |
| refresh_token | string | OAuth refresh token (long-lived) | OAuth flow |
| token_uri | string | Endpoint for token refresh | OAuth config |
| client_id | string | OAuth client ID | OAuth config |
| client_secret | string | OAuth client secret | OAuth config |
| scopes | list[string] | Granted OAuth scopes | OAuth flow |
| expiry | datetime | Token expiration timestamp | OAuth flow |

**File Location**: `./secrets/gmail/token.json`
**File Permissions**: chmod 600 (owner read/write only)
**Auto-Created**: Yes, by `--auth` flow

**Validation Rules**:
- `refresh_token` must be present for token refresh to work
- `expiry` is used to proactively refresh before expiration
- `scopes` must include `gmail.readonly`

---

### 3. EmailMessage

Data extracted from Gmail API representing a single email.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| message_id | string | Gmail's unique message ID | `message['id']` |
| thread_id | string | Gmail's thread ID | `message['threadId']` |
| sender | string | From header value | `headers['From']` |
| subject | string | Subject header value | `headers['Subject']` |
| date | datetime | Email date (RFC 2822 parsed) | `headers['Date']` |
| snippet | string | Gmail's preview snippet | `message['snippet']` |
| body | string | Full body text (plain text preferred) | `payload.parts` |
| label_ids | list[string] | Gmail labels | `message['labelIds']` |
| is_unread | bool | True if UNREAD label present | Derived |
| is_starred | bool | True if STARRED label present | Derived |
| is_important | bool | True if IMPORTANT label present | Derived |
| attachments | list[Attachment] | List of attachment metadata | `payload.parts` |

**Computed Fields**:
- `urgency`: "urgent" if `is_starred` or `is_important`, else "normal"
- `destination_dir`: `/Needs_Action/email/` if urgent, else `/Inbox/email/`

---

### 4. Attachment

Metadata for email attachments (content not downloaded).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| filename | string | Attachment filename | `part['filename']` |
| mime_type | string | MIME type of attachment | `part['mimeType']` |
| size | int | Size in bytes | `part['body']['size']` |

**Note**: Attachments are listed in Markdown output but not downloaded. The Markdown file contains a checklist:
```markdown
## Attachments
- [ ] attachment: document.pdf (application/pdf, 125 KB)
- [ ] attachment: image.png (image/png, 45 KB)
```

---

### 5. CapturedEmailFile

Markdown file written to vault with frontmatter and body content.

| Field | Type | Description |
|-------|------|-------------|
| filepath | Path | Full path to the created Markdown file |
| filename | string | Generated filename (timestamp + slug) |
| frontmatter | dict | YAML frontmatter fields |
| body_content | string | Markdown body (email content) |

**Filename Pattern**: `{YYYYMMDD-HHMMSS}_{subject_slug}.md`

**Frontmatter Schema**:
```yaml
---
source: gmail-api
message_id: "<Gmail message ID>"
captured_at: "2026-02-28T10:30:00Z"
sender: "John Doe <john@example.com>"
subject: "Meeting tomorrow"
urgency: normal | urgent
status: unread
tags: [inbox, gmail]
---
```

**Body Template**:
```markdown
# {subject}

**From**: {sender}
**Date**: {date}

---

{body_text}

## Attachments

- [ ] attachment: {filename} ({mime_type}, {size_human})
```

---

### 6. DeduplicationState

Hash registry tracking captured messages to prevent duplicates.

| Field | Type | Description |
|-------|------|-------------|
| message_ids | dict[str, str] | Map of message_id → captured_at timestamp |
| last_poll | datetime | Timestamp of most recent poll |
| version | int | State file format version |

**File Location**: `.watcher-state/gmail-api.json`
**File Format**:
```json
{
    "version": 1,
    "last_poll": "2026-02-28T10:30:00Z",
    "message_ids": {
        "18dc5a3f12345678": "2026-02-28T10:25:00Z",
        "18dc5a3f87654321": "2026-02-28T10:30:00Z"
    }
}
```

**Operations**:
- `is_captured(message_id)`: Check if message already captured
- `mark_captured(message_id)`: Add to registry with current timestamp
- `save()`: Persist to disk
- `load()`: Load from disk (create empty if missing)

---

### 7. SentinelConfig

Runtime configuration loaded from environment variables.

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| vault_path | Path | `.` | `VAULT_PATH` | Path to Obsidian vault |
| poll_interval | int | 300 | `GMAIL_POLL_INTERVAL` | Poll interval in seconds |
| max_initial_fetch | int | 100 | `GMAIL_MAX_FETCH` | Max messages on first poll |
| credentials_path | Path | `./secrets/gmail/credentials.json` | - | OAuth credentials file |
| token_path | Path | `./secrets/gmail/token.json` | - | OAuth token file |
| state_path | Path | `./.watcher-state/gmail-api.json` | - | Dedup state file |
| dry_run | bool | False | - | CLI flag, preview mode |
| auth_mode | bool | False | - | CLI flag, run OAuth setup |

---

## State Transitions

### EmailMessage Lifecycle

```
[Gmail Inbox]
     │
     │ poll() - fetches unread messages
     ▼
[EmailMessage] ─────────────────────────────┐
     │                                      │
     │ is_captured()?                       │
     ├── YES ──────────────────────────────▶│ Skip (already processed)
     │                                      │
     └── NO                                 │
          │                                 │
          │ determine_urgency()             │
          ├── urgent ──▶ /Needs_Action/email/
          └── normal ──▶ /Inbox/email/
                    │
                    │ write_markdown()
                    ▼
            [CapturedEmailFile]
                    │
                    │ mark_captured()
                    ▼
            [DeduplicationState] (persisted)
```

### OAuth Token Lifecycle

```
[No Token]
     │
     │ --auth flag
     ▼
[OAuth Browser Flow]
     │
     │ user grants consent
     ▼
[GmailToken] ── saved to token.json
     │
     │ poll()
     ├── token valid ──▶ proceed
     │
     └── token expired
          │
          │ credentials.refresh()
          ├── SUCCESS ──▶ save updated token, proceed
          │
          └── FAILURE (refresh_token revoked)
               │
               ▼
          [Log Error: "Run --auth to re-authenticate"]
```

---

## Relationships

```
GmailCredentials ──────┐
                       │
                       ▼
GmailToken ────────────────────────▶ Gmail API Service
                                          │
                                          │ list/get messages
                                          ▼
SentinelConfig ──────────────────▶ EmailMessage[]
                                          │
DeduplicationState ◀─────────────────────┤
     │                                    │
     │ filter duplicates                  │
     ▼                                    ▼
[New messages only] ──────────────▶ CapturedEmailFile[]
                                          │
                                          │ write to vault
                                          ▼
                               /Inbox/email/ or /Needs_Action/email/
```

---

## File System Artifacts

| Artifact | Path | Purpose | Auto-Created |
|----------|------|---------|--------------|
| OAuth Client Config | `./secrets/gmail/credentials.json` | OAuth app configuration | No (user downloads) |
| OAuth User Token | `./secrets/gmail/token.json` | Access/refresh tokens | Yes (by --auth) |
| Dedup State | `./.watcher-state/gmail-api.json` | Message tracking | Yes (on first poll) |
| Email Files | `<VAULT>/Inbox/email/*.md` | Normal emails | Yes (on capture) |
| Urgent Files | `<VAULT>/Needs_Action/email/*.md` | Urgent emails | Yes (on capture) |
| Log Files | `<VAULT>/Logs/*.md` | Audit trail | Yes (on events) |
