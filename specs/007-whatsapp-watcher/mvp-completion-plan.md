# Implementation Plan: WhatsApp Watcher MVP Completion

**Feature**: 007-whatsapp-watcher
**Scope**: Complete remaining MVP modules only (session, scraper, writer, state, poll-loop)
**Date**: 2026-04-12
**Branch**: 008-facebook-post-execution (will create feature branch)

---

## Executive Summary

This plan completes the WhatsApp Watcher MVP by implementing 5 missing modules that will enable automated capture of WhatsApp Web messages into the Obsidian vault. The existing foundation (config, models, selectors) provides data structures and DOM selectors; this plan adds the core logic for browser automation, message extraction, markdown generation, deduplication, and polling orchestration.

**Implementation Goal**: Enable headless monitoring of WhatsApp Web with QR-based authentication, capturing unread messages as Markdown files in `/Inbox/whatsapp/` or `/Needs_Action/whatsapp/` based on urgency keywords.

**Target Pipeline**:
```
session/auth → scrape → normalize → write → state/dedup
```

**Estimated Complexity**: ~800 LOC across 5 modules

---

## Foundation Analysis

### Existing Modules (Complete)

#### 1. config.py (73 LOC)
**Status**: ✅ Complete
**Provides**:
- `WatcherConfig` dataclass with all required settings
- `load_config()` function reading from environment variables
- Default values: poll_interval=60s, urgency_keywords, page_timeout=30s
- Session/state path configuration: `.watcher-state/whatsapp/`

**Key Contract**:
```python
@dataclass
class WatcherConfig:
    vault_path: Path
    poll_interval: int
    urgency_keywords: list[str]
    page_timeout: int
    session_path: Path  # .watcher-state/whatsapp/
    dedup_path: Path    # .watcher-state/whatsapp-dedup.json
    dry_run: bool = False
    headless: bool = True

    @property
    def storage_state_path(self) -> Path:
        return self.session_path / "storage_state.json"
```

**Reuse Strategy**: Import `load_config()` in poll-loop; pass config to all modules.

#### 2. models.py (102 LOC)
**Status**: ✅ Complete
**Provides**:
- `WhatsAppMessage` dataclass with hash property for deduplication
- `WhatsAppConversation` dataclass for chat threads
- `DeduplicationState` dataclass for persistent state
- `CapturedMessageFile` dataclass for markdown output
- `compute_hash()` function using SHA-256 of message attributes

**Key Contracts**:
```python
@dataclass
class WhatsAppMessage:
    chat_name: str
    chat_type: str  # "individual" | "group"
    sender: str
    timestamp: datetime
    body: str
    has_media: bool = False
    media_type: str | None = None

    @property
    def hash(self) -> str:
        """SHA-256 hash (16 chars) of message attributes for dedup."""

@dataclass
class DeduplicationState:
    version: int = 1
    last_poll: datetime | None = None
    message_hashes: dict[str, str] = field(default_factory=dict)  # hash -> captured_at
```

**Reuse Strategy**:
- Scraper returns `WhatsAppMessage` instances
- Writer accepts `WhatsAppMessage` and produces `CapturedMessageFile`
- State manager loads/saves `DeduplicationState`

#### 3. selectors.py (65 LOC)
**Status**: ✅ Complete
**Provides**:
- `Selectors` class with WhatsApp Web DOM selectors
- `Timeouts` class with operation timeout values
- QR code detection: `QR_CODE = 'canvas[aria-label="Scan me!"]'`
- Chat list: `CHAT_LIST = '[data-testid="chat-list"]'`
- Unread badge: `UNREAD_BADGE = 'span[data-testid="icon-unread-count"]'`
- Message rows: `MESSAGE_ROW = '[data-testid="msg-container"]'`

**Key Selectors for MVP**:
```python
class Selectors:
    QR_CODE = 'canvas[aria-label="Scan me!"]'
    MAIN_INTERFACE = '[data-testid="chat-list"]'
    CHAT_ITEM = '[data-testid="cell-frame-container"]'
    UNREAD_BADGE = 'span[data-testid="icon-unread-count"]'
    MESSAGE_ROW = '[data-testid="msg-container"]'
    MESSAGE_TEXT = "span.selectable-text"
    MESSAGE_TIME = '[data-testid="msg-time"]'
```

**Reuse Strategy**: Import `Selectors` in scraper; use for Playwright element queries.

#### 4. __main__.py (60 LOC)
**Status**: ⚠️ Stub Only (CLI structure exists, logic missing)
**Provides**:
- Argument parser with `--auth`, `--dry-run`, `--once` flags
- Entry point structure

**Gap**: No actual implementation — all branches print "not yet implemented"

**Completion Strategy**: Wire to session.py (auth mode) and poll-loop (normal mode) after those modules are complete.

---

## Missing Modules (To Implement)

### 1. session.py — Playwright Session Management

**Purpose**: Manage Playwright browser context with persistent WhatsApp Web authentication.

**File**: `src/whatsapp_watcher/session.py`

**Estimated LOC**: ~150

**Responsibilities**:
1. Initialize Playwright browser with session persistence
2. Detect QR code vs authenticated state
3. Handle QR code authentication flow (headed mode)
4. Reuse stored session for headless polling
5. Detect session expiration and report actionable errors

**Key Functions**:

