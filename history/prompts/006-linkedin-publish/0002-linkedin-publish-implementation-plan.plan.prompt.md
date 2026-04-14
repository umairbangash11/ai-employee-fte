---
id: 0002
title: LinkedIn Publish Implementation Plan
stage: plan
date: 2026-03-12
surface: agent
model: claude-opus-4-5-20251101
feature: 006-linkedin-publish
branch: 006-linkedin-publish
user: umair
command: /sp.plan
labels: [linkedin, publish, execution, phase-4, implementation, plan]
links:
  spec: specs/006-linkedin-publish/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-linkedin-publish/plan.md
tests:
  - null
---

## Prompt

Create an implementation plan for the approved LinkedIn publish execution phase.

Requirements:
- Base the plan strictly on the approved spec
- No scope expansion
- Keep the architecture vault-first and file-driven
- Assume HITL already exists and is not being rebuilt
- Include plan sections for:
  - approved file detection
  - LinkedIn publish executor
  - audit logging
  - done/failure state handling
  - test scenarios
- Keep the phase limited to LinkedIn publish execution only

Output a structured implementation plan only.

## Response snapshot

Created comprehensive implementation plan with 10 sections:

1. **Approved File Detection** (Section 1)
   - Watcher mode (watchdog) and poll mode fallback
   - 30-second detection latency target
   - Safety boundary: only `/Approved/linkedin/`, never `/Pending_Approval/`

2. **LinkedIn Publish Executor** (Section 2)
   - Playwright browser automation with persistent session
   - Session storage in `.watcher-state/linkedin/session/`
   - Selector abstraction for maintenance
   - Ralph Wiggum Loop retry (3 attempts)

3. **Audit Logging** (Section 3)
   - JSON lines format in `/Logs/linkedin/`
   - Events: detected, publishing, published, failed, moved_to_done, moved_to_needs_action

4. **State Management** (Section 4)
   - Success: update frontmatter, move to `/Done/linkedin/`, log
   - Failure: preserve in `/Approved/linkedin/` with error metadata
   - Unrecoverable: move to `/Needs_Action/linkedin/`
   - Idempotency via content hash tracking

5. **CLI Interface** (Section 5)
   - Commands: run, watch, list, status, auth
   - Entry point: `linkedin-publish`

6. **Integration Points** (Section 6)
   - Consumes HITL output, does not modify HITL
   - Reuses patterns from `src/hitl_approval/`

7. **Test Scenarios** (Section 7)
   - 15 unit tests, 10 integration tests, 4 E2E tests

8. **Risk Analysis** (Section 8)
   - LinkedIn DOM changes (high likelihood, medium impact)
   - Session expiry, rate limiting, file watcher miss

9. **Dependencies** (Section 9)
   - New: playwright >=1.40, click >=8.0, pyyaml >=6.0
   - Existing: watchdog, python-dotenv

10. **Implementation Order** (Section 10)
    - 9 phases: Foundation → Parser → Logger → State → Detector → Executor → State Handlers → CLI → Testing

**Constitution Check**: All 8 principles PASS.

## Outcome

- Impact: Implementation plan created for LinkedIn publish execution
- Tests: None (plan phase)
- Files: 1 created (plan.md)
- Next prompts: `/sp.tasks` to generate dependency-ordered tasks
- Reflection: Plan follows existing HITL architecture patterns for consistency

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Constitution check PASS (8/8 principles)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
