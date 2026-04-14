# Tasks: WhatsApp Watcher MVP Completion

**Feature**: 007-whatsapp-watcher
**Scope**: Complete remaining MVP modules only (session, scraper, writer, state, poll-loop)
**Date**: 2026-04-12
**Prerequisites**: mvp-completion-plan.md

---

## Context

This task list covers **only** the remaining work to complete the WhatsApp Watcher MVP.

**Foundation Already Complete:**
- ✅ config.py - WatcherConfig with environment variable loading
- ✅ models.py - WhatsAppMessage, DeduplicationState, CapturedMessageFile dataclasses
- ✅ selectors.py - WhatsApp Web DOM selectors and timeout constants
- ✅ __main__.py - CLI argument parsing (stub only, needs wiring)

**This Document: Remaining MVP Work (5 modules)**
- Phase 1: Session module (session.py)
- Phase 2: Scraper module (scraper.py)
- Phase 3: Writer module (writer.py)
- Phase 4: State module (state.py)
- Phase 5: Poll-loop integration (__main__.py)

---

## Task Format

`- [ ] TXXX [Module] Description`

**Modules**: SESSION | SCRAPER | WRITER | STATE | POLL-LOOP

**Acceptance Criteria**: Included at end of each phase

**Out of Scope** (will NOT have tasks):
- Message sending/replying
- Media file downloads
- Multi-account support
- Real-time push notifications
- Message read/deletion in WhatsApp
- Advanced CLI polish
- Comprehensive test suite
- Performance optimization
- State pruning

---

## Phase 1: Session Module (T001-T012)

**Goal**: Implement Playwright browser session management with QR authentication and session reuse

**File**: `src/whatsapp_watcher/session.py`

**Interface Contract**:
```python
async def create_browser_context(
    config: WatcherConfig,
    playwright: Playwright
) -> BrowserContext

async def wait_for_whatsapp_ready(page: Page, timeout: int = 30000) -> bool
async def detect_session_state(page: Page) -> str
async def wait_for_qr_authentication(page: Page, timeout: int = 120000) -> None
```

### Tasks

- [ ] T001 [SESSION] Create `src/whatsapp_watcher/session.py` module skeleton with imports
  - **Acceptance**: File exists, imports playwright.async_api, config.WatcherConfig, selectors.Selectors

- [ ] T002 [SESSION] Implement `create_browser_context()` function structure with headed/headless branching
  - **Acceptance**: Function accepts config and playwright, branches based on config.headless flag

- [ ] T003 [SESSION] Implement headless mode branch in `create_browser_context()`
  - **Logic**: Load storage_state from config.storage_state_path, launch headless browser
  - **Acceptance**: Returns BrowserContext with loaded session if file exists

- [ ] T004 [SESSION] Implement headed mode branch in `create_browser_context()` for --auth
  - **Logic**: Launch headed browser (headless=False), create context without storage_state
  - **Acceptance**: Returns BrowserContext with headed browser visible

- [ ] T005 [SESSION] Implement `detect_session_state()` function
  - **Logic**: Check for Selectors.QR_CODE presence vs Selectors.MAIN_INTERFACE presence
  - **Return**: "qr_code" | "authenticated" | "loading"
  - **Acceptance**: Correctly detects QR code vs main interface on page

- [ ] T006 [SESSION] Implement `wait_for_qr_authentication()` function
  - **Logic**: Poll page state until QR code disappears and main interface loads
  - **Timeout**: 120 seconds (Timeouts.QR_SCAN)
  - **Acceptance**: Returns when main interface detected, raises QRTimeoutError on timeout

- [ ] T007 [SESSION] Implement `wait_for_whatsapp_ready()` function
  - **Logic**: Wait for Selectors.MAIN_INTERFACE to be visible
  - **Timeout**: 30 seconds (Timeouts.PAGE_LOAD)
  - **Acceptance**: Returns True when main interface loaded, raises TimeoutError otherwise

- [ ] T008 [SESSION] Add session save logic in `create_browser_context()` for headed mode
  - **Logic**: After QR authentication completes, save context.storage_state() to config.storage_state_path
  - **Acceptance**: storage_state.json file created in .watcher-state/whatsapp/

