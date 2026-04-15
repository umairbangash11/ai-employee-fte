# Feature Specification: Gold Phase 2 — Odoo Accounting Integration

**Feature Branch**: `012-odoo-accounting`
**Created**: 2026-04-15
**Status**: Draft
**Phase**: Gold Phase 2 (of 5)
**Constitution**: v3.0.0

## Overview

Implement the Odoo accounting integration code foundation for the AI Employee.
This phase introduces the connection layer, read operations, and draft-only
accounting action flows — each approval-gated before any write reaches Odoo.
No financial operation is executed without explicit human authorization via the
`Pending_Approval/odoo/` → `Approved/odoo/` gate. The output is a working set
of code modules, vault flows, and MCP-boundary contracts covering invoices,
payments, and reconciliation.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Odoo Connection and Read Operations (Priority: P1)

As a human operator, I want the AI Employee to establish a connection to my
Odoo Community instance and retrieve accounting data — invoices, partner records,
and account balances — so that triage decisions and draft proposals are grounded
in live financial context rather than assumptions.

**Why this priority**: Read operations are the prerequisite for every other
Phase 2 story. No draft can be intelligently prepared without first reading
current Odoo state. Establishing and validating the connection is the foundation
all other code modules depend on.

**Independent Test**: Configure Odoo credentials in `.env`, call the connection
module, and verify that a list of invoices is returned and written as structured
data. No vault write required; the read path is independently verifiable.

**Acceptance Scenarios**:

1. **Given** valid Odoo credentials in `.env`, **When** the connection module
   is invoked, **Then** it returns a successful connection result and the
   system logs `outcome: success` to `vault/Logs/`.
2. **Given** a request to read open invoices, **When** the read operation runs,
   **Then** it returns a list of invoice records with at minimum: invoice ID,
   partner name, amount, currency, and status.
3. **Given** a request to read a specific partner record, **When** the read
   operation runs, **Then** it returns: partner name, email, outstanding balance,
   and active invoice count.
4. **Given** invalid or expired Odoo credentials, **When** the connection
   module is invoked, **Then** the system logs `outcome: failure` with full
   error context and routes a triage item to `vault/Needs_Action/odoo/` for
   human review.
5. **Given** the Odoo server is unreachable, **When** the connection module is
   invoked, **Then** the system retries 3 times (Ralph Wiggum Loop), logs the
   failure after attempt 3, and routes the failure notice to
   `vault/Needs_Action/odoo/`.

---

### User Story 2 — Invoice Draft Creation and Approval Gate (Priority: P1)

As a human operator, I want the AI Employee to prepare a structured invoice
draft — complete with partner, line items, and amounts — and route it to
`vault/Pending_Approval/odoo/` for my review before any record is created in
Odoo, so that no invoice is ever created without my explicit sign-off.

**Why this priority**: Invoice creation is the primary accounting action in
Phase 2. The draft-then-approve pattern defined here becomes the template for
all other accounting action flows. Getting this right first ensures every
subsequent story inherits a proven gate.

**Independent Test**: Trigger invoice draft creation with fixture data; verify
the draft file appears in `vault/Pending_Approval/odoo/` with correct
frontmatter, complete line items, and `status: awaiting_approval`. Verify
nothing is written to Odoo until the file is moved to `vault/Approved/odoo/`.

**Acceptance Scenarios**:

1. **Given** an invoice request (partner, items, amounts) reaches the
   orchestrator, **When** the invoice draft module runs, **Then** a draft
   proposal file is written to `vault/Pending_Approval/odoo/<slug>.md` with
   `type: pending_action`, `action_type: create_invoice`, and
   `status: awaiting_approval` — and nothing is sent to Odoo.
2. **Given** a proposal file in `vault/Pending_Approval/odoo/`, **When** the
   human operator moves it to `vault/Approved/odoo/`, **Then** the execution
   module detects the move, creates the invoice in Odoo as a draft, and logs
   the result to `vault/Logs/` with all 6 required fields.
3. **Given** a successfully executed invoice creation, **When** the operation
   completes, **Then** a confirmation record is written to `vault/Accounting/`
   with the Odoo invoice ID, and the approved action file is moved to
   `vault/Done/odoo/`.
4. **Given** a proposal file in `vault/Pending_Approval/odoo/`, **When** the
   human operator moves it to `vault/Rejected/`, **Then** the system logs the
   rejection with the file path and takes no further action.
5. **Given** the system has written a proposal, **When** a subsequent process
   attempts to self-approve (move from `Pending_Approval` to `Approved`
   autonomously), **Then** the action is blocked and a boundary violation is
   logged.

