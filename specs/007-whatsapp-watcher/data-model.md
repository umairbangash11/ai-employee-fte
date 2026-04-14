# Data Model: WhatsApp Watcher

**Feature Branch**: `007-whatsapp-watcher`
**Created**: 2026-03-22

## Overview

This document defines the data structures for the WhatsApp watcher module. Models follow the pattern established by `gmail_watcher.models` for consistency.

---

## Core Entities

### WhatsAppMessage

Data extracted from WhatsApp Web representing a single message.

```python
@dataclass
class WhatsAppMessage:
    """Data extracted from WhatsApp Web representing a single message."""

    # Identification
    hash: str                    # SHA-256 hash for deduplication

    # Chat context
    chat_name: str               # Contact or group name
    chat_type: str               # "individual" | "group"

    # Message content
    sender: str                  # Message author (same as chat_name for individual)
    timestamp: datetime          # Original message timestamp
    body: str                    # Message text content

    # Media indicators
    has_media: bool = False      # Whether message contains media
    media_type: str | None = None  # "image" | "video" | "audio" | "document" | None

    # Derived properties
    @property
    def urgency(self) -> str:
        """Return 'urgent' if body contains urgency keywords, else 'normal'."""
        # Implementation checks against config keywords
        pass

    @property
    def is_group(self) -> bool:
        """True if message is from a group chat."""
        return self.chat_type == "group"
```

**Field Mapping from WhatsApp Web DOM**:

| Field | DOM Source |
|-------|------------|
| chat_name | Conversation header title |
| chat_type | Presence of group icon or multiple senders |
| sender | Author span in message (groups) or chat_name (individual) |
| timestamp | Message timestamp element |
| body | `.selectable-text` span content |
| has_media | Presence of media container element |
| media_type | Media icon type or file extension |

---

### WhatsAppConversation

A chat thread containing messages to process.

```python
@dataclass
class WhatsAppConversation:
    """A WhatsApp chat thread (individual or group)."""

    chat_name: str               # Display name of conversation
    chat_type: str               # "individual" | "group"
    unread_count: int            # Number of unread messages
    messages: list[WhatsAppMessage] = field(default_factory=list)
```

---

### DeduplicationState

Hash registry tracking captured messages to prevent duplicates.

```python
@dataclass
class DeduplicationState:
    """Hash registry tracking captured messages to prevent duplicates."""

    version: int = 1
    last_poll: datetime | None = None
    message_hashes: dict[str, str] = field(default_factory=dict)  # hash -> captured_at ISO
```

**Persistence**: `.watcher-state/whatsapp-dedup.json`

**JSON Schema**:
```json
{
  "version": 1,
  "last_poll": "2026-03-22T14:30:00Z",
  "message_hashes": {
    "abc123def456": "2026-03-22T14:25:00Z",
    "789xyz012abc": "2026-03-22T14:26:00Z"
  }
}
```

---

### WatcherConfig

Configuration loaded from environment variables.

```python
@dataclass
class WatcherConfig:
    """Configuration for WhatsApp watcher."""

    vault_path: Path             # VAULT_PATH env, default: cwd
    poll_interval: int           # WHATSAPP_POLL_INTERVAL, default: 60
    urgency_keywords: list[str]  # WHATSAPP_URGENCY_KEYWORDS, default: [URGENT, ASAP, ...]
    session_path: Path           # .watcher-state/whatsapp/
    dedup_path: Path             # .watcher-state/whatsapp-dedup.json
    dry_run: bool                # --dry-run flag
    headless: bool               # True for normal operation, False for --auth
```

---

### CapturedMessageFile

Represents a Markdown file written to the vault.

```python
@dataclass
class CapturedMessageFile:
    """Markdown file written to vault with frontmatter and body."""

    message: WhatsAppMessage     # Source message
    filepath: Path               # Destination path in vault
    frontmatter: str             # YAML frontmatter content
    body: str                    # Markdown body content

    @property
    def full_content(self) -> str:
        """Return complete file content."""
        return f"{self.frontmatter}\n\n{self.body}\n"
```