- [ ] T009 [SESSION] Add session validation logic in `create_browser_context()` for headless mode
  - **Logic**: After loading session, navigate to web.whatsapp.com, detect_session_state()
  - **If QR detected**: Raise SessionExpiredError with actionable message
  - **Acceptance**: Raises SessionExpiredError if session invalid in headless mode

- [ ] T010 [SESSION] Create custom exception classes
  - **Classes**: SessionExpiredError, QRTimeoutError (inherit from Exception)
  - **Acceptance**: Both exceptions defined with descriptive messages

- [ ] T011 [SESSION] Add session directory creation in `create_browser_context()`
  - **Logic**: Ensure config.session_path directory exists before saving storage_state
  - **Acceptance**: .watcher-state/whatsapp/ directory created if missing

- [ ] T012 [SESSION] Add logging for session operations
  - **Events**: Session loaded, session saved, QR scan started, QR scan complete, session expired
  - **Acceptance**: Log statements output to stderr for each event

### Phase 1 Acceptance Criteria

✅ **Session Module Complete When**:
1. `create_browser_context()` launches headed browser for --auth mode
2. QR code detection works and waits for scan
3. Session saved to storage_state.json after authentication
4. Headless mode loads session from storage_state.json
5. Session expiration detected and raises SessionExpiredError
6. All custom exceptions defined
7. Logging covers key session events

**Verification Test**:
```python
# Test 1: Auth mode
config = WatcherConfig(headless=False, ...)
async with async_playwright() as p:
    context = await create_browser_context(config, p)
    # Manually scan QR code
    # Verify storage_state.json created

# Test 2: Headless reuse
config = WatcherConfig(headless=True, ...)
async with async_playwright() as p:
    context = await create_browser_context(config, p)
    # Verify no QR prompt, main interface loads
```

---

## Phase 2: Scraper Module (T013-T026)

**Goal**: Extract unread messages from WhatsApp Web using Playwright DOM queries

**File**: `src/whatsapp_watcher/scraper.py`

**Interface Contract**:
```python
async def scrape_unread_messages(
    page: Page,
    config: WatcherConfig
) -> list[WhatsAppMessage]
```

### Tasks

- [ ] T013 [SCRAPER] Create `src/whatsapp_watcher/scraper.py` module skeleton with imports
  - **Acceptance**: File exists, imports playwright.async_api, config.WatcherConfig, models.WhatsAppMessage, selectors.Selectors

- [ ] T014 [SCRAPER] Implement `get_unread_chat_elements()` function
  - **Logic**: Query page for Selectors.CHAT_ITEM elements containing Selectors.UNREAD_BADGE
  - **Return**: list[ElementHandle] of chat items with unread badges
  - **Acceptance**: Returns element handles for unread chats only

- [ ] T015 [SCRAPER] Implement `extract_chat_info()` function
  - **Logic**: From chat element, extract chat name from Selectors.CHAT_TITLE
  - **Logic**: Detect chat type by checking for Selectors.GROUP_ICON presence
  - **Return**: dict with chat_name, chat_type, unread_count
  - **Acceptance**: Returns dict with all fields populated

- [ ] T016 [SCRAPER] Implement `extract_messages_from_conversation()` function structure
  - **Logic**: Query page for Selectors.MESSAGE_ROW elements
  - **Logic**: Filter to incoming messages only (has Selectors.MESSAGE_IN, not MESSAGE_OUT)
  - **Acceptance**: Function exists, queries message rows, filters to incoming only

- [ ] T017 [SCRAPER] Implement message text extraction in `extract_messages_from_conversation()`
  - **Logic**: For each message row, query Selectors.MESSAGE_TEXT and extract text_content()
  - **Acceptance**: Message body text extracted correctly

- [ ] T018 [SCRAPER] Implement message timestamp extraction in `extract_messages_from_conversation()`
  - **Logic**: For each message row, query Selectors.MESSAGE_TIME and extract text
  - **Logic**: Call parse_message_timestamp() to convert to datetime
  - **Acceptance**: Timestamp extracted and parsed to datetime

- [ ] T019 [SCRAPER] Implement `parse_message_timestamp()` function
  - **Logic**: Parse WhatsApp timestamp formats: "HH:MM", "Yesterday", "DD/MM/YYYY"
  - **Logic**: For "HH:MM", use today's date; for "Yesterday", use yesterday's date
  - **Return**: datetime object (best-effort)
  - **Acceptance**: All three timestamp formats parsed correctly