---

### User Story 3 — Payment Preparation Draft and Approval Gate (Priority: P2)

As a human operator, I want the AI Employee to prepare payment processing
drafts — specifying vendor, amount, and target invoice — and route them to
`vault/Pending_Approval/odoo/` for my review before any payment instruction
reaches Odoo, so that no outgoing payment is initiated without my approval.

**Why this priority**: Payments carry direct financial consequence. Building on
the invoice draft pattern, this story applies the same gate to outbound
payment flows. It is P2 because it requires the connection layer (US1) and
the established gate pattern (US2) to already be in place.

**Independent Test**: Trigger payment draft preparation with a fixture vendor
and amount; verify the draft appears in `vault/Pending_Approval/odoo/` with
`action_type: prepare_payment`. Verify nothing is registered in Odoo until
the file is moved to `vault/Approved/odoo/`.

**Acceptance Scenarios**:

1. **Given** a payment request (vendor, invoice reference, amount) reaches the
   orchestrator, **When** the payment draft module runs, **Then** a draft
   proposal is written to `vault/Pending_Approval/odoo/<slug>.md` with
   `type: pending_action`, `action_type: prepare_payment`, and
   `status: awaiting_approval` — nothing is registered in Odoo.
2. **Given** a payment proposal in `vault/Approved/odoo/`, **When** the
   execution module processes it, **Then** it registers the payment in Odoo
   as a draft journal entry (not posted), logs the result, and moves the
   source file to `vault/Done/odoo/`.
3. **Given** a payment draft is executed, **When** the operation completes,
   **Then** a record is written to `vault/Accounting/` referencing the Odoo
   payment ID and linked invoice.
4. **Given** the Odoo payment registration fails after 3 retries, **When** the
   Ralph Wiggum Loop is exhausted, **Then** the failure is logged to
   `vault/Logs/` with `outcome: failure` and the proposal is moved to
   `vault/Needs_Action/odoo/` for human review.

---

### User Story 4 — Reconciliation Draft Actions (Priority: P2)

As a human operator, I want the AI Employee to detect unreconciled invoices
and payments in Odoo, prepare a structured reconciliation proposal, and route
it to `vault/Pending_Approval/odoo/` for my review — so that no reconciliation
journal entry is created without my approval.

**Why this priority**: Reconciliation corrects mismatches between payments and
invoices. It is P2 because it requires a working read layer (US1) and the
established gate pattern (US2). It is lower than payment drafts because it
operates on existing records rather than creating new financial obligations.

**Independent Test**: Run the reconciliation scan on a test Odoo instance with
known unreconciled items; verify a reconciliation proposal appears in
`vault/Pending_Approval/odoo/` with `action_type: reconcile_payment`. Verify
no journal entries are created in Odoo without approval.

**Acceptance Scenarios**:

1. **Given** the reconciliation scan runs, **When** unreconciled invoice-payment
   pairs are detected, **Then** a reconciliation proposal is written to
   `vault/Pending_Approval/odoo/<slug>.md` per pair with `action_type:
   reconcile_payment`, `status: awaiting_approval`, and the invoice/payment
   IDs listed in the proposal body.
2. **Given** a reconciliation proposal in `vault/Approved/odoo/`, **When** the
   execution module processes it, **Then** it applies the reconciliation in
   Odoo and logs the result to `vault/Logs/`.
3. **Given** the reconciliation scan finds no unreconciled items, **When** the
   scan completes, **Then** a summary log entry is written to `vault/Logs/`
   with `outcome: success` and `details: no items to reconcile` — no proposal
   is written.

---

### User Story 5 — Accounting Vault Lifecycle Tracking (Priority: P3)

As a human operator, I want every accounting item produced by the AI Employee
— drafts, proposals, confirmations, and logs — to land in the correct canonical
vault directory and carry complete YAML frontmatter, so that I can inspect the
state of any accounting action at any point in its lifecycle.

**Why this priority**: Lifecycle tracking is the audit foundation. It validates
that vault routing and frontmatter completeness are consistent across all Phase 2
flows. It is P3 because it can only be verified after US1–US4 paths are
implemented.

**Independent Test**: Run a complete triage cycle (read → draft → proposal →
approval → execute) with fixture data and inspect: `vault/Accounting/`,
`vault/Pending_Approval/odoo/`, `vault/Approved/odoo/`, `vault/Done/odoo/`,
and `vault/Logs/` to verify all files have correct `type`, `action_type`,
and required frontmatter fields.

**Acceptance Scenarios**:

