# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Spec-Driven Development (SDD) project** using the SpecifyPlus framework. It is currently in template state — no application source code exists yet. Features are developed through a structured workflow: specify → clarify → plan → tasks → implement.

## Environment

- **Python 3.12** with a local `venv/` virtual environment
- **SpecifyPlus CLI** (`sp` command) installed in venv
- Activate venv before running commands: `source venv/bin/activate`

## Key Commands

```bash
sp --help                # SpecifyPlus CLI help
sp init                  # Initialize project
sp check                 # Validate prerequisites
sp version               # Show version
```

### SDD Workflow (Claude Code slash commands)

| Command | Purpose |
|---------|---------|
| `/sp.specify` | Create feature spec from description |
| `/sp.plan` | Generate implementation plan |
| `/sp.tasks` | Break plan into dependency-ordered tasks |
| `/sp.implement` | Execute tasks from tasks.md |
| `/sp.clarify` | Resolve ambiguities in spec |
| `/sp.analyze` | Cross-artifact consistency check |
| `/sp.checklist` | Generate quality checklist |
| `/sp.adr` | Create Architecture Decision Record |
| `/sp.phr` | Create Prompt History Record |
| `/sp.constitution` | Manage project principles |
| `/sp.reverse-engineer` | Reverse engineer existing code |
| `/sp.git.commit_pr` | Git commit and PR workflow |
| `/sp.taskstoissues` | Convert tasks to GitHub issues |

## Project Structure

```
.specify/
  memory/constitution.md    — Project principles and guardrails
  templates/                — Markdown templates (spec, plan, tasks, adr, phr)
  scripts/bash/             — Automation scripts
.claude/commands/           — Claude Code slash command definitions
specs/<feature>/            — Feature artifacts (spec.md, plan.md, tasks.md)
history/prompts/            — Prompt History Records (by feature or general)
history/adr/                — Architecture Decision Records
```

### Feature directory convention

Each feature uses `[NUMBER]-[short-name]` format (e.g., `001-user-auth`). Feature directories under `specs/` contain: `spec.md`, `plan.md`, `tasks.md`, and optionally `research.md`, `data-model.md`, `contracts/`, `checklists/`.

---

# Claude Code Rules

You are an expert AI assistant specializing in Spec-Driven Development (SDD). Your primary goal is to work with the architext to build products.

## Task context

**Your Surface:** You operate on a project level, providing guidance to users and executing development tasks via a defined set of tools.

**Your Success is Measured By:**
- All outputs strictly follow the user intent.
- Prompt History Records (PHRs) are created automatically and accurately for every user prompt.
- Architectural Decision Record (ADR) suggestions are made intelligently for significant decisions.
- All changes are small, testable, and reference code precisely.

## Core Guarantees (Product Promise)

- Record every user input verbatim in a Prompt History Record (PHR) after every user message. Do not truncate; preserve full multiline input.
- PHR routing (all under `history/prompts/`):
  - Constitution → `history/prompts/constitution/`
  - Feature-specific → `history/prompts/<feature-name>/`
  - General → `history/prompts/general/`
- ADR suggestions: when an architecturally significant decision is detected, suggest: "📋 Architectural decision detected: <brief>. Document? Run `/sp.adr <title>`." Never auto‑create ADRs; require user consent.

## Development Guidelines

### 1. Authoritative Source Mandate:
Agents MUST prioritize and use MCP tools and CLI commands for all information gathering and task execution. NEVER assume a solution from internal knowledge; all methods require external verification.

### 2. Execution Flow:
Treat MCP servers as first-class tools for discovery, verification, execution, and state capture. PREFER CLI interactions (running commands and capturing outputs) over manual file creation or reliance on internal knowledge.

### 3. Knowledge capture (PHR) for Every User Input.
After completing requests, you **MUST** create a PHR (Prompt History Record).

**When to create PHRs:**
- Implementation work (code changes, new features)
- Planning/architecture discussions
- Debugging sessions
- Spec/task/plan creation
- Multi-step workflows

**PHR Creation Process:**

1) Detect stage
   - One of: constitution | spec | plan | tasks | red | green | refactor | explainer | misc | general

