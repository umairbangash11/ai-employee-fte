# Feature Specification: WhatsApp Watcher — Message Ingestion

**Feature Branch**: `007-whatsapp-watcher`
**Phase**: Silver Tier — WhatsApp Integration (Ingestion Only)
**Created**: 2026-03-22
**Status**: Draft
**Constitution**: v2.0.0 (Principle III: Silver Tier, Principle VI: Silver Tier Autonomy)
**Input**: User description: "Add a WhatsApp watcher using a local session-based approach suitable for hackathon/demo use. Monitor WhatsApp for new or unread messages. Convert captured messages into markdown with YAML frontmatter. Store messages in the vault under a clearly defined WhatsApp folder structure. Define routing behavior for normal vs urgent/actionable messages. Define deduplication behavior. Define required metadata fields. Define logging requirements. Define failure behavior for session loss, selector failure, and temporary page load issues. Read-only ingestion only — no reply sending."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Headless WhatsApp Message Capture (Priority: P1)

The system silently monitors WhatsApp Web via Playwright browser automation, capturing unread messages from conversations without requiring user interaction. Each poll cycle retrieves new or unread messages and writes them as Obsidian-compatible Markdown files to the vault's `/Inbox/whatsapp/` directory. The user's workflow is uninterrupted — the browser runs headless and no manual intervention is required during normal operation.

**Why this priority**: Core value proposition — users need a background service that captures WhatsApp messages for triage without manual copy-paste. This enables the existing Brain/Orchestrator to process WhatsApp messages alongside Gmail emails.

**Independent Test**: Run the watcher after initial WhatsApp Web QR authentication. Verify that messages from unread conversations appear as markdown files in `/Inbox/whatsapp/`, and the process runs entirely headless.

**Acceptance Scenarios**:

1. **Given** a valid WhatsApp Web session exists in `.watcher-state/whatsapp/`, **When** the watcher polls WhatsApp Web, **Then** it retrieves unread messages without requiring user interaction.
2. **Given** 3 unread conversations exist in WhatsApp, **When** a poll cycle completes, **Then** 3 new Markdown files appear in `/Inbox/whatsapp/` with correct frontmatter.
3. **Given** the watcher is running, **When** a new message arrives and the next poll executes, **Then** the new message is captured within one poll interval.

---

### User Story 2 - One-Time QR Code Authentication (Priority: P1)

When no valid session exists, the user runs a setup command that opens a visible browser window displaying the WhatsApp Web QR code. After scanning with their phone, the session is persisted locally in `.watcher-state/whatsapp/` and the watcher can run headlessly thereafter. The user never stores their WhatsApp password (WhatsApp uses phone-based authentication).

**Why this priority**: Essential for usability — WhatsApp Web requires QR code scanning for authentication. A one-time headed setup enables subsequent headless operation.

**Independent Test**: Delete `.watcher-state/whatsapp/`, run the auth setup command, scan QR code with phone, verify session is persisted and subsequent polls work headlessly.

**Acceptance Scenarios**:

1. **Given** no session directory exists, **When** the user runs `whatsapp-watcher --auth`, **Then** a visible browser window opens showing the WhatsApp Web QR code.
2. **Given** the user scans the QR code with their phone, **When** WhatsApp Web loads successfully, **Then** the session is persisted to `.watcher-state/whatsapp/`.
3. **Given** a valid session exists, **When** running `whatsapp-watcher` normally, **Then** the browser runs headless and no QR code prompt appears.
4. **Given** the user logs out of WhatsApp Web from their phone, **When** the watcher attempts to poll, **Then** an actionable error message directs the user to re-run `--auth`.

---

### User Story 3 - Urgent Message Routing (Priority: P2)

Messages containing configured urgency keywords (e.g., "URGENT", "ASAP", "call me", "emergency") are automatically routed to `/Needs_Action/whatsapp/` instead of `/Inbox/whatsapp/`. This enables the existing routing infrastructure to immediately flag actionable messages.

**Why this priority**: Builds on User Story 1 to provide intelligent routing. Enables zero-touch handling of urgent messages consistent with Gmail urgent email routing.

**Independent Test**: Send a WhatsApp message containing "URGENT" from another contact, trigger a poll cycle, verify the message appears in `/Needs_Action/whatsapp/` with `urgency: urgent` in frontmatter.

**Acceptance Scenarios**:

