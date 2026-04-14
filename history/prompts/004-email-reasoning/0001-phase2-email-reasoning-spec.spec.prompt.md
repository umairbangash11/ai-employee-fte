---
id: 0001
title: Phase 2 Email Reasoning Specification
stage: spec
date: 2026-03-07
surface: agent
model: claude-opus-4-5-20251101
feature: 004-email-reasoning
branch: 004-email-reasoning
user: umair
command: /sp.specify
labels: ["phase-2", "email-reasoning", "specification", "classification"]
links:
  spec: phase-2/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - phase-2/spec.md
  - phase-2/README.md
tests:
  - none (specification phase)
---

## Prompt

/sp.specify
Phase: 2 (Email Reasoning Layer)

SCOPE & CONSTRAINTS
- All work for this phase must be limited to /phase-2/
- Input source is markdown email files already created in vault/Inbox/email
- Output must be markdown task files in vault/Needs_Action and optional plan files in vault/Plans
- Do not send emails, modify Gmail state, delete original email files
- Respect local-first and human-in-the-loop principles

REQUIREMENTS FOR THE SPEC
1) Define reasoning behavior: read emails, classify, create tasks/plans
2) Define what counts as actionable vs promotional/informational/ignore
3) Define output schemas for task and plan files
4) Define safety and non-goals
5) Define acceptance tests

## Response snapshot

Created comprehensive Phase 2 specification at `phase-2/spec.md`:

**User Stories**: 5 stories covering:
- US1: Actionable email creates task (P1)
- US2: Promotional email does not create task (P1)
- US3: Multi-step email creates plan (P2)
- US4: Original email files unchanged (P1)
- US5: Idempotent processing (P2)

**Requirements**: 12 functional + 3 non-functional
- FR-001 to FR-012: Read emails, classify, create tasks/plans, track state
- NFR-001 to NFR-003: Performance, structured output, error handling

**Classification Criteria**:
- Actionable: job opportunities, payments, invitations, requests
- Informational: order confirmations, reports, status updates
- Promotional: marketing, newsletters, discounts
- Ignore: spam, auto-replies, generic notifications

**Output Schemas**:
- Task file with priority, due_date, wikilink to source email
- Plan file with ordered steps for multi-step requests
- Reasoner state JSON for deduplication

**Safety**: No email sending, no Gmail changes, no auto-approval, no deletion

**CLI**: `email-reasoner` with --dry-run, --vault-path, --limit flags

## Outcome

- Impact: Complete spec for email reasoning layer ready for planning
- Tests: 6 acceptance tests defined (AT-01 to AT-06)
- Files: 2 created (spec.md, README.md)
- Next prompts: User confirmation "Phase 2 spec ready", then /sp.plan
- Reflection: Spec follows Constitution principles II, IV, VI, VII

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (specification)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.plan after confirmation
