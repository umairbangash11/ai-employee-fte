---
id: 0005
title: WhatsApp Watcher MVP Tasks Generation
stage: tasks
date: 2026-04-12
surface: agent
model: claude-sonnet-4-5
feature: 007-whatsapp-watcher
branch: 008-facebook-post-execution
user: umair
command: /sp.tasks
labels: ["mvp", "tasks", "whatsapp-watcher", "completion"]
links:
  spec: /home/umair/ai-employee-fte/specs/007-whatsapp-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/007-whatsapp-watcher/mvp-completion-tasks.md
tests:
  - 7 verification tests defined
---

## Prompt

/sp.tasks

Feature ID: 007-whatsapp-watcher
Feature Name: WhatsApp Watcher MVP Completion

Generate implementation tasks for completing only the WhatsApp Watcher MVP work.

Context:
- This is not a greenfield feature
- Existing foundation already exists in:
  - src/whatsapp_watcher/config.py
  - src/whatsapp_watcher/models.py
  - src/whatsapp_watcher/selectors.py
- Remaining or incomplete MVP files to complete:
  - src/whatsapp_watcher/session.py
  - src/whatsapp_watcher/scraper.py
  - src/whatsapp_watcher/writer.py
  - src/whatsapp_watcher/state.py
- Poll-loop integration is also required for MVP execution

Locked scope:
- Complete only the WhatsApp Watcher MVP
- Do not expand scope beyond this feature
- Do not include Facebook, LinkedIn, Gmail reasoning, banking, Odoo, cloud delegation, or unrelated CLI polish
- Do not modify SpecifyPlus internal folders
- Keep implementation read-only with respect to outbound communication
- No sending messages
- No replying
- No creating contacts
- No external mutations beyond local session use for reading
- Only create vault markdown artifacts for relevant inbound messages
- Use Playwright-based WhatsApp Web automation for MVP
- Reuse the existing config/models/selectors contracts where possible
- Use state tracking for idempotency and duplicate prevention

Target MVP pipeline:
session/auth -> scrape unread/relevant chats -> normalize message data -> write markdown artifact -> record state/dedup

Required MVP behavior:
1. Initialize and reuse a local WhatsApp Web session
2. Detect unread or relevant chats/messages through Playwright
3. Extract and normalize message data needed for vault artifacts
4. Write normalized markdown files into the approved vault action area
5. Record processed message/chat state to prevent duplicates
6. Support MVP execution flow with poll-loop behavior if required by the approved scope
7. Keep logging and error handling minimal but sufficient for MVP reliability

Task generation requirements:
- Break work into small, verifiable, implementation-ready tasks
- Group tasks by module responsibility
- Include tasks for:
  - session.py
  - scraper.py
  - writer.py
  - state.py
  - poll-loop integration
  - reuse/integration of existing config.py, models.py, selectors.py
  - minimal logging/error handling for the MVP path
- Prefer tasks that can be completed and verified independently
- Keep task granularity tight enough for disciplined implementation
- Include explicit acceptance checks for each meaningful task group
- Mark out-of-scope items clearly and do not create tasks for them

Output rules:
- Output only tasks
- Do not generate code
- Do not generate implementation
- Do not add future-feature tasks
- Do not expand beyond the approved WhatsApp Watcher MVP scope

## Response snapshot

Created focused MVP completion task list at specs/007-whatsapp-watcher/mvp-completion-tasks.md

**59 Tasks Total:**
- Phase 1: Session (T001-T012) - 12 tasks, ~150 LOC
- Phase 2: Scraper (T013-T026) - 14 tasks, ~250 LOC
- Phase 3: Writer (T027-T038) - 12 tasks, ~200 LOC
- Phase 4: State (T039-T047) - 9 tasks, ~120 LOC
- Phase 5: Poll-Loop (T048-T059) - 12 tasks, ~100 LOC

**Key Features:**
- Session management: Playwright storage_state for QR auth and headless reuse
- Scraping: DOM queries for unread chats, message extraction, group vs individual detection
- Writer: YAML frontmatter, urgency keyword routing, atomic file writes
- State: Hash-based deduplication with JSON persistence
- Poll-loop: Continuous polling with Ralph Wiggum retry, graceful shutdown
- Output routing: /Inbox/whatsapp/ vs /Needs_Action/whatsapp/

**Module Breakdown:**

**Phase 1 - Session (T001-T012):**
- Browser context creation with headed/headless branching
- QR code detection and authentication flow
- Session persistence via storage_state.json
- Session expiration detection
- Custom exception classes (SessionExpiredError, QRTimeoutError)

**Phase 2 - Scraper (T013-T026):**
- Unread chat detection via unread badges
- Message extraction from conversation panels
- Timestamp parsing (HH:MM, Yesterday, DD/MM/YYYY formats)
- Group vs individual chat differentiation
- Media type detection (image/video/audio/document)
- Ralph Wiggum retry for selector failures

**Phase 3 - Writer (T027-T038):**
- Urgency keyword matching (case-insensitive)
- Filename generation with sanitization
- YAML frontmatter with all required fields
- Markdown body formatting
- Directory routing (Inbox vs Needs_Action)
- Atomic writes (temp file + rename)
- Dry-run mode support

**Phase 4 - State (T039-T047):**
- Load/save deduplication state from JSON
- Hash-based duplicate detection
- Corrupted state recovery
- In-memory state mutations with atomic saves

**Phase 5 - Poll-Loop (T048-T059):**
- Auth mode implementation (--auth flag)
- Poll cycle orchestration (scrape → filter → write → save)
- Continuous polling loop with sleep
- Single-shot mode (--once flag)
- Ralph Wiggum retry for poll cycle errors
- Graceful shutdown (Ctrl+C handling)
- Stats logging to /Logs/

**7 Verification Tests:**
1. Fresh Authentication: --auth mode saves session
2. Headless Message Capture: --once captures without QR
3. Urgency Routing: "URGENT" keyword routes to /Needs_Action/
4. Deduplication: Second run creates no duplicates
5. Dry-Run: Preview mode logs without writing
6. Group Chat Message: Group messages include sender and chat_name
7. Session Expiration: Detects expired session with actionable error

**Excluded:** Message sending/replying, media downloads, multi-account, real-time push, message deletion, comprehensive tests, state pruning

## Outcome

- ✅ Impact: WhatsApp Watcher MVP completion tasks ready (59 tasks, ~820 LOC)
- 🧪 Tests: 7 verification tests defined
- 📁 Files: mvp-completion-tasks.md created
- 🔁 Next prompts: Begin T001 (session.py) or /sp.implement
- 🧠 Reflection: Tight task granularity (59 tasks for 5 modules), clear acceptance criteria per phase, risk-first sequencing

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A (task generation)
- Prompt variant (if applicable): Standard
- Next experiment (smallest change to try): Implement session.py first (T001-T012) to validate Playwright + QR auth (highest risk)
