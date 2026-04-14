# Implementation Plan: WhatsApp Watcher — Message Ingestion

**Branch**: `007-whatsapp-watcher` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-whatsapp-watcher/spec.md`

## Summary

Implement a WhatsApp Web watcher that polls for unread messages via Playwright browser automation, converts them to Obsidian-compatible Markdown files with YAML frontmatter, and routes them to the vault's `/Inbox/whatsapp/` or `/Needs_Action/whatsapp/` directories. The watcher operates headless after initial QR code authentication and deduplicates messages across restarts. This is read-only ingestion only — no message sending.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Playwright (>=1.40), python-dotenv (>=1.0)
**Storage**: Local filesystem (JSON state files, Markdown vault files)
**Testing**: pytest, manual hackathon validation
**Target Platform**: Linux (WSL2), local development
**Project Type**: Single project (CLI module within monorepo)
**Performance Goals**: <45s poll cycle for 20 unread conversations
**Constraints**: <300MB memory, 4+ hour continuous operation
**Scale/Scope**: Single WhatsApp account, hackathon/demo use case

## Constitution Check

*GATE: Must pass before implementation. All principles validated.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First Operations | ✅ PASS | All processing local; Playwright runs locally |
| II. Canonical Folder Structure | ✅ PASS | Routes to `/Inbox/whatsapp/`, `/Needs_Action/whatsapp/`, `/Logs/` |
| III. Tiered Scope | ✅ PASS | WhatsApp monitoring is ratified Silver Tier capability |
| IV. Safety-First Execution | ✅ PASS | Read-only operation; no system-modifying actions |
| V. Ralph Wiggum Loop | ✅ PASS | 3-attempt retry pattern for all transient failures |
| VI. Silver Tier Autonomy | ✅ PASS | Read-only monitoring via Playwright; no external actions |
| VII. Phased Development | ✅ PASS | This is a distinct feature phase; no scope mixing |
| VIII. Gmail API Migration | ✅ N/A | Gmail rules do not apply to WhatsApp (Playwright permitted) |

**Operational Constraints Compliance**:
- ✅ No secrets in code: Session data in `.watcher-state/` (gitignored)
- ✅ Smallest viable diff: New module only; no existing code modified
- ✅ Audit trail: All captures logged to `/Logs/`
- ✅ Obsidian compatibility: Valid Markdown with YAML frontmatter
- ✅ Playwright security: Headless by default; headed only for `--auth`

## Project Structure

### Documentation (this feature)

```text
specs/007-whatsapp-watcher/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Technical decisions
├── data-model.md        # Entity definitions
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks.md             # Implementation tasks (created by /sp.tasks)
```

### Source Code (repository root)

```text
src/
├── whatsapp_watcher/           # NEW MODULE
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # CLI entrypoint (whatsapp-watcher command)
│   ├── config.py               # Environment config loading
│   ├── models.py               # Data classes (WhatsAppMessage, etc.)
│   ├── selectors.py            # WhatsApp Web DOM selectors
│   ├── session.py              # Playwright session management
│   ├── scraper.py              # Message extraction from DOM
│   ├── writer.py               # Markdown file generation
│   ├── state.py                # Deduplication state persistence
│   └── logger.py               # Watcher-specific logging
├── gmail_watcher/              # EXISTING (unchanged)
├── sentinel/                   # EXISTING (unchanged)
├── router/                     # EXISTING (unchanged)
├── orchestrator/               # EXISTING (unchanged)
└── ...

tests/
├── unit/
│   └── whatsapp_watcher/       # Unit tests
│       ├── test_models.py
│       ├── test_selectors.py
│       ├── test_state.py
│       └── test_writer.py
└── integration/
    └── whatsapp_watcher/       # Integration tests
        └── test_end_to_end.py
```

**Structure Decision**: Single project pattern matching existing `gmail_watcher/` module layout for consistency.

---

## Implementation Sections

### 1. Session Handling

**Objective**: Manage Playwright browser sessions for WhatsApp Web authentication and polling.

**Components**:
- `session.py`: Session management functions
- `.watcher-state/whatsapp/storage_state.json`: Persisted session data

**Key Functions**:

```python
# session.py

