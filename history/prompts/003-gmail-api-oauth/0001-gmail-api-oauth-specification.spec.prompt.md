---
id: "0001"
title: "Gmail API OAuth Sentinel Specification"
stage: spec
date: 2026-02-28
surface: agent
model: claude-opus-4-5-20251101
feature: 003-gmail-api-oauth
branch: 003-gmail-api-oauth
user: umair
command: /sp.specify
labels: ["gmail-api", "oauth", "sentinel", "specification", "silver-tier"]
links:
  spec: specs/003-gmail-api-oauth/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gmail-api-oauth/spec.md
  - specs/003-gmail-api-oauth/checklists/requirements.md
tests:
  - null
---

## Prompt

/sp.specify Replace Playwright-based Gmail sentinel with Gmail API (OAuth) sentinel. Requirements:
- MUST NOT open a browser during normal runs
- MUST authenticate via OAuth token stored locally (credentials.json + token.json/pickle in ./secrets/gmail/)
- MUST poll for unread emails (optionally filter important) and write normalized markdown files into <VAULT_PATH>/Inbox/email/
- MUST deduplicate across restarts using persistent state in .watcher-state/
- MUST support poll interval via env (GMAIL_POLL_INTERVAL)
- MUST be safe-by-default: read-only scopes initially (gmail.readonly)
- MUST log errors to <VAULT_PATH>/Logs/ with actionable messages
- MUST remove need for GMAIL_PASSWORD and Playwright for Gmail
Out of scope:
- Sending emails
- UI automation for Gmail

## Response snapshot

Created feature specification for Gmail API OAuth Sentinel (003-gmail-api-oauth) with:

**5 User Stories**:
- US1 (P1): Headless Email Capture — silent polling via Gmail API without browser windows
- US2 (P1): One-Time OAuth Setup — `--auth` flag for initial browser-based consent
- US3 (P2): Urgent Email Routing — starred/important emails routed to /Needs_Action/email/
- US4 (P2): Deduplication Across Restarts — persistent hash registry in .watcher-state/
- US5 (P3): Error Logging with Actionable Messages — clear remediation steps in logs

**15 Functional Requirements** covering:
- OAuth 2.0 authentication with credentials.json + token.json
- Headless-by-default operation (no browser during normal runs)
- Read-only Gmail API scope (gmail.readonly)
- Configurable poll interval via GMAIL_POLL_INTERVAL env
- Ralph Wiggum retry pattern for transient failures
- --dry-run support

**Key Improvements over Playwright approach**:
- No plain-text password storage (GMAIL_PASSWORD eliminated)
- No browser automation dependency
- Revocable access via Google account settings
- More reliable and efficient API-based polling

## Outcome

- Impact: Created complete feature specification for Gmail API OAuth sentinel (replaces Playwright-based approach)
- Tests: None (spec phase)
- Files: 2 files created (spec.md, checklists/requirements.md)
- Next prompts: /sp.clarify (if needed) or /sp.plan to generate implementation plan
- Reflection: Clear user requirements enabled direct spec creation without clarification questions; all requirements well-specified

## Evaluation notes (flywheel)

- Failure modes observed: Git SSH auth issue blocked remote fetch; proceeded with local workflow
- Graders run and results (PASS/FAIL): Checklist validation PASS (all items checked)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
