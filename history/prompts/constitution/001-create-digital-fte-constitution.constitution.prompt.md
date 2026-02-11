---
id: 001
title: Create Digital FTE Constitution
stage: constitution
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: umair
command: /sp.constitution
labels: ["constitution", "governance", "project-setup"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
---

## Prompt

create --name "Digital_FTE_Constitution" --rules "
1. PROJECT GOAL: Build a local-first autonomous AI employee for business ops.
2. FOLDER STRUCTURE: Always use /Inbox, /Needs_Action, /Approved, /Done, and /Logs.
3. BRONZE TIER: Focus only on Obsidian vault management and local file monitoring.
4. SAFETY: Never execute a system-modifying script without writing a plan to /Approved first.
5. PERSISTENCE: Use the Ralph Wiggum loop logic to retry failed tasks up to 3 times."

## Response snapshot

Created the Digital FTE Constitution v1.0.0 with 5 core principles: (I) Local-First Autonomous Operations, (II) Canonical Folder Structure, (III) Bronze Tier Scope, (IV) Safety-First Execution, (V) Persistent Retry Logic (Ralph Wiggum Loop). Added Operational Constraints, Development Workflow, and Governance sections. All template placeholders resolved. Consistency check passed against plan, spec, and tasks templates — no updates required.

## Outcome

- Impact: Initial constitution ratified — all future specs/plans must pass Constitution Check
- Tests: N/A (governance document)
- Files: `.specify/memory/constitution.md` created
- Next prompts: `/sp.specify` to create the first feature spec under Bronze Tier scope
- Reflection: User provided clear, well-structured rules that mapped directly to principles

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Manual placeholder scan PASS, SemVer PASS, date format PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