def create_auth_session(session_path: Path, timeout: int = 120) -> bool:
    """Open headed browser for QR code authentication.

    1. Launch Chromium in headed mode
    2. Navigate to web.whatsapp.com
    3. Wait for QR code scan (user scans with phone)
    4. Wait for main interface to load
    5. Save session state to storage_state.json
    6. Return True on success, False on timeout
    """

def create_headless_session(session_path: Path) -> BrowserContext:
    """Create headless browser context with saved session.

    1. Load storage_state.json
    2. Launch Chromium headless
    3. Create context with storage_state
    4. Return browser context for polling
    """

def validate_session(context: BrowserContext) -> bool:
    """Check if session is still valid.

    1. Navigate to WhatsApp Web
    2. Check for QR code element (indicates logged out)
    3. Check for main chat interface (indicates logged in)
    4. Return True if valid, False if expired
    """
```

**Session Flow**:
```
--auth mode:
[Launch Headed] → [Show QR] → [User Scans] → [Save State] → [Exit]

Normal mode:
[Load State] → [Launch Headless] → [Validate] → [Poll Loop]
                                       ↓
                              [Invalid → Exit(1)]
```

**Error Handling**:
- Session file missing: Exit with message "Run `whatsapp-watcher --auth` first"
- Session expired: Log actionable error, exit with code 1
- Network error: Ralph Wiggum retry (3x)

---

### 2. Message Detection

**Objective**: Detect and extract unread messages from WhatsApp Web DOM.

**Components**:
- `selectors.py`: WhatsApp Web DOM selectors (centralized for easy updates)
- `scraper.py`: Message extraction logic

**Selector Strategy**:

```python
# selectors.py

class Selectors:
    """WhatsApp Web DOM selectors.

    Centralized for easy updates when WhatsApp UI changes.
    """

    # Chat list (left panel)
    CHAT_LIST = '[data-testid="chat-list"]'
    CHAT_ITEM = '[data-testid="cell-frame-container"]'
    UNREAD_BADGE = 'span[data-testid="icon-unread-count"]'
    CHAT_TITLE = 'span[data-testid="cell-frame-title"] span'

    # Conversation view (right panel)
    CONVERSATION_PANEL = '[data-testid="conversation-panel-messages"]'
    MESSAGE_ROW = '[data-testid="msg-container"]'
    MESSAGE_TEXT = 'span.selectable-text'
    MESSAGE_TIME = '[data-testid="msg-time"]'

    # Group chat indicators
    GROUP_ICON = '[data-testid="group"]'
    MESSAGE_AUTHOR = 'span[data-testid="author"]'

    # Media indicators
    MEDIA_IMAGE = '[data-testid="media-url-provider"]'
    MEDIA_DOCUMENT = '[data-testid="document-thumb"]'
    MEDIA_AUDIO = '[data-testid="audio-play"]'
```

**Scraping Flow**:

```python
# scraper.py

def get_unread_conversations(page: Page) -> list[dict]:
    """Find all conversations with unread badges.

    Returns list of {chat_name, unread_count, element} dicts.
    """

def extract_messages(page: Page, chat_element) -> list[WhatsAppMessage]:
    """Click into chat and extract unread messages.

    1. Click chat element to open conversation
    2. Wait for conversation panel to load
    3. Find message rows
    4. Extract: sender, timestamp, body, media indicators
    5. Return list of WhatsAppMessage objects
    """

def detect_chat_type(page: Page) -> str:
    """Determine if current chat is individual or group.

    Check for group icon or multiple distinct senders.
    Returns "individual" or "group".
    """

def extract_media_info(message_element) -> tuple[bool, str | None]:
    """Extract media type from message element.

    Returns (has_media, media_type).
    media_type is one of: "image", "video", "audio", "document", None
    """