- [ ] T020 [SCRAPER] Implement sender extraction for group messages in `extract_messages_from_conversation()`
  - **Logic**: If chat_type is "group", query Selectors.MESSAGE_AUTHOR for sender name
  - **Logic**: If individual chat, sender is same as chat_name
  - **Acceptance**: Sender extracted correctly for both individual and group chats

- [ ] T021 [SCRAPER] Implement `detect_media_type()` function
  - **Logic**: Check message element for Selectors.MEDIA_IMAGE, MEDIA_VIDEO, MEDIA_AUDIO, MEDIA_DOCUMENT
  - **Return**: (has_media: bool, media_type: str | None)
  - **Acceptance**: Media type detected correctly for image/video/audio/document

- [ ] T022 [SCRAPER] Implement WhatsAppMessage construction in `extract_messages_from_conversation()`
  - **Logic**: Build WhatsAppMessage instance from extracted data (chat_name, chat_type, sender, timestamp, body, has_media, media_type)
  - **Acceptance**: WhatsAppMessage instances created with all fields populated

- [ ] T023 [SCRAPER] Implement `scrape_unread_messages()` orchestration function
  - **Logic**: Call get_unread_chat_elements() to get unread chats
  - **Logic**: For each chat: click element, wait for conversation to load, extract_chat_info(), extract_messages_from_conversation()
  - **Logic**: Navigate back to chat list after each conversation
  - **Return**: Flat list of all WhatsAppMessage instances from all chats
  - **Acceptance**: Returns all messages from all unread conversations

- [ ] T024 [SCRAPER] Add retry logic with Ralph Wiggum pattern in `scrape_unread_messages()`
  - **Logic**: Wrap page queries in try/except, retry 3 times with 2s, 4s delays
  - **Fallback**: On 3rd failure, log error and skip conversation
  - **Acceptance**: Transient failures retried, permanent failures logged and skipped

- [ ] T025 [SCRAPER] Add navigation waits in `scrape_unread_messages()`
  - **Logic**: After clicking chat, wait for Selectors.CONVERSATION_PANEL visible (Timeouts.CHAT_OPEN)
  - **Logic**: After navigating back, wait for Selectors.CHAT_LIST visible
  - **Acceptance**: Waits prevent scraping before page fully loads

- [ ] T026 [SCRAPER] Add logging for scraper operations
  - **Events**: Unread chats found (count), opening chat (name), messages extracted (count), errors
  - **Acceptance**: Log statements output for each operation

### Phase 2 Acceptance Criteria

✅ **Scraper Module Complete When**:
1. `scrape_unread_messages()` finds all chats with unread badges
2. Each unread chat is clicked and messages extracted
3. Message data includes: sender, timestamp, body, media indicators
4. Group messages include sender name, individual messages use chat_name
5. Timestamp parsing handles WhatsApp's three formats
6. Media type detected for images/videos/audio/documents
7. Ralph Wiggum retry handles selector failures
8. Navigation waits prevent race conditions
9. Returns flat list of WhatsAppMessage instances

**Verification Test**:
```python
# Send test messages to WhatsApp (manual setup)
# Run scraper
messages = await scrape_unread_messages(page, config)
assert len(messages) > 0
assert all(isinstance(m, WhatsAppMessage) for m in messages)
assert all(m.hash for m in messages)  # Hash property works
```

---

## Phase 3: Writer Module (T027-T038)

**Goal**: Convert WhatsAppMessage instances to Obsidian-compatible Markdown files

**File**: `src/whatsapp_watcher/writer.py`

**Interface Contract**:
```python
def write_message_file(
    message: WhatsAppMessage,
    config: WatcherConfig,
    captured_at: datetime
) -> Path
```

### Tasks

- [ ] T027 [WRITER] Create `src/whatsapp_watcher/writer.py` module skeleton with imports
  - **Acceptance**: File exists, imports Path, datetime, yaml, config.WatcherConfig, models.WhatsAppMessage

- [ ] T028 [WRITER] Implement `determine_urgency()` function
  - **Logic**: Case-insensitive search in message.body for any keyword in config.urgency_keywords
  - **Return**: "urgent" if any keyword found, else "normal"
  - **Acceptance**: Correctly detects urgency keywords (URGENT, ASAP, emergency, etc.)

