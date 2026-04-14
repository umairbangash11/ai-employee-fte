---
id: 0002
title: Phase 2 Email Reasoning Plan
stage: plan
date: 2026-03-07
surface: agent
model: claude-opus-4-5-20251101
feature: 004-email-reasoning
branch: 004-email-reasoning
user: umair
command: /sp.plan
labels: ["phase-2", "email-reasoning", "planning", "architecture"]
links:
  spec: phase-2/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-email-reasoning/research.md
  - specs/004-email-reasoning/data-model.md
  - specs/004-email-reasoning/plan.md
  - phase-2/README.md
tests:
  - none (planning phase)
---

## Prompt

/sp.plan

(Phase 2: Email Reasoning Layer - generate implementation plan)

## Response snapshot

Created comprehensive planning artifacts for Phase 2:

**Research Document** (`specs/004-email-reasoning/research.md`):
- LLM Selection: GPT-4o with JSON mode
- Classification prompt engineering (system + user templates)
- Structured output schema with Pydantic validation
- Email file parsing strategy with python-frontmatter
- Task/plan file generation formats
- Deduplication strategy with state tracking
- Error handling per Ralph Wiggum Loop (Principle V)
- Performance considerations (batch processing, token limits)

**Data Model Document** (`specs/004-email-reasoning/data-model.md`):
- 5 core entities: EmailFile, ClassificationResult, TaskFile, PlanFile, ReasonerState
- Entity relationship diagram
- Full Python dataclass/Pydantic definitions
- Validation rules per entity
- JSON schemas for LLM output and state file
- Data flow pipeline diagram
- File system layout

**Implementation Plan** (`specs/004-email-reasoning/plan.md`):
- 8 implementation phases with 75 tasks (T001-T075)
- Module structure: config, scanner, classifier, writer, state, engine, CLI
- Dependency graph (internal and external)
- Constitution check: 7/7 principles PASS
- Risk analysis with mitigations
- Success criteria mapped to acceptance tests

**Constitution Compliance**:
- Principle I (Local-First): PASS
- Principle II (Canonical Folders): PASS
- Principle IV (Safety-First): PASS
- Principle V (Ralph Wiggum Loop): PASS
- Principle VI (Silver Tier Autonomy): PASS
- Principle VII (Phased Development): PASS

## Outcome

- Impact: Complete architecture ready for task breakdown
- Tests: none (planning phase)
- Files: 4 created/modified
- Next prompts: `/sp.tasks` to generate dependency-ordered tasks.md
- Reflection: Plan follows spec exactly, no complexity creep

## Evaluation notes (flywheel)

- Failure modes observed: setup-plan.sh detected wrong feature (003 vs 004), resolved manually
- Graders run and results (PASS/FAIL): Constitution Check 7/7 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.tasks to validate task breakdown
