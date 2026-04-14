---
id: "0002"
title: "WhatsApp Watcher Implementation Plan"
stage: plan
date: 2026-03-22
surface: agent
model: claude-opus-4-5-20251101
feature: 007-whatsapp-watcher
branch: 007-whatsapp-watcher
user: umair
command: /sp.plan
labels: ["whatsapp", "watcher", "playwright", "implementation", "architecture"]
links:
  spec: specs/007-whatsapp-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/007-whatsapp-watcher/plan.md
  - specs/007-whatsapp-watcher/research.md
  - specs/007-whatsapp-watcher/data-model.md
tests:
  - null
---

## Prompt

Create an implementation plan for the approved WhatsApp watcher phase.

Requirements:
- Base the plan strictly on the approved spec
- No scope expansion
- Keep the architecture vault-first and file-driven
- Assume Gmail watcher, router, brain, and HITL already exist
- Include plan sections for:
  - session handling
  - message detection
  - markdown generation
  - vault routing
  - deduplication
  - logging
  - testing
- Keep the phase limited to WhatsApp ingestion only

Output a structured implementation plan only.

## Response snapshot

Created comprehensive implementation plan with 7 detailed sections:

1. **Session Handling**: Playwright storage_state() for session persistence, headed mode for QR auth, headless for polling
2. **Message Detection**: Centralized selectors in `selectors.py`, scraper functions with Ralph Wiggum retry
3. **Markdown Generation**: Mirrors gmail_watcher/writer.py pattern, 12 required frontmatter fields
4. **Vault Routing**: `/Inbox/whatsapp/` for normal, `/Needs_Action/whatsapp/` for urgent (keyword-based)
5. **Deduplication**: SHA-256 hash of chat+sender+timestamp+body, persisted to `.watcher-state/whatsapp-dedup.json`
6. **Logging**: Daily log files in `/Logs/`, append-only Markdown with poll cycle and error entries
7. **Testing**: Unit tests for models/state/writer, integration tests, manual hackathon scenarios

**Supporting artifacts created**:
- `research.md`: 8 research topics resolved (session persistence, selectors, hashing, etc.)
- `data-model.md`: 5 entities defined (WhatsAppMessage, DeduplicationState, WatcherConfig, etc.)

**Constitution Check**: All 8 principles PASS (WhatsApp uses Playwright per Principle VI/VIII)

**Module structure**: 10 files following gmail_watcher pattern for consistency

## Outcome

- ✅ Impact: Implementation plan ready for `/sp.tasks` to generate actionable tasks
- 🧪 Tests: Unit + integration + manual test scenarios defined
- 📁 Files: 3 files created (plan.md, research.md, data-model.md)
- 🔁 Next prompts: `/sp.tasks` to generate implementation task list
- 🧠 Reflection: Plan follows existing gmail_watcher pattern for consistency; centralized selectors mitigate WhatsApp UI change risk

## Evaluation notes (flywheel)

- Failure modes observed: None — plan aligns with spec without scope expansion
- Graders run and results (PASS/FAIL): Constitution check PASS (all 8 principles verified)
- Prompt variant (if applicable): Standard /sp.plan with section requirements
- Next experiment (smallest change to try): None needed — proceed to task generation