- [ ] T029 [WRITER] Implement `generate_filename()` function
  - **Logic**: Format as {YYYYMMDD}-{HHMMSS}-{chat-slug}-{sender-slug}.md
  - **Logic**: For urgent messages, insert "URGENT" before chat slug
  - **Logic**: Sanitize: lowercase, replace spaces with hyphens, remove special chars, truncate to 100 chars
  - **Return**: Filename string (not full path)
  - **Acceptance**: Filename is filesystem-safe and follows format

- [ ] T030 [WRITER] Implement `build_frontmatter()` function
  - **Logic**: Create dict with keys: source, captured_at, sender, chat_name, chat_type, message_timestamp, urgency, status, has_media, media_type, tags, hash
  - **Logic**: Format timestamps as ISO 8601 strings
  - **Logic**: tags always ["inbox", "whatsapp"]
  - **Return**: Dict with all frontmatter fields
  - **Acceptance**: All required fields present with correct types

- [ ] T031 [WRITER] Implement `format_frontmatter()` function
  - **Logic**: Serialize dict to YAML using yaml.safe_dump()
  - **Logic**: Wrap in "---\n" prefix and "\n---\n" suffix
  - **Return**: Complete YAML frontmatter block as string
  - **Acceptance**: Valid YAML output, parseable by frontmatter parsers

- [ ] T032 [WRITER] Implement `format_body()` function
  - **Logic**: Create markdown structure with heading, sender/timestamp, body text, media indicator
  - **Format**:
    ```
    # {chat_name}

    **Sender**: {sender}
    **Timestamp**: {timestamp}

    {body}

    [Media: {media_type}] (if has_media)
    ```
  - **Return**: Markdown body as string
  - **Acceptance**: Valid markdown with all sections

- [ ] T033 [WRITER] Implement `determine_output_directory()` function
  - **Logic**: If urgency == "urgent", return vault_path / "Needs_Action" / "whatsapp"
  - **Logic**: If urgency == "normal", return vault_path / "Inbox" / "whatsapp"
  - **Return**: Path to output directory
  - **Acceptance**: Correct directory returned based on urgency

- [ ] T034 [WRITER] Implement `write_file_atomic()` function
  - **Logic**: Write content to temp file in same directory (filename + ".tmp")
  - **Logic**: Use os.rename() to atomically move temp file to final path
  - **Acceptance**: File written atomically (no partial writes on interrupt)

- [ ] T035 [WRITER] Implement `write_message_file()` orchestration function structure
  - **Logic**: Call determine_urgency(), generate_filename(), build_frontmatter(), format_frontmatter(), format_body()
  - **Logic**: Combine frontmatter + "\n\n" + body + "\n"
  - **Logic**: Call determine_output_directory(), ensure directory exists
  - **Logic**: Call write_file_atomic() with full content
  - **Return**: Path to created file
  - **Acceptance**: Function orchestrates all steps, returns Path

- [ ] T036 [WRITER] Add directory creation in `write_message_file()`
  - **Logic**: Ensure output directory exists before writing (Path.mkdir(parents=True, exist_ok=True))
  - **Acceptance**: Directories created automatically if missing

- [ ] T037 [WRITER] Add dry-run mode handling in `write_message_file()`
  - **Logic**: If config.dry_run is True, log what would be written, return None without writing
  - **Acceptance**: Dry-run logs filename and location, does not create file

- [ ] T038 [WRITER] Add logging for writer operations
  - **Events**: File created (path), urgency detected, dry-run preview
  - **Acceptance**: Log statements output for each written file

### Phase 3 Acceptance Criteria

✅ **Writer Module Complete When**:
1. `write_message_file()` creates markdown file with valid YAML frontmatter
2. Filename format: {YYYYMMDD}-{HHMMSS}-{chat-slug}-{sender-slug}.md
3. Urgent messages include "URGENT" in filename
4. Frontmatter includes all required fields (source, sender, chat_name, urgency, hash, etc.)
5. Body includes heading, sender/timestamp, message text, media indicator
6. Urgency keyword matching is case-insensitive
7. Routing: urgent → /Needs_Action/whatsapp/, normal → /Inbox/whatsapp/
8. Output directories created automatically if missing
9. Atomic writes (temp file + rename)
10. Dry-run mode previews without writing

