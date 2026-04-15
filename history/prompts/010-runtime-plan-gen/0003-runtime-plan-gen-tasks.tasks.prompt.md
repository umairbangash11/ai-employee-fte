---
id: "0003"
title: Runtime Plan Generation Tasks
stage: tasks
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 010-runtime-plan-gen
branch: 010-runtime-plan-gen
user: Umair Ahmad
command: /sp.tasks
labels: ["silver-tier", "orchestrator", "plan-generation", "tasks"]
links:
  spec: specs/010-runtime-plan-gen/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/010-runtime-plan-gen/tasks.md
  - history/prompts/010-runtime-plan-gen/0003-runtime-plan-gen-tasks.tasks.prompt.md
tests:
  - tests/unit/orchestrator/test_plan_writer.py
---

## Prompt

Break the approved runtime Plan.md generation plan into small, verifiable implementation tasks.

Rules:

* No scope expansion
* No Gold-tier tasks
* No unrelated refactors
* Include validation tasks for:

  * plan file creation
  * correct vault location
  * expected markdown structure
  * end-to-end runtime flow

## Response snapshot

Created `specs/010-runtime-plan-gen/tasks.md` with:
- Phase 1 (Setup): T001 — create `tests/unit/orchestrator/__init__.py`
- Phase 2 (Foundational): T002–T005 — create `src/orchestrator/plan_writer.py` with `_safe_slug`, `_deduplicate_path`, `write_runtime_plan`
- Phase 3 (US1 — actionable email, P1 MVP): T006–T010 — 5 unit tests: plan created, all 7 fields present, correct vault location, 6 markdown sections, standard checkboxes
- Phase 4 (US2 — non-actionable path, P2): T011–T015 — brain.py integration: `plans_dir` attr, import, `_route_reply_needed()` call site, verify single call site only
- Phase 5 (US3 — independent testability, P2): T016–T021 — 5 additional edge-case tests: deduplication, error fallback steps, write failure → None, plans_dir created if missing, requires_approval always true
- Phase 6 (E2E validation): T022–T027 — smoke test against real vault, validate location, structure, frontmatter, checkboxes
- Total: 27 tasks across 6 phases

## Outcome

- ✅ Impact: Complete, immediately executable task breakdown covering all 3 user stories and explicit E2E validation
- 🧪 Tests: 10 unit tests planned (T006–T010, T016–T020) + 1 import verify (T021) — no OpenAI, no watcher
- 📁 Files: tasks.md
- 🔁 Next prompts: /sp.implement
- 🧠 Reflection: Phase 6 (E2E) is the only phase that touches the real vault — all unit tests use `tmp_path`. This keeps the test suite fast and deterministic while still validating the full runtime path.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): task format validated — all tasks have ID, optional [P], optional [Story], description with file path
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.implement to execute T001–T027
