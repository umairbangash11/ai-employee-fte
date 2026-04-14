---
id: "0003"
title: "WhatsApp Watcher Task Generation"
stage: tasks
date: 2026-03-22
surface: agent
model: claude-opus-4-5-20251101
feature: 007-whatsapp-watcher
branch: 007-whatsapp-watcher
user: umair
command: /sp.tasks
labels: ["whatsapp", "watcher", "tasks", "implementation", "playwright"]
links:
  spec: specs/007-whatsapp-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/007-whatsapp-watcher/tasks.md
tests:
  - null
---

## Prompt

Generate small, verifiable implementation tasks for the approved WhatsApp watcher phase.

Requirements:
- Tasks must be atomic and testable
- No scope expansion
- Cover only:
  - watcher setup
  - WhatsApp session handling
  - unread/new message detection
  - markdown capture with frontmatter
  - vault routing
  - deduplication
  - logging
  - tests
- Each task must include a clear completion condition

Output tasks only.

## Response snapshot

Generated comprehensive tasks.md with 61 tasks organized into 10 phases:

1. **Phase 1: Setup** (3 tasks): Module skeleton, CLI entrypoint, .watcher-state directory
2. **Phase 2: Foundational** (4 tasks): config.py, models.py, selectors.py, test directories
3. **Phase 3: US1 Headless Capture** (11 tasks): Session loading, scraper, writer, poll loop
4. **Phase 4: US2 QR Authentication** (4 tasks): Headed browser, QR scan persistence
5. **Phase 5: US3 Urgency Routing** (6 tasks): is_urgent(), determine_destination(), routing
6. **Phase 6: US4 Deduplication** (8 tasks): state.py with load/save/is_captured/mark_captured
7. **Phase 7: US5 Group Chats** (5 tasks): detect_chat_type(), group metadata extraction
8. **Phase 8: US6 Error Logging** (10 tasks): logger.py, Ralph Wiggum retry wrapper
9. **Phase 9: Integration Tests** (4 tasks): End-to-end, dedup, routing, recovery tests
10. **Phase 10: Polish** (6 tasks): pyproject.toml entry, media detection, test runs

**Task Format**: Every task follows `[ID] [P?] [Story?] Description with file path` format.

**Parallel Opportunities**: Identified parallel execution points within each phase.

**MVP Strategy**: US1 + US2 provide demo-ready functionality for hackathon.

## Outcome

- ✅ Impact: 61 atomic, testable tasks ready for `/sp.implement` execution
- 🧪 Tests: 16 test tasks included (unit + integration per spec.md requirements)
- 📁 Files: 1 file created (tasks.md)
- 🔁 Next prompts: `/sp.implement` to execute tasks sequentially
- 🧠 Reflection: Tasks organized by user story enable independent implementation; MVP achievable with Phase 1-4 only

## Evaluation notes (flywheel)

- Failure modes observed: None — tasks align with plan.md structure and spec.md requirements
- Graders run and results (PASS/FAIL): Manual review PASS — all 61 tasks have completion conditions and file paths
- Prompt variant (if applicable): Standard /sp.tasks with atomic task requirements
- Next experiment (smallest change to try): None needed — proceed to implementation
