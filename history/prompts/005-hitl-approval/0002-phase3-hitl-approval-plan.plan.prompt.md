---
id: 0002
title: Phase 3 HITL Approval Implementation Plan
stage: plan
date: 2026-03-08
surface: agent
model: claude-opus-4-5-20251101
feature: 005-hitl-approval
branch: 005-hitl-approval
user: umair
command: /sp.plan
labels: ["phase-3", "hitl", "approval", "implementation", "plan"]
links:
  spec: phase-3/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-hitl-approval/plan.md
  - phase-3/README.md
tests:
  - none (planning phase)
---

## Prompt

/sp.plan
Create an implementation plan for the approved HITL phase spec.

Requirements:
- Base the plan strictly on the approved spec
- No scope expansion
- Keep the design vault-first and file-driven
- Separate plan sections for:
  - folder/state model
  - approval file generation
  - orchestrator/reasoner integration
  - approval state detection
  - logging
  - testing
- Keep the phase limited to approval workflow only
- Do not add MCP execution logic beyond future-ready boundaries if already defined in the spec

Output a structured implementation plan only.

## Response snapshot

Created comprehensive implementation plan at `specs/005-hitl-approval/plan.md` with 14 sections:

**Section 1: Folder/State Model**
- Directory structure: /Pending_Approval/, /Approved/, /Rejected/ with email/ and linkedin/ subdirs
- State transitions: pending → approved, pending → rejected (location is source of truth)
- Deduplication via SHA256 hash registry in `.watcher-state/approvals.json`

**Section 2: Approval File Generation**
- ApprovalRequest model with all required fields
- YAML frontmatter schema matching spec
- ApprovalWriter module with create_approval_request() function

**Section 3: Orchestrator/Reasoner Integration**
- Email reasoner: integrates at engine.py:_process_email()
- Orchestrator: request_linkedin_post_approval() function
- Detection criteria for external actions requiring approval

**Section 4: Approval State Detection (Watcher)**
- ApprovalWatcher class using watchdog library
- Move detection strategy via delete+create events
- NFR-002 compliance: detection within 5 seconds

**Section 5: Logging**
- /Logs/approvals/approval-YYYYMMDD.log location
- JSON lines format per NFR-003
- All 5 event types: created, approved, rejected, expired, error

**Section 6: CLI Interface**
- hitl-approval list/show/stats commands
- Entry point in pyproject.toml

**Section 7: Testing**
- 10 unit tests, 5 integration tests, 7 acceptance tests

**Sections 8-14**: Package structure, dependencies, constitution compliance, non-goals, future-ready boundaries, risk analysis, implementation order

## Outcome

- Impact: Complete implementation plan ready for /sp.tasks
- Tests: Testing strategy defined with 22 total tests
- Files: 2 created/modified (plan.md, README.md)
- Next prompts: User confirmation, then /sp.tasks
- Reflection: Plan adheres strictly to spec scope, no scope creep

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Constitution Check 8/8 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.tasks after user confirmation