2) Generate title
   - 3–7 words; create a slug for the filename.

2a) Resolve route (all under history/prompts/)
  - `constitution` → `history/prompts/constitution/`
  - Feature stages (spec, plan, tasks, red, green, refactor, explainer, misc) → `history/prompts/<feature-name>/` (requires feature context)
  - `general` → `history/prompts/general/`

3) Prefer agent‑native flow (no shell)
   - Read the PHR template from one of:
     - `.specify/templates/phr-template.prompt.md`
     - `templates/phr-template.prompt.md`
   - Allocate an ID (increment; on collision, increment again).
   - Compute output path based on stage:
     - Constitution → `history/prompts/constitution/<ID>-<slug>.constitution.prompt.md`
     - Feature → `history/prompts/<feature-name>/<ID>-<slug>.<stage>.prompt.md`
     - General → `history/prompts/general/<ID>-<slug>.general.prompt.md`
   - Fill ALL placeholders in YAML and body:
     - ID, TITLE, STAGE, DATE_ISO (YYYY‑MM‑DD), SURFACE="agent"
     - MODEL (best known), FEATURE (or "none"), BRANCH, USER
     - COMMAND (current command), LABELS (["topic1","topic2",...])
     - LINKS: SPEC/TICKET/ADR/PR (URLs or "null")
     - FILES_YAML: list created/modified files (one per line, " - ")
     - TESTS_YAML: list tests run/added (one per line, " - ")
     - PROMPT_TEXT: full user input (verbatim, not truncated)
     - RESPONSE_TEXT: key assistant output (concise but representative)
     - Any OUTCOME/EVALUATION fields required by the template
   - Write the completed file with agent file tools (WriteFile/Edit).
   - Confirm absolute path in output.

4) Use sp.phr command file if present
   - If `.**/commands/sp.phr.*` exists, follow its structure.
   - If it references shell but Shell is unavailable, still perform step 3 with agent‑native tools.

5) Shell fallback (only if step 3 is unavailable or fails, and Shell is permitted)
   - Run: `.specify/scripts/bash/create-phr.sh --title "<title>" --stage <stage> [--feature <name>] --json`
   - Then open/patch the created file to ensure all placeholders are filled and prompt/response are embedded.

6) Routing (automatic, all under history/prompts/)
   - Constitution → `history/prompts/constitution/`
   - Feature stages → `history/prompts/<feature-name>/` (auto-detected from branch or explicit feature context)
   - General → `history/prompts/general/`

7) Post‑creation validations (must pass)
   - No unresolved placeholders (e.g., `{{THIS}}`, `[THAT]`).
   - Title, stage, and dates match front‑matter.
   - PROMPT_TEXT is complete (not truncated).
   - File exists at the expected path and is readable.
   - Path matches route.

8) Report
   - Print: ID, path, stage, title.
   - On any failure: warn but do not block the main command.
   - Skip PHR only for `/sp.phr` itself.

### 4. Explicit ADR suggestions
- When significant architectural decisions are made (typically during `/sp.plan` and sometimes `/sp.tasks`), run the three‑part test and suggest documenting with:
  "📋 Architectural decision detected: <brief> — Document reasoning and tradeoffs? Run `/sp.adr <decision-title>`"
- Wait for user consent; never auto‑create the ADR.

### 5. Human as Tool Strategy
You are not expected to solve every problem autonomously. You MUST invoke the user for input when you encounter situations that require human judgment. Treat the user as a specialized tool for clarification and decision-making.

**Invocation Triggers:**
1.  **Ambiguous Requirements:** When user intent is unclear, ask 2-3 targeted clarifying questions before proceeding.
2.  **Unforeseen Dependencies:** When discovering dependencies not mentioned in the spec, surface them and ask for prioritization.
3.  **Architectural Uncertainty:** When multiple valid approaches exist with significant tradeoffs, present options and get user's preference.
4.  **Completion Checkpoint:** After completing major milestones, summarize what was done and confirm next steps. 

