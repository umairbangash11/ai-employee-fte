---
id: 0004
title: Phase 1 Precise Specification Document
stage: spec
date: 2026-03-03
surface: agent
model: claude-opus-4-5-20251101
feature: 003-gmail-api-oauth
branch: 003-gmail-api-oauth
user: umair
command: /sp.specify
labels: ["phase-1", "gmail-api", "specification", "contract"]
links:
  spec: phase-1/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - phase-1/spec.md
tests:
  - none
---

## Prompt

/sp.specify
Phase: 1 (Gmail API Migration)

SCOPE & CONSTRAINTS
- All work limited to: /phase-1/
- Do NOT modify SpecifyPlus internal folders
- Do NOT implement anything
- Produce spec as contract: precise, testable, minimal
- Migrate Gmail sentinel from Playwright to Gmail API (OAuth) safely
- Preserve existing watcher pattern and vault file output format
- Security: tokens/secrets never in vault, never committed
- Safety: conservative polling/backoff, no aggressive loops
- Entry-point safety: don't change CLI until new module exists with main()

REQUIREMENTS FOR SPEC:
1. Definition of Done for Phase 1
2. Explicit file/module plan (names only)
3. pyproject.toml changes (spec-only)
4. Non-goals list
5. Acceptance tests (manual steps)

OUTPUT FORMAT: Phase 1 spec document for /phase-1/spec.md

## Response snapshot

Created comprehensive Phase 1 specification at `/phase-1/spec.md` containing:

**1. Definition of Done** - 6 categories with checkboxes:
- Gmail API Watcher Module exists at `src/gmail_watcher/`
- Action files generated with canonical frontmatter
- Deduplication via `.watcher-state/gmail-api.json`
- Conservative polling (120s default, exponential backoff)
- Dry-run mode (no writes, no state updates)
- Documentation at `docs/gmail-api-setup.md`

**2. File/Module Plan**:
- `src/gmail_watcher/{__init__,auth,watcher,writer,state,__main__}.py`
- `secrets/gmail/{credentials,token}.json` (outside vault, gitignored)
- `.watcher-state/gmail-api.json` (outside vault, gitignored)

**3. CLI Surface**:
- `--vault-path`, `--credentials`, `--token`, `--state`
- `--interval` (min 60s), `--once`, `--dry-run`, `--auth`

**4. pyproject.toml Changes**:
- Add: google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib
- Add entry point: `gmail-watcher = "gmail_watcher.__main__:main"` (after module exists)
- Remove: playwright (for Gmail only)

**5. Non-Goals**: WhatsApp, MCP server, Pub/Sub, sending emails, modifying labels

**6. Acceptance Tests** (6 manual tests):
- T1: OAuth authentication flow
- T2: Single email capture
- T3: Deduplication verification
- T4: Dry-run mode
- T5: Urgent email routing
- T6: Error recovery/backoff

## Outcome

- Impact: Phase 1 specification document created as contract
- Tests: none (specification only)
- Files: 1 created (phase-1/spec.md)
- Next prompts: User confirmation "Phase 1 spec ready", then /sp.plan
- Reflection: Spec is precise, testable, minimal; follows Constitution v2.0.0

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (specification)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed with /sp.plan after confirmation