```

**Error Handling**:
- Selector not found: Ralph Wiggum retry with simplified selectors
- Page timeout: Increase timeout on retry
- Stale element: Refresh and retry

---

### 3. Markdown Generation

**Objective**: Convert extracted messages to Obsidian-compatible Markdown files.

**Components**:
- `writer.py`: Markdown file generation (mirrors `gmail_watcher/writer.py` pattern)

**Key Functions**:

```python
# writer.py

def generate_filename(message: WhatsAppMessage) -> str:
    """Generate filename from date, chat slug, and time.

    Pattern: {YYYY-MM-DD}-{chat_slug}-{sender_slug}-{HHMMSS}.md
    Add "URGENT" suffix for urgent messages.
    """

def generate_frontmatter(message: WhatsAppMessage, captured_at: datetime) -> str:
    """Generate YAML frontmatter per spec requirements.

    Includes all 12 required fields from spec.
    """

def generate_body(message: WhatsAppMessage) -> str:
    """Generate Markdown body content.

    # Message from {sender}

    **Chat**: {chat_name}
    **Type**: {chat_type}
    **Date**: {timestamp}

    ---

    {body content}

    {media placeholder if present}
    """

def determine_destination(message: WhatsAppMessage, vault_path: Path) -> Path:
    """Return /Inbox/whatsapp/ or /Needs_Action/whatsapp/ based on urgency."""

def write_message_file(
    message: WhatsAppMessage,
    vault_path: Path,
    dry_run: bool = False,
) -> Path | None:
    """Write message as Markdown file to vault.

    Returns filepath on success, None if dry_run.
    """
```

**Frontmatter Schema** (from spec):

```yaml
---
source: whatsapp
captured_at: "2026-03-22T14:30:00Z"
sender: "Contact Name"
chat_name: "Contact or Group Name"
chat_type: individual
message_timestamp: "2026-03-22T14:25:00Z"
urgency: normal
status: unread
has_media: false
media_type: null
tags: [inbox, whatsapp]
hash: "abc123def456"
---
```

---

### 4. Vault Routing

**Objective**: Route messages to appropriate vault directories based on urgency.

**Routing Rules** (from spec FR-006):

| Condition | Destination |
|-----------|-------------|
| Message body contains urgency keyword | `/Needs_Action/whatsapp/` |
| Normal message | `/Inbox/whatsapp/` |

**Urgency Detection**:

```python
# In models.py or writer.py

def is_urgent(body: str, keywords: list[str]) -> bool:
    """Case-insensitive substring match against keywords."""
    body_lower = body.lower()
    return any(kw.lower() in body_lower for kw in keywords)
```

**Default Keywords** (from spec FR-016):
```
URGENT, ASAP, emergency, call me, time-sensitive
```

**Folder Creation**:
- `Inbox/whatsapp/` and `Needs_Action/whatsapp/` created on first write
- Assumes parent directories exist (Bronze Tier vault sentinel)

---

### 5. Deduplication

**Objective**: Prevent duplicate message files across poll cycles and restarts.

**Components**:
- `state.py`: Deduplication state persistence (mirrors `gmail_watcher/state.py`)
- `.watcher-state/whatsapp-dedup.json`: Persistent hash registry

**Hash Computation**:

```python
import hashlib

def compute_hash(chat_name: str, sender: str, timestamp: str, body: str) -> str:
    """Generate deterministic hash for message deduplication.

    Uses SHA-256 of: whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}
    Returns first 16 hex characters.
    """
    content = f"whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**State Functions**:

```python
# state.py

def load_state(path: Path) -> DeduplicationState:
    """Load state from JSON, return empty state if missing/corrupt."""

def save_state(state: DeduplicationState, path: Path) -> None:
    """Persist state to JSON, create directory if needed."""

def is_captured(state: DeduplicationState, hash: str) -> bool:
    """Check if message hash exists in registry."""

def mark_captured(state: DeduplicationState, hash: str) -> None:
    """Add hash to registry with current timestamp."""
```

**Corruption Recovery**:
- If JSON parse fails: Log warning, reset to empty state
- This causes re-capture of all messages (safe, just creates duplicates temporarily)

