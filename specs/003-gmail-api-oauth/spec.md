# Feature Specification: Gmail API OAuth Sentinel

**Feature Branch**: `003-gmail-api-oauth`
**Phase**: 1 — Gmail API Migration
**Created**: 2026-02-28
**Updated**: 2026-03-03
**Status**: Draft
**Constitution**: v2.0.0 (Principle VII: Phase 1, Principle VIII: Gmail API Migration Safety)
**Input**: User description: "Replace Playwright-based Gmail sentinel with Gmail API (OAuth) sentinel. Requirements: MUST NOT open a browser during normal runs, MUST authenticate via OAuth token stored locally (credentials.json + token.json/pickle in ./secrets/gmail/), MUST poll for unread emails (optionally filter important) and write normalized markdown files into <VAULT_PATH>/Inbox/email/, MUST deduplicate across restarts using persistent state in .watcher-state/, MUST support poll interval via env (GMAIL_POLL_INTERVAL), MUST be safe-by-default: read-only scopes initially (gmail.readonly), MUST log errors to <VAULT_PATH>/Logs/ with actionable messages, MUST remove need for GMAIL_PASSWORD and Playwright for Gmail. Out of scope: Sending emails, UI automation for Gmail."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Headless Email Capture (Priority: P1)

The system silently polls the user's Gmail inbox via the Gmail API without opening a browser window. Each poll cycle retrieves unread emails and writes them as Obsidian-compatible Markdown files to the vault's `/Inbox/email/` directory. The user's workflow is uninterrupted — no browser windows pop up, no password prompts appear during normal operation.

**Why this priority**: Core value proposition — users need a background service that captures emails without visual interruption. This replaces the Playwright approach which could open visible browser windows and required storing plain-text passwords.

**Independent Test**: Run the sentinel after initial OAuth setup. Verify that no browser opens, unread emails appear as markdown files in `/Inbox/email/`, and the process runs entirely headless.

**Acceptance Scenarios**:

1. **Given** a valid OAuth token exists in `./secrets/gmail/token.json`, **When** the sentinel polls Gmail, **Then** it retrieves unread emails without opening any browser window.
2. **Given** 3 unread emails exist in the Gmail inbox, **When** a poll cycle completes, **Then** 3 new Markdown files appear in `/Inbox/email/` with correct frontmatter.
3. **Given** the sentinel is running, **When** a new email arrives and the next poll executes, **Then** the new email is captured within one poll interval.

---

### User Story 2 - One-Time OAuth Setup (Priority: P1)

When no valid OAuth token exists, the user runs a setup command that opens a browser for Google OAuth consent. After granting permission, the token is stored locally in `./secrets/gmail/` and the sentinel can run headlessly thereafter. The user never stores their Gmail password in plain text.

**Why this priority**: Essential for security and usability — OAuth eliminates the security risk of storing plain-text passwords (GMAIL_PASSWORD) and enables users to revoke access via Google account settings.

**Independent Test**: Delete `./secrets/gmail/token.json`, run the auth setup command, complete OAuth in browser, verify token is created and subsequent polls work without browser.

**Acceptance Scenarios**:

1. **Given** no token file exists, **When** the user runs `gmail-sentinel --auth`, **Then** a browser opens to Google OAuth consent page.
2. **Given** the user completes OAuth consent, **When** the browser redirects back, **Then** `./secrets/gmail/token.json` is created with valid credentials.
3. **Given** a valid token exists, **When** running `gmail-sentinel` normally, **Then** no browser opens and authentication uses the stored token.
4. **Given** the user revokes app access via Google account settings, **When** the sentinel attempts to poll, **Then** an actionable error message directs the user to re-run `--auth`.

---

### User Story 3 - Urgent Email Routing (Priority: P2)

Emails marked as starred or important in Gmail are automatically routed to `/Needs_Action/email/` instead of `/Inbox/email/`. This enables the existing Inbox Router to immediately process urgent items without waiting for triage.