```python
async def create_browser_context(
    config: WatcherConfig,
    playwright: Playwright
) -> BrowserContext:
    """Create Playwright browser context with persistent session.

    If config.headless=False (--auth mode):
        - Launch headed browser
        - Navigate to web.whatsapp.com
        - Wait for QR code scan or existing session
        - Save session to storage_state_path

    If config.headless=True (normal mode):
        - Launch headless browser
        - Load session from storage_state_path
        - Navigate to web.whatsapp.com
        - Verify session is valid

    Returns:
        BrowserContext ready for scraping

    Raises:
        SessionExpiredError: If session invalid and headless mode
        QRTimeoutError: If QR not scanned within timeout
    """

async def wait_for_whatsapp_ready(
    page: Page,
    timeout: int = 30000
) -> bool:
    """Wait for WhatsApp Web main interface to load.

    Returns:
        True if loaded successfully

    Raises:
        TimeoutError: If main interface not detected
    """

async def detect_session_state(page: Page) -> str:
    """Detect current session state.

    Returns:
        "qr_code" | "authenticated" | "loading"
    """

async def wait_for_qr_authentication(
    page: Page,
    timeout: int = 120000
) -> None:
    """Wait for user to scan QR code.

    Polls page state until QR code disappears and main interface loads.

    Raises:
        QRTimeoutError: If not scanned within timeout
    """
```

**Error Cases**:
- Session file corrupted → Delete and prompt re-auth
- Network unavailable → Ralph Wiggum retry (3x)
- QR code timeout → Exit with clear message
- Session expired → Exit with "Run `whatsapp-watcher --auth`"

**Session Persistence Strategy**:
- Playwright's `storage_state` option saves cookies and localStorage to JSON
- Path: `.watcher-state/whatsapp/storage_state.json`
- Reuse on subsequent launches via `context = browser.new_context(storage_state=path)`

**Implementation Sequence**:
1. Create `create_browser_context()` with headed/headless branching
2. Implement `detect_session_state()` checking for QR_CODE vs MAIN_INTERFACE
3. Implement `wait_for_qr_authentication()` with timeout
4. Implement `wait_for_whatsapp_ready()` verifying main interface loaded
5. Add error handling with custom exceptions

**Dependencies**:
- `playwright.async_api` (Playwright, Browser, BrowserContext, Page)
- `config.WatcherConfig`
- `selectors.Selectors`, `selectors.Timeouts`

---

### 2. scraper.py — WhatsApp Web Scraping

**Purpose**: Extract unread messages from WhatsApp Web using Playwright DOM queries.

**File**: `src/whatsapp_watcher/scraper.py`

**Estimated LOC**: ~250

**Responsibilities**:
1. Find all chat items with unread badges
2. Click into each unread conversation
3. Extract messages from conversation panel
4. Parse message metadata (sender, timestamp, body, media indicators)
5. Differentiate individual vs group chats
6. Return structured `WhatsAppMessage` instances

**Key Functions**:

```python
async def scrape_unread_messages(
    page: Page,
    config: WatcherConfig
) -> list[WhatsAppMessage]:
    """Scrape all unread messages from WhatsApp Web.

    Algorithm:
        1. Query chat list for items with unread badges
        2. For each unread chat:
            a. Click to open conversation
            b. Wait for messages to load
            c. Extract message elements
            d. Parse each message to WhatsAppMessage
            e. Navigate back to chat list
        3. Return all extracted messages

    Returns:
        List of WhatsAppMessage instances (may be empty)

    Raises:
        ScraperError: If critical selector fails after retries
    """

async def get_unread_chat_elements(page: Page) -> list[ElementHandle]:
    """Find all chat items with unread badges.

    Returns:
        List of chat item element handles
    """

async def extract_chat_info(chat_element: ElementHandle) -> dict:
    """Extract chat metadata from chat list item.

    Returns:
        {
            "chat_name": str,
            "chat_type": "individual" | "group",
            "unread_count": int
        }
    """

async def extract_messages_from_conversation(
    page: Page,
    chat_name: str,
    chat_type: str
) -> list[WhatsAppMessage]:
    """Extract messages from open conversation panel.

    Algorithm:
        1. Query all MESSAGE_ROW elements
        2. Filter to incoming messages only (skip MESSAGE_OUT)
        3. For each message row:
            a. Extract text from MESSAGE_TEXT
            b. Extract timestamp from MESSAGE_TIME
            c. Extract sender (for groups)
            d. Detect media indicators
        4. Build WhatsAppMessage instances

    Returns:
        List of WhatsAppMessage instances
    """

def parse_message_timestamp(time_str: str) -> datetime:
    """Parse WhatsApp Web timestamp to datetime.

    WhatsApp shows times as:
        - "14:30" (today)
        - "Yesterday"
        - "DD/MM/YYYY"

    Returns:
        Best-effort datetime (may use current date for "14:30" format)
    """

async def detect_media_type(message_element: ElementHandle) -> tuple[bool, str | None]:
    """Detect if message contains media and its type.

    Returns:
        (has_media: bool, media_type: str | None)
        media_type in ["image", "video", "audio", "document", None]
    """
```

**Message Extraction Strategy**:
- Use `page.query_selector_all(Selectors.MESSAGE_ROW)` to get message elements
- Filter to incoming messages: `message_element.query_selector(Selectors.MESSAGE_IN)`
- Extract text: `await text_element.text_content()`
- Extract timestamp: parse from `MESSAGE_TIME` element
- For groups: extract sender from `MESSAGE_AUTHOR` if present
- Media detection: check for `MEDIA_IMAGE`, `MEDIA_VIDEO`, etc. child elements

**Chat Type Detection**:
- Individual: No `GROUP_ICON` in conversation header
- Group: `GROUP_ICON` present in conversation header

**Retry Strategy (Ralph Wiggum Loop)**:
- If selector not found → wait 2s → retry → wait 4s → retry → fail
- If page load timeout → retry full scrape up to 3 times
- Log each retry attempt

**Implementation Sequence**:
1. Implement `get_unread_chat_elements()` with unread badge filter
2. Implement `extract_chat_info()` parsing chat name and type
3. Implement `extract_messages_from_conversation()` with message row parsing
4. Implement `parse_message_timestamp()` handling WhatsApp's time formats
5. Implement `detect_media_type()` checking for media indicators
6. Implement `scrape_unread_messages()` orchestrating full scrape flow
7. Add retry logic with Ralph Wiggum pattern