---

### 6. Logging

**Objective**: Maintain audit trail of watcher activity in vault-compatible format.

**Components**:
- `logger.py`: Watcher-specific logging functions

**Log Location**: `<VAULT_PATH>/Logs/whatsapp-watcher-<YYYY-MM-DD>.md`

**Log Functions**:

```python
# logger.py

def get_log_path(vault_path: Path, date: datetime) -> Path:
    """Return path to daily log file."""

def ensure_log_file(log_path: Path) -> None:
    """Create log file with frontmatter if it doesn't exist."""

def log_poll_start(log_path: Path, timestamp: datetime) -> None:
    """Append poll cycle start entry."""

def log_poll_result(
    log_path: Path,
    timestamp: datetime,
    messages_found: int,
    new_captures: int,
    duplicates_skipped: int,
    urgent_count: int,
    results: list[dict],  # [{chat, sender, urgency, status}, ...]
) -> None:
    """Append poll cycle result entry."""

def log_error(
    log_path: Path,
    timestamp: datetime,
    error_type: str,
    attempt: int,
    message: str,
    action: str,
) -> None:
    """Append error entry with actionable remediation."""
```

**Log Entry Format**:

```markdown
### [14:30:00] Poll Cycle

- **Status**: success
- **Messages found**: 5
- **New captures**: 3
- **Duplicates skipped**: 2
- **Urgent messages**: 0

| Chat | Sender | Type | Urgency | Result |
|------|--------|------|---------|--------|
| John Doe | John Doe | individual | normal | captured |
| Work Group | Alice | group | normal | captured |
| Family | Mom | group | normal | duplicate |
```

**Error Entry Format**:

```markdown
### [14:35:00] Error

- **Type**: selector_failed
- **Attempt**: 2/3
- **Message**: Could not find chat list element
- **Action**: Retrying with simplified selector...
```

---

### 7. Testing

**Objective**: Validate implementation meets spec requirements.

#### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_models.py` | WhatsAppMessage, DeduplicationState validation |
| `test_selectors.py` | Selector string constants |
| `test_state.py` | load_state, save_state, is_captured, mark_captured |
| `test_writer.py` | generate_filename, generate_frontmatter, determine_destination |

**Unit Test Examples**:

```python
# test_writer.py

def test_generate_filename_individual():
    msg = WhatsAppMessage(
        hash="abc123",
        chat_name="John Doe",
        chat_type="individual",
        sender="John Doe",
        timestamp=datetime(2026, 3, 22, 14, 30, 0),
        body="Hello world",
    )
    filename = generate_filename(msg)
    assert filename == "2026-03-22-john-doe-143000.md"

def test_generate_filename_urgent():
    msg = WhatsAppMessage(..., body="URGENT: Call me!")
    filename = generate_filename(msg)
    assert "URGENT" in filename

def test_is_urgent_case_insensitive():
    assert is_urgent("Please call ASAP", ["asap"]) == True
    assert is_urgent("No urgency here", ["urgent"]) == False
```

#### Integration Tests

| Test | Description |
|------|-------------|
| End-to-End Capture | Mock Playwright → Extract → Write → Verify file |
| Deduplication | Process same message twice → Only one file |
| Urgency Routing | Message with keyword → `/Needs_Action/whatsapp/` |
| Session Recovery | Corrupt state → Fresh start |

#### Manual Test Scenarios (Hackathon)

Per spec Test Scenarios section:

1. **QR Authentication**: Run `--auth`, scan QR, verify session persists
2. **Message Capture**: Send test message, run poll, verify markdown file
3. **Deduplication**: Stop watcher, restart, verify no duplicate files
4. **Urgency Routing**: Send "URGENT" message, verify routing
5. **Network Error**: Disconnect network, verify Ralph Wiggum retry
6. **Session Expiration**: Log out from phone, verify error logged

---

## CLI Interface

**Entrypoint**: `python -m whatsapp_watcher` or `whatsapp-watcher` (via pyproject.toml)

**Commands**:

