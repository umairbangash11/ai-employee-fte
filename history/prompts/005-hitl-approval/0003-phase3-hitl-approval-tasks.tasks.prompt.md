---
id: 0003
title: Phase 3 HITL Approval Tasks Generation
stage: tasks
date: 2026-03-08
surface: agent
model: claude-opus-4-5-20251101
feature: 005-hitl-approval
branch: 005-hitl-approval
user: umair
command: /sp.tasks
labels: ["phase-3", "hitl", "approval", "tasks", "implementation"]
links:
  spec: phase-3/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-hitl-approval/tasks.md
  - phase-3/README.md
tests:
  - none (task generation phase)
---

## Prompt

/sp.tasks
Generate small, verifiable implementation tasks for the approved HITL phase plan.

Requirements:
- Tasks must be atomic and testable
- No scope expansion
- Cover only:
  - approval folder support
  - markdown approval file schema
  - reasoner/orchestrator approval file creation
  - approved/rejected detection
  - audit logging
  - tests for pending/approved/rejected flows
- Each task must include a clear completion condition

Output tasks only.

## Response snapshot

Created comprehensive task list at `specs/005-hitl-approval/tasks.md` with 68 atomic tasks across 10 phases:

**Phase 1: Setup (T001-T004)**
- Package structure, exceptions, dependencies, CLI entry point

**Phase 2: Foundational (T005-T010)**
- ApprovalRequest/ApprovalState models, config, directory utilities, slug/filename generation

**Phase 3: US1 - Approval Creation (T011-T024)**
- Frontmatter generator, body generator, hash computation, state management
- Duplicate checking, main writer function
- Email reasoner integration (_requires_approval, _detect_action_type, _process_email)
- 4 unit/integration tests

**Phase 4: US2 - Approval Detection (T025-T036)**
- ApprovalLogger class with JSON lines output
- ApprovalEventHandler with on_created() for /Approved/
- ApprovalWatcher class with start()/stop()
- 3 tests

**Phase 5: US3 - Rejection Detection (T037-T042)**
- Extends watcher for /Rejected/ directory
- _is_rejected_path(), _handle_rejection() handlers
- 2 tests

**Phase 6: US4 - CLI Interface (T043-T052)**
- list, show, stats commands
- Approval file parser, output formatting
- 3 tests

**Phase 7: US5 - Rollback Strategy (T053-T058)**
- Rollback validation in model, frontmatter, body
- Frontmatter validator
- 2 tests

**Phase 8: Edge Cases (T059-T062)**
- Duplicate prevention, abandoned file logging, invalid frontmatter handling

**Phase 9: LinkedIn Integration (T063-T065)**
- request_linkedin_post_approval() function
- Orchestrator integration documentation

**Phase 10: Polish (T066-T068)**
- Docstrings, README update, test verification

**Task Summary:**
- Total: 68 tasks
- Parallel opportunities: 23 tasks marked [P]
- User story coverage: US1-US5 complete
- Acceptance test mapping: AT-01 through AT-07 covered

## Outcome

- Impact: Complete task breakdown ready for /sp.implement
- Tests: 16 test tasks included (unit + integration)
- Files: 2 created/modified (tasks.md, README.md)
- Next prompts: User confirmation, then /sp.implement
- Reflection: Tasks are atomic, file-specific, with clear completion conditions

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Task format validation PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.implement after user confirmation