**Dependencies**:
- `playwright.async_api` (Page, ElementHandle)
- `config.WatcherConfig`
- `models.WhatsAppMessage`
- `selectors.Selectors`

---

### 3. writer.py — Markdown File Generation

**Purpose**: Convert `WhatsAppMessage` instances to Obsidian-compatible Markdown files with YAML frontmatter.

**File**: `src/whatsapp_watcher/writer.py`

**Estimated LOC**: ~200

**Responsibilities**:
1. Generate YAML frontmatter from message metadata
2. Format message body as Markdown
3. Determine urgency based on keyword matching
4. Route to `/Inbox/whatsapp/` or `/Needs_Action/whatsapp/`
5. Generate unique, filesystem-safe filenames
6. Write files atomically (temp file + rename)

**Key Functions**:

```python
def write_message_file(
    message: WhatsAppMessage,
    config: WatcherConfig,
    captured_at: datetime
) -> Path:
    """Write WhatsApp message to Markdown file in vault.

    Algorithm:
        1. Determine urgency by checking body for keywords
        2. Generate filename from timestamp, chat, sender
        3. Build frontmatter dict
        4. Format frontmatter as YAML
        5. Format body as Markdown
        6. Determine output directory (Inbox vs Needs_Action)
        7. Write file atomically
        8. Return Path to created file

    Args:
        message: WhatsAppMessage to write
        config: WatcherConfig with vault_path and urgency_keywords
        captured_at: Timestamp when message was captured

    Returns:
        Path to created markdown file

    Raises:
        WriteError: If file write fails
    """

def determine_urgency(body: str, keywords: list[str]) -> str:
    """Check if message body contains urgency keywords.

    Case-insensitive matching.

    Returns:
        "urgent" if any keyword found, else "normal"
    """

def generate_filename(
    message: WhatsAppMessage,
    urgency: str
) -> str:
    """Generate filesystem-safe filename for message.

    Format:
        {YYYYMMDD}-{HHMMSS}-{chat-slug}-{sender-slug}.md

    For urgent messages:
        {YYYYMMDD}-{HHMMSS}-URGENT-{chat-slug}.md

    Examples:
        20260322-143000-john-doe.md
        20260322-144500-URGENT-family-group.md

    Returns:
        Filename string (not path)
    """

def build_frontmatter(
    message: WhatsAppMessage,
    urgency: str,
    captured_at: datetime
) -> dict:
    """Build frontmatter dict from message.

    Returns:
        Dict with keys: source, captured_at, sender, chat_name, chat_type,
        message_timestamp, urgency, status, has_media, media_type, tags, hash
    """

def format_frontmatter(frontmatter: dict) -> str:
    """Format frontmatter dict as YAML block.

    Returns:
        "---\nkey: value\n...\n---\n"
    """

def format_body(message: WhatsAppMessage) -> str:
    """Format message body as Markdown.

    Structure:
        # {chat_name}

        **Sender**: {sender}
        **Timestamp**: {timestamp}

        {body}

        [Media: {media_type}] (if has_media)

    Returns:
        Markdown string
    """

def determine_output_directory(
    vault_path: Path,
    urgency: str
) -> Path:
    """Determine output directory based on urgency.

    Returns:
        vault_path / "Inbox" / "whatsapp" (if normal)
        vault_path / "Needs_Action" / "whatsapp" (if urgent)
    """

def write_file_atomic(content: str, filepath: Path) -> None:
    """Write file atomically using temp file + rename.

    Ensures no partial writes on crash.
    """
```

**Frontmatter Schema** (from spec):
```yaml
---
source: whatsapp
captured_at: 2026-03-22T14:30:00Z
sender: "Contact Name"
chat_name: "Contact or Group Name"
chat_type: individual | group
message_timestamp: 2026-03-22T14:25:00Z
urgency: normal | urgent
status: unread
has_media: true | false
media_type: image | video | audio | document | null
tags: [inbox, whatsapp]
hash: "abc123def456"
---
```

**Filename Sanitization**:
- Replace spaces with hyphens
- Remove special characters except hyphens and underscores
- Convert to lowercase
- Truncate to 100 chars max

**Urgency Keyword Matching**:
- Case-insensitive search in message body
- Default keywords: URGENT, ASAP, emergency, call me, time-sensitive
- Configurable via `WHATSAPP_URGENCY_KEYWORDS` env var

**Implementation Sequence**:
1. Implement `build_frontmatter()` creating dict from message
2. Implement `format_frontmatter()` converting dict to YAML
3. Implement `format_body()` creating markdown body
4. Implement `determine_urgency()` with keyword matching
5. Implement `generate_filename()` with sanitization
6. Implement `determine_output_directory()` routing logic
7. Implement `write_file_atomic()` for safe writes
8. Implement `write_message_file()` orchestrating full write flow

**Dependencies**:
- `yaml` (for frontmatter serialization)
- `pathlib.Path`
- `config.WatcherConfig`
- `models.WhatsAppMessage`, `models.CapturedMessageFile`

---

### 4. state.py — Deduplication State Management

**Purpose**: Persist and query message hashes to prevent duplicate file creation.

**File**: `src/whatsapp_watcher/state.py`

**Estimated LOC**: ~120

**Responsibilities**:
1. Load deduplication state from JSON file
2. Check if message hash exists in state
3. Mark message as processed by adding hash
4. Save state incrementally (after each message batch)
5. Handle corrupted state file gracefully

**Key Functions**:

```python
def load_dedup_state(config: WatcherConfig) -> DeduplicationState:
    """Load deduplication state from JSON file.

    If file doesn't exist → return empty DeduplicationState
    If file corrupted → log warning, backup corrupted file, return empty state

    Args:
        config: WatcherConfig with dedup_path

    Returns:
        DeduplicationState instance
    """

def save_dedup_state(state: DeduplicationState, config: WatcherConfig) -> None:
    """Save deduplication state to JSON file.

    Uses atomic write (temp file + rename).
    Updates state.last_poll to current timestamp.

    Args:
        state: DeduplicationState to save
        config: WatcherConfig with dedup_path
    """

def is_message_processed(message: WhatsAppMessage, state: DeduplicationState) -> bool:
    """Check if message hash exists in state.

    Args:
        message: WhatsAppMessage to check
        state: Current deduplication state

    Returns:
        True if message.hash in state.message_hashes
    """

def mark_message_processed(
    message: WhatsAppMessage,
    state: DeduplicationState,
    captured_at: datetime
) -> None:
    """Add message hash to state.

    Args:
        message: WhatsAppMessage that was processed
        state: DeduplicationState to update (mutated in-place)
        captured_at: Timestamp when message was captured
    """

def prune_old_hashes(
    state: DeduplicationState,
    retention_days: int = 30
) -> int:
    """Remove hashes older than retention period.

    Prevents unbounded state file growth.

    Returns:
        Number of hashes removed
    """
```

**State File Format** (`.watcher-state/whatsapp-dedup.json`):
```json
{
  "version": 1,
  "last_poll": "2026-03-22T14:30:00Z",
  "message_hashes": {
    "abc123def456": "2026-03-22T14:25:00Z",
    "xyz789ghi012": "2026-03-22T14:26:00Z"
  }
}
```

**Hash Collision Handling**:
- Hashes are 16-character SHA-256 prefixes
- Collision probability is negligible for MVP scope
- If collision occurs, message is skipped (acceptable tradeoff)

**State Corruption Recovery**:
- If JSON parse fails → rename to `.watcher-state/whatsapp-dedup.json.corrupted.{timestamp}`
- Log warning: "State file corrupted, resetting. All messages will be reprocessed."
- Continue with empty state

**Implementation Sequence**:
1. Implement `load_dedup_state()` with JSON parsing and error handling
2. Implement `save_dedup_state()` with atomic write
3. Implement `is_message_processed()` hash lookup
4. Implement `mark_message_processed()` adding to dict
5. Implement `prune_old_hashes()` cleanup logic
6. Add state file directory creation if missing

**Dependencies**:
- `json` (for state serialization)
- `pathlib.Path`
- `config.WatcherConfig`
- `models.WhatsAppMessage`, `models.DeduplicationState`

---

### 5. Poll-Loop Integration (in __main__.py)

**Purpose**: Orchestrate full watcher flow: session → scrape → write → state → sleep → repeat.

**File**: `src/whatsapp_watcher/__main__.py` (expand existing stub)

**Estimated LOC**: ~100 (additions to existing 60 LOC)

**Responsibilities**:
1. Handle CLI arguments (--auth, --dry-run, --once)
2. Load configuration from environment
3. Initialize Playwright
4. Create browser session (auth or reuse)
5. Loop: scrape → filter duplicates → write files → update state
6. Log poll cycle stats
7. Handle errors with Ralph Wiggum retry
8. Clean shutdown on interrupt

**Key Functions**:

```python
async def run_auth_mode(config: WatcherConfig) -> int:
    """Run one-time QR code authentication flow.

    Algorithm:
        1. Launch Playwright with headless=False
        2. Create browser context (triggers QR flow)
        3. Wait for authentication
        4. Save session
        5. Exit

    Returns:
        Exit code (0 success, 1 failure)
    """

async def run_poll_cycle(
    page: Page,
    config: WatcherConfig,
    state: DeduplicationState
) -> dict:
    """Execute single poll cycle.

    Algorithm:
        1. Scrape unread messages from WhatsApp Web
        2. Filter out already-processed messages
        3. Write new messages to vault
        4. Update dedup state
        5. Save state
        6. Return stats

    Returns:
        {
            "scraped": int,      # Total messages scraped
            "new": int,          # New messages (not duplicates)
            "written": int,      # Files written
            "duplicates": int,   # Skipped duplicates
            "errors": int        # Errors encountered
        }
    """

async def run_polling_mode(config: WatcherConfig, run_once: bool = False) -> int:
    """Run continuous polling mode.

    Algorithm:
        1. Load config
        2. Load dedup state
        3. Initialize Playwright
        4. Create browser context (reuse session)
        5. Loop:
            a. Run poll cycle
            b. Log stats
            c. Sleep for poll_interval
            d. Break if run_once=True
        6. Clean shutdown

    Returns:
        Exit code
    """

def main() -> int:
    """Main CLI entry point.

    Branches based on CLI args:
        --auth → run_auth_mode()
        --once → run_polling_mode(run_once=True)
        default → run_polling_mode(run_once=False)
    """
```

**Poll Cycle Flow**:
```
1. Load config, state
2. Initialize Playwright
3. Create browser context (session.py)
4. Navigate to WhatsApp Web
5. Scrape unread messages (scraper.py)
6. Filter duplicates (state.py)
7. Write new messages (writer.py)
8. Update state (state.py)
9. Log stats
10. Sleep poll_interval seconds
11. Repeat from step 5
```

**Error Handling (Ralph Wiggum Loop)**:
```python
for attempt in range(3):
    try:
        # Poll cycle
        break
    except ScraperError as e:
        if attempt < 2:
            wait = 2 ** attempt  # 1s, 2s, 4s
            log(f"Scraper error (attempt {attempt+1}/3), retrying in {wait}s: {e}")
            await asyncio.sleep(wait)
        else:
            log(f"Scraper failed after 3 attempts, skipping cycle: {e}")
```

**Logging**:
- Each poll cycle logs to `<VAULT_PATH>/Logs/whatsapp-watcher-{YYYY-MM-DD}.md`
- Format:
```markdown
## 2026-03-22 14:30:00 — Poll Cycle Start
- Scraped: 5 messages
- New: 3 messages
- Duplicates skipped: 2
- Written: 3 files
  - `/Inbox/whatsapp/20260322-143000-john-doe.md`
  - `/Needs_Action/whatsapp/20260322-143100-URGENT-alice.md`
  - `/Inbox/whatsapp/20260322-143200-family-group.md`
- Cycle duration: 8.3s
```