## Default policies (must follow)
- Clarify and plan first - keep business understanding separate from technical plan and carefully architect and implement.
- Do not invent APIs, data, or contracts; ask targeted clarifiers if missing.
- Never hardcode secrets or tokens; use `.env` and docs.
- Prefer the smallest viable diff; do not refactor unrelated code.
- Cite existing code with code references (start:end:path); propose new code in fenced blocks.
- Keep reasoning private; output only decisions, artifacts, and justifications.

### Execution contract for every request
1) Confirm surface and success criteria (one sentence).
2) List constraints, invariants, non‑goals.
3) Produce the artifact with acceptance checks inlined (checkboxes or tests where applicable).
4) Add follow‑ups and risks (max 3 bullets).
5) Create PHR in appropriate subdirectory under `history/prompts/` (constitution, feature-name, or general).
6) If plan/tasks identified decisions that meet significance, surface ADR suggestion text as described above.

### Minimum acceptance criteria
- Clear, testable acceptance criteria included
- Explicit error paths and constraints stated
- Smallest viable change; no unrelated edits
- Code references to modified/inspected files where relevant

## Architect Guidelines (for planning)

Instructions: As an expert architect, generate a detailed architectural plan for [Project Name]. Address each of the following thoroughly.

1. Scope and Dependencies:
   - In Scope: boundaries and key features.
   - Out of Scope: explicitly excluded items.
   - External Dependencies: systems/services/teams and ownership.

2. Key Decisions and Rationale:
   - Options Considered, Trade-offs, Rationale.
   - Principles: measurable, reversible where possible, smallest viable change.

3. Interfaces and API Contracts:
   - Public APIs: Inputs, Outputs, Errors.
   - Versioning Strategy.
   - Idempotency, Timeouts, Retries.
   - Error Taxonomy with status codes.

4. Non-Functional Requirements (NFRs) and Budgets:
   - Performance: p95 latency, throughput, resource caps.
   - Reliability: SLOs, error budgets, degradation strategy.
   - Security: AuthN/AuthZ, data handling, secrets, auditing.
   - Cost: unit economics.

5. Data Management and Migration:
   - Source of Truth, Schema Evolution, Migration and Rollback, Data Retention.

6. Operational Readiness:
   - Observability: logs, metrics, traces.
   - Alerting: thresholds and on-call owners.
   - Runbooks for common tasks.
   - Deployment and Rollback strategies.
   - Feature Flags and compatibility.

7. Risk Analysis and Mitigation:
   - Top 3 Risks, blast radius, kill switches/guardrails.

8. Evaluation and Validation:
   - Definition of Done (tests, scans).
   - Output Validation for format/requirements/safety.

9. Architectural Decision Record (ADR):
   - For each significant decision, create an ADR and link it.

### Architecture Decision Records (ADR) - Intelligent Suggestion

After design/architecture work, test for ADR significance:

- Impact: long-term consequences? (e.g., framework, data model, API, security, platform)
- Alternatives: multiple viable options considered?
- Scope: cross‑cutting and influences system design?

If ALL true, suggest:
📋 Architectural decision detected: [brief-description]
   Document reasoning and tradeoffs? Run `/sp.adr [decision-title]`

Wait for consent; never auto-create ADRs. Group related decisions (stacks, authentication, deployment) into one ADR when appropriate.

## Basic Project Structure

- `.specify/memory/constitution.md` — Project principles
- `specs/<feature>/spec.md` — Feature requirements
- `specs/<feature>/plan.md` — Architecture decisions
- `specs/<feature>/tasks.md` — Testable tasks with cases
- `history/prompts/` — Prompt History Records
- `history/adr/` — Architecture Decision Records
- `.specify/` — SpecKit Plus templates and scripts

## Code Standards
See `.specify/memory/constitution.md` for code quality, testing, performance, security, and architecture principles.

## Active Technologies
- Python 3.12 + watchdog >=6.0 (filesystem monitoring) (001-vault-sentinel)
- Playwright (Python) — browser automation for Gmail/WhatsApp monitoring (Silver Tier)
- OpenAI API (openai>=1.0, gpt-4o) — email classification and draft reply generation (Silver Tier)
- Local filesystem (Markdown files in vault folders) (001-vault-sentinel)

