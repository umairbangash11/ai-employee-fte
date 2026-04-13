<!--
Sync Impact Report
===================
- Version change: 1.1.0 → 2.0.0 (Hackathon 0 restructure)
- Modified principles:
  - III. Tiered Scope → III. Tiered Scope (amended to note Silver Tier Gmail migration)
  - VI. Silver Tier Autonomy → VI. Silver Tier Autonomy (amended for Gmail API path)
- Added principles:
  - VII. Phased Development (new 4-phase hackathon structure)
  - VIII. Gmail API Migration Safety
- Added sections:
  - Project Structure (required directory layout)
  - Phase Execution Rules
- Removed sections: none
- Templates requiring updates:
  - `.specify/templates/plan-template.md` — review for phase alignment
  - `.specify/templates/spec-template.md` — review for phase scoping
- Follow-up TODOs:
  - Create /phase-1/, /phase-2/, /phase-3/, /phase-4/ directories when specs are created
-->

# Digital FTE Constitution

## Core Principles

### I. Local-First Autonomous Operations

This project MUST build a local-first autonomous AI employee for
business operations. All processing, file management, and task
execution MUST occur on the local machine without requiring cloud
services for core functionality. External APIs MAY be used for
AI inference but MUST NOT be required for file operations,
scheduling, or task orchestration.

### II. Canonical Folder Structure

All managed workspaces MUST use the following directory convention:

- `/Inbox` — Incoming items awaiting triage
- `/Needs_Action` — Items requiring human or AI decision
- `/Approved` — Plans and scripts cleared for execution
- `/Done` — Completed artifacts and archived results
- `/Logs` — Execution logs, audit trails, and error records

No feature or automation MAY create, rename, or bypass these
directories. New subdirectories within them are permitted when
justified by a spec.

### III. Tiered Scope

Feature implementation is governed by ratified tiers. Each tier
defines which capabilities are in scope. Higher tiers subsume all
lower-tier capabilities.

**Bronze Tier** (ratified 2026-02-11):

1. **Obsidian vault management** — reading, organizing, tagging,
   and summarizing notes within an Obsidian-compatible vault.
2. **Local file monitoring** — watching designated directories
   for new or changed files and routing them through the
   canonical folder structure.

**Silver Tier** (ratified 2026-02-12, amended 2026-03-03):

3. **Gmail monitoring** — polling Gmail for unread and urgent
   emails, converting them to Markdown files routed to
   `/Inbox/email/` or `/Needs_Action/email/`.

   **Migration note**: Silver Tier Gmail monitoring is transitioning
   from Playwright browser automation to Gmail API with OAuth.
   See Principle VIII for migration safety rules.

4. **WhatsApp monitoring** — browser-automated polling of
   WhatsApp Web for unread conversations, converting them to
   Markdown files routed to `/Inbox/whatsapp/` or
   `/Needs_Action/whatsapp/`.

Features outside the highest ratified tier (e.g., calendar sync,
CRM integration, autonomous purchasing) are explicitly out of
scope until a higher tier is ratified via constitution amendment.

### IV. Safety-First Execution

The system MUST NOT execute any system-modifying script (file
moves, deletions, renames, shell commands, or API calls with
side effects) without first writing a human-readable execution
plan to `/Approved`. The plan MUST include:

- Action description and affected paths
- Rollback strategy
- Expected outcome

Only after the plan is present in `/Approved` MAY the system
proceed with execution. Emergency overrides are not permitted
at Bronze Tier. At Silver Tier, emergency overrides remain
prohibited; all external actions MUST follow the Human-in-the-Loop
workflow defined in Principle VI.

### V. Persistent Retry Logic (Ralph Wiggum Loop)

When a task fails, the system MUST retry up to **3 times** using
the Ralph Wiggum loop pattern:

1. **Attempt 1**: Execute as planned.
2. **Attempt 2**: Re-read context, adjust parameters, retry.
3. **Attempt 3**: Simplify approach to minimal viable action, retry.
4. **After 3 failures**: Log the failure to `/Logs` with full
   context and move the task to `/Needs_Action` for human review.

The system MUST NOT silently drop failed tasks or retry
indefinitely.

### VI. Silver Tier Autonomy

Silver Tier authorizes read-only monitoring of Gmail and WhatsApp
Web. This principle defines what the system MAY and MUST NOT do
at Silver Tier.

**Permitted (read-only monitoring):**

- Poll Gmail for unread, starred, or priority-flagged emails
  at a configurable interval (via Gmail API with OAuth).
- Poll WhatsApp Web for unread conversations and new messages
  (via Playwright browser automation).
- Extract message metadata (sender, subject, timestamp, body
  preview, attachment list, contact/group name).
- Convert captured items to Obsidian-compatible Markdown files
  with standardized YAML frontmatter.
- Route normal items to `/Inbox/<source>/` and urgent items to
  `/Needs_Action/<source>/`.
- Maintain persistent sessions (OAuth tokens for Gmail, cookies
  for WhatsApp) to avoid repeated authentication.

**Prohibited without Human-in-the-Loop:**

The system MUST NOT perform any **external action** — defined as
any operation that sends data to, modifies state in, or is
visible to parties outside the local machine — without first
writing an execution plan to `/Approved` and receiving explicit
human approval. External actions include but are not limited to:

- Sending, replying to, or forwarding emails
- Sending or replying to WhatsApp messages
- Clicking links, downloading attachments, or interacting with
  web content beyond read-only scraping
- Posting to any external service or API with side effects

**Human-in-the-Loop workflow for external actions:**

1. The system writes a proposed action plan to
   `/Approved/<source>/<action-slug>.md` containing: action
   description, target recipient, message content or payload,
   expected outcome, and rollback strategy.
