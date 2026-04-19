# Feature Specification: Gold Phase 1 — Cross-Domain Integration Foundation

**Feature Branch**: `011-gold-phase-1-foundation`
**Created**: 2026-04-14
**Status**: Draft
**Phase**: Gold Phase 1 (of 5)
**Constitution**: v3.0.0

## Overview

Establish a stable, unified foundation for all Gold-tier work. This phase
audits, validates, and where necessary corrects the routing, vault state
boundaries, MCP boundaries, logging completeness, and Silver compatibility
across the entire AI Employee system. No new end-user features are added.
The output is a provably consistent, well-bounded system ready for Gold
Phase 2 work.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Unified Vault Routing (Priority: P1)

As a human operator, I want all captured items from every watcher (Gmail,
WhatsApp) to land in the correct canonical vault location — `/Inbox/<source>/`
for normal items and `/Needs_Action/<source>/` for urgent items — so that I
can trust the vault structure and never find items in unexpected locations.

**Why this priority**: Routing correctness is the foundation everything else
depends on. If items are misrouted, no subsequent Gold-tier phase can rely on
the vault as a stable input. This must be correct before anything else.

**Independent Test**: Drop a simulated email file and a simulated WhatsApp
file into the system; verify each lands at the expected canonical path. Can be
tested without running live watchers by calling routing logic directly with
fixture files.

**Acceptance Scenarios**:

1. **Given** a Gmail-captured email with `urgency: normal`, **When** the
   watcher processes it, **Then** the file appears at
   `vault/Inbox/email/<filename>.md` and nowhere else.
2. **Given** a Gmail-captured email with `urgency: urgent`, **When** the
   watcher processes it, **Then** the file appears at
   `vault/Needs_Action/email/<filename>.md` and nowhere else.
3. **Given** a WhatsApp message with `urgency: normal`, **When** the watcher
   processes it, **Then** the file appears at
   `vault/Inbox/whatsapp/<filename>.md` and nowhere else.
4. **Given** a WhatsApp message marked urgent, **When** the watcher
   processes it, **Then** the file appears at
   `vault/Needs_Action/whatsapp/<filename>.md` and nowhere else.
5. **Given** any watcher output, **When** the file is written, **Then** the
   YAML frontmatter contains `source`, `captured_at`, `sender`, `subject`,
   `urgency`, `status`, and `tags` fields — no mandatory field is missing.

---

### User Story 2 — Vault State Boundary Validation (Priority: P1)

As a human operator, I want confidence that each vault directory is used for
exactly and only its defined purpose — so that `Needs_Action/plans` only ever
contains AI-generated triage plans, `Pending_Approval` only contains proposed
external actions awaiting sign-off, and `Approved` only contains items cleared
for execution.

**Why this priority**: Boundary violations silently corrupt the meaning of
each directory. Any Gold-tier phase that reads from these directories (Odoo,
social, briefings) will produce wrong results if boundaries are not clean.
Tied P1 with routing because both must be correct before Phase 2 begins.

**Independent Test**: Run a vault audit tool that scans each canonical
directory and verifies all files in it match the directory's expected file
type and frontmatter signature. Produces a pass/fail report per directory.

**Acceptance Scenarios**:

1. **Given** the vault is initialized, **When** an audit runs, **Then** every
   file in `Needs_Action/plans/` has `type: runtime_plan` frontmatter.
2. **Given** the orchestrator processes a reply-needed email, **When** triage
   completes, **Then** the runtime plan is in `Needs_Action/plans/` and NOT
   in `Approved/`, `Plans/`, or any other directory.
3. **Given** a proposed external action is generated, **When** the system
   writes the proposal, **Then** it lands in `Pending_Approval/` with status
   `awaiting_approval` and is NOT placed directly in `Approved/`.
4. **Given** a human moves a proposal from `Pending_Approval/` to `Approved/`,
   **When** the system checks for authorized actions, **Then** it finds and
   acts on items in `Approved/` only — not `Pending_Approval/`.
5. **Given** an audit scan, **When** a file is found in a directory whose
   type does not match the file's frontmatter `type` field, **Then** the
   audit report flags it as a boundary violation.

---

### User Story 3 — MCP Orchestration Boundary Enforcement (Priority: P2)

As a human operator, I want a clear, documented contract for how MCP tools
are used in the system, and confidence that no component issues external
actions by bypassing the MCP layer — so that every external action is
traceable, auditable, and controllable from one place.

**Why this priority**: MCP boundary enforcement is required before Gold Phase
2 (Odoo) and Phase 3 (social) introduce real external actions. Defining it
in Phase 1 prevents architectural drift in later phases.