**Verification Test**:
```python
message = WhatsAppMessage(
    chat_name="John Doe",
    chat_type="individual",
    sender="John Doe",
    timestamp=datetime.now(),
    body="Can you review the PR?",
    has_media=False,
    media_type=None
)
filepath = write_message_file(message, config, datetime.now())
assert filepath.exists()
assert filepath.parent.name == "whatsapp"
assert "john-doe" in filepath.name
```

---

## Phase 4: State Module (T039-T047)

**Goal**: Persist and query message hashes to prevent duplicate file creation

**File**: `src/whatsapp_watcher/state.py`

**Interface Contract**:
```python
def load_dedup_state(config: WatcherConfig) -> DeduplicationState
def save_dedup_state(state: DeduplicationState, config: WatcherConfig) -> None
def is_message_processed(message: WhatsAppMessage, state: DeduplicationState) -> bool
def mark_message_processed(message: WhatsAppMessage, state: DeduplicationState, captured_at: datetime) -> None
```

### Tasks

- [ ] T039 [STATE] Create `src/whatsapp_watcher/state.py` module skeleton with imports
  - **Acceptance**: File exists, imports json, Path, datetime, config.WatcherConfig, models.WhatsAppMessage, models.DeduplicationState

- [ ] T040 [STATE] Implement `load_dedup_state()` function for fresh state
  - **Logic**: If config.dedup_path does not exist, return new DeduplicationState()
  - **Acceptance**: Returns empty DeduplicationState when file missing

- [ ] T041 [STATE] Implement `load_dedup_state()` function for existing state
  - **Logic**: If config.dedup_path exists, read JSON and parse to DeduplicationState
  - **Logic**: Convert last_poll ISO string to datetime, message_hashes values to datetime
  - **Return**: DeduplicationState instance
  - **Acceptance**: Loads state from JSON correctly

- [ ] T042 [STATE] Add corrupted state handling in `load_dedup_state()`
  - **Logic**: Wrap JSON parsing in try/except
  - **Logic**: On JSONDecodeError, rename file to .corrupted.{timestamp}, log warning, return empty state
  - **Acceptance**: Corrupted state backed up and reset gracefully

- [ ] T043 [STATE] Implement `save_dedup_state()` function
  - **Logic**: Set state.last_poll to current datetime
  - **Logic**: Serialize state to dict, convert datetimes to ISO strings
  - **Logic**: Write JSON to temp file, rename to config.dedup_path
  - **Acceptance**: State saved to JSON atomically

- [ ] T044 [STATE] Implement `is_message_processed()` function
  - **Logic**: Check if message.hash exists in state.message_hashes dict
  - **Return**: True if hash found, False otherwise
  - **Acceptance**: Correctly detects duplicate hashes

- [ ] T045 [STATE] Implement `mark_message_processed()` function
  - **Logic**: Add message.hash to state.message_hashes dict with captured_at timestamp
  - **Acceptance**: Hash added to state dict (mutates in-place)

- [ ] T046 [STATE] Add state directory creation in `save_dedup_state()`
  - **Logic**: Ensure config.dedup_path.parent directory exists before writing
  - **Acceptance**: .watcher-state/ directory created if missing

- [ ] T047 [STATE] Add logging for state operations
  - **Events**: State loaded (hash count), state saved, corrupted state recovered, duplicate detected
  - **Acceptance**: Log statements output for key events

### Phase 4 Acceptance Criteria

✅ **State Module Complete When**:
1. `load_dedup_state()` returns empty state if file missing
2. Loads existing state from JSON correctly
3. Corrupted state backed up and reset gracefully
4. `save_dedup_state()` writes JSON atomically (temp file + rename)
5. `is_message_processed()` detects duplicate hashes
6. `mark_message_processed()` adds hash to state dict
7. State directory created automatically if missing
8. Logging covers load, save, corruption, duplicates

**Verification Test**:
```python
# Test 1: Fresh state
state = load_dedup_state(config)
assert state.message_hashes == {}

# Test 2: Mark and save
message = WhatsAppMessage(...)
mark_message_processed(message, state, datetime.now())
save_dedup_state(state, config)

# Test 3: Load and check
state2 = load_dedup_state(config)
assert is_message_processed(message, state2) is True
```

