<!--
Sync Impact Report
===================
- Version change: 0.0.0 → 1.0.0 (initial ratification)
- Added principles:
  - I. Local-First Autonomous Operations
  - II. Canonical Folder Structure
  - III. Bronze Tier Scope
  - IV. Safety-First Execution
  - V. Persistent Retry Logic
- Added sections:
  - Operational Constraints
  - Development Workflow
  - Governance
- Templates requiring updates:
  - `.specify/templates/plan-template.md` — ✅ no update needed (Constitution Check section is generic)
  - `.specify/templates/spec-template.md` — ✅ no update needed (structure is generic)
  - `.specify/templates/tasks-template.md` — ✅ no update needed (phases are generic)
- Follow-up TODOs: none
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

### III. Bronze Tier Scope

The initial implementation (Bronze Tier) MUST focus exclusively on:

1. **Obsidian vault management** — reading, organizing, tagging,
   and summarizing notes within an Obsidian-compatible vault.
2. **Local file monitoring** — watching designated directories
   for new or changed files and routing them through the
   canonical folder structure.

Features outside this scope (e.g., email integration, calendar
sync, web scraping) are explicitly out of scope until a higher
tier is ratified via constitution amendment.

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
at Bronze Tier.

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
  Constitution Check section validating adherence to all five
  principles. Violations MUST be justified in a Complexity
  Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-11