**Independent Test**: An MCP boundary audit document is produced that
enumerates every external action path in the codebase, labels each as
MCP-routed or direct, and confirms zero direct external calls exist or are
planned. Independently verifiable by code inspection.

**Acceptance Scenarios**:

1. **Given** the codebase, **When** a boundary audit runs, **Then** every
   external action path is identified and documented in the MCP contracts.
2. **Given** the vault MCP server, **When** Claude Code uses it to read or
   write vault files, **Then** the operation is logged with timestamp,
   tool name, path, and outcome in `Logs/`.
3. **Given** a Gold-tier integration (Odoo, social, etc.), **When** its
   MCP contract is defined, **Then** the contract specifies input schema,
   output schema, approval gate requirement, and error behavior — documented
   in `specs/gold/phase-1/contracts/`.
4. **Given** any watcher or orchestrator component, **When** it needs to
   perform a read or write on the vault from an external client, **Then** it
   does so through the vault MCP server, not by direct filesystem access
   from outside the process.

---

### User Story 4 — Silver Compatibility Regression Check (Priority: P2)

As a human operator, I want proof that all Silver-tier features continue to
work correctly after any Phase 1 changes — so that the Gold-tier foundation
does not break existing value.

**Why this priority**: Silver is the only deployed functionality. Any
regression destroys working value. This validation gates Phase 1 closure.

**Independent Test**: Run the full Silver-tier test suite (unit tests for
orchestrator, vault MCP server, router, etc.) and produce a green result.
All 15 plan-writer tests, 20 MCP tests, and any existing watcher tests pass.

**Acceptance Scenarios**:

1. **Given** Gold Phase 1 changes are applied, **When** the full unit test
   suite runs, **Then** all previously passing tests still pass — zero
   regressions.
2. **Given** the Gmail watcher is running, **When** a new email arrives,
   **Then** the watcher captures it, routes it correctly, and the
   orchestrator produces a plan file in `Needs_Action/plans/`.
3. **Given** the vault MCP server is running, **When** Claude Code calls
   `list_files`, `read_file`, or `write_file`, **Then** the correct result
   is returned and the operation is logged.
4. **Given** the HITL approval workflow, **When** a draft reply is created,
   **Then** it appears in `Needs_Action/drafts/` awaiting human approval and
   is NOT sent without an approved action in `Approved/email/`.

---

### User Story 5 — Log Completeness Audit (Priority: P3)

As a human operator, I want every automated action in the system to produce
a complete log entry — so that I can audit what the system has done, diagnose
failures, and verify compliance with the project constitution.

**Why this priority**: Logs are required by Constitution Principle IX. This
story validates the requirement is met across all existing flows before new
Gold-tier flows are added. Lower priority because it is a validation task,
not a new capability.

**Independent Test**: Run the system through a complete triage cycle
(email captured → classified → plan written → draft created → logged) and
verify the `Logs/` directory contains an entry for every step with all
required fields present.

**Acceptance Scenarios**:

1. **Given** the orchestrator processes an email, **When** triage completes,
   **Then** a log entry exists in `Logs/` with all six mandatory fields:
   `timestamp`, `action_type`, `source_path`, `dest_path`, `outcome`,
   `details`.
2. **Given** the vault MCP server handles a request, **When** the operation
   completes, **Then** a log entry is written with the tool name, path
   operated on, and outcome.
3. **Given** a triage failure after 3 retries, **When** the Ralph Wiggum
   loop is exhausted, **Then** a log entry is written with
   `outcome: failure` and the full error context.
4. **Given** the audit tool inspects `Logs/`, **When** it checks all recent
   entries, **Then** 100% of entries contain all six required fields — no
   partial or missing-field entries exist.

---

### Edge Cases

- A watcher receives a file that is missing mandatory frontmatter fields —
  system MUST write the file with `status: error` frontmatter to
  `Needs_Action/<source>/` rather than silently dropping it.
- A vault directory does not exist at startup — the system MUST create it
  rather than failing.
- A file is written to a canonical directory with a `type` field that does
  not match the directory's expected type — the boundary audit MUST flag it;
  the runtime system MUST still process it (audit is non-blocking).
- The MCP server is unreachable when a vault operation is attempted — the
  calling component MUST log the failure and follow the Ralph Wiggum retry
  loop before routing the task to `Needs_Action/`.
- A routing decision produces a destination path outside the vault root —
  the system MUST reject the write and log a boundary violation error.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST route all Gmail-captured items to
  `vault/Inbox/email/` (normal) or `vault/Needs_Action/email/` (urgent) —
  no other destination is permitted.
- **FR-002**: The system MUST route all WhatsApp-captured items to
  `vault/Inbox/whatsapp/` (normal) or `vault/Needs_Action/whatsapp/`
  (urgent) — no other destination is permitted.
