---
id: 0004
title: WhatsApp Watcher MVP Completion Plan
stage: plan
date: 2026-04-12
surface: agent
model: claude-sonnet-4-5
feature: 007-whatsapp-watcher
branch: 008-facebook-post-execution
user: umair
command: /sp.plan
labels: ["mvp", "planning", "whatsapp-watcher", "completion"]
links:
  spec: /home/umair/ai-employee-fte/specs/007-whatsapp-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/007-whatsapp-watcher/mvp-completion-plan.md
tests:
  - none
---

## Prompt

/sp.plan

Feature ID: 007-whatsapp-watcher
Feature Name: WhatsApp Watcher MVP Completion

Plan the implementation for completing the WhatsApp Watcher MVP only.

Locked scope:
- Continue from the existing foundation already present in:
  - src/whatsapp_watcher/config.py
  - src/whatsapp_watcher/models.py
  - src/whatsapp_watcher/selectors.py
- Complete only the missing or incomplete MVP pieces:
  - src/whatsapp_watcher/session.py
  - src/whatsapp_watcher/scraper.py
  - src/whatsapp_watcher/writer.py
  - src/whatsapp_watcher/state.py
  - poll-loop integration for MVP execution

Target MVP pipeline:
session/auth -> scrape -> normalize -> write -> state/dedup

Planning constraints:
- Do not invent requirements
- Do not expand beyond WhatsApp Watcher MVP
- Do not include Facebook, LinkedIn, Gmail, banking, Odoo, or cloud architecture
- Do not modify existing Gmail watcher, router, or HITL systems
- Treat the spec as fixed (no clarification needed, spec is complete)
- Keep implementation read-only with respect to WhatsApp Web
- No message sending, replying, or deletion
- Only generate vault markdown outputs for captured messages
- Use existing deduplication state mechanism

MVP behavior to plan for:
1. Playwright browser automation of WhatsApp Web
2. QR code authentication flow (one-time, headed mode)
3. Session persistence for headless polling
4. Message scraping from unread conversations
5. Urgency detection via keyword matching
6. Markdown file generation with YAML frontmatter
7. Routing to /Inbox/whatsapp/ or /Needs_Action/whatsapp/
8. Hash-based deduplication
9. Poll-loop with configurable interval (default 60s)
10. Error handling with Ralph Wiggum retry pattern

For each missing module, describe:
1. Module purpose and responsibilities
2. Key functions and their signatures
3. How this module reuses existing config.py, models.py, selectors.py
4. Interface boundaries (what this module exports, what it imports from others)
5. Data flow for one watcher pass (session -> scrape -> write -> state)
6. Authentication/session persistence strategy (QR code vs reuse)
7. Deduplication strategy (hash computation, state persistence)
8. Polling model and execution flow (continuous loop vs single-shot)
9. Implementation sequencing (which module to build first, dependencies between modules)

## Response snapshot

Created comprehensive MVP completion plan at specs/007-whatsapp-watcher/mvp-completion-plan.md

**Plan Summary:**

**Missing Modules (5):**
1. session.py - Playwright browser context with QR auth and session reuse (~150 LOC)
2. scraper.py - WhatsApp Web DOM scraping for unread messages (~250 LOC)
3. writer.py - Markdown file generation with frontmatter (~200 LOC)
4. state.py - Deduplication state management (~120 LOC)
5. poll-loop in __main__.py - Orchestration and polling (~100 LOC additions)

**Foundation Analysis (Complete):**
- config.py: WatcherConfig with all settings, environment variable loading
- models.py: WhatsAppMessage, DeduplicationState, CapturedMessageFile dataclasses
- selectors.py: WhatsApp Web DOM selectors and timeout constants
- __main__.py: CLI structure exists (stub only, needs wiring)

**Target Pipeline Flow:**
```
Input (WhatsApp Web) → session/auth → scrape → normalize → write → state/dedup → Output (Inbox/whatsapp/*.md)
```

**Key Design Decisions:**

**Session Management:**
- Playwright storage_state for cookie/localStorage persistence
- QR code flow: headed browser, wait for scan, save session
- Headless reuse: load storage_state.json, validate session
- Session expiration detection: QR code in headless → exit with actionable error

**Scraping Strategy:**
- Find chats with unread badges via `[data-testid="icon-unread-count"]`
- Click into each conversation
- Extract messages from `[data-testid="msg-container"]`
- Parse sender, timestamp, body, media indicators
- Differentiate individual vs group chats

**Writer Strategy:**
- YAML frontmatter: source, sender, chat_name, chat_type, urgency, hash, etc.
- Urgency keyword matching (URGENT, ASAP, emergency) → /Needs_Action/whatsapp/
- Normal messages → /Inbox/whatsapp/
- Filename format: {YYYYMMDD}-{HHMMSS}-{chat-slug}-{sender-slug}.md
- Atomic writes (temp file + rename)

**Deduplication Strategy:**
- Hash: SHA-256 of "whatsapp|{chat_name}|{sender}|{timestamp}|{body[:100]}" (first 16 chars)
- State: .watcher-state/whatsapp-dedup.json with message_hashes dict
- Filter: Check hash before writing, skip if exists
- Persistence: Save state after each poll cycle

**Polling Model:**
- Normal mode: Infinite loop with poll_interval sleep (default 60s)
- Single mode (--once): One poll cycle then exit
- Dry-run mode: Scrape and log, no file writes, no state updates
- Ralph Wiggum retry: 3 attempts with 2s, 4s delays for transient errors

**Implementation Sequence (Risk-First):**
1. Phase 1: session.py (highest risk - Playwright + QR auth unknowns)
2. Phase 2: scraper.py (high risk - WhatsApp Web DOM fragility)
3. Phase 3: writer.py (medium risk - markdown generation)
4. Phase 4: state.py (low risk - JSON serialization)
5. Phase 5: poll-loop in __main__.py (low risk, high value - orchestration)

**Estimated Complexity:** ~800 LOC across 5 modules, 17-24 hours (2-3 days)

**Verification Tests (5):**
1. Auth Flow: --auth mode completes QR scan and saves session
2. Headless Polling: --once mode captures messages without QR prompt
3. Urgency Routing: "URGENT" keyword routes to /Needs_Action/whatsapp/
4. Deduplication: Second run with same messages creates no duplicates
5. Dry-Run: --dry-run logs what would be captured without creating files

**Excluded from MVP:** Message sending/replying, media downloads, multi-account support, real-time push, message deletion, comprehensive test suite, state pruning

## Outcome

- ✅ Impact: WhatsApp Watcher MVP completion plan ready for implementation
- 🧪 Tests: 5 verification tests defined (auth, polling, urgency, dedup, dry-run)
- 📁 Files: 1 comprehensive plan document created (mvp-completion-plan.md)
- 🔁 Next prompts: /sp.tasks to generate dependency-ordered tasks, then /sp.implement
- 🧠 Reflection: Plan maintains narrow MVP scope, builds on complete foundation (config/models/selectors), clear 5-phase sequencing with risk-first approach

## Evaluation notes (flywheel)

- Failure modes observed: None (planning phase)
- Graders run and results (PASS/FAIL): Not applicable (planning phase)
- Prompt variant (if applicable): Standard planning prompt with locked scope
- Next experiment (smallest change to try): Implement session.py first to validate Playwright + QR auth (highest risk area)
