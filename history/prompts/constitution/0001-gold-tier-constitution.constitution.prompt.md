---
id: "0001"
title: Gold Tier Constitution
stage: constitution
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-vault-sentinel
user: Umair Ahmad
command: /sp.constitution
labels: ["gold-tier", "constitution", "governance", "amendment"]
links:
  spec: .specify/memory/constitution.md
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - history/prompts/constitution/0001-gold-tier-constitution.constitution.prompt.md
tests:
  - null
---

## Prompt

Create the one-time project constitution for the AI Employee project, starting Gold Tier.

STRICT RULES:

* Follow the existing project document exactly
* Do not invent requirements
* Do not modify or interfere with SpecifyPlus internal folders
* This constitution is created only once for the whole project
* Project structure must be defined inside the constitution
* Gold work must proceed one phase at a time
* No skipping steps
* No re-creating the constitution later
* Treat specs as contracts
* Use only SpecifyPlus commands for the workflow

Project context:
This project has completed the Silver-tier foundation and is now beginning Gold-tier work.

The constitution must define:

1. Project rules: local-first, HITL for sensitive actions, approval-gated actions for payments/sends/posts, no secrets in vault, AI functionality as agent skills, MCP for external actions, audit logging, graceful degradation, no Gold scope expansion outside approved phase specs.

2. Project folder structure: /phase-1 through /phase-5 (phase-scoped specs), full vault structure including /Inbox, /Needs_Action, /Needs_Action/plans, /Plans, /Pending_Approval, /Approved, /Rejected, /Done, /Logs, /Briefings, /Accounting, /Updates, /In_Progress, /Signals.

3. Gold-tier 5 phases: Phase 1 (cross-domain integration), Phase 2 (Odoo accounting), Phase 3 (social expansion), Phase 4 (weekly audit/CEO briefing), Phase 5 (reliability and autonomous completion).

4. Enforcement: one phase at a time, no skipping specify/plan/tasks/implement, no re-creating constitution, no touching SpecifyPlus internals, no implementation outside approved phase tasks.

## Response snapshot

Amended constitution from v2.0.0 → v3.0.0 (MAJOR — Gold Tier ratification).

Changes made:
- Principle II (Canonical Folder Structure): expanded to full 13-directory vault structure
- Principle III (Tiered Scope): Gold Tier added with 5 capabilities (items 7–11)
- Principle IV (Safety-First): expanded to cover `/Pending_Approval` flow for external actions
- Principle VI: replaced "Silver Tier Autonomy" with "Human-in-the-Loop and Approval Gates" — broader HITL with explicit `/Pending_Approval` → `/Approved` workflow
- Principle VII: replaced "Gmail API Migration Safety" with "Credential and Secrets Isolation" — generalized beyond Gmail
- Principle VIII: new — "Agent Skills and MCP Orchestration"
- Principle IX: new — "Audit Logging" (mandatory fields specified)
- Principle X: new — "Graceful Degradation"
- Principle XI: new — "Gold-Tier Phased Development" (5 phases defined)
- Principle XII: new — "Gold Scope Boundary Enforcement" (explicit prohibitions)
- Project Structure: updated to `specs/gold/phase-1/` through `phase-5/`, full vault structure defined
- Governance: updated to reference 12 principles, added phase-gating clause

## Outcome

- ✅ Impact: Constitution v3.0.0 ratified — Gold Tier is now the active working tier with 12 principles, 5 phases, and explicit scope/approval/audit rules
- 🧪 Tests: n/a — constitution is a governance document
- 📁 Files: .specify/memory/constitution.md (amended to v3.0.0)
- 🔁 Next prompts: /sp.specify for Gold Phase 1 (cross-domain integration foundation)
- 🧠 Reflection: The critical new additions are Principle XII (no phase-skipping, no spec-expansion, specs-as-contracts) and the `/Pending_Approval` → `/Approved` HITL workflow in Principle VI — these two together prevent the most common Gold-tier failure mode: scope creep and unsanctioned external actions.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): 12 principles present, all vault dirs defined, 5 Gold phases specified, enforcement rules explicit — PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.specify for Gold Phase 1