**Dry-Run Mode**:
- Scrape and filter normally
- Log what would be written
- Do not create files
- Do not update state

**Implementation Sequence**:
1. Implement `run_auth_mode()` calling session.py auth flow
2. Implement `run_poll_cycle()` orchestrating scrape → write → state
3. Implement `run_polling_mode()` with loop and sleep
4. Wire CLI args to mode functions in `main()`
5. Add logging integration
6. Add Ralph Wiggum retry logic
7. Add graceful shutdown on Ctrl+C

**Dependencies**:
- `asyncio` (for async/await)
- `playwright.async_api`
- All watcher modules: session, scraper, writer, state, config, models

---

## Data Flow Diagram (One Watcher Pass)

```
┌─────────────────────────────────────────────────────────────────────┐
│ START: Poll Cycle                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Load Config (config.py)                                          │
│    - vault_path, poll_interval, urgency_keywords                    │
│    - session_path, dedup_path                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. Load Dedup State (state.py)                                      │
│    - load_dedup_state() → DeduplicationState                        │
│    - message_hashes: dict[hash, captured_at]                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. Create Browser Session (session.py)                              │
│    - create_browser_context(config) → BrowserContext                │
│    - Reuse storage_state.json (headless)                            │
│    - wait_for_whatsapp_ready() → verify loaded                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. Scrape Unread Messages (scraper.py)                              │
│    - scrape_unread_messages(page, config) → list[WhatsAppMessage]   │
│    - Find chats with unread badges                                  │
│    - Click into each conversation                                   │
│    - Extract messages (sender, timestamp, body, media)              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Filter Duplicates (state.py)                                     │
│    - For each message:                                              │
│      if is_message_processed(message, state):                       │
│        skip (duplicate)                                             │
│      else:                                                          │
│        add to new_messages list                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Write Messages to Vault (writer.py)                              │
│    - For each new_message:                                          │
│      write_message_file(message, config, captured_at)               │
│        → determine urgency                                          │
│        → generate filename                                          │
│        → build frontmatter                                          │
│        → format body                                                │
│        → route to /Inbox or /Needs_Action                           │
│        → write file atomically                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. Update Dedup State (state.py)                                    │
│    - For each written message:                                      │
│      mark_message_processed(message, state, captured_at)            │
│    - save_dedup_state(state, config)                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. Log Stats                                                        │
│    - Scraped: N, New: M, Duplicates: P, Written: M                  │
│    - File paths of written messages                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 9. Sleep (poll_interval seconds)                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        [Loop back to step 3]
```

---

## Authentication/Session Persistence Strategy

### First-Time Setup (--auth mode)

**User Action**: `whatsapp-watcher --auth`

**Flow**:
1. Check if `.watcher-state/whatsapp/` exists → create if missing
2. Launch Playwright browser with `headless=False`
3. Navigate to `https://web.whatsapp.com`
4. Detect page state:
   - If QR code visible → wait for user to scan
   - If already authenticated → save session and exit
5. After QR scan, WhatsApp Web redirects to main interface
6. Save browser context storage state to `.watcher-state/whatsapp/storage_state.json`
7. Exit with message: "Authentication successful. Run `whatsapp-watcher` to start polling."

**Session Data Saved**:
- Cookies (authentication tokens)
- localStorage (session identifiers)
- IndexedDB (optional, Playwright supports this)

**Playwright Code**:
```python
context = await browser.new_context()
# ... QR scan flow ...
await context.storage_state(path=".watcher-state/whatsapp/storage_state.json")
```

### Normal Polling (headless)

**User Action**: `whatsapp-watcher` (or `whatsapp-watcher --once`)

**Flow**:
1. Load configuration
2. Check `.watcher-state/whatsapp/storage_state.json` exists:
   - If missing → exit with "Session not found. Run `whatsapp-watcher --auth` first."
3. Launch Playwright browser with `headless=True`
4. Load stored session:
   ```python
   context = await browser.new_context(
       storage_state=".watcher-state/whatsapp/storage_state.json"
   )
   ```
5. Navigate to `https://web.whatsapp.com`
6. Detect page state:
   - If main interface loads → session valid, proceed
   - If QR code appears → session expired, exit with "Session expired. Run `whatsapp-watcher --auth`."
7. Begin polling loop

### Session Expiration Detection

**Scenarios**:
- User logs out from phone
- WhatsApp Web session times out (typically 14 days inactivity)
- User clears WhatsApp Web sessions from phone settings

**Detection**:
- After navigation to web.whatsapp.com, check for `Selectors.QR_CODE` presence
- If QR code detected in headless mode → session invalid

**Response**:
- Log error: "WhatsApp session expired or invalid."
- Exit with code 1 and message: "Run `whatsapp-watcher --auth` to re-authenticate."

### Session File Security

**Permissions**:
- `.watcher-state/whatsapp/` directory: `700` (owner-only)
- `storage_state.json`: `600` (owner read/write only)

**Gitignore**:
- `.watcher-state/` MUST be in `.gitignore` (already enforced by existing watchers)

---

## Deduplication Strategy

### Hash Generation

**Input**: WhatsAppMessage instance

**Algorithm** (from models.py):
```python
content = f"whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}"
hash = hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Example**:
```
Message:
  chat_name: "John Doe"
  sender: "John Doe"
  timestamp: "2026-03-22T14:30:00Z"
  body: "Can you review the PR today?"