---

## Phase 5: Poll-Loop Integration (T048-T059)

**Goal**: Orchestrate full watcher flow and wire modules together

**File**: `src/whatsapp_watcher/__main__.py` (expand existing stub)

**Interface Contract**:
```python
async def run_auth_mode(config: WatcherConfig) -> int
async def run_poll_cycle(page: Page, config: WatcherConfig, state: DeduplicationState) -> dict
async def run_polling_mode(config: WatcherConfig, run_once: bool = False) -> int
def main() -> int
```

### Tasks

- [ ] T048 [POLL-LOOP] Import all watcher modules in `__main__.py`
  - **Imports**: asyncio, playwright.async_api, config.load_config, session, scraper, writer, state
  - **Acceptance**: All imports present, no errors

- [ ] T049 [POLL-LOOP] Implement `run_auth_mode()` function
  - **Logic**: Load config with headless=False
  - **Logic**: Initialize Playwright, create browser context via session.create_browser_context()
  - **Logic**: Wait for QR authentication, session saves automatically
  - **Logic**: Close browser and exit with success message
  - **Return**: Exit code 0 on success, 1 on failure
  - **Acceptance**: QR auth flow completes, session saved

- [ ] T050 [POLL-LOOP] Implement `run_poll_cycle()` function structure
  - **Logic**: Scrape messages, filter duplicates, write new messages, update state
  - **Return**: Stats dict with keys: scraped, new, written, duplicates, errors
  - **Acceptance**: Function structure exists, returns stats dict

- [ ] T051 [POLL-LOOP] Implement scraping step in `run_poll_cycle()`
  - **Logic**: Call scraper.scrape_unread_messages(page, config)
  - **Logic**: Store result in all_messages list
  - **Acceptance**: Messages scraped and stored

- [ ] T052 [POLL-LOOP] Implement duplicate filtering step in `run_poll_cycle()`
  - **Logic**: For each message in all_messages, check state.is_message_processed()
  - **Logic**: If not processed, add to new_messages list
  - **Logic**: If processed, increment duplicates counter
  - **Acceptance**: Duplicates filtered out, new messages identified

- [ ] T053 [POLL-LOOP] Implement writing step in `run_poll_cycle()`
  - **Logic**: For each message in new_messages, call writer.write_message_file()
  - **Logic**: Call state.mark_message_processed() for each written message
  - **Logic**: Increment written counter
  - **Acceptance**: New messages written, state updated

- [ ] T054 [POLL-LOOP] Implement state save step in `run_poll_cycle()`
  - **Logic**: Call state.save_dedup_state() after all messages processed
  - **Acceptance**: State saved to disk

- [ ] T055 [POLL-LOOP] Add error handling with Ralph Wiggum retry in `run_poll_cycle()`
  - **Logic**: Wrap scraping/writing in try/except, retry 3 times with 2s, 4s delays
  - **Logic**: Log errors, increment error counter
  - **Acceptance**: Errors retried, logged, don't crash poll cycle

- [ ] T056 [POLL-LOOP] Implement `run_polling_mode()` function
  - **Logic**: Load config, load state, initialize Playwright
  - **Logic**: Create browser context via session.create_browser_context()
  - **Logic**: Navigate to web.whatsapp.com
  - **Logic**: Loop: run_poll_cycle(), log stats, sleep poll_interval
  - **Logic**: Break loop if run_once=True
  - **Acceptance**: Continuous polling loop works, --once mode exits after one cycle

- [ ] T057 [POLL-LOOP] Add graceful shutdown in `run_polling_mode()`
  - **Logic**: Catch KeyboardInterrupt (Ctrl+C), close browser context, exit cleanly
  - **Acceptance**: Ctrl+C shuts down without errors

- [ ] T058 [POLL-LOOP] Wire CLI arguments to mode functions in `main()`
  - **Logic**: If --auth, call run_auth_mode()
  - **Logic**: If --once, call run_polling_mode(run_once=True)
  - **Logic**: Otherwise, call run_polling_mode(run_once=False)
  - **Acceptance**: All CLI flags work correctly