2. The system MUST NOT proceed until a human moves the plan to
   `/Approved` status (or the plan is already in `/Approved`).
3. After execution, the system logs the result to `/Logs` with
   full context.

**Deduplication:** Each captured item MUST be assigned a
deterministic hash (source + sender + timestamp + subject).
Previously captured items (tracked in `.watcher-state/`) MUST
be skipped. The system MUST NOT produce duplicate Markdown files.

### VII. Phased Development

Development is structured into four sequential phases. Each phase
MUST be completed before the next phase begins. Phases MUST NOT
be skipped, reordered, or combined.

**Phase 1: Gmail API Migration**
Replace Gmail Playwright automation with Gmail API watcher safely.
Scope is limited to `/phase-1/` specs only.

**Phase 2: HITL + Approval Workflow Hardening**
File-based approvals + audit logs. Scope is limited to `/phase-2/`
specs only.

**Phase 3: Process Management & Reliability**
PM2/systemd runbooks, auto-restart, backoff. Scope is limited to
`/phase-3/` specs only.

**Phase 4: Demo & Documentation**
Setup guide + demo script + troubleshooting. Scope is limited to
`/phase-4/` specs only.

**Phase Execution Rules:**

For each phase, execute in this order using SpecifyPlus commands:

1. `/sp.specify` — Create spec scoped to `/phase-X/` only
2. `/sp.plan` — Generate plan based strictly on approved spec
3. `/sp.tasks` — Create small, verifiable, non-expanding tasks
4. `/sp.implement` — Execute only tasks from the approved spec

A phase is closed only after explicit user acknowledgement.
Do NOT auto-start the next phase.

### VIII. Gmail API Migration Safety

This principle governs the Phase 1 migration from Playwright to
Gmail API. These rules are project-wide and MUST be followed
throughout the migration.

**Required:**

- Use Gmail API with OAuth 2.0 for authentication
- Store OAuth tokens and secrets outside the Obsidian vault
- Implement conservative polling with exponential backoff
- OAuth credentials MUST be stored in `.env` or secure storage
- Respect Gmail API rate limits (250 quota units/user/second)

**Prohibited:**

- Do NOT use Playwright for Gmail (WhatsApp still uses Playwright)
- Do NOT use password-based or app-password authentication
- Do NOT commit OAuth tokens, secrets, or credentials to git
- Do NOT implement aggressive polling loops
- Do NOT change CLI entrypoint to a new module until that module
  exists and has a working `main()` function

**Migration Safety Checklist:**

Before switching the CLI entrypoint from the old Gmail watcher to
the new Gmail API watcher:

1. New module MUST exist at the target path
2. New module MUST have a `main()` function
3. New module MUST be tested manually with real Gmail account
4. Old module MUST remain available as fallback during transition

## Project Structure

The repository root MUST contain the following directories:

```
/phase-1/          # Gmail API Migration specs and artifacts
/phase-2/          # HITL + Approval Workflow specs
/phase-3/          # Process Management specs
/phase-4/          # Demo & Documentation specs
/sentinels/        # Watchers and sentinel entrypoints
/orchestrator/     # Orchestrator + health monitoring
/skills/           # Skill docs and references
/vault_templates/  # Obsidian vault templates and schemas
/docs/             # Architecture notes, setup, runbooks
pyproject.toml
README.md
.env.example
.gitignore
```

**Protected directories (MUST NOT be modified):**

- `.specify/` — SpecifyPlus internal folders
- `.claude/` — Claude Code command definitions

## Operational Constraints

- **No secrets in code**: All API keys, tokens, and credentials
  MUST be stored in `.env` files excluded from version control.
- **Smallest viable diff**: Changes MUST be minimal and focused.
  Do not refactor unrelated code alongside feature work.
- **Audit trail**: Every automated action MUST produce a log
  entry in `/Logs` with timestamp, action, and outcome.
- **Obsidian compatibility**: Files written to the vault MUST
  be valid Markdown compatible with Obsidian (YAML frontmatter,
  `[[wikilinks]]`, standard Markdown syntax).
- **OAuth token security**: Gmail OAuth tokens stored in
  `.watcher-state/` or `.secrets/` MUST be excluded from version
  control via `.gitignore`.
- **Playwright session security**: WhatsApp browser session data
  stored in `.watcher-state/` MUST be excluded from version
  control. Playwright MUST run headless by default; headed mode
  is permitted only for initial authentication setup.

## Development Workflow

1. **Specify**: Define the feature via `/sp.specify`.
2. **Clarify**: Resolve ambiguities via `/sp.clarify`.
3. **Plan**: Architect the solution via `/sp.plan`. Plans MUST
   pass a Constitution Check before implementation.
4. **Tasks**: Break the plan into ordered tasks via `/sp.tasks`.
5. **Implement**: Execute tasks via `/sp.implement`, committing
   after each logical unit of work.
6. **Review**: All PRs MUST verify compliance with this
   constitution before merge.

## Governance

- This constitution is the supreme governance document for the
  Digital FTE project. It supersedes all other practices and
  conventions when conflicts arise.
- **Amendments** require: (1) a written proposal, (2) rationale
  documenting why the change is needed, (3) a migration plan for
  any affected artifacts, and (4) version increment per SemVer.
- **Versioning policy**: MAJOR for principle removals or
  redefinitions; MINOR for new principles or material expansions;
  PATCH for clarifications and typo fixes.
- **Compliance review**: Every `/sp.plan` output MUST include a
  Constitution Check section validating adherence to all eight
  principles. Violations MUST be justified in a Complexity
  Tracking table.

**Version**: 2.0.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-03-03
