---
id: 002
title: Amend Constitution to Silver Tier
stage: constitution
date: 2026-02-12
surface: agent
model: claude-opus-4-6
feature: none
branch: 001-vault-sentinel
user: umair
command: /sp.constitution
labels: ["constitution", "silver-tier", "playwright", "gmail", "whatsapp", "human-in-the-loop"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - CLAUDE.md
tests:
  - none
---

## Prompt

Amend the project constitution to Silver Tier. Include a new 'Section 7: Silver Tier Autonomy' that authorizes the use of Playwright for Gmail/WhatsApp monitoring. Explicitly state that any external actions (sending/posting) MUST follow a 'Human-in-the-Loop' workflow via the /Approved folder.

## Response snapshot

Amended constitution from v1.0.0 to v1.1.0 (MINOR bump — new principle added, existing principle expanded). Key changes:

1. **Principle III renamed**: "Bronze Tier Scope" → "Tiered Scope" — now defines both Bronze (vault management, file monitoring) and Silver (Gmail monitoring, WhatsApp monitoring) as ratified tiers.
2. **Principle VI added**: "Silver Tier Autonomy" — authorizes Playwright for read-only browser-automated monitoring of Gmail and WhatsApp Web. Explicitly prohibits external actions (sending, replying, forwarding) without Human-in-the-Loop workflow via `/Approved`.
3. **Principle IV updated**: Cross-references Principle VI for Silver Tier external action rules.
4. **Operational Constraints**: Added Playwright session security rule (`.watcher-state/` in `.gitignore`, headless by default).
5. **Governance**: Updated compliance review to reference six principles (was five).

Also updated CLAUDE.md: unblocked WatcherInfrastructure skill, added Playwright to Active Technologies, updated Recent Changes.

Templates checked — no updates needed (all use generic Constitution Check references).

## Outcome

- ✅ Impact: Constitution amended to v1.1.0; Silver Tier ratified; Gmail/WhatsApp monitoring now in scope
- 🧪 Tests: none (governance document change)
- 📁 Files: .specify/memory/constitution.md (rewritten), CLAUDE.md (4 edits)
- 🔁 Next prompts: `/sp.specify` for Gmail or WhatsApp watcher feature; consider `/sp.adr` for Playwright browser automation decision
- 🧠 Reflection: Clean amendment — expanded Principle III rather than replacing it preserves Bronze Tier traceability

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