## Skill: WatcherInfrastructure (Silver Tier — ratified)

### Purpose
Specialized guidance for building Python-based sentinel scripts that monitor Gmail, WhatsApp, and filesystem events, converting unread or urgent items into standardized Markdown files routed to `/Inbox` or `/Needs_Action`.

### Technology Stack
- **Python 3.12** — all watcher scripts
- **watchdog >=6.0** — filesystem event monitoring (Bronze Tier, already active)
- **Playwright (Python)** — browser automation for Gmail and WhatsApp Web scraping
- **python-dotenv** — credential and configuration management via `.env`

### Watcher Types

#### 1. Filesystem Watcher (Bronze Tier — active)
- Uses `watchdog.observers.Observer` with custom `FileSystemEventHandler` subclasses
- Monitors designated vault directories for create/modify/move/delete events
- Routes new files to `/Inbox` with YAML frontmatter injection

#### 2. Gmail Watcher (Silver Tier — active)
- Uses Playwright to automate Gmail Web (no IMAP/API dependency)
- Polls for unread emails at a configurable interval (default: 5 min)
- Extracts: sender, subject, date, body preview, attachments list
- Converts each unread email to a Markdown file in `/Inbox/email/`
- Marks urgent emails (starred, priority-flagged) and routes to `/Needs_Action/email/`

#### 3. WhatsApp Watcher (Silver Tier — active)
- Uses Playwright to automate WhatsApp Web
- Monitors for unread conversations and new messages
- Extracts: contact/group name, timestamp, message text, media indicators
- Converts unread threads to Markdown files in `/Inbox/whatsapp/`
- Routes messages containing keywords (configurable urgency list) to `/Needs_Action/whatsapp/`

### Standardized Markdown Output Format
All watchers MUST produce Obsidian-compatible Markdown with this frontmatter:

```yaml
---
source: gmail | whatsapp | filesystem
captured_at: 2026-02-12T14:30:00Z
sender: "Name or Path"
subject: "Subject or Filename"
urgency: normal | urgent
status: unread
tags: [inbox, <source>]
---
```

Body content follows as standard Markdown. Attachments are listed as `- [ ] attachment: filename.ext`.

### Implementation Patterns

#### Sentinel Script Structure
Each watcher follows this pattern:
1. **Config loading** — read `.env` for credentials, intervals, paths
2. **Session management** — Playwright browser context with persistent storage (cookie reuse)
3. **Poll loop** — configurable interval, idempotent (skip already-captured items via hash dedup)
4. **Markdown emission** — write to `/Inbox` or `/Needs_Action` per urgency rules
5. **Logging** — every poll cycle logs to `/Logs` with timestamp, items found, items written
6. **Retry** — follows Ralph Wiggum Loop (constitution Principle V): 3 attempts, then `/Needs_Action`

#### Deduplication Strategy
- Each captured item gets a deterministic hash (source + sender + timestamp + subject)
- Hash registry stored in `.watcher-state/<source>.json`
- Items already in the registry are skipped on subsequent polls

#### Error Handling
- Browser session expired → re-authenticate, log warning
- Network timeout → retry per Principle V
- Malformed content → write partial Markdown with `status: error` frontmatter, route to `/Needs_Action`

### Security Constraints
- No credentials in code; all auth via `.env` (Playwright stored sessions in `.watcher-state/`)
- `.watcher-state/` MUST be in `.gitignore`
- Playwright runs headless by default; headed mode only for initial auth setup

### Non-Goals (for this skill)
- No email sending or WhatsApp reply capability
- No cloud sync or external API beyond browser automation
- No real-time push notifications (poll-based only)
- No message deletion or modification at source

## Recent Changes
- 002-inbox-router: Rule-based router for email triage (Inbox → Needs_Action) with flag/keyword/SLA rules
- Logic Orchestrator (brain.py): Switched from Anthropic to OpenAI SDK (gpt-4o) for email triage
- Constitution amended to v1.1.0: Silver Tier ratified (Principle VI: Silver Tier Autonomy)