1. **Given** a message containing "URGENT" (case-insensitive) exists in an unread conversation, **When** the watcher polls, **Then** the message file is created in `/Needs_Action/whatsapp/` with `urgency: urgent`.
2. **Given** a message containing "ASAP" exists, **When** the watcher polls, **Then** the message file is created in `/Needs_Action/whatsapp/` with `urgency: urgent`.
3. **Given** a normal message without urgency keywords, **When** the watcher polls, **Then** the message file is created in `/Inbox/whatsapp/` with `urgency: normal`.

---

### User Story 4 - Deduplication Across Restarts (Priority: P2)

The watcher remembers which messages it has already captured, even after restarts. If the same message is seen in multiple poll cycles, it is not written again. Deduplication uses a deterministic hash of message attributes.

**Why this priority**: Prevents duplicate files in the vault. Users may not immediately read captured messages; without deduplication, the vault would fill with redundant copies.

**Independent Test**: Poll once to capture a message, stop the watcher, restart it, poll again — verify the same message is not written twice.

**Acceptance Scenarios**:

1. **Given** a message was captured in a previous poll, **When** the same message appears in a subsequent poll, **Then** no new file is created (skipped as duplicate).
2. **Given** the watcher is stopped and restarted, **When** it polls and encounters previously captured messages, **Then** those messages are skipped based on persistent state in `.watcher-state/whatsapp-dedup.json`.
3. **Given** a new message arrives from the same sender with identical text but different timestamp, **When** polled, **Then** it is treated as a new message and captured.

---

### User Story 5 - Group Chat Message Capture (Priority: P2)

Messages from WhatsApp group chats are captured alongside individual messages. Group name is recorded in metadata, and each message includes the sender's name within the group.

**Why this priority**: Many business communications occur in group chats. Capturing only individual messages would miss significant context.

**Independent Test**: Send a message in a WhatsApp group, trigger a poll cycle, verify the message appears with group name and sender in frontmatter.

**Acceptance Scenarios**:

1. **Given** an unread message exists in a group chat, **When** the watcher polls, **Then** a markdown file is created with `chat_type: group` and `group_name` in frontmatter.
2. **Given** a group message, **When** captured, **Then** frontmatter includes both `sender` (message author) and `group_name` (group title).
3. **Given** the same person sends messages in individual and group contexts, **When** polled, **Then** both messages are captured with appropriate `chat_type` differentiation.

---

### User Story 6 - Error Logging with Actionable Messages (Priority: P3)

When errors occur (session expired, page load failure, selector not found), the watcher logs them to `<VAULT_PATH>/Logs/` with clear, actionable messages that tell the user exactly what to do.

**Why this priority**: Users need self-service diagnostics. Clear error messages reduce support burden and enable quick recovery. Hackathon/demo context requires easy troubleshooting.

**Independent Test**: Corrupt the session data, run the watcher, verify an error log entry appears with instructions to re-run `--auth`.

**Acceptance Scenarios**:

1. **Given** the WhatsApp Web session is expired or invalid, **When** a poll fails, **Then** a log entry is written with message: "WhatsApp session expired. Run `whatsapp-watcher --auth` to re-authenticate."
2. **Given** a network timeout occurs, **When** the poll fails, **Then** a log entry is written with message: "Network error loading WhatsApp Web. Check internet connection and retry."
3. **Given** WhatsApp Web UI changes and a selector fails, **When** the poll fails after 3 retry attempts, **Then** a log entry is written with message: "WhatsApp Web selector failed. WhatsApp may have updated their UI. Check for watcher updates."

---

### Edge Cases

