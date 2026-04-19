# Project State

## Verified Working

- Gmail OAuth + watcher — captures emails into `vault/Inbox/email/`
- WhatsApp watcher — Playwright-based, polling loop implemented
- LinkedIn publisher — Playwright-based, HITL-gated via `Pending_Approval/` → `Approved/`
- Vault MCP server — registered in `.mcp.json`, 20 unit tests pass
- Runtime Plan.md generation — `orchestrator/plan_writer.py`, real artifact in `vault/Needs_Action/plans/`, 15 tests pass
- HITL approval workflow — `hitl_approval/writer.py` writes to `Pending_Approval/`, publisher reads from `Approved/`
- Vault folder structure — `Inbox/`, `Needs_Action/`, `Needs_Action/plans/`, `Approved/`, `Done/`, `Logs/`
- Routing logic — `router/` moves emails from `Inbox/email/` to `Needs_Action/email/` based on rules
- Agent Skills — 6 skill files in `.claude/skills/`
- Unit tests — 121 passing, 3 pre-existing failures (facebook_publisher only)

## Local Setup Needed After Clone

- Copy `.env_example` → `.env` and fill all values
- Place `credentials.json` from Google Cloud Console at `secrets/gmail/credentials.json`
- Run `gmail-watcher --auth` once for OAuth token
- Run `sentinel init --vault-path <path>` to create vault directories
- Create `vault/Dashboard.md` and `vault/Company_Handbook.md` (Bronze tier requirement)

## Main Commands

```bash
gmail-watcher                            # Start Gmail polling
PYTHONPATH=src python3 -m orchestrator.brain  # Start email triage orchestrator
whatsapp-watcher                         # Start WhatsApp polling
linkedin-publish watch                   # Watch Approved/ for LinkedIn posts
PYTHONPATH=src pytest tests/unit/ -q     # Run full test suite
```

## Current Known Issues

- `vault/Dashboard.md` and `vault/Company_Handbook.md` missing — Bronze requirement unmet
- No persistent process supervision — watchers have internal polling loops but no PM2/systemd/auto-restart
- Brain orchestrator uses `gpt-5o` model string in `.env` default — verify correct model name in `.env`
- 3 pre-existing test failures in `facebook_publisher` (datetime deprecation) — unrelated to Silver tier
- `GMAIL_EMAIL` / `GMAIL_PASSWORD` in `.env_example` are legacy Playwright fields — Gmail API OAuth replaced them; not needed for `gmail-watcher`
- Gold Phase 1 plan written but not yet implemented (`specs/011-gold-phase-1-foundation/`)

## Next Recommended Step

- Create `vault/Dashboard.md` and `vault/Company_Handbook.md` to satisfy the last two Bronze requirements
- Add a minimal `ecosystem.config.js` (PM2) or systemd service file to satisfy the scheduling/process supervision Silver requirement
- Then re-run the Silver tier audit to confirm 100% completion before starting Gold Phase 1 implementation
