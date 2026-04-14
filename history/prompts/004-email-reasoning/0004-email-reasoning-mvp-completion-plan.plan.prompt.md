---
id: 0004
title: Email Reasoning MVP Completion Plan
stage: plan
date: 2026-04-12
surface: agent
model: claude-sonnet-4-5
feature: 004-email-reasoning
branch: 008-facebook-post-execution
user: umair
command: /sp.plan
labels: ["mvp", "planning", "email-reasoning", "completion"]
links:
  spec: /home/umair/ai-employee-fte/phase-2/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-email-reasoning/mvp-completion-plan.md
tests:
  - none
---

## Prompt

/sp.plan

Feature ID: 004-email-reasoning
Feature Name: Email Reasoning Layer MVP Completion

Plan the implementation for completing the remaining Email Reasoning MVP only.

Locked scope:
- Continue from the existing foundation already present in:
  - src/email_reasoner/models.py
  - src/email_reasoner/config.py
  - src/email_reasoner/scanner.py
  - src/email_reasoner/state.py
- Complete only the missing reasoning pipeline pieces:
  - src/email_reasoner/classifier.py
  - src/email_reasoner/writer.py
  - src/email_reasoner/engine.py

Target MVP pipeline:
scanner -> classifier -> writer -> engine -> state

Planning constraints:
- Do not invent requirements
- Do not expand beyond Email Reasoning MVP
- Do not include WhatsApp, Facebook, LinkedIn, banking, Odoo, or cloud architecture
- Do not modify SpecifyPlus internal folders
- Treat the clarified scope as fixed
- Keep implementation read-only with respect to external systems
- No email sending, deleting, archiving, or Gmail mutation
- Only generate actionable markdown outputs for non-ignore classifications
- Use the existing state mechanism to prevent duplicate processing

MVP behavior to plan for:
1. Consume scanned email markdown inputs from the existing scanner contract
2. Classify each email into exactly one of: ignore, respond, follow_up, urgent
3. Return structured classification output including: label, confidence, reason, suggested_action, priority
4. Write non-ignore items as normalized markdown task files in the vault
5. Update processing state to ensure idempotency and prevent duplicate task generation
6. Add retry handling for transient model/API failures
7. Keep implementation minimal and production-minded

## Response snapshot

Created comprehensive MVP completion plan at specs/004-email-reasoning/mvp-completion-plan.md

**Plan Summary:**

**Missing Modules (3):**
1. classifier.py - LLM email classification using OpenAI GPT-4o
2. writer.py - Task markdown file generation
3. engine.py - Pipeline orchestration

**Pipeline Flow:**
Input (Inbox/email/*.md) → scanner (existing) → filter by state (existing) → classifier (new) → writer (new) → engine orchestration (new) → state update (existing) → Output (Needs_Action/tasks/*.md)

**Classification Labels:** ignore, respond, follow_up, urgent

**Key Design Decisions:**
- OpenAI GPT-4o with JSON mode for structured output
- 3-retry backoff for API failures (Ralph Wiggum Loop)
- Fallback to "ignore" on classification errors
- Incremental state saves (after each email)
- Body truncation to 4000 chars
- Single task folder (no subdirectories for MVP)
- Fixed templates (no customization)

**Implementation Sequence:**
1. Phase 1: Classifier (highest risk)
2. Phase 2: Writer (medium risk)
3. Phase 3: Engine (low risk, highest value)

**Excluded from MVP:** Multi-step plans, CLI polish, advanced logging, batch optimization, priority folders

## Outcome

- ✅ Impact: MVP completion plan ready for implementation
- 🧪 Tests: 5 verification tests defined (T1-T5)
- 📁 Files: 1 plan document created
- 🔁 Next prompts: /sp.tasks or begin implementation of classifier.py
- 🧠 Reflection: Plan maintains narrow MVP scope, builds on existing foundation, clear sequencing

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Not applicable (planning phase)
- Prompt variant (if applicable): Standard planning prompt
- Next experiment (smallest change to try): Implement classifier.py with mock API for testing
