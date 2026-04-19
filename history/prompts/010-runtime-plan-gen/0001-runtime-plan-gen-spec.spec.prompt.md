---
id: "0001"
title: Runtime Plan Generation Spec
stage: spec
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 010-runtime-plan-gen
branch: 010-runtime-plan-gen
user: Umair Ahmad
command: /sp.specify
labels: ["silver-tier", "orchestrator", "plan-generation", "spec"]
links:
  spec: specs/010-runtime-plan-gen/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/010-runtime-plan-gen/spec.md
  - specs/010-runtime-plan-gen/checklists/requirements.md
  - history/prompts/010-runtime-plan-gen/0001-runtime-plan-gen-spec.spec.prompt.md
tests:
  - null
---

## Prompt

Implement runtime Plan.md generation in the existing AI Employee project to satisfy the remaining Silver-tier requirement.

Scope:

* Update the existing reasoning/orchestrator flow only
* When a new actionable item is processed, generate a runtime markdown plan file in the vault
* The plan must be created from real runtime processing, not spec artifacts
* Keep implementation minimal and aligned with current architecture
* Do not modify unrelated modules
* Do not modify SpecifyPlus internal folders
* Do not start Gold-tier work
* Do not refactor the broader architecture

Plan file requirements:

* title
* objective
* source/context
* action steps as checkboxes
* approval requirement if applicable
* status
* created timestamp

Success criteria:

* Runtime processing creates a real Plan.md-style file in the vault
* Existing flow remains working
* Plan generation is testable and verifiable
* Scope stays limited to Silver compliance

## Response snapshot

Created `specs/010-runtime-plan-gen/spec.md` with:
- 3 user stories: plan for actionable email (P1), no plan for non-actionable (P2), independently testable writer function (P2)
- 10 functional requirements (FR-001–FR-010) covering creation, fields, ordering, error handling, deduplication
- 3 key entities: RuntimePlan, PlanMetadata, ActionStep
- 5 measurable success criteria
- Assumptions clarifying that new plan writer is SEPARATE from existing `write_execution_plan()` — serves different purposes
- Tight Out of Scope preventing any changes outside `brain.py`
- Quality checklist: all 14 items pass

## Outcome

- ✅ Impact: Second remaining Silver-tier gap now has a complete, unambiguous spec
- 🧪 Tests: SC-004 explicitly requires the plan writer to be unit-testable without OpenAI or watcher loop
- 📁 Files: specs/010-runtime-plan-gen/spec.md, checklists/requirements.md
- 🔁 Next prompts: /sp.plan, then /sp.tasks, then /sp.implement
- 🧠 Reflection: Key architectural decision captured in Assumptions — new plan writer sits alongside brain.py, not inside planner.py; preserves separation of concerns between safety-plan (Approved/) and reasoning-plan (Needs_Action/plans/)

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist 14/14 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.plan to design the minimal writer function and integration point