Hash input: "whatsapp|John Doe|John Doe|2026-03-22T14:30:00Z|Can you review the PR today?"
Hash output: "a3f5d8c2e1b4f9a7"  (16 chars)
```

**Uniqueness Guarantees**:
- Same message from same sender at same time → same hash
- Different timestamp → different hash (even if content identical)
- Different sender (group chats) → different hash
- Body truncated to 100 chars to limit hash input size

### State Persistence

**File**: `.watcher-state/whatsapp-dedup.json`

**Structure**:
```json
{
  "version": 1,
  "last_poll": "2026-03-22T14:35:00Z",
  "message_hashes": {
    "a3f5d8c2e1b4f9a7": "2026-03-22T14:30:15Z",
    "b7e2c9d4a1f3e8b6": "2026-03-22T14:31:22Z",
    "c1d5e8a3b9f2c7d4": "2026-03-22T14:32:45Z"
  }
}
```

**State Updates**:
- After each poll cycle, new message hashes are added
- `last_poll` timestamp updated to current time
- File written atomically (temp file + rename)

### Deduplication Flow (Per Poll Cycle)

```python
# 1. Load state
state = load_dedup_state(config)

# 2. Scrape messages
all_messages = await scrape_unread_messages(page, config)

# 3. Filter duplicates
new_messages = []
for message in all_messages:
    if not is_message_processed(message, state):
        new_messages.append(message)

# 4. Write new messages
for message in new_messages:
    filepath = write_message_file(message, config, datetime.now())
    mark_message_processed(message, state, datetime.now())

# 5. Save state
save_dedup_state(state, config)
```

**Why This Works**:
- WhatsApp Web shows all unread messages (including older ones)
- First poll may capture many messages (e.g., 50)
- All 50 hashes saved to state
- Second poll may see same 50 messages still unread (user hasn't opened WhatsApp)
- All 50 hashes found in state → skipped
- Third poll: user received 3 new messages → only 3 new hashes → only 3 written

**State Growth Management**:
- Hash dict grows unbounded without pruning
- Optional: Implement `prune_old_hashes()` to remove hashes older than 30 days
- For MVP: Skip pruning (acceptable for hackathon scope)

---

## Polling Model and Execution Flow

### Polling Modes

#### 1. Normal Continuous Polling (default)

**Command**: `whatsapp-watcher`

**Behavior**:
- Infinite loop: poll → sleep → poll → sleep → ...
- Sleep duration: `WHATSAPP_POLL_INTERVAL` env var (default: 60s)
- Continues until user presses Ctrl+C

**Loop Structure**:
```python
while True:
    try:
        stats = await run_poll_cycle(page, config, state)
        log_stats(stats)
        await asyncio.sleep(config.poll_interval)
    except KeyboardInterrupt:
        log("Shutting down gracefully...")
        break
    except Exception as e:
        log(f"Poll cycle error: {e}")
        # Ralph Wiggum retry handled inside run_poll_cycle
```

#### 2. Single Poll (--once)

**Command**: `whatsapp-watcher --once`

**Behavior**:
- Run one poll cycle
- Exit immediately after

**Use Case**: Manual triggering, testing, cron jobs

#### 3. Dry-Run Preview (--dry-run)

**Command**: `whatsapp-watcher --dry-run`

**Behavior**:
- Scrape messages normally
- Filter duplicates normally
- Log what would be written
- Do NOT create files
- Do NOT update state

**Output Example**:
```
[Dry Run] Would write 3 files:
  /Inbox/whatsapp/20260322-143000-john-doe.md
  /Needs_Action/whatsapp/20260322-143100-URGENT-alice.md
  /Inbox/whatsapp/20260322-143200-family-group.md
```

### Cycle Overlap Prevention

**Problem**: If poll cycle takes longer than poll interval, cycles could overlap.

**Solution**: Use sequential execution, not concurrent:
```python
while True:
    cycle_start = time.time()
    await run_poll_cycle(...)  # Blocks until complete
    cycle_duration = time.time() - cycle_start

    sleep_time = max(0, config.poll_interval - cycle_duration)
    await asyncio.sleep(sleep_time)
```

**Effect**: Next cycle starts at poll_interval OR when previous cycle completes (whichever is later).

### Graceful Shutdown

**Signal Handling**:
- Catch `KeyboardInterrupt` (Ctrl+C)
- Close browser context cleanly
- Close Playwright instance
- Save final state
- Exit with code 0

**Code**:
```python
try:
    await run_polling_mode(config)
except KeyboardInterrupt:
    log("Received interrupt, shutting down...")
finally:
    await context.close()
    await browser.close()
    await playwright.stop()
