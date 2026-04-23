---
id: "0002"
title: Implementation plan error recovery resilience
stage: plan
date: 2026-04-20
surface: agent
model: claude-opus-4-5-20251101
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.plan
labels: ["planning", "resilience", "error-handling", "circuit-breaker", "retry-logic"]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/015-error-recovery-resilience/plan.md (created)
  - specs/015-error-recovery-resilience/research.md (created)
  - specs/015-error-recovery-resilience/data-model.md (created)
  - specs/015-error-recovery-resilience/quickstart.md (created)
  - specs/015-error-recovery-resilience/contracts/cli-contract.md (created)
  - specs/015-error-recovery-resilience/contracts/resilience-api.md (created)
tests:
  - N/A (planning phase)
---

## Prompt

/sp.plan

Execute implementation planning workflow for 015-error-recovery-resilience feature. Generate research.md, data-model.md, contracts/, and quickstart.md per plan template.

## Response snapshot

Completed full planning workflow for Error Recovery & Process Resilience (Gold Phase 5):

**Phase 0 Research:**
- Analyzed existing retry patterns in orchestrator/brain.py, linkedin_publisher, facebook_publisher
- Found Ralph Wiggum Loop implemented inconsistently (only 3/7 subsystems)
- Identified gaps: no health files, no circuit breaker, no unified exceptions
- Recommended shared `src/resilience/` module

**Phase 1 Design:**
- Created data-model.md with 7 core entities: ResilienceError, FailureCategory, RetryPolicy, FailureLog, HealthStatus, CircuitBreaker, FailedItemWrapper
- Created CLI contract for sentinel-status and sentinel-recover commands
- Created API contract for resilience module (exceptions, retry, health, circuit_breaker)
- Created quickstart.md with code examples and PM2/systemd integration

**Constitution Check:** All 8 principles PASS.

## Outcome

- ✅ Impact: Complete planning artifacts for Gold Phase 5 ready for /sp.tasks
- 🧪 Tests: N/A (planning phase)
- 📁 Files: 6 artifacts created in specs/015-error-recovery-resilience/
- 🔁 Next prompts: /sp.tasks to generate implementation tasks
- 🧠 Reflection: Research revealed mature retry patterns in publishers that can be extracted; watchers have critical gaps

## Evaluation notes (flywheel)

- Failure modes observed: None; setup-plan.sh defaulted to 001-vault-sentinel branch, required manual feature selection
- Graders run and results (PASS/FAIL): PASS (constitution check passed, all artifacts complete)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Automate feature detection from untracked files in git status
