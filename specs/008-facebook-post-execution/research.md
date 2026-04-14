# Research: Facebook Post Execution

**Feature**: 008-facebook-post-execution
**Date**: 2026-03-22

---

## Overview

This document records technical research and decisions for implementing the Facebook post execution phase. All decisions align with the approved spec and follow the LinkedIn publisher (006-linkedin-publish) pattern for consistency.

---

## Decision 1: Browser Automation Framework

**Decision**: Use Playwright (Python) for Facebook browser automation

**Rationale**:
- Consistent with existing Silver Tier architecture (Gmail watcher, WhatsApp watcher, LinkedIn publisher)
- Already a project dependency with proven patterns
- Supports persistent sessions via storage_state
- Headless-first with headed mode for authentication

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Facebook Graph API | Requires app approval, OAuth complexity, limited personal profile posting |
| Selenium | Playwright has better async support, cleaner API, already in project |
| Direct HTTP requests | Facebook requires JS rendering, auth complexity |

---

## Decision 2: Session Persistence Strategy

**Decision**: Store Playwright storage_state at `.watcher-state/facebook/storage_state.json`

**Rationale**:
- Follows WhatsApp and LinkedIn watcher patterns
- Enables headless operation after initial headed auth
- Path excluded from git via existing `.gitignore` rules

**Storage Layout**:
```
.watcher-state/
└── facebook/
    ├── storage_state.json    # Playwright session (cookies, localStorage)
    └── publisher.json        # Execution state (processed hashes)
```

---

## Decision 3: File Detection Strategy

**Decision**: Use watchdog (watcher mode) with poll fallback

**Rationale**:
- Already a project dependency (watchdog >=6.0)
- Consistent with other watchers
- Poll mode provides fallback for unreliable inotify environments
- Detection latency target: 30 seconds (per FR-001)

**Configuration**:
- Default: watcher mode using `watchdog.observers.Observer`
- Fallback: poll mode at 30-second intervals
- Startup: scan existing files in `/Approved/facebook/` for catch-up

---

## Decision 4: Content Extraction

**Decision**: Extract post content from `## Content Preview` section or full body

**Rationale**:
- Matches LinkedIn publisher pattern
- Clear separation between metadata (frontmatter) and content (body)
- Fallback to full body allows flexibility

**Extraction Logic**:
1. Look for `## Content Preview` heading
2. If found, extract everything after until next heading or EOF
3. If not found, use entire body after frontmatter separator

---

## Decision 5: Facebook Selector Strategy

**Decision**: Centralized selector configuration with fallback chains

**Rationale**:
- Facebook's DOM changes frequently (like LinkedIn)
- Centralized selectors enable quick maintenance
- Fallback chains improve resilience

**Selector Categories**:
```python
SELECTORS = {
    "new_post_trigger": [...],      # Button to open composer
    "post_editor": [...],           # Text input area
    "visibility_dropdown": [...],   # Public/Friends/Only Me
    "post_button": [...],           # Submit button
    "post_success": [...],          # Confirmation indicator
}
```

---

## Decision 6: Retry Strategy (Ralph Wiggum Loop)

**Decision**: 3 retries with adaptive strategy per Constitution Principle V

**Rationale**:
- Constitution mandates 3-retry loop
- Adaptive strategy increases success on transient failures
- Clear escalation path after exhaustion

**Retry Levels**:
1. **Attempt 1**: Standard execution with default timeouts
2. **Attempt 2**: Increased timeouts, re-read page, alternative selectors
3. **Attempt 3**: Maximum timeouts, page refresh, simplified approach
4. **After 3 failures**: Log, update frontmatter, preserve file

---

## Decision 7: Audit Log Format

**Decision**: JSON Lines format in daily-rotated files

**Rationale**:
- Consistent with LinkedIn publisher and HITL logger patterns
- Easy to parse, grep, and analyze
- Daily rotation prevents unbounded file growth

**Log Path**: `/Logs/facebook/facebook-YYYYMMDD.log`

**Event Types**:
- `detected`: File found in /Approved/facebook/
- `validated`: Frontmatter passed validation
- `publishing`: Publish attempt started
- `published`: Post successfully published
- `failed`: Publish attempt failed (with retry count)
- `moved_to_done`: File moved to /Done/facebook/
- `moved_to_needs_action`: File moved due to unrecoverable error
- `duplicate_skipped`: Content hash already processed

---

## Decision 8: CLI Framework

**Decision**: Use Click for CLI implementation

**Rationale**:
- Already used by LinkedIn publisher
- Clean decorator-based command definitions
- Built-in help generation and option parsing

**Commands**:
- `facebook-publish run` — One-shot processing
- `facebook-publish watch` — Continuous monitoring
- `facebook-publish list` — Show pending approved posts
- `facebook-publish status` — Show execution statistics
- `facebook-publish auth` — Headed mode for login

---

## Decision 9: Idempotency Strategy

**Decision**: Content hash tracking in `.watcher-state/facebook/publisher.json`

**Rationale**:
- Prevents duplicate posts from identical content
- 24-hour deduplication window (per SC-006)
- Hash includes: action_type + content + source_path

**Hash Algorithm**: SHA-256 truncated to 16 hex characters

---

## Decision 10: Post Visibility Handling

**Decision**: Support `public`, `friends`, `only_me` visibility options

**Rationale**:
- Matches spec frontmatter schema
- Covers common personal profile posting use cases
- Implemented via Playwright visibility dropdown interaction

**Default**: `public` (if not specified in frontmatter)

---

## Non-Decisions (Deferred)

These items are explicitly out of scope per the spec:

1. **Image/video attachments** — Text only in this phase
2. **Facebook Pages posting** — Personal profile only
3. **Facebook Groups posting** — Personal timeline only
4. **Scheduled posting** — Immediate only
5. **Facebook API migration** — Playwright only for this phase

---

**End of Research Document**