- **Session file is corrupted**: Watcher logs actionable error and prompts re-authentication via `--auth`.
- **Network is unavailable**: Watcher follows Ralph Wiggum retry loop (3 attempts), then logs and continues.
- **WhatsApp Web requires phone confirmation**: Some sessions may require phone proximity confirmation; watcher logs this clearly.
- **Poll cycle takes longer than poll interval**: Next poll is deferred; cycles do not overlap.
- **User has hundreds of unread messages**: First poll may be slow; subsequent polls process incrementally.
- **Message contains emoji or special characters**: Content is encoded properly in markdown.
- **Media messages (images, voice notes, documents)**: Placeholder text indicates media type; actual files are not downloaded in this phase.
- **`.watcher-state/whatsapp/` directory doesn't exist**: Created automatically during `--auth` flow.
- **WhatsApp Web is already logged in on another browser**: Session may conflict; watcher logs clear error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use Playwright to automate WhatsApp Web in a browser context with persistent session storage.
- **FR-002**: System MUST NOT open a visible browser window during normal polling operation (headless-by-default).
- **FR-003**: System MUST provide an `--auth` flag/command to initiate QR code authentication in headed mode when session is missing or expired.
- **FR-004**: System MUST poll WhatsApp Web for unread messages at a configurable interval (env: `WHATSAPP_POLL_INTERVAL`, default: 60 seconds).
- **FR-005**: System MUST write captured messages as Obsidian-compatible Markdown files with standardized frontmatter.
- **FR-006**: System MUST route normal messages to `<VAULT_PATH>/Inbox/whatsapp/` and urgent messages (containing configured keywords) to `<VAULT_PATH>/Needs_Action/whatsapp/`.
- **FR-007**: System MUST deduplicate messages using a persistent hash registry stored in `.watcher-state/whatsapp-dedup.json`.
- **FR-008**: System MUST capture messages from both individual and group conversations.
- **FR-009**: System MUST log errors to `<VAULT_PATH>/Logs/` using the existing logging pattern with actionable error messages.
- **FR-010**: System MUST follow the Ralph Wiggum retry pattern (3 attempts with escalating strategies) for transient failures.
- **FR-011**: System MUST read vault path from environment variable `VAULT_PATH` (default: current directory).
- **FR-012**: System MUST support `--dry-run` flag to preview which messages would be captured without writing files.
- **FR-013**: System MUST persist Playwright session data (cookies, localStorage) to `.watcher-state/whatsapp/` for session reuse.
- **FR-014**: System MUST create `.watcher-state/whatsapp/` directory automatically if it doesn't exist.
- **FR-015**: System MUST NOT send, reply to, or delete any WhatsApp messages (read-only operation).
- **FR-016**: System MUST support configurable urgency keywords via environment variable `WHATSAPP_URGENCY_KEYWORDS` (default: "URGENT,ASAP,emergency,call me,time-sensitive").

### Non-Functional Requirements

- **NFR-001**: Poll cycle completes in under 45 seconds for up to 20 unread conversations.
- **NFR-002**: Watcher process uses under 300MB memory during steady-state operation (includes Chromium overhead).
- **NFR-003**: Session data stored with file permissions restricting access to owner only.

### Key Entities

- **WhatsAppSession**: Playwright browser context with persisted cookies and localStorage stored in `.watcher-state/whatsapp/`.
- **WhatsAppMessage**: Data extracted from WhatsApp Web representing a single message (message_id, sender, chat_name, chat_type, timestamp, body, has_media, media_type).
- **WhatsAppConversation**: A chat thread (individual or group) containing messages.
- **CapturedMessageFile**: Markdown file written to vault with frontmatter and body content.
- **DeduplicationState**: Hash registry mapping message hashes to capture timestamps, persisted to `.watcher-state/whatsapp-dedup.json`.

### Required Metadata Fields (YAML Frontmatter)

Each captured WhatsApp message MUST include the following frontmatter:

```yaml
---
source: whatsapp
captured_at: 2026-03-22T14:30:00Z    # ISO 8601 timestamp of capture
sender: "Contact Name"               # Message sender name
chat_name: "Contact or Group Name"   # Conversation name
chat_type: individual | group        # Chat type
message_timestamp: 2026-03-22T14:25:00Z  # Original message timestamp
urgency: normal | urgent             # Based on keyword matching
status: unread                       # Always "unread" at capture
has_media: true | false              # Whether message contains media
media_type: image | video | audio | document | null  # Media type if present
tags: [inbox, whatsapp]              # Standard tags
hash: "abc123def456"                 # Deduplication hash
---
```

### Vault Folder Structure

```
<VAULT_PATH>/
├── Inbox/
│   └── whatsapp/                    # Normal messages
│       ├── 2026-03-22-contact-name-143000.md
│       └── 2026-03-22-group-name-sender-143500.md
├── Needs_Action/
│   └── whatsapp/                    # Urgent messages
│       └── 2026-03-22-contact-name-URGENT-144000.md
└── Logs/
    └── whatsapp-watcher-2026-03-22.md  # Daily log file
```

### Logging Requirements

- **Log Location**: `<VAULT_PATH>/Logs/whatsapp-watcher-<YYYY-MM-DD>.md`
- **Log Format**: Append-only markdown with timestamped entries
- **Required Log Events**:
  - Poll cycle start/end with message count
  - Each captured message (sender, chat, urgency)
  - Skipped duplicates (hash reference)
  - Errors with actionable remediation steps
  - Session events (authentication, expiration)

### Failure Behavior

