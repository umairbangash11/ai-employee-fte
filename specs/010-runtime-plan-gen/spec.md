# Feature Specification: Runtime Plan Generation

**Feature Branch**: `010-runtime-plan-gen`
**Created**: 2026-04-14
**Status**: Draft
**Input**: User description: "Implement runtime Plan.md generation in the existing AI Employee project to satisfy the remaining Silver-tier requirement."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Plan Created for Actionable Email (Priority: P1)

When the orchestrator processes an incoming email and determines it requires a reply, it generates a structured plan file in the vault. The plan captures what the AI reasoned, what action is proposed, and what the human must approve before any reply is sent.

**Why this priority**: This is the direct Silver-tier gap. The reasoning loop must produce Plan.md files at runtime. Without this, Silver compliance is incomplete regardless of other components.

**Independent Test**: Drop a Markdown email file into the vault's Inbox. Let the orchestrator process it. Confirm a plan file appears in `Needs_Action/plans/` with all required fields populated before the draft reply is written.

**Acceptance Scenarios**:

1. **Given** an email file lands in Inbox, **When** the orchestrator classifies it as needing a reply, **Then** a plan file is created in `Needs_Action/plans/` containing: title, objective, source context, at least one action step checkbox, approval requirement, status `pending`, and a created timestamp
2. **Given** the plan file is created, **When** a human inspects it, **Then** it is readable as standard Obsidian-compatible Markdown with YAML frontmatter
3. **Given** the plan file already exists for the same email (duplicate processing), **When** the orchestrator runs again, **Then** a deduplicated filename is used and no existing plan is overwritten

---

### User Story 2 — Plan Skipped for Non-Actionable Email (Priority: P2)

When the orchestrator determines an email does not require a reply (newsletter, automated notification, etc.), no plan file is generated. The vault is not cluttered with plans for items that need no action.

**Why this priority**: Precision matters — plan files should only exist for items that have a decision to make. Generating plans for every email would defeat the signal value of the `Needs_Action/plans/` folder.

**Independent Test**: Drop a newsletter-style email into Inbox. Confirm the orchestrator processes it without creating any file in `Needs_Action/plans/`.

**Acceptance Scenarios**:

1. **Given** an email is classified as not requiring a reply, **When** the orchestrator processes it, **Then** no plan file is created in `Needs_Action/plans/`
2. **Given** the orchestrator encounters a classification failure after all retries, **When** it falls back to routing for human review, **Then** a plan file IS created with `status: error` and action step "Human review required"

---

### User Story 3 — Plan Is Verifiable Without Running the Full System (Priority: P2)

A developer or tester can invoke the plan generation logic directly with a sample email and verify the output plan file without starting the full orchestrator watch loop.

**Why this priority**: Testability is a Silver compliance requirement. The plan generation must be independently callable and verifiable through a direct function call or CLI invocation, not just via the long-running watcher.

**Independent Test**: Call the plan-generation function directly with a known email content string and a temp vault path. Assert the resulting file exists with correct fields. No OpenAI call is needed for this test.

**Acceptance Scenarios**:

1. **Given** a classification result dict and email metadata, **When** the plan writer function is called directly, **Then** the plan file is created at the expected path with all required fields
2. **Given** an invalid vault path, **When** the plan writer is called, **Then** it raises a clear error rather than silently failing

---

### Edge Cases

- What if the vault's `Needs_Action/plans/` directory does not exist? It must be created automatically before writing.
- What if the email subject contains characters unsafe for filenames (slashes, colons, null bytes)? Sanitize to a safe slug.
- What if the plan file cannot be written (permissions, disk full)? Log the error to `Logs/` and continue — plan write failure must not block the email triage flow.
- What if the classification result contains no action steps? Include a default step: "Review and respond to email."
- What if `created_at` clock is unavailable? Use a fallback of "unknown" — this must not crash the system.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orchestrator MUST generate a plan file in `Needs_Action/plans/` for every email classified as requiring a reply
- **FR-002**: The plan file MUST contain all seven required fields: title, objective, source context, action steps (as Markdown checkboxes), approval requirement, status, and created timestamp
- **FR-003**: Plan files MUST be valid Obsidian-compatible Markdown with YAML frontmatter containing at minimum: `type`, `status`, `created_at`, `source_file`, `requires_approval`
- **FR-004**: The plan file MUST be written BEFORE the draft reply is written and BEFORE the source email is moved — preserving the existing safety-first ordering
- **FR-005**: The plan generation function MUST be callable independently from the rest of the orchestrator (i.e., it takes a classification result and email metadata as inputs and returns the plan file path)
- **FR-006**: The `Needs_Action/plans/` directory MUST be created automatically if it does not exist
- **FR-007**: Plan filenames MUST be deduplicated if a file with the same name already exists (using the existing deduplication helper)
- **FR-008**: Plan file creation failure MUST be caught, logged to `Logs/`, and MUST NOT halt the email triage flow
- **FR-009**: No plan file MUST be created for emails classified as not requiring a reply
- **FR-010**: The plan file for a fallback/error classification MUST have `status: error` and action step "Human review required"

### Key Entities

- **RuntimePlan**: A Markdown file written to `Needs_Action/plans/` at the moment the orchestrator decides an email is actionable. Contains structured reasoning output from the triage step.
- **PlanMetadata** (YAML frontmatter): Machine-readable fields — `type`, `status`, `created_at`, `source_file`, `requires_approval`, `email_sender`, `email_subject`.
- **ActionStep**: A single checkbox line in the plan body representing one discrete task the system or human must complete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every actionable email processed by the orchestrator produces exactly one plan file in `Needs_Action/plans/` — zero missed plans for reply-needed emails
- **SC-002**: Every plan file contains all seven required fields — zero plan files with missing fields
- **SC-003**: Plan file creation completes in under 500ms for any input size typical of email content
- **SC-004**: The plan writer function passes its unit tests when called with sample inputs — no dependency on the running orchestrator or OpenAI API required for test execution
- **SC-005**: The existing email triage flow (classification → move to drafts → generate draft reply) continues to work identically after this change — zero regressions

## Assumptions

- The plan file is written to `Needs_Action/plans/` (a new subdirectory within the existing canonical `Needs_Action/` folder). This does not violate Constitution Principle II, which permits new subdirectories when justified by a spec.
- The plan generation logic lives in a new standalone function (or small module) called from `brain.py`. No new top-level module is needed.
- The existing `sentinel.planner.write_execution_plan()` (which writes to `/Approved/`) is NOT modified — it serves Constitution Principle IV (safety-first file moves). The new plan writer serves the Silver-tier reasoning-loop requirement and is separate.
- The action steps in the plan are derived from the AI classification result (e.g., "Draft a reply to [sender]", "Move email to Needs_Action/drafts/"). They are not re-generated with a second AI call.
- `requires_approval` is always `true` for reply-needed emails (per Constitution Principle VI — no external action without HITL).
- The plan writer does not send any data externally. All output is local vault files.

## Out of Scope

- No changes to the existing `write_execution_plan()` function in `sentinel/planner.py`
- No new top-level CLI commands or entry points
- No Gold-tier features
- No changes to SpecifyPlus internal folders
- No changes to any module other than `src/orchestrator/brain.py` (and optionally a new small helper alongside it)
- No second AI/LLM call to generate the plan — steps are derived from the classification result already obtained
- No plan file for non-actionable emails (newsletters, notifications, receipts)
