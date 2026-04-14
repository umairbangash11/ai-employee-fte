---
id: 003
title: Amend Constitution for Hackathon 0 Phases
stage: constitution
date: 2026-03-03
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: 003-gmail-api-oauth
user: umair
command: /sp.constitution
labels: ["constitution", "hackathon", "phases", "gmail-api"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - none
---

## Prompt

/sp.constitution
You are building "Personal AI Employee Hackathon 0: Digital FTE" as a local-first, agent-driven system using Claude Code as executor and an Obsidian vault as memory/UI.

GLOBAL RULES

Follow the provided project document exactly. Do not invent requirements.

Do not disturb or modify any SpecifyPlus internal folders.

Do not implement anything unless explicitly instructed by /sp.implement.

Specs are contracts: do not deviate from approved specs.

Work one phase at a time; do not skip steps.

Do not recreate this constitution once created.

PROJECT STRUCTURE (must be enforced)
Repository root contains:

/phase-1/

/phase-2/

/phase-3/

/phase-4/

/sentinels/ (watchers and sentinel entrypoints)

/orchestrator/ (orchestrator + health monitoring if used)

/skills/ (skill docs and references if applicable)

/vault_templates/ (Obsidian vault templates and schemas)

/docs/ (architecture notes, setup, runbooks)

pyproject.toml

README.md

.env.example

.gitignore

PHASES (do not change count; one at a time)
Phase 1: Gmail API Migration (replace Gmail Playwright automation with Gmail API watcher safely)
Phase 2: HITL + Approval Workflow Hardening (file-based approvals + audit logs)
Phase 3: Process Management & Reliability (PM2/systemd runbooks, auto-restart, backoff)
Phase 4: Demo & Documentation (setup guide + demo script + troubleshooting)

PHASE EXECUTION RULES
For each phase, run in this order with SpecifyPlus commands only:

/sp.specify for that phase (scope limited to /phase-X only; no other folders)

/sp.plan based strictly on approved spec

/sp.tasks small, verifiable, non-expanding

/sp.implement implementing only tasks and only what the spec allows

Phase close acknowledgement only; do not auto-start next phase

GMAIL SENTINEL MIGRATION SAFETY RULES (project-wide)

Do not use Playwright for Gmail.

Use Gmail API with OAuth; do not use password-based login.

Store OAuth tokens and secrets outside the Obsidian vault; never commit them.

Implement conservative polling/backoff by default; avoid aggressive loops.

The CLI entrypoint must not be changed to a new module until that module exists and has a main().

STOP AFTER OUTPUT
After outputting this constitution prompt, stop and wait for user confirmation: "Constitution ready".

## Response snapshot

Updated constitution from v1.1.0 to v2.0.0 with the following changes:

1. **Added Principle VII: Phased Development** — Defines four sequential phases (Gmail API Migration, HITL Hardening, Process Management, Demo & Documentation) with strict execution rules.

2. **Added Principle VIII: Gmail API Migration Safety** — Project-wide rules prohibiting Playwright for Gmail, requiring OAuth 2.0, and mandating conservative polling with backoff.

3. **Amended Principle III (Tiered Scope)** — Added migration note for Silver Tier Gmail monitoring transitioning to Gmail API.

4. **Amended Principle VI (Silver Tier Autonomy)** — Updated Gmail monitoring to use "Gmail API with OAuth" instead of Playwright.

5. **Added Project Structure section** — Required directory layout including /phase-1/ through /phase-4/, /sentinels/, /orchestrator/, /skills/, /vault_templates/, /docs/.

6. **Updated Operational Constraints** — Added OAuth token security requirements.

## Outcome

- Impact: Major version bump (1.1.0 → 2.0.0) restructuring project for Hackathon 0
- Tests: none (constitution document)
- Files: 1 modified (.specify/memory/constitution.md)
- Next prompts: User to confirm "Constitution ready" before proceeding to Phase 1
- Reflection: Constitution now enforces phased development and Gmail API migration safety

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (constitution amendment)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.specify for Phase 1 after user confirmation