**Why this priority**: Builds on User Story 1 to provide intelligent routing based on Gmail's native priority signals. Enables zero-touch handling of urgent emails.

**Independent Test**: Star or mark an email as important in Gmail, trigger a poll cycle, verify the email appears in `/Needs_Action/email/` with `urgency: urgent` in frontmatter.

**Acceptance Scenarios**:

1. **Given** a starred unread email exists, **When** the sentinel polls, **Then** the email file is created in `/Needs_Action/email/` with `urgency: urgent`.
2. **Given** an important-marked unread email exists, **When** the sentinel polls, **Then** the email file is created in `/Needs_Action/email/` with `urgency: urgent`.
3. **Given** a normal unread email (not starred, not important), **When** the sentinel polls, **Then** the email file is created in `/Inbox/email/` with `urgency: normal`.

---

### User Story 4 - Deduplication Across Restarts (Priority: P2)

The sentinel remembers which emails it has already captured, even after restarts. If the same unread email is seen in multiple poll cycles (because the user hasn't read it yet), it is not written again.

**Why this priority**: Prevents duplicate files in the vault. Users often leave emails unread for extended periods; without deduplication, the vault would fill with redundant copies.

**Independent Test**: Poll once to capture an email, stop the sentinel, restart it, poll again — verify the same email is not written twice.

**Acceptance Scenarios**:

1. **Given** an email was captured in a previous poll, **When** the same email appears in a subsequent poll, **Then** no new file is created (skipped as duplicate).
2. **Given** the sentinel is stopped and restarted, **When** it polls and encounters previously captured emails, **Then** those emails are skipped based on persistent state in `.watcher-state/gmail-api.json`.
3. **Given** a new email arrives with the same sender and subject as a previous one but different timestamp, **When** polled, **Then** it is treated as a new email and captured.

---

### User Story 5 - Error Logging with Actionable Messages (Priority: P3)

When errors occur (authentication failure, network timeout, API quota exceeded), the sentinel logs them to `<VAULT_PATH>/Logs/` with clear, actionable messages that tell the user exactly what to do.

**Why this priority**: Users need self-service diagnostics. Clear error messages reduce support burden and enable quick recovery.

**Independent Test**: Simulate a token expiration by corrupting `token.json`, run the sentinel, verify an error log entry appears with instructions to re-run `--auth`.

**Acceptance Scenarios**:

1. **Given** the OAuth token is expired or revoked, **When** a poll fails, **Then** a log entry is written with message: "Gmail authentication failed. Run `gmail-sentinel --auth` to re-authenticate."
2. **Given** a network timeout occurs, **When** the poll fails, **Then** a log entry is written with message: "Network error connecting to Gmail API. Check internet connection and retry."
3. **Given** API quota is exceeded, **When** the poll fails, **Then** a log entry is written with message: "Gmail API quota exceeded. Service will retry automatically. See https://developers.google.com/gmail/api/guides/quota for details."

---

### Edge Cases

- **Token file is corrupted**: Sentinel logs actionable error and prompts re-authentication via `--auth`.
- **Network is unavailable**: Sentinel follows Ralph Wiggum retry loop (3 attempts), then logs and continues.
- **Gmail account has 2FA**: OAuth flow handles 2FA natively; no special handling required.
- **Poll cycle takes longer than poll interval**: Next poll is deferred; cycles do not overlap.
- **User has thousands of unread emails**: First poll may be slow; subsequent polls process incrementally.
- **Email body contains YAML-like content**: Frontmatter extraction is sandboxed; body content is quoted safely.
- **secrets/gmail/ directory doesn't exist**: Created automatically during `--auth` flow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate with Gmail using OAuth 2.0 with locally stored credentials (`./secrets/gmail/credentials.json` for app config, `./secrets/gmail/token.json` for user token).
- **FR-002**: System MUST NOT open a browser window during normal polling operation (headless-by-default).
- **FR-003**: System MUST provide an `--auth` flag/command to initiate OAuth browser flow when token is missing or expired.
- **FR-004**: System MUST poll Gmail for unread emails at a configurable interval (env: `GMAIL_POLL_INTERVAL`, default: 300 seconds).
- **FR-005**: System MUST write captured emails as Obsidian-compatible Markdown files with standardized frontmatter (source, captured_at, sender, subject, urgency, status, tags).
- **FR-006**: System MUST route normal emails to `<VAULT_PATH>/Inbox/email/` and urgent emails (starred or important) to `<VAULT_PATH>/Needs_Action/email/`.
- **FR-007**: System MUST deduplicate emails using a persistent hash registry stored in `.watcher-state/gmail-api.json`.
- **FR-008**: System MUST use read-only Gmail API scope (`gmail.readonly`) by default.
- **FR-009**: System MUST log errors to `<VAULT_PATH>/Logs/` using the existing sentinel.logger module with actionable error messages.
- **FR-010**: System MUST follow the Ralph Wiggum retry pattern (3 attempts with escalating strategies) for transient failures.
- **FR-011**: System MUST read vault path from environment variable `VAULT_PATH` (default: current directory).
- **FR-012**: System MUST support `--dry-run` flag to preview which emails would be captured without writing files.
- **FR-013**: System MUST gracefully handle token refresh when access token expires (automatic refresh using refresh token).
- **FR-014**: System MUST NOT store `GMAIL_PASSWORD` or any plain-text passwords.
- **FR-015**: System MUST create `./secrets/gmail/` and `.watcher-state/` directories automatically if they don't exist.

### Non-Functional Requirements

- **NFR-001**: Poll cycle completes in under 30 seconds for up to 50 unread emails.
- **NFR-002**: Sentinel process uses under 50MB memory during steady-state operation.
- **NFR-003**: OAuth token stored with file permissions restricting access to owner only (chmod 600).

### Key Entities

- **GmailCredentials**: OAuth client configuration loaded from `./secrets/gmail/credentials.json` (client_id, client_secret, redirect_uri).
- **GmailToken**: User's OAuth access/refresh tokens stored in `./secrets/gmail/token.json` (access_token, refresh_token, expiry).
- **EmailMessage**: Data extracted from Gmail API representing a single email (message_id, sender, subject, date, body, snippet, labels, attachments).
- **CapturedEmailFile**: Markdown file written to vault with frontmatter and body content.
- **DeduplicationState**: Hash registry mapping message hashes to capture timestamps, persisted to `.watcher-state/gmail-api.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can capture Gmail emails into their Obsidian vault without opening a browser window during normal operation (zero browser windows after initial OAuth setup).
- **SC-002**: Users do not need to store Gmail passwords in plain text; authentication uses industry-standard OAuth 2.0.
- **SC-003**: 100% of unread emails are captured within one poll interval (default 5 minutes).
- **SC-004**: Zero duplicate email files are created for emails already captured in previous sessions.
- **SC-005**: When errors occur, 100% of error log entries contain actionable remediation steps.
- **SC-006**: Sentinel can run continuously for 7+ days without manual intervention (excluding token refresh via refresh token).
- **SC-007**: Migration from Playwright-based sentinel requires only running `--auth` once; no `.env` password configuration needed.

## Assumptions

- User has a Google Cloud project with Gmail API enabled and OAuth 2.0 credentials configured.
- User will manually download `credentials.json` from Google Cloud Console and place it in `./secrets/gmail/`.
- Gmail API quotas (250 quota units per user per second, 1 billion units per day) are sufficient for personal email polling.
- The existing `sentinel.logger` module is available and compatible with this feature.
- `./secrets/gmail/` and `.watcher-state/` directories are excluded from version control via `.gitignore`.

## Out of Scope

- Sending emails from the sentinel
- Replying to or forwarding emails
- UI automation (Playwright) for Gmail — this is explicitly being replaced
- WhatsApp or other messaging platform integration (separate feature)
- Real-time push notifications (Gmail Pub/Sub) — future enhancement
- Email deletion or label modification at source