- **FR-003**: Every captured item MUST include a complete YAML frontmatter
  with fields: `source`, `captured_at`, `sender`, `subject`, `urgency`,
  `status`, `tags`.
- **FR-004**: Runtime triage plan files MUST be written exclusively to
  `vault/Needs_Action/plans/` with `type: runtime_plan` frontmatter.
- **FR-005**: Proposed external actions MUST be written to
  `vault/Pending_Approval/<domain>/` before any execution — never directly
  to `Approved/`.
- **FR-006**: The system MUST provide a vault boundary audit capability that
  scans all canonical directories and reports files whose `type` frontmatter
  field does not match the expected type for that directory.
- **FR-007**: The vault MCP server MUST be the sole interface for external
  clients (Claude Code, future Gold-tier integrations) reading or writing
  vault files.
- **FR-008**: MCP contracts for all current and planned Gold-tier external
  integrations MUST be documented in `specs/gold/phase-1/contracts/` before
  Phase 1 closes.
- **FR-009**: Every automated action MUST produce a log entry in `vault/Logs/`
  containing all six required fields: `timestamp`, `action_type`,
  `source_path`, `dest_path`, `outcome`, `details`.
- **FR-010**: All Silver-tier unit tests MUST pass without modification after
  Phase 1 changes — zero regressions permitted.
- **FR-011**: The system MUST create any missing canonical vault directories
  at startup rather than failing with a missing-directory error.
- **FR-012**: Any routing or write path that would place a file outside the
  vault root MUST be rejected by the system, and a boundary violation MUST
  be logged.

### Key Entities

- **VaultRoute**: A mapping from (source, urgency) to a canonical vault
  directory path. Defines the authoritative routing table for all watchers.
- **BoundaryAuditReport**: A document produced by the audit tool listing
  each canonical directory, the expected file type, any violations found,
  and an overall pass/fail result.
- **MCPContract**: A structured document defining a tool's name, input
  schema, output schema, approval gate requirement, and error behavior.
  Stored in `specs/gold/phase-1/contracts/`.
- **LogEntry**: A record in `vault/Logs/` capturing one automated action.
  Required fields: `timestamp`, `action_type`, `source_path`, `dest_path`,
  `outcome`, `details`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of captured items from all watchers land in the correct
  canonical vault directory — zero misrouted files after Phase 1.
- **SC-002**: The vault boundary audit tool produces a passing report showing
  zero `type` mismatches across all canonical directories in the test vault.
- **SC-003**: MCP contract documents exist for all vault operations and for
  each planned Gold-tier external integration — 100% coverage before Phase 1
  closes.
- **SC-004**: All existing Silver-tier automated tests pass after Phase 1
  changes — zero regressions.
- **SC-005**: 100% of log entries produced during a complete triage cycle
  contain all six required fields — no partial entries.
- **SC-006**: A full triage cycle (email captured → classified → plan written
  → draft created → logged) completes end-to-end with all items in the
  correct vault locations and all log entries present.

---

## Out of Scope

The following are explicitly excluded from Phase 1:

- Odoo accounting integration (Phase 2)
- Facebook, Instagram, or X social media posting (Phase 3)
- CEO briefing or weekly audit generation (Phase 4)
- Error recovery improvements or process resilience work (Phase 5)
- Any new watcher beyond Gmail and WhatsApp
- Any change to the SpecifyPlus internal folders (`.specify/`, `.claude/`)
- Any implementation work not covered by an approved Phase 1 spec

---

## Dependencies and Assumptions

**Dependencies**:

- Silver-tier implementation complete (Gmail watcher, WhatsApp watcher,
  orchestrator, plan writer, MCP server, HITL approval workflow) — confirmed
  complete as of 2026-04-14.
- Constitution v3.0.0 ratified — confirmed 2026-04-14.
- `vault/` directory initialized with `sentinel init`.

**Assumptions**:

- The vault MCP server (`src/vault_mcp/`) is already the designated
  interface for external vault access — Phase 1 formalizes this boundary
  rather than building a new server.
- "MCP contracts for Gold-tier integrations" in FR-008 means human-readable
  Markdown contract documents defining tool signatures and approval
  requirements — not code implementation of those tools (which is Phase 2+).
- The boundary audit tool (FR-006) is a script or function that can be run
  on demand — it does not need to run continuously as a watcher.
- Log completeness validation (SC-005) is measured against a single
  controlled triage cycle run in a test vault, not against all historical
  log entries.
- WhatsApp watcher uses Playwright browser automation — Phase 1 does not
  migrate it; it validates that existing routing is correct.
