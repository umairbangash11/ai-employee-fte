---
id: 0005
title: Email Reasoning MVP Tasks Generation
stage: tasks
date: 2026-04-12
surface: agent
model: claude-sonnet-4-5
feature: 004-email-reasoning
branch: 008-facebook-post-execution
user: umair
command: /sp.tasks
labels: ["mvp", "tasks", "email-reasoning", "completion"]
links:
  spec: /home/umair/ai-employee-fte/phase-2/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-email-reasoning/mvp-completion-tasks.md
tests:
  - 5 verification tests defined
---

## Prompt

/sp.tasks

Feature ID: 004-email-reasoning
Feature Name: Email Reasoning Layer MVP Completion

Generate implementation tasks for completing only the remaining Email Reasoning MVP work.

Context:
- This is not a greenfield feature
- Existing foundation already exists in: src/email_reasoner/models.py, config.py, scanner.py, state.py
- Remaining core files to complete: classifier.py, writer.py, engine.py

Locked scope:
- Complete only the Email Reasoning MVP
- Keep implementation read-only with respect to external systems
- No email sending, deleting, archiving, or modifying Gmail state
- Only create actionable vault task artifacts for non-ignore classifications

Target MVP pipeline: scanner -> classifier -> writer -> engine -> state

## Response snapshot

Created focused MVP completion task list at specs/004-email-reasoning/mvp-completion-tasks.md

**22 Tasks Total:**
- Phase 3: Classifier (T032-T042) - 11 tasks, ~250 LOC
- Phase 4: Writer (T043-T048) - 6 tasks, ~200 LOC
- Phase 5: Engine (T049-T053) - 5 tasks, ~150 LOC

**Key Features:**
- Classification labels: ignore, respond, follow_up, urgent
- OpenAI GPT-4o with JSON mode
- 3-retry backoff for API failures
- Task output: /Needs_Action/tasks/
- Incremental state saves
- 5 verification tests defined

**Excluded:** Multi-step plans, CLI polish, /Logs/ logging, batch optimization, custom templates

## Outcome

- ✅ Impact: MVP completion tasks ready (22 tasks, ~600 LOC)
- 🧪 Tests: 5 verification tests defined
- 📁 Files: mvp-completion-tasks.md created
- 🔁 Next prompts: Begin T032 (classifier.py) or /sp.implement
- 🧠 Reflection: Tight task granularity, clear acceptance criteria

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A (task generation)
- Prompt variant (if applicable): Standard
- Next experiment (smallest change to try): Implement classifier first (highest risk)
