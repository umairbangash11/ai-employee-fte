---
id: "0001"
title: "Gold Phase 2 Odoo Accounting Spec"
stage: spec
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 012-odoo-accounting
branch: 012-odoo-accounting
user: Umair Ahmad
command: /sp.specify
labels: ["spec", "gold-phase-2", "odoo", "accounting", "mcp", "hitl"]
links:
  spec: specs/012-odoo-accounting/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/012-odoo-accounting/spec.md
  - specs/012-odoo-accounting/checklists/requirements.md
tests:
  - null
---

## Prompt

/sp.specify Gold Phase 2 — Odoo Accounting Integration

(Implementation-focused. Strict rules: constitution v3.0.0, Gold Phase 2 only, HITL/MCP/vault boundaries enforced, no Phase 3–5 scope. Code structure and vault flow wiring priority; not testing-heavy.)

## Response snapshot

Created `specs/012-odoo-accounting/spec.md` with 5 user stories and 14 FRs covering:
- US1 (P1): Odoo connection and read operations (no approval gate)
- US2 (P1): Invoice draft creation → Pending_Approval → Approved → execute → Done
- US3 (P2): Payment preparation draft → same gate pattern
- US4 (P2): Reconciliation draft actions → same gate pattern
- US5 (P3): Accounting vault lifecycle tracking + boundary audit validation

14 FRs enforce: credentials in .env only, MCP-only write boundary, all writes proposal-gated, no self-approval, Ralph Wiggum Loop, 6-field audit log, directory auto-creation, vault root path safety. 6 measurable success criteria. 7 edge cases. Explicit out-of-scope section excluding Phases 3–5 and invoice posting.

All 14 checklist items pass.

## Outcome

- ✅ Impact: Gold Phase 2 spec complete; all 5 user stories, 14 FRs, 6 SCs, 7 edge cases, checklist 14/14 pass
- 🧪 Tests: N/A — spec stage
- 📁 Files: specs/012-odoo-accounting/spec.md, specs/012-odoo-accounting/checklists/requirements.md
- 🔁 Next prompts: `/sp.plan` to generate implementation plan
- 🧠 Reflection: Kept spec strictly implementation-priority-oriented without leaking code structure. Connection protocol (XML-RPC vs JSON-RPC) correctly pushed to assumption, not requirement. FR-014 ensures MCP contract is updated at Phase 2 close.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist 14/14 pass
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.clarify if any ambiguities surface during planning
