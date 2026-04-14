---
id: 0003
title: Phase 2 Email Reasoning Tasks
stage: tasks
date: 2026-03-07
surface: agent
model: claude-opus-4-5-20251101
feature: 004-email-reasoning
branch: 004-email-reasoning
user: umair
command: /sp.tasks
labels: ["phase-2", "email-reasoning", "tasks", "implementation-breakdown"]
links:
  spec: phase-2/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-email-reasoning/tasks.md
  - phase-2/README.md
tests:
  - none (task generation phase)
---

## Prompt

/sp.tasks

(Phase 2: Email Reasoning Layer - generate dependency-ordered tasks from plan)

## Response snapshot

Generated comprehensive tasks.md with 107 tasks organized by user story:

**Task Breakdown by Phase**:

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Setup | 6 (T001-T006) | 4 |
| Foundational | 25 (T007-T031) | 9 |
| US1: Actionable Creates Task (P1) | 24 (T032-T055) | 2 |
| US2: Promotional No Task (P1) | 7 (T056-T062) | 2 |
| US3: Multi-Step Creates Plan (P2) | 11 (T063-T073) | 2 |
| US4: Original Unchanged (P1) | 5 (T074-T078) | 2 |
| US5: Idempotent Processing (P2) | 7 (T079-T085) | 3 |
| CLI | 13 (T086-T098) | 1 |
| Logging | 4 (T099-T102) | 0 |
| Polish | 5 (T103-T107) | 3 |

**User Story Organization**:
- US1 (P1): Actionable Email Creates Task - Core classifier, writer, engine
- US2 (P1): Promotional Email Does Not Create Task - Classification filtering
- US3 (P2): Multi-Step Email Creates Plan - Plan file generation
- US4 (P1): Original Email Files Unchanged - Safety/read-only verification
- US5 (P2): Idempotent Processing - State management integration

**Key Features**:
- Each user story independently testable
- Acceptance tests mapped to tasks (AT-01 to AT-06)
- Critical path identified: Setup → Foundational → US1 → CLI → Polish
- 28 parallelizable tasks identified across all phases
- MVP scope: Setup + Foundational + US1 (55 tasks)

**Module Structure**:
- `src/email_reasoner/models.py` - 6 data models
- `src/email_reasoner/config.py` - ReasonerConfig
- `src/email_reasoner/scanner.py` - Email file parsing
- `src/email_reasoner/state.py` - Deduplication
- `src/email_reasoner/classifier.py` - LLM classification
- `src/email_reasoner/writer.py` - Task/plan generation
- `src/email_reasoner/engine.py` - Orchestration
- `src/email_reasoner/__main__.py` - CLI

## Outcome

- Impact: 107 tasks ready for implementation
- Tests: Unit test tasks included per component
- Files: 2 created/modified (tasks.md, README.md)
- Next prompts: `/sp.implement` to execute tasks
- Reflection: Tasks organized by user story for incremental delivery; MVP = US1

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh detected wrong feature (003 vs 004), resolved manually
- Graders run and results (PASS/FAIL): N/A (task generation)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.implement starting with Phase 1 Setup