1. **Given** any accounting item is created, **When** the write operation
   completes, **Then** the file's YAML frontmatter contains all required
   fields: `type`, `action_type`, `status`, `source_path`, `dest_path`,
   `outcome`, and `captured_at`.
2. **Given** a complete accounting lifecycle, **When** an audit runs,
   **Then** each stage is represented by a file in its canonical directory:
   `Accounting/` (working draft), `Pending_Approval/odoo/` (awaiting sign-off),
   `Approved/odoo/` (authorized), `Done/odoo/` (completed), `Logs/` (audit trail).
3. **Given** a vault boundary audit runs (using `vault_audit.py`), **When** it
   scans `Pending_Approval/odoo/` and `Approved/odoo/`, **Then** every file
   has `type: pending_action` or `type: execution_plan` respectively — zero
   boundary violations reported.

---

### Edge Cases

- Odoo server unreachable during proposal execution → retry 3 times, log
  failure, move proposal to `vault/Needs_Action/odoo/` — do NOT leave proposal
  in `vault/Approved/odoo/` after failure.
- Duplicate proposal file written (same invoice/payment slug) → deduplicate by
  appending a counter suffix; never silently overwrite an existing proposal.
- Odoo returns a partial record (missing required fields) → reject the read
  result, log a structured error to `vault/Logs/`, route error notice to
  `vault/Needs_Action/odoo/`.
- Human moves a proposal to both `Approved/` and `Rejected/` simultaneously
  (race condition) → system acts on whichever appears first; logs a conflict
  warning for the second.
- A proposal file is manually edited after being moved to `Approved/` → the
  execution module uses the file content at execution time; no pre-validation
  is performed against the original draft.
- An Odoo write succeeds but the vault `Done/` write fails → log the Odoo
  result to `Logs/` immediately after execution; vault write failure is logged
  separately and does NOT roll back the Odoo operation.
- Connection credentials missing from `.env` at startup → log error with
  `outcome: failure` to `vault/Logs/` and skip all Odoo operations for that
  cycle; do NOT raise an unhandled exception that would crash the orchestrator.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST connect to Odoo Community using credentials
  supplied exclusively via environment variables — no credentials in vault
  files, specs, or committed source.
- **FR-002**: The system MUST support read operations for: open invoices,
  partner records (name, email, outstanding balance), and unreconciled payment
  pairs — without requiring any approval gate.
- **FR-003**: The system MUST route all Odoo write actions through the MCP
  boundary — no component may call the Odoo API directly for write operations
  outside the defined MCP tool interface.
- **FR-004**: The system MUST write every invoice draft proposal to
  `vault/Pending_Approval/odoo/<slug>.md` with `type: pending_action`,
  `action_type: create_invoice`, and `status: awaiting_approval` before any
  Odoo write occurs.
- **FR-005**: The system MUST write every payment preparation proposal to
  `vault/Pending_Approval/odoo/<slug>.md` with `type: pending_action`,
  `action_type: prepare_payment`, and `status: awaiting_approval` before any
  Odoo write occurs.
- **FR-006**: The system MUST write every reconciliation proposal to
  `vault/Pending_Approval/odoo/<slug>.md` with `type: pending_action`,
  `action_type: reconcile_payment`, and `status: awaiting_approval` before
  any Odoo write occurs.
- **FR-007**: The system MUST detect files moved to `vault/Approved/odoo/`
  and execute the corresponding Odoo action — no Odoo write is triggered by
  any other mechanism.
- **FR-008**: The system MUST NOT self-approve any proposal — moving a file
  from `vault/Pending_Approval/` to `vault/Approved/` is a human-only action.
- **FR-009**: After successful execution of an approved action, the system
  MUST move the source file from `vault/Approved/odoo/` to `vault/Done/odoo/`
  and write a confirmation record to `vault/Accounting/`.
- **FR-010**: Every accounting-related operation MUST produce a log entry in
  `vault/Logs/` containing all six required fields: `timestamp`, `action_type`,
  `source_path`, `dest_path`, `outcome`, `details`.
- **FR-011**: The system MUST follow the Ralph Wiggum Loop (3 attempts) for
  all Odoo connection and execution failures before routing to
  `vault/Needs_Action/odoo/`.
- **FR-012**: The system MUST create any missing canonical vault subdirectories
  (`Accounting/`, `Pending_Approval/odoo/`, `Approved/odoo/`, `Done/odoo/`,
  `Needs_Action/odoo/`) at startup — no manual directory creation required.
- **FR-013**: Any path that would write a vault file outside the configured
  vault root MUST be rejected and logged as a boundary violation.
