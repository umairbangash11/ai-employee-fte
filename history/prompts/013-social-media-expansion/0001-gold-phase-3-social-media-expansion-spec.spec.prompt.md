---
id: "0001"
title: "Gold Phase 3 Social Media Expansion Spec"
stage: spec
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 013-social-media-expansion
branch: 013-social-media-expansion
user: Umair Ahmad
command: /sp.specify
labels: ["spec", "gold-phase-3", "facebook", "instagram", "x", "social-media", "hitl", "vault", "playwright"]
links:
  spec: specs/013-social-media-expansion/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/013-social-media-expansion/spec.md
  - specs/013-social-media-expansion/checklists/requirements.md
tests:
  - null
---

## Prompt

/sp.specify Gold Phase 3 — Social Media Expansion

(Implementation-focused. Strict rules: constitution v3.0.0, Gold Phase 3 only, HITL/vault boundaries enforced, no Phase 4–5 scope. Code structure and vault flow wiring priority; no pytest generation in this phase.)

SCOPE: Facebook publishing flow (drafter), Instagram publishing flow (full), X publishing flow (full), shared vault integration, reuse of existing LinkedIn/Facebook publisher architecture, logging and traceability.

## Response snapshot

Created `specs/013-social-media-expansion/spec.md` on branch `013-social-media-expansion` with 5 user stories and 14 FRs covering:
- US1 (P1): Facebook draft-first publishing — close the drafter gap, reuse existing executor
- US2 (P1): Instagram draft-first publishing — full new package (Playwright, vault-gated)
- US3 (P1): X draft-first publishing — full new package (Playwright, vault-gated, char limit advisory)
- US4 (P2): Shared social post vault lifecycle — consistent frontmatter, boundary audit validation
- US5 (P3): Publisher architecture consistency — shared `social_drafters` module, no duplicated frontmatter logic

14 FRs enforce: draft-first proposal gate, no self-approval, Ralph Wiggum Loop, 6-field audit log, directory auto-creation, vault root path safety, shared drafter module, Instagram image validation, X char count tracking.

Key insight: `facebook_publisher` executor already exists (Silver Tier). Phase 3 gap = Facebook drafter (writes to `Pending_Approval/facebook/`). Instagram and X are net-new packages.

6 success criteria. 7 edge cases. Explicit out-of-scope section (no scheduling, no feed monitoring, no multi-image carousels, no Phase 4–5).

Checklist 14/14 pass.

## Outcome

- ✅ Impact: Gold Phase 3 spec complete; all 5 user stories, 14 FRs, 6 SCs, 7 edge cases; checklist 14/14 pass
- 🧪 Tests: N/A — spec stage; testing deferred to project end per user instruction
- 📁 Files: specs/013-social-media-expansion/spec.md, specs/013-social-media-expansion/checklists/requirements.md
- 🔁 Next prompts: `/sp.plan` to generate implementation plan with social_drafters shared module design
- 🧠 Reflection: Correctly identified that Facebook executor already exists and the gap is the drafter layer only. Shared `social_drafters` module (FR-012) is the key architectural decision that prevents tripling the frontmatter logic. X character limit treated as advisory-only at draft stage — correct for a human-review workflow. No pytest scope included per explicit user instruction.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist 14/14 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.plan to validate shared social_drafters design and three-package split
