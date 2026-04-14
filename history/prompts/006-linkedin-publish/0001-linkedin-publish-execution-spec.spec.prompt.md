---
id: 0001
title: LinkedIn Publish Execution Spec
stage: spec
date: 2026-03-12
surface: agent
model: claude-opus-4-5-20251101
feature: 006-linkedin-publish
branch: 006-linkedin-publish
user: umair
command: /sp.specify
labels: [linkedin, publish, execution, phase-4, hitl]
links:
  spec: specs/006-linkedin-publish/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-linkedin-publish/spec.md
  - specs/006-linkedin-publish/checklists/requirements.md
tests:
  - null
---

## Prompt

Create a phase specification for LinkedIn publish execution in my Digital FTE project.

Constraints:
- Respect the existing constitution and vault-first architecture
- Do not modify SpecifyPlus internal folders
- Do not recreate HITL
- Do not expand scope beyond LinkedIn publish execution
- Limit work to approved LinkedIn post execution only

Current confirmed baseline:
- HITL approval workflow already exists
- LinkedIn approval request generation already exists
- Approved and Rejected folder monitoring already exists
- The remaining gap is actual LinkedIn publish execution after approval

Required scope:
- Define how approved LinkedIn post files in the vault are detected
- Define the execution path that publishes the approved LinkedIn post
- Define whether publishing is done via browser automation or another approved local execution path
- Define required input schema for approved LinkedIn post files
- Define output behavior after successful publish:
  - write audit log
  - move item to Done
- Define failure behavior:
  - log failure
  - preserve recoverable state
  - do not silently discard approved items
- Define safety boundaries:
  - execute only approved LinkedIn posts
  - never publish directly from Pending_Approval
  - no broader social platform support in this phase
- Define acceptance criteria and non-goals

Output a strict phase specification only.

## Response snapshot

Created feature branch `006-linkedin-publish` and wrote a comprehensive phase specification for LinkedIn publish execution. The spec defines:

1. **5 User Stories** (4 P1, 1 P2) covering:
   - Publish approved LinkedIn posts via Playwright
   - Handle publication failures with retry logic
   - Detect approved files within 30 seconds
   - CLI manual trigger capability
   - Move to Done after success

2. **13 Functional Requirements** (FR-001 to FR-013) specifying:
   - File detection, validation, publication, logging
   - Safety boundary: only process `/Approved/linkedin/`, never `/Pending_Approval/`
   - Ralph Wiggum Loop retry pattern (3 attempts)
   - Idempotency via hash tracking

3. **Input/Output Schemas** defining frontmatter structure for approved files and published files in `/Done/linkedin/`

4. **7 Success Criteria** with measurable metrics

5. **Constitution Compliance** table confirming adherence to all 8 principles

6. **Clear Scope Boundaries** explicitly listing 10 non-goals (no API, no articles, no images, no scheduled posts, etc.)

## Outcome

- Impact: New phase-4 feature spec created for LinkedIn publish execution
- Tests: None (spec phase)
- Files: 2 created (spec.md, checklists/requirements.md)
- Next prompts: `/sp.plan` to generate implementation architecture
- Reflection: Spec tightly scoped to fill the exact gap between HITL approval and actual execution

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Manual checklist validation PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