```

---

## Error Handling and Ralph Wiggum Retry Pattern

### Retry Strategy

**Philosophy**: 3 attempts with escalating delays before fallback.

**Delays**:
- Attempt 1: Immediate (no delay before first try)
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- After 3 failures: Log error, fallback action

### Error Categories and Handlers

#### 1. Session Errors

**Scenario**: Session expired, QR code detected in headless mode

**Retry**: NO (not transient)

**Fallback**: Exit with actionable error message
```
ERROR: WhatsApp session expired or invalid.
ACTION: Run `whatsapp-watcher --auth` to re-authenticate.
```

**Exit Code**: 1

#### 2. Network Errors

**Scenario**: `page.goto()` timeout, DNS failure, network unreachable

**Retry**: YES (Ralph Wiggum Loop)

**Fallback**: Log error, skip poll cycle, continue to next cycle
```
ERROR: Network error loading WhatsApp Web after 3 attempts.
ACTION: Check internet connection. Will retry in next poll cycle.
```

**Exit Code**: Continue (don't exit)

#### 3. Scraper Errors (Selector Not Found)

**Scenario**: WhatsApp Web UI changed, selector fails

**Retry**: YES (Ralph Wiggum Loop)

**Fallback**: Log error, skip poll cycle, continue
```
ERROR: WhatsApp Web selector failed after 3 attempts.
DETAILS: Could not find element: [data-testid="chat-list"]
ACTION: WhatsApp may have updated their UI. Check for watcher updates.
```

**Exit Code**: Continue (don't exit)

#### 4. File Write Errors

**Scenario**: Disk full, permission denied

**Retry**: YES (Ralph Wiggum Loop)

**Fallback**: Log error, skip message, continue to next message
```
ERROR: Failed to write message file after 3 attempts.
DETAILS: [Errno 28] No space left on device
ACTION: Free up disk space in vault directory.
```

**Exit Code**: Continue (don't exit)

### Retry Code Pattern

```python
async def with_retry(func, *args, **kwargs):
    """Execute async function with Ralph Wiggum retry."""
    for attempt in range(3):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt < 2:
                delay = 2 ** attempt  # 0, 2, 4 (effectively 2, 4 after failures)
                log(f"Attempt {attempt+1}/3 failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                log(f"All 3 attempts failed: {e}")
                raise
```

### Logging Error Details

**Log Entry Format**:
```markdown
## 2026-03-22 14:35:00 — ERROR

**Type**: ScraperError
**Message**: Selector not found: [data-testid="chat-list"]
**Attempts**: 3
**Action**: Check for watcher updates. WhatsApp Web may have changed UI.
**Stack Trace** (if verbose mode):
```
Traceback (most recent call last):
  ...
```
```

---

## Interface Boundaries

### Module Interface Contracts

#### config.py → All Modules
**Exports**: `WatcherConfig` dataclass, `load_config()` function
**Contract**: All modules accept `config: WatcherConfig` parameter
**Guarantees**: Config is immutable once loaded (no mid-execution changes)

#### models.py → All Modules
**Exports**: `WhatsAppMessage`, `WhatsAppConversation`, `DeduplicationState`, `CapturedMessageFile`, `compute_hash()`
**Contract**: All data passed between modules uses these dataclasses
**Guarantees**: Hash computation is deterministic and collision-resistant

#### selectors.py → session.py, scraper.py
**Exports**: `Selectors` class, `Timeouts` class
**Contract**: All DOM queries use `Selectors.*` constants
**Guarantees**: Centralized selector updates when WhatsApp UI changes

#### session.py → __main__.py
**Exports**: `create_browser_context()`, `wait_for_whatsapp_ready()`, `detect_session_state()`
**Contract**: Returns ready `BrowserContext` or raises `SessionExpiredError`
**Guarantees**: Session validity checked before returning context

#### scraper.py → __main__.py
**Exports**: `scrape_unread_messages()`
**Contract**: Returns `list[WhatsAppMessage]` or empty list (never None)
**Guarantees**: All returned messages have valid hash property

#### writer.py → __main__.py
**Exports**: `write_message_file()`
**Contract**: Returns `Path` to created file or raises `WriteError`
**Guarantees**: File written atomically (no partial writes)

#### state.py → __main__.py
**Exports**: `load_dedup_state()`, `save_dedup_state()`, `is_message_processed()`, `mark_message_processed()`
**Contract**: State mutations are in-memory until `save_dedup_state()` called
**Guarantees**: State file always valid JSON (atomic writes)

---

## Implementation Sequence (Risk-First)

### Phase 1: Session Management (Highest Risk)
**Why First**: Playwright automation and QR auth are unknowns; validate early.

**Tasks**:
1. Implement `session.py` with QR detection and session reuse
2. Test `--auth` mode manually with real WhatsApp account
3. Verify session persistence across restarts
4. Test session expiration detection

**Acceptance**:
- QR code scan completes successfully
- `storage_state.json` created
- Headless mode reuses session without QR prompt

**Estimated Effort**: 4-6 hours

---

### Phase 2: Scraper (High Risk)
**Why Second**: WhatsApp Web DOM is fragile; selectors may fail.

**Tasks**:
1. Implement `scraper.py` with unread chat detection
2. Implement message extraction from conversation panel
3. Test with individual and group chats
4. Add retry logic for selector failures

**Acceptance**:
- Unread messages extracted successfully
- Group messages include sender name
- Media indicators detected
- Timestamp parsing works for WhatsApp formats

**Estimated Effort**: 6-8 hours

---

### Phase 3: Writer (Medium Risk)
**Why Third**: Markdown generation is straightforward but needs testing.

**Tasks**:
1. Implement `writer.py` with frontmatter generation
2. Implement urgency keyword matching
3. Implement filename sanitization
4. Test routing to `/Inbox` vs `/Needs_Action`

**Acceptance**:
- Valid YAML frontmatter generated
- Urgent messages routed correctly
- Filenames are filesystem-safe
- Files created in correct vault folders

**Estimated Effort**: 3-4 hours

---

### Phase 4: State Management (Low Risk)
**Why Fourth**: JSON serialization is simple; low uncertainty.

**Tasks**:
1. Implement `state.py` with JSON load/save
2. Implement hash lookup and marking
3. Test deduplication across restarts
4. Test corrupted state recovery

**Acceptance**:
- State persists across restarts
- Duplicate messages skipped
- Corrupted state handled gracefully

**Estimated Effort**: 2-3 hours

---

### Phase 5: Poll-Loop Integration (Low Risk, High Value)
**Why Last**: Requires all other modules complete; orchestrates full flow.

**Tasks**:
1. Wire modules together in `__main__.py`
2. Implement poll loop with sleep
3. Add logging integration
4. Test end-to-end flow

**Acceptance**:
- Full poll cycle completes successfully
- Stats logged correctly
- Ctrl+C shutdown graceful
- Dry-run mode works

**Estimated Effort**: 2-3 hours

---

**Total Estimated Effort**: 17-24 hours (2-3 full development days)

---

## Testing Strategy

### Unit Tests (Per Module)

**session.py**:
- Test QR detection vs authenticated detection
- Test session state persistence
- Mock Playwright page for selector testing

**scraper.py**:
- Test unread badge detection
- Test message parsing (timestamp, sender, body)
- Test media type detection
- Test group vs individual differentiation

**writer.py**:
- Test urgency keyword matching (case-insensitive)
- Test filename sanitization (special chars, max length)
- Test frontmatter YAML validity
- Test routing logic (Inbox vs Needs_Action)

**state.py**:
- Test hash computation determinism
- Test duplicate detection
- Test state persistence across save/load
- Test corrupted state recovery

### Integration Tests

**End-to-End Flow**:
1. Seed WhatsApp Web with test messages (manual setup)
2. Run watcher once
3. Verify markdown files created
4. Run watcher again
5. Verify no duplicates created

**Session Reuse**:
1. Run `--auth` mode
2. Verify session saved
3. Run normal mode headless
4. Verify no QR prompt

**Urgency Routing**:
1. Send message with "URGENT" keyword
2. Run watcher
3. Verify file in `/Needs_Action/whatsapp/`

### Manual Test Scenarios (Hackathon Validation)

1. **Fresh Install**: Delete `.watcher-state/`, run `--auth`, scan QR, verify session works
2. **Normal Polling**: Run watcher, send messages from phone, verify captures within 60s
3. **Duplicate Prevention**: Run watcher twice without new messages, verify no duplicates
4. **Urgency Routing**: Send "URGENT call me", verify `/Needs_Action/` routing
5. **Group Chats**: Send group message, verify group_name and sender in frontmatter
6. **Session Expiration**: Log out from phone, verify watcher detects and prompts re-auth
7. **Network Interruption**: Disconnect network, verify Ralph Wiggum retry, reconnect, verify recovery
8. **Dry-Run**: Run `--dry-run`, verify no files created but logging shows what would be captured

---

## Verification Tests (MVP Complete)

Run these tests to verify MVP completion:

### Test 1: Authentication Flow
```bash
# Clean slate
rm -rf .watcher-state/whatsapp/

# Run auth
whatsapp-watcher --auth

# Expected:
# - Browser window opens with QR code
# - After scan, main WhatsApp interface loads
# - Session saved to .watcher-state/whatsapp/storage_state.json
# - Exit with success message
```

### Test 2: Headless Polling
```bash
# Prerequisites: Test 1 complete (session exists)

# Run once
whatsapp-watcher --once

# Expected:
# - No browser window visible
# - Unread messages captured to /Inbox/whatsapp/
# - Stats logged
# - Exit after single cycle
```

### Test 3: Urgency Routing
```bash
# Send message containing "URGENT" from another contact
# Run watcher
whatsapp-watcher --once

# Expected:
# - Message file created in /Needs_Action/whatsapp/
# - Frontmatter contains: urgency: urgent
```

### Test 4: Deduplication
```bash
# Run watcher twice without new messages
whatsapp-watcher --once
whatsapp-watcher --once

# Expected:
# - First run: N files created
# - Second run: 0 files created (all duplicates skipped)
# - Logs show "Duplicates skipped: N"
```

### Test 5: Dry-Run Mode
```bash
# Delete .watcher-state/whatsapp-dedup.json to reset state
whatsapp-watcher --dry-run --once

# Expected:
# - Logs show "[Dry Run] Would write: ..."
# - No files created in /Inbox or /Needs_Action
# - State file not updated
```

---

## Definition of Done

The WhatsApp Watcher MVP is **complete** when:

1. ✅ All 5 modules implemented: `session.py`, `scraper.py`, `writer.py`, `state.py`, poll-loop in `__main__.py`
2. ✅ `--auth` mode successfully authenticates and saves session
3. ✅ Normal polling mode runs headlessly and captures messages
4. ✅ All 5 verification tests pass
5. ✅ Deduplication prevents duplicate files on repeated runs
6. ✅ Urgent messages route to `/Needs_Action/whatsapp/`
7. ✅ Group messages include group_name and sender
8. ✅ Session expiration detected with actionable error message
9. ✅ Ralph Wiggum retry pattern implemented for transient errors
10. ✅ Logging to `<VAULT_PATH>/Logs/whatsapp-watcher-{date}.md` works

---

## Out of Scope (Explicitly Excluded from MVP)

The following are **NOT** included in this MVP:

- ❌ Message reply/sending functionality
- ❌ Media file downloads (images, videos, documents)
- ❌ Multi-account support
- ❌ Real-time push notifications (poll-based only)
- ❌ Message read/deletion in WhatsApp
- ❌ Advanced CLI options (custom templates, filters)
- ❌ Comprehensive test suite (unit tests optional for MVP)
- ❌ Performance optimization (acceptable for up to 20 unread chats)
- ❌ State pruning (hash dict grows unbounded)
- ❌ Facebook Messenger integration
- ❌ LinkedIn modifications
- ❌ Gmail/Router/HITL modifications
- ❌ MCP server integration
- ❌ Constitution amendments

These may be added in future iterations **after** MVP validation.

---

## Success Criteria

The WhatsApp Watcher MVP is **successful** when:

- **SC-001**: Users can capture WhatsApp messages into their vault after one-time QR authentication
- **SC-002**: 100% of unread messages captured within one poll interval (60s default)
- **SC-003**: Zero duplicate message files created
- **SC-004**: Urgent messages (with keywords) routed to `/Needs_Action/whatsapp/` 100% of the time
- **SC-005**: Watcher runs continuously for 4+ hours (hackathon duration) without manual intervention
- **SC-006**: All error messages include actionable remediation steps
- **SC-007**: Both individual and group chat messages captured with correct metadata

---

## Next Steps After Plan Approval

1. **Create Tasks** (`/sp.tasks`): Break down into dependency-ordered tasks (T001-T0XX)
2. **Implement Phase 1** (session.py): Validate Playwright + QR auth
3. **Implement Phase 2** (scraper.py): Validate message extraction
4. **Implement Phase 3-5**: Complete remaining modules
5. **Run Verification Tests**: Validate all 5 tests pass
6. **User Acceptance**: Demo with real WhatsApp account
7. **Create PHR**: Document implementation session
8. **Decision on Next Phase**: WhatsApp reply capability (Silver Tier) or move to Phase 4 (Facebook Publisher)

---

**END OF MVP COMPLETION PLAN**
