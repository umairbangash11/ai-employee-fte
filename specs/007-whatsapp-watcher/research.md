# Research: WhatsApp Watcher — Message Ingestion

**Feature Branch**: `007-whatsapp-watcher`
**Created**: 2026-03-22
**Purpose**: Resolve technical decisions and research findings before implementation

## Summary

This document captures research findings and design decisions for the WhatsApp watcher module. All decisions align with existing codebase patterns (gmail_watcher, sentinel) and constitution requirements.

---

## Research Topics

### 1. Playwright Session Persistence for WhatsApp Web

**Decision**: Use Playwright's `browser_context.storage_state()` to persist and restore session cookies/localStorage.

**Rationale**:
- WhatsApp Web stores authentication state in cookies and localStorage
- Playwright provides built-in session persistence via `storage_state(path)` and `context.storage_state()`
- This matches constitution Principle VI which requires "persistent sessions (cookies for WhatsApp)"
- Session data stored in `.watcher-state/whatsapp/storage_state.json`

**Alternatives Considered**:
- Manual cookie extraction: More complex, less reliable
- Selenium WebDriver: Heavier dependency, less Python-native
- Direct API access: WhatsApp has no public API for personal accounts

**Implementation Pattern**:
```python
# Save session after QR auth
context.storage_state(path=".watcher-state/whatsapp/storage_state.json")

# Restore session for headless polling
context = browser.new_context(storage_state=".watcher-state/whatsapp/storage_state.json")
```

---

### 2. WhatsApp Web Selector Strategy

**Decision**: Use stable selectors based on `data-*` attributes and ARIA labels where available; fallback to CSS class patterns for unread indicators.

**Rationale**:
- WhatsApp Web uses React with dynamically generated class names that change between deployments
- `data-testid` and `aria-label` attributes are more stable for automation
- Selector failures are expected periodically; constitution Principle V (Ralph Wiggum retry) handles this

**Key Selectors** (subject to WhatsApp UI changes):
- Chat list container: `[data-testid="chat-list"]` or `#pane-side`
- Unread badge: `span[data-testid="icon-unread-count"]` or `.unread-count`
- Chat item: `[data-testid="cell-frame-container"]`
- Message container: `[data-testid="conversation-panel-messages"]`
- Message text: `span.selectable-text`
- Group name: `[data-testid="conversation-info-header-chat-title"]`
- Sender in group: `span[data-testid="author"]`

**Risk Mitigation**:
- Centralize selectors in `selectors.py` module for easy updates
- Log selector failures with version info for debugging
- Hackathon scope: selectors tested against current WhatsApp Web (March 2026)

---

### 3. Message Deduplication Hash Strategy

**Decision**: Use SHA-256 hash of `{chat_name}|{sender}|{timestamp}|{body_preview}` to generate deterministic message ID.

**Rationale**:
- WhatsApp Web doesn't expose internal message IDs consistently in DOM
- Combination of chat + sender + timestamp + body is unique for practical purposes
- Matches constitution Principle VI: "deterministic hash (source + sender + timestamp + subject)"
- Consistent with gmail_watcher pattern using message_id mapping

**Implementation**:
```python
import hashlib

def compute_hash(chat_name: str, sender: str, timestamp: str, body: str) -> str:
    content = f"whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Storage**: `.watcher-state/whatsapp-dedup.json` (matches spec FR-007)

---

### 4. Urgency Keyword Detection

**Decision**: Case-insensitive substring matching against configurable keyword list.

**Rationale**:
- Simple, predictable behavior for hackathon demo
- Consistent with existing router keyword matching
- User can customize via `WHATSAPP_URGENCY_KEYWORDS` env variable

**Default Keywords**: `URGENT,ASAP,emergency,call me,time-sensitive`

**Implementation**:
```python
def is_urgent(body: str, keywords: list[str]) -> bool:
    body_lower = body.lower()
    return any(kw.lower() in body_lower for kw in keywords)
```

---

### 5. Logging Pattern

**Decision**: Daily log file with append-only Markdown format, consistent with spec logging requirements.

**Rationale**:
- Matches spec requirement: `<VAULT_PATH>/Logs/whatsapp-watcher-<YYYY-MM-DD>.md`
- Append-only allows continuous monitoring without file overwrites
- Markdown format is Obsidian-compatible for vault integration

**Log Entry Format**:
```markdown
### [HH:MM:SS] Poll Cycle

- **Messages found**: 3
- **New captures**: 2
- **Duplicates skipped**: 1
- **Urgent**: 0

| Chat | Sender | Urgency | Status |
|------|--------|---------|--------|
| John Doe | John Doe | normal | captured |
| Work Group | Alice | normal | captured |
| Family | Mom | normal | duplicate |
```

---

### 6. Error Recovery and Ralph Wiggum Loop

**Decision**: Implement 3-attempt retry pattern with escalating strategies per constitution Principle V.

**Rationale**:
- Constitution mandates Ralph Wiggum loop for all failures
- Selector failures are common with WhatsApp Web UI changes
- Network issues require graceful degradation

**Attempt Strategy**:
1. **Attempt 1**: Execute as planned (normal timeout)
2. **Attempt 2**: Re-read page, increase timeout, retry
3. **Attempt 3**: Simplify to minimal action (skip complex selectors, try basic detection)
4. **After 3 failures**: Log with actionable message, continue to next poll cycle

**Session Expiration**: Special case — exit with code 1 immediately (user must re-auth)

---

### 7. Module Structure Pattern

**Decision**: Follow gmail_watcher module pattern for consistency.

**Rationale**:
- Existing pattern is proven and constitution-compliant
- Reduces cognitive load for maintenance
- Enables potential shared abstractions in future

**Module Layout**:
```
src/whatsapp_watcher/
├── __init__.py       # Package exports
├── __main__.py       # CLI entrypoint
├── config.py         # Environment config loading
├── models.py         # Data classes (WhatsAppMessage, etc.)
├── selectors.py      # WhatsApp Web DOM selectors
├── session.py        # Playwright session management
├── scraper.py        # Message extraction from DOM
├── writer.py         # Markdown file generation
├── state.py          # Deduplication state persistence
└── logger.py         # Watcher-specific logging
```

---

### 8. Media Message Handling

**Decision**: Extract media type metadata only; do not download actual files.

**Rationale**:
- Spec explicitly excludes media downloads as out of scope
- Media detection improves message context without complexity
- Placeholder text in markdown body indicates media presence

**Media Types Detected**:
- Image: `[Image]`
- Video: `[Video]`
- Audio/Voice: `[Voice Note]`
- Document: `[Document: filename.ext]`

**Implementation**: Check for media container elements in message DOM and extract type.

---

## Resolved Unknowns

All technical unknowns from spec have been resolved:

| Unknown | Resolution |
|---------|------------|
| Session persistence mechanism | Playwright storage_state() |
| Selector strategy | data-testid + ARIA labels + fallback CSS |
| Hash computation | SHA-256 of chat+sender+timestamp+body |
| Module structure | Follow gmail_watcher pattern |
| Media handling | Metadata only, placeholder text |

---

## Dependencies Confirmed

| Dependency | Version | Purpose |
|------------|---------|---------|
| playwright | >=1.40 | Browser automation |
| python-dotenv | >=1.0 | Environment config |
| (existing) sentinel.logger | — | May reuse for consistency |

**Note**: No new dependencies beyond what's already in pyproject.toml.