---

## File Schemas

### YAML Frontmatter (spec-defined)

```yaml
---
source: whatsapp
captured_at: "2026-03-22T14:30:00Z"
sender: "Contact Name"
chat_name: "Contact or Group Name"
chat_type: individual | group
message_timestamp: "2026-03-22T14:25:00Z"
urgency: normal | urgent
status: unread
has_media: true | false
media_type: image | video | audio | document | null
tags: [inbox, whatsapp]
hash: "abc123def456"
---
```

### Markdown Body Template

```markdown
# Message from {sender}

**Chat**: {chat_name}
**Type**: {chat_type}
**Date**: {message_timestamp formatted}

---

{body content}

{media placeholder if has_media}
```

**Media Placeholders**:
- `[Image attached]`
- `[Video attached]`
- `[Voice note attached]`
- `[Document: filename.ext]`

---

### Log Entry Schema

Daily log file: `<VAULT_PATH>/Logs/whatsapp-watcher-<YYYY-MM-DD>.md`

```yaml
---
log_type: whatsapp-watcher
date: "2026-03-22"
---
```

**Entry Format**:
```markdown
### [HH:MM:SS] Poll Cycle

- **Status**: success | partial | failed
- **Messages found**: N
- **New captures**: N
- **Duplicates skipped**: N
- **Urgent messages**: N
- **Errors**: N

| Chat | Sender | Type | Urgency | Result |
|------|--------|------|---------|--------|
| ... | ... | ... | ... | captured/skipped/error |
```

**Error Entry Format**:
```markdown
### [HH:MM:SS] Error

- **Type**: session_expired | network_timeout | selector_failed | page_timeout
- **Attempt**: 1/2/3
- **Message**: {actionable error message}
- **Action**: {user remediation steps}
```

---

## Filename Conventions

### Message Files

Pattern: `{YYYY-MM-DD}-{chat_slug}-{HHMMSS}.md`

Examples:
- Individual: `2026-03-22-john-doe-143000.md`
- Group: `2026-03-22-work-group-alice-143500.md`
- Urgent: `2026-03-22-john-doe-URGENT-144000.md`

**Slug Rules**:
- Lowercase
- Replace spaces with hyphens
- Remove special characters
- Limit to 50 characters
- Append sender name for groups to distinguish authors

### Log Files

Pattern: `whatsapp-watcher-{YYYY-MM-DD}.md`

Example: `whatsapp-watcher-2026-03-22.md`

---

## State Transitions

### Message State

```
[DOM Element] → [WhatsAppMessage] → [Hash Check] → [CapturedMessageFile] → [Vault]
                                         ↓
                                   [Duplicate → Skip]
```

### Session State

```
[No Session] → [--auth] → [QR Scan] → [Session Saved] → [Headless Polling]
                                             ↓
                                      [Session Expired] → [Exit + Error Log]
```

### Poll Cycle State

```
[Idle] → [Poll Start] → [Load Conversations] → [Process Each] → [Log Results] → [Idle]
                              ↓                      ↓
                        [Page Error]           [Message Error]
                              ↓                      ↓
                      [Ralph Wiggum Retry]    [Skip + Log]
```

---

## Validation Rules

### WhatsAppMessage

| Field | Validation |
|-------|------------|
| hash | 16-character hex string |
| chat_name | Non-empty string |
| chat_type | One of: "individual", "group" |
| sender | Non-empty string |
| timestamp | Valid datetime |
| body | String (may be empty for media-only) |
| media_type | One of: "image", "video", "audio", "document", None |

### WatcherConfig

| Field | Validation |
|-------|------------|
| vault_path | Existing directory with Inbox/, Needs_Action/, Logs/ |
| poll_interval | Positive integer, minimum 30 |
| urgency_keywords | Non-empty list of strings |
| session_path | Writable directory path |
