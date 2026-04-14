---
id: 0001
title: Phase 3 HITL Approval Specification
stage: spec
date: 2026-03-08
surface: agent
model: claude-opus-4-5-20251101
feature: 005-hitl-approval
branch: 005-hitl-approval
user: umair
command: /sp.specify
labels: ["phase-3", "hitl", "approval", "safety", "specification"]
links:
  spec: phase-3/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - phase-3/spec.md
  - phase-3/README.md
tests:
  - none (specification phase)
---

## Prompt

/sp.specify
Create a phase specification for a Human-in-the-Loop (HITL) approval system for my Digital FTE project.

Constraints:
- Respect the existing constitution and current vault-first architecture
- Limit work to the HITL phase only
- Do not modify SpecifyPlus internal folders
- Do not implement anything
- Do not include MCP execution in this phase except interface readiness if needed
- Use local markdown files in the vault as the approval mechanism

Required scope:
- Add a file-based approval workflow using:
  - /Pending_Approval/email/
  - /Pending_Approval/linkedin/
  - /Approved/email/
  - /Approved/linkedin/
  - /Rejected/email/
  - /Rejected/linkedin/
- Define which action types require approval in this phase:
  - send email reply
  - send follow-up email
  - publish LinkedIn post
- Require the reasoning layer to create approval request files instead of executing sensitive actions
- Define the approval request markdown schema with frontmatter and body sections
- Define valid state transitions:
  - pending -> approved
  - pending -> rejected
- Define logging requirements for approval creation and state transitions
- Define clear acceptance criteria and non-goals

Output a strict phase specification only.

## Response snapshot

Created comprehensive Phase 3 specification at `phase-3/spec.md`:

**User Stories**: 5 stories covering:
- US1: Reasoning Layer Creates Approval Request (P1)
- US2: Human Approves Action via File Move (P1)
- US3: Human Rejects Action via File Move (P1)
- US4: CLI Lists Pending Approvals (P2)
- US5: Approval Request Includes Rollback Strategy (P2)

**Requirements**: 10 functional + 3 non-functional
- FR-001 to FR-010: Create requests, detect moves, log events, validate schema
- NFR-001 to NFR-003: Performance, detection speed, log format

**Action Types Requiring Approval**:
- send_email_reply
- send_email_followup
- publish_linkedin_post

**Approval Request Schema**:
- YAML frontmatter: action_type, status, target, source, rollback_strategy
- Markdown body: summary, content preview, context, risk assessment

**State Transitions**:
- (none) → pending (created)
- pending → approved (file moved to /Approved/)
- pending → rejected (file moved to /Rejected/)

**Safety**: No direct execution, no auto-approval, no approval reversal

**CLI**: `hitl-approval` with list, show, stats commands

## Outcome

- Impact: Complete spec for HITL approval system ready for planning
- Tests: 7 acceptance tests defined (AT-01 to AT-07)
- Files: 2 created (spec.md, README.md)
- Next prompts: User confirmation "Phase 3 HITL spec ready", then /sp.plan
- Reflection: Spec follows Constitution principles II, IV, VI strictly

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Constitution Check 6/6 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.plan after confirmation