- [ ] T059 [POLL-LOOP] Add poll cycle stats logging
  - **Events**: Cycle start/end, messages scraped/new/duplicates/written, cycle duration
  - **Format**: Append to <VAULT_PATH>/Logs/whatsapp-watcher-{YYYY-MM-DD}.md
  - **Acceptance**: Stats logged in markdown format after each cycle

### Phase 5 Acceptance Criteria

✅ **Poll-Loop Complete When**:
1. `run_auth_mode()` launches headed browser, waits for QR scan, saves session
2. `run_poll_cycle()` orchestrates: scrape → filter → write → save state
3. Stats returned with scraped/new/duplicates/written/errors counts
4. Ralph Wiggum retry handles errors (3 attempts, 2s/4s delays)
5. `run_polling_mode()` runs continuous loop with poll_interval sleep
6. `--once` flag runs single cycle then exits
7. Ctrl+C gracefully shuts down
8. All CLI args wired correctly
9. Stats logged to /Logs/ after each cycle

**Verification Test**:
```python
# Test 1: Auth mode
python -m whatsapp_watcher --auth
# Manually scan QR code
# Verify .watcher-state/whatsapp/storage_state.json created

# Test 2: Poll once
python -m whatsapp_watcher --once
# Verify messages captured to /Inbox/whatsapp/

# Test 3: Deduplication
python -m whatsapp_watcher --once
python -m whatsapp_watcher --once
# Verify second run logs 0 new messages (all duplicates)
```

---

## Integration Checkpoint

**After T059 Complete, Full MVP Pipeline Works**:

```
Input: WhatsApp Web (web.whatsapp.com)

↓ [session.create_browser_context - T001-T012]

BrowserContext (authenticated, ready)

↓ [scraper.scrape_unread_messages - T013-T026]

list[WhatsAppMessage]

↓ [state.is_message_processed - T039-T047]

Filtered list (duplicates removed)

↓ [writer.write_message_file - T027-T038]

Markdown files created in /Inbox or /Needs_Action

↓ [state.mark_processed, save_dedup_state - T039-T047]

State updated, no duplicates next run

↓ [run_poll_cycle - T048-T059]

Stats returned: {scraped, new, written, duplicates, errors}

Output: Task files in /Inbox/whatsapp/ or /Needs_Action/whatsapp/
```

---

## Final Verification Tests (MVP Complete)

Run these tests to verify MVP completion:

### Test 1: Fresh Authentication
```bash
# Clean slate
rm -rf .watcher-state/whatsapp/

# Run auth
whatsapp-watcher --auth

# Expected:
# - Browser window opens with QR code
# - After scan, session saved
# - Exit with success message
# - .watcher-state/whatsapp/storage_state.json exists
```

### Test 2: Headless Message Capture
```bash
# Prerequisites: Test 1 complete (session exists)
# Send test message to WhatsApp from another device

# Run once
whatsapp-watcher --once

# Expected:
# - No browser window visible
# - Message captured to /Inbox/whatsapp/{timestamp}-{contact}.md
# - Frontmatter contains all required fields
# - Stats logged to /Logs/whatsapp-watcher-{date}.md
```

### Test 3: Urgency Routing
```bash
# Send message containing "URGENT call me" from another contact

# Run once
whatsapp-watcher --once

# Expected:
# - Message file created in /Needs_Action/whatsapp/
# - Filename contains "URGENT"
# - Frontmatter contains: urgency: urgent
```

### Test 4: Deduplication
```bash
# Prerequisites: Test 2 complete (messages already captured)

# Run again without new messages
whatsapp-watcher --once

# Expected:
# - Stats show: scraped: N, new: 0, duplicates: N
# - No new files created
# - Logs show "Duplicates skipped: N"
```

### Test 5: Dry-Run Mode
```bash
# Delete state to reset
rm .watcher-state/whatsapp-dedup.json

# Run dry-run
whatsapp-watcher --dry-run --once

# Expected:
# - Logs show "[Dry Run] Would write: ..."
# - No files created in /Inbox or /Needs_Action
# - State file not created/updated
```

### Test 6: Group Chat Message
```bash
# Send message in a WhatsApp group

# Run once
whatsapp-watcher --once

# Expected:
# - Message file created with chat_type: group
# - Frontmatter includes both sender and chat_name (group name)
```

