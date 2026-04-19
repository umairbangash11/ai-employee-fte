---
id: "0004"
title: Runtime Plan Generation Implementation
stage: green
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 010-runtime-plan-gen
branch: 010-runtime-plan-gen
user: Umair Ahmad
command: /sp.implement
labels: ["silver-tier", "orchestrator", "plan-generation", "green"]
links:
  spec: specs/010-runtime-plan-gen/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - tests/unit/orchestrator/__init__.py
  - src/orchestrator/plan_writer.py
  - tests/unit/orchestrator/test_plan_writer.py
  - src/orchestrator/brain.py
  - specs/010-runtime-plan-gen/tasks.md
  - history/prompts/010-runtime-plan-gen/0004-runtime-plan-gen-implement.green.prompt.md
tests:
  - tests/unit/orchestrator/test_plan_writer.py
---

## Prompt

Implement the approved tasks for runtime Plan.md generation in the existing AI Employee project.

Rules:

* Do not touch unrelated modules
* Do not modify SpecifyPlus internal folders
* Keep implementation minimal and clean
* Create/update only files needed for runtime Plan.md generation
* Show files changed
* Show exact run commands
* Show exact verification steps
* Stop when Plan.md implementation is complete

## Response snapshot

Executed all 27 tasks across 6 phases:

**Phase 1**: Created `tests/unit/orchestrator/__init__.py` (empty package init).

**Phase 2**: Created `src/orchestrator/plan_writer.py` with:
- `_safe_slug(subject)` — lowercase, `[a-z0-9-]`, max 40 chars, strip hyphens
- `_deduplicate_path(plans_dir, filename)` — appends `_1`, `_2` on conflict
- `write_runtime_plan(plans_dir, source_filename, email_meta, classification)` — writes YAML frontmatter + 6 Markdown sections; `OSError` caught; returns `Path | None`

**Phase 3 + 5**: Created `tests/unit/orchestrator/test_plan_writer.py` — 15 tests covering all user stories and edge cases. All 15 pass in 0.07s.

**Phase 4**: Modified `src/orchestrator/brain.py`:
- Added import: `from orchestrator.plan_writer import write_runtime_plan`
- Added `self.plans_dir = self.needs_action_dir / "plans"` to `InboxTriageHandler.__init__`
- Inserted `write_runtime_plan(...)` call in `_route_reply_needed()` after `write_execution_plan()`, before `shutil.move()`
- Log entry updated to include plan filename

**Phase 6 (E2E)**: Smoke test against `vault/Needs_Action/plans/` — plan file created, all 7 frontmatter fields present, all 6 Markdown sections correct, `- [ ]` checkbox format verified.

## Outcome

- ✅ Impact: Silver-tier runtime Plan.md generation gap fully closed — orchestrator now writes a triage plan file to `Needs_Action/plans/` for every actionable email
- 🧪 Tests: 15/15 unit tests pass (0.07s) — no OpenAI, no watcher, no vault required
- 📁 Files: plan_writer.py (NEW), brain.py (MODIFIED), test_plan_writer.py (NEW), __init__.py (NEW)
- 🔁 Next prompts: Silver tier audit to confirm 100% compliance
- 🧠 Reflection: `write_runtime_plan()` is a standalone function in `plan_writer.py` — independently testable, follows `sentinel/planner.py` pattern exactly. The `brain.py` diff is minimal: 1 import, 1 attribute, 1 call block.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): 15/15 unit tests PASS, E2E smoke test PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run Silver tier audit to verify 100% compliance