- **FR-014**: The Odoo MCP contract document (`specs/gold/phase-1/contracts/odoo-mcp.md`)
  MUST be updated at Phase 2 close to reflect the finalized tool names,
  input schemas, and output schemas implemented in this phase.

### Key Entities

- **OdooReadResult**: Data returned from a read operation against Odoo.
  Contains: `record_type` (invoice | partner | payment), `odoo_id`, `fields`
  (key-value map of returned data), `fetched_at` (ISO 8601 timestamp).

- **AccountingDraft**: A working accounting item stored in `vault/Accounting/`
  before a proposal is generated. Contains: `type: accounting_draft`,
  `action_type` (create_invoice | prepare_payment | reconcile_payment),
  `status: draft`, `source` (trigger that initiated it), and the item payload.

- **OdooProposal**: An approval-pending Odoo write action stored in
  `vault/Pending_Approval/odoo/`. Contains: `type: pending_action`,
  `action_type`, `status: awaiting_approval`, `odoo_payload` (the data to
  be sent to Odoo on approval), and a human-readable description.

- **OdooApprovedAction**: An authorized Odoo action stored in
  `vault/Approved/odoo/`. Same schema as OdooProposal with
  `status: approved`. Consumed by the execution module.

- **OdooLogEntry**: A log record in `vault/Logs/` produced after every
  accounting operation. Required fields: `timestamp`, `action_type`,
  `source_path`, `dest_path`, `outcome`, `details`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Odoo write operations are preceded by a proposal in
  `vault/Pending_Approval/odoo/` — zero direct Odoo writes without a
  corresponding proposal file.
- **SC-002**: 100% of log entries produced during a complete accounting cycle
  (read → draft → propose → approve → execute) contain all six required fields
  — no partial log entries.
- **SC-003**: All read operations complete without writing any data to Odoo —
  confirmed by vault boundary audit showing zero write-type actions originating
  from read code paths.
- **SC-004**: A complete invoice draft creation cycle (trigger → proposal in
  `Pending_Approval/` → human approval → execution in Odoo → confirmation in
  `Accounting/` → file in `Done/`) completes end-to-end without manual
  intervention beyond the human approval step.
- **SC-005**: 100% of Odoo write proposals contain the required frontmatter
  fields (`type`, `action_type`, `status`, `source_path`, `dest_path`) —
  confirmed by `vault_audit.py` boundary scan reporting zero violations on
  `Pending_Approval/odoo/`.
- **SC-006**: Connection failures are handled gracefully — no uncaught
  exception reaches the orchestrator; every failure produces a log entry and
  routes a triage item to `vault/Needs_Action/odoo/`.

---

## Out of Scope

The following are explicitly excluded from Phase 2:

- Odoo CRM, sales orders, or HR modules — accounting only
- Posting (confirming) invoices directly — draft creation only in Phase 2
- Sending invoices by email from Odoo — Phase 3+ scope
- Social media publishing (Phase 3)
- CEO briefing generation (Phase 4)
- Reliability and autonomous completion improvements (Phase 5)
- Any new watcher or Gmail/WhatsApp changes
- Changes to SpecifyPlus internal folders (`.specify/`, `.claude/`)
- Any implementation work not covered by an approved Phase 2 spec

---

## Dependencies and Assumptions

**Dependencies**:

- Gold Phase 1 complete (vault routing, boundary audit, MCP contracts, logger
  fix, Silver regression confirmed) — confirmed complete 2026-04-15.
- Constitution v3.0.0 ratified — confirmed 2026-04-14.
- Odoo Community instance accessible with XML-RPC or JSON-RPC API enabled.
- `vault/` directory initialized with canonical subdirectory structure.
- `vault_audit.py` available for boundary validation (`src/sentinel/vault_audit.py`).

**Assumptions**:

- Odoo connection uses the standard XML-RPC or JSON-RPC API (Odoo Community
  default) — connection protocol will be confirmed during planning.
- "Draft-only" means creating Odoo records in draft state; posting/confirming
  is explicitly excluded from Phase 2.
- Reconciliation proposals are invoice-payment match suggestions — the AI
  Employee reads open items and proposes pairings; the human approves pairings
  before reconciliation is applied in Odoo.
- The reconciliation scan is triggered on-demand or on a configurable schedule
  — not continuously.
- `vault/Accounting/` stores confirmation summaries after execution; it does
  not mirror the full Odoo database.
- Odoo credentials (`ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`) are
  stored in `.env` — consistent with Constitution Principle VII.
- The orchestrator detects files moved to `vault/Approved/odoo/` via the same
  filesystem watcher mechanism used for Silver-tier inbox routing.