### Test 7: Session Expiration Detection
```bash
# Log out of WhatsApp Web from phone

# Run once
whatsapp-watcher --once

# Expected:
# - Error logged: "WhatsApp session expired"
# - Exit with message: "Run `whatsapp-watcher --auth` to re-authenticate"
# - Exit code 1
```

---

## Task Summary

| Phase | Tasks | Module | LOC Estimate |
|-------|-------|--------|--------------|
| Phase 1: Session | T001-T012 (12 tasks) | session.py | ~150 LOC |
| Phase 2: Scraper | T013-T026 (14 tasks) | scraper.py | ~250 LOC |
| Phase 3: Writer | T027-T038 (12 tasks) | writer.py | ~200 LOC |
| Phase 4: State | T039-T047 (9 tasks) | state.py | ~120 LOC |
| Phase 5: Poll-Loop | T048-T059 (12 tasks) | __main__.py | ~100 LOC |
| **Total** | **59 tasks** | **5 modules** | **~820 LOC** |

---

## Dependencies

**Task Dependencies**:
- T001-T012 (Session) can start immediately (no blockers)
- T013-T026 (Scraper) can run in parallel with Session
- T027-T038 (Writer) can run in parallel with Session and Scraper
- T039-T047 (State) can run in parallel with other phases
- T048-T059 (Poll-Loop) requires T012, T026, T038, T047 complete (all modules done)

**Parallel Opportunities**:
- Phases 1-4 (Session, Scraper, Writer, State) can be implemented in parallel by different developers
- Phase 5 (Poll-Loop) must be implemented last as it integrates all modules

**Recommended Sequence** (risk-first):
1. Phase 1: Session (T001-T012) - highest risk (Playwright + QR auth unknowns)
2. Phase 2: Scraper (T013-T026) - high risk (DOM fragility)
3. Phase 3: Writer (T027-T038) - medium risk (markdown generation)
4. Phase 4: State (T039-T047) - low risk (JSON serialization)
5. Phase 5: Poll-Loop (T048-T059) - low risk, high value (orchestration)

---

## Out of Scope (No Tasks)

The following are explicitly **excluded** from this MVP task list:

- ❌ Message sending/replying functionality
- ❌ Media file downloads (images, videos, documents)
- ❌ Multi-account support
- ❌ Real-time push notifications
- ❌ Message read/deletion in WhatsApp
- ❌ Advanced CLI options (custom templates, filters)
- ❌ Comprehensive test suite (unit tests for each function)
- ❌ Performance optimization (batch processing, caching)
- ❌ State pruning (hash dict cleanup)
- ❌ Facebook Messenger integration
- ❌ LinkedIn modifications
- ❌ Gmail/Router/HITL modifications
- ❌ MCP server integration
- ❌ Documentation updates beyond code comments

These items may be added in future iterations **after** MVP validation.

---

## Definition of Done

The WhatsApp Watcher MVP is **complete** when:

1. ✅ All 59 tasks (T001-T059) marked complete
2. ✅ All 5 modules implemented: session.py, scraper.py, writer.py, state.py, poll-loop in __main__.py
3. ✅ All 7 verification tests pass
4. ✅ `whatsapp-watcher --auth` successfully authenticates and saves session
5. ✅ `whatsapp-watcher --once` captures messages in headless mode
6. ✅ Deduplication prevents duplicate files on repeated runs
7. ✅ Urgent messages route to /Needs_Action/whatsapp/
8. ✅ Group messages include group_name and sender
9. ✅ Session expiration detected with actionable error message
10. ✅ Ralph Wiggum retry pattern implemented for transient errors

**Sign-off Criteria**:
- Demo to user with real WhatsApp account
- User confirms message capture quality meets expectations
- No blocking bugs in core pipeline

---

## Next Steps After Completion

Once MVP is complete and verified:

1. Update tasks.md to mark T001-T059 as complete
2. Update specs/007-whatsapp-watcher/README.md status to "MVP Complete"
3. Create PHR for implementation session
4. Decide on next iteration:
   - Option A: Add message reply capability (Silver Tier expansion)
   - Option B: Add media file downloads
   - Option C: Add comprehensive test coverage
   - Option D: Move to next phase (Facebook Publisher or other feature)

---

**END OF MVP COMPLETION TASKS**