| Failure Type | Behavior | User Action |
|--------------|----------|-------------|
| Session expired/invalid | Log error, exit with code 1 | Run `whatsapp-watcher --auth` |
| Network timeout | Ralph Wiggum retry (3x), then log and continue | Check internet, wait for next poll |
| Selector not found | Ralph Wiggum retry (3x), then log and skip conversation | Check for watcher updates |
| Page load timeout | Ralph Wiggum retry (3x), then log and continue | Increase timeout via env |
| QR code scan timeout | Exit headed mode with clear message | Re-run `--auth` and scan faster |
| Dedup state corrupted | Reset state file, log warning, process all as new | Automatic recovery |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can capture WhatsApp messages into their Obsidian vault without manual copy-paste after initial QR code authentication.
- **SC-002**: 100% of unread messages from monitored conversations are captured within one poll interval (default 60 seconds).
- **SC-003**: Zero duplicate message files are created for messages already captured in previous sessions.
- **SC-004**: When errors occur, 100% of error log entries contain actionable remediation steps.
- **SC-005**: Watcher can run for 4+ hours continuously without manual intervention (suitable for hackathon/demo duration).
- **SC-006**: Messages with urgency keywords are correctly routed to `/Needs_Action/whatsapp/` 100% of the time.
- **SC-007**: Both individual and group chat messages are captured with appropriate metadata differentiation.

## Assumptions

- User has WhatsApp installed on their phone and can scan QR codes.
- User's phone remains connected to the internet during watcher operation (WhatsApp Web requirement).
- WhatsApp Web is accessible from the user's network (not blocked by firewall).
- Playwright is installed and Chromium browser is available.
- The existing vault structure (`/Inbox`, `/Needs_Action`, `/Logs`) exists (created by vault sentinel).
- `.watcher-state/` directory is excluded from version control via `.gitignore`.
- WhatsApp Web UI selectors are relatively stable for hackathon duration (UI changes may break selectors).

## Out of Scope (Non-Goals)

- **No reply sending**: System MUST NOT send, reply to, or forward WhatsApp messages.
- **No Facebook integration**: No Facebook Messenger or Meta platform features.
- **No LinkedIn changes**: No modifications to LinkedIn publisher or related features.
- **No MCP server changes**: No modifications to MCP server configurations.
- **No media downloads**: Media files (images, videos, documents) are not downloaded; only metadata is captured.
- **No message deletion**: System does not mark messages as read or delete them in WhatsApp.
- **No real-time push**: Poll-based monitoring only; no WebSocket or push notification integration.
- **No multi-account support**: Single WhatsApp account per watcher instance.
- **No Gmail/Router/HITL modifications**: Existing Gmail watcher, router, and HITL systems are unchanged.
- **No constitution amendments**: This phase operates within existing Silver Tier authorization.

## Dependencies

- **Existing Infrastructure**:
  - Vault sentinel (Bronze Tier) — folder structure must exist
  - Logging pattern from `sentinel.logger` module
  - Ralph Wiggum retry pattern implementation
- **External Dependencies**:
  - Playwright Python library (`playwright >= 1.40`)
  - Chromium browser (installed via `playwright install chromium`)
  - WhatsApp Web (web.whatsapp.com)
  - User's phone with WhatsApp for QR authentication

## Security Considerations

- Session data in `.watcher-state/whatsapp/` contains authentication cookies — MUST be in `.gitignore`.
- No credentials are stored in code or environment variables (QR-based auth).
- Playwright runs headless by default to minimize attack surface.
- Read-only operation limits blast radius of potential exploits.

## Test Scenarios

### Unit Tests

1. **Hash Generation**: Verify deterministic hash from message attributes.
2. **Urgency Detection**: Verify keyword matching is case-insensitive and handles edge cases.
3. **Frontmatter Generation**: Verify valid YAML frontmatter for all message types.
4. **Filename Generation**: Verify filename sanitization for special characters.

### Integration Tests

1. **End-to-End Capture**: Authenticated session → poll → markdown file created.
2. **Deduplication**: Same message polled twice → only one file created.
3. **Urgency Routing**: Message with "URGENT" → routed to `/Needs_Action/whatsapp/`.
4. **Group Message**: Group chat message → includes group_name and sender.
5. **Error Logging**: Session expired → actionable log entry created.

### Manual Test Scenarios (Hackathon)

1. Run `--auth`, scan QR code, verify session persists.
2. Send test message, run poll, verify markdown file appears.
3. Stop watcher, restart, verify no duplicate files.
4. Send "URGENT" message, verify routing to `/Needs_Action/`.
5. Disconnect network, verify Ralph Wiggum retry behavior.
6. Log out from phone, verify session expiration is detected and logged.