```bash
# One-time authentication (headed mode)
whatsapp-watcher --auth

# Normal polling (headless mode)
whatsapp-watcher

# Dry run (preview without writing)
whatsapp-watcher --dry-run

# Single poll cycle (useful for testing)
whatsapp-watcher --once
```

**Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `.` | Path to vault root |
| `WHATSAPP_POLL_INTERVAL` | `60` | Seconds between polls |
| `WHATSAPP_URGENCY_KEYWORDS` | `URGENT,ASAP,...` | Comma-separated list |
| `WHATSAPP_PAGE_TIMEOUT` | `30000` | Page load timeout (ms) |

---

## Execution Flow

### Main Poll Loop

```python
# __main__.py

def main():
    # 1. Load config
    config = load_config()

    # 2. Handle --auth mode
    if args.auth:
        success = create_auth_session(config.session_path)
        sys.exit(0 if success else 1)

    # 3. Validate session exists
    if not config.session_path.exists():
        print("No session found. Run `whatsapp-watcher --auth` first.")
        sys.exit(1)

    # 4. Create headless browser
    context = create_headless_session(config.session_path)
    page = context.new_page()

    # 5. Load deduplication state
    state = load_state(config.dedup_path)

    # 6. Poll loop
    while True:
        try:
            poll_cycle(page, state, config)
            save_state(state, config.dedup_path)
        except SessionExpired:
            log_error("session_expired", ...)
            sys.exit(1)
        except Exception as e:
            log_error(str(e), ...)

        if args.once:
            break

        time.sleep(config.poll_interval)

def poll_cycle(page: Page, state: DeduplicationState, config: WatcherConfig):
    """Single poll cycle with Ralph Wiggum retry."""

    log_poll_start(...)

    # Navigate to WhatsApp Web
    page.goto("https://web.whatsapp.com")

    # Get unread conversations
    conversations = get_unread_conversations(page)  # With retry

    results = []
    for conv in conversations:
        messages = extract_messages(page, conv)  # With retry

        for msg in messages:
            if is_captured(state, msg.hash):
                results.append({..., "status": "duplicate"})
                continue

            write_message_file(msg, config.vault_path, config.dry_run)
            mark_captured(state, msg.hash)
            results.append({..., "status": "captured"})

    log_poll_result(...)
```

---

## Complexity Tracking

No constitution violations to justify. Implementation follows all principles.

| Aspect | Justification |
|--------|---------------|
| Playwright dependency | Required by constitution for WhatsApp (Principle VI) |
| New module | Smallest viable diff; no existing code modified |
| DOM selectors | Necessary for browser automation; centralized for updates |

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WhatsApp UI changes | Medium | High | Centralized selectors, clear error messages |
| Session expiration | Medium | Low | Actionable error, easy re-auth |
| Network failures | Low | Low | Ralph Wiggum retry handles transient issues |
| Memory usage | Low | Medium | Headless Chromium is ~200-300MB (within spec) |

---

## Dependencies

### New Dependencies

None — Playwright already in pyproject.toml for LinkedIn publisher.

### Existing Dependencies Used

| Dependency | Usage |
|------------|-------|
| `playwright` | Browser automation |
| `python-dotenv` | Environment config |
| `pathlib` | Path handling (stdlib) |
| `dataclasses` | Data models (stdlib) |
| `hashlib` | Hash computation (stdlib) |
| `json` | State persistence (stdlib) |

---

## Next Steps

After plan approval:

1. Run `/sp.tasks` to generate implementation tasks
2. Tasks will follow this order:
   - T1: Create module skeleton with `__init__.py`, `__main__.py`
   - T2: Implement `config.py` and `models.py`
   - T3: Implement `session.py` (auth flow)
   - T4: Implement `selectors.py` and `scraper.py`
   - T5: Implement `state.py` (deduplication)
   - T6: Implement `writer.py` (markdown generation)
   - T7: Implement `logger.py` (audit logging)
   - T8: Wire up `__main__.py` poll loop
   - T9: Add unit tests
   - T10: Manual integration testing
