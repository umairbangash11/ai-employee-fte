# Feature Specification: Gold Phase 3 — Social Media Expansion

**Feature Branch**: `013-social-media-expansion`
**Created**: 2026-04-15
**Status**: Draft
**Phase**: Gold Phase 3 (of 5)
**Constitution**: v3.0.0
**Prerequisite**: Gold Phase 2 complete (vault patterns, approval gate, MCP foundation confirmed)

## Overview

Implement the social media publishing expansion layer for the AI Employee. This phase
extends the existing vault-based draft-and-approve publishing model — already proven
with LinkedIn (Silver Tier) and the Facebook executor (Silver Tier) — to cover three
fully approval-gated publishing flows: **Facebook**, **Instagram**, and **X** (formerly
Twitter).

Every post on every platform follows the same lifecycle: draft written to
`Pending_Approval/<platform>/` → human moves to `Approved/<platform>/` → executor
detects the file and publishes → `Done/<platform>/` on success or
`Needs_Action/<platform>/` on failure. No post reaches any social platform without
explicit human authorization at the approval gate. The AI Employee never self-approves.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Facebook Draft-First Publishing (Priority: P1)

As a human operator, I want the AI Employee to prepare Facebook post drafts — with
content, target audience, and reference context — and route them to
`vault/Pending_Approval/facebook/` for my review before anything reaches Facebook, so
that no post is published without my explicit sign-off.

**Why this priority**: Facebook is the highest-reach platform in scope and the executor
layer already exists. Completing the draft-to-approval wiring closes the full loop and
establishes the pattern the other platforms follow.

**Independent Test**: Trigger Facebook draft creation with fixture content. Verify the
draft appears in `vault/Pending_Approval/facebook/` with `type: pending_action`,
`action_type: publish_post`, `platform: facebook`, and `status: awaiting_approval`.
Move the file manually to `vault/Approved/facebook/`. Verify the executor detects the
file, publishes to Facebook, and moves to `vault/Done/facebook/` with a log entry.

**Acceptance Scenarios**:

1. **Given** a social post request (content, optional image, optional audience) reaches
   the orchestrator, **When** the Facebook draft module runs, **Then** a draft proposal
   is written to `vault/Pending_Approval/facebook/<slug>.md` with `type: pending_action`,
   `action_type: publish_post`, `platform: facebook`, and `status: awaiting_approval` —
   nothing is sent to Facebook.
2. **Given** a proposal file in `vault/Approved/facebook/`, **When** the executor detects
   it, **Then** the post is published to Facebook with the exact content from the file,
   a log entry is written to `vault/Logs/` with all 6 required fields, and the file
   is moved to `vault/Done/facebook/`.
3. **Given** a successfully published Facebook post, **When** the operation completes,
   **Then** the moved file in `vault/Done/facebook/` contains `status: published` and
   the post URL (if retrievable) in its frontmatter.
4. **Given** a Facebook publish attempt fails after 3 retries (Ralph Wiggum Loop), **When**
   retries are exhausted, **Then** the file is moved from `vault/Approved/facebook/` to
   `vault/Needs_Action/facebook/` and a failure log entry is written.
5. **Given** the system has written a Facebook proposal, **When** any automated process
   attempts to self-approve (move from `Pending_Approval` to `Approved` autonomously),
   **Then** the action is blocked and a boundary violation is logged.

---

### User Story 2 — Instagram Draft-First Publishing (Priority: P1)

As a human operator, I want the AI Employee to prepare Instagram post drafts — including
caption, optional image path, and optional hashtags — and route them to
`vault/Pending_Approval/instagram/` for my review before anything is sent to Instagram,
so that no post goes live without my explicit approval.

**Why this priority**: Instagram is the second platform in this phase and mirrors the
Facebook pattern exactly. Completing it alongside Facebook delivers two platform flows
from a single implementation pass, maximising reuse of the shared vault pattern.

**Independent Test**: Trigger Instagram draft creation with fixture caption and optional
image path. Verify the draft appears in `vault/Pending_Approval/instagram/` with the
required frontmatter fields. Move to `vault/Approved/instagram/`. Verify the executor
detects the file, publishes to Instagram, and moves to `vault/Done/instagram/` with a
log entry.

**Acceptance Scenarios**:

1. **Given** an Instagram post request (caption, optional image path, optional hashtags)
   reaches the orchestrator, **When** the Instagram draft module runs, **Then** a proposal
   is written to `vault/Pending_Approval/instagram/<slug>.md` with `type: pending_action`,
   `action_type: publish_post`, `platform: instagram`, `status: awaiting_approval` —
   nothing is posted to Instagram.
2. **Given** a proposal in `vault/Approved/instagram/`, **When** the executor detects it,
   **Then** the caption and image (if provided) are published to Instagram, the log entry
   records the outcome, and the file is moved to `vault/Done/instagram/`.
3. **Given** a post requires an image but the image path in the proposal is invalid or
   missing, **When** the executor processes the file, **Then** the post is not attempted,
   the file is moved to `vault/Needs_Action/instagram/`, and the failure is logged with
   `details: missing or invalid image path`.
4. **Given** an Instagram session has expired or requires re-authentication, **When** the
   executor attempts to publish, **Then** the session error is logged, the file is left
   unprocessed for manual retry, and the operator is alerted via `vault/Needs_Action/instagram/`.
5. **Given** an Instagram publish attempt fails after 3 retries, **When** retries are
   exhausted, **Then** the file is moved to `vault/Needs_Action/instagram/` with the
   failure reason in the frontmatter.

---

### User Story 3 — X Draft-First Publishing (Priority: P1)

As a human operator, I want the AI Employee to prepare X post drafts — with content
text, optional media, and optional thread context — and route them to
`vault/Pending_Approval/x/` for my review before anything is sent to X, so that no
post goes live without my explicit approval.

**Why this priority**: X completes the three-platform scope for Phase 3. Its character
limit and threading mechanics make the draft stage especially valuable — the operator
reviews content length and thread structure before approving.

**Independent Test**: Trigger X draft creation with fixture content (under 280 characters).
Verify the draft appears in `vault/Pending_Approval/x/` with the required frontmatter.
Move to `vault/Approved/x/`. Verify the executor detects the file, publishes to X, and
moves to `vault/Done/x/` with a log entry.

**Acceptance Scenarios**:

1. **Given** an X post request (content text, optional media, optional reply-to reference)
   reaches the orchestrator, **When** the X draft module runs, **Then** a proposal is
   written to `vault/Pending_Approval/x/<slug>.md` with `type: pending_action`,
   `action_type: publish_post`, `platform: x`, `status: awaiting_approval` — nothing is
   posted to X.
2. **Given** a proposal in `vault/Approved/x/`, **When** the executor detects it, **Then**
   the post text (and media if present) are published to X, the log entry records the
   outcome, and the file is moved to `vault/Done/x/`.
3. **Given** a post draft where the text exceeds 280 characters, **When** the draft module
   creates the proposal, **Then** the character count is recorded as `char_count: N` in
   frontmatter and a `warning: exceeds_char_limit` field is added — the draft is still
   written for human review and the operator decides whether to edit before approving.
4. **Given** an X session has expired or requires re-authentication, **When** the executor
   attempts to publish, **Then** the session error is logged, the file is left unprocessed,
   and the operator is alerted via `vault/Needs_Action/x/`.
5. **Given** an X publish attempt fails after 3 retries, **When** retries are exhausted,
   **Then** the file is moved to `vault/Needs_Action/x/` with the failure reason in the
   frontmatter.

---

### User Story 4 — Shared Social Post Vault Lifecycle (Priority: P2)

As a human operator, I want every social post produced by the AI Employee — drafts,
approvals, confirmations, and logs — to land in the correct canonical vault directory
with complete YAML frontmatter, so that I can inspect the state of any social post
action across all three platforms at any point in its lifecycle.

**Why this priority**: Lifecycle consistency across three platforms is the audit
foundation. It ensures all flows are inspectable from a single vault root and that
`vault_audit.py` reports zero violations after each platform publish.

**Independent Test**: Run one complete draft-to-done cycle for each platform and inspect
`vault/Pending_Approval/<platform>/`, `vault/Done/<platform>/`, and `vault/Logs/` —
verify all files have correct `type`, `platform`, `action_type`, and required frontmatter
fields. Run `vault_audit.py` and confirm zero boundary violations.

**Acceptance Scenarios**:

1. **Given** any social post file is created, **When** the write operation completes,
   **Then** the YAML frontmatter contains all required fields: `type`, `platform`,
   `action_type`, `status`, `source_path`, `dest_path`, `captured_at`.
2. **Given** a vault boundary audit runs, **When** it scans `Pending_Approval/facebook/`,
   `Pending_Approval/instagram/`, and `Pending_Approval/x/`, **Then** every file has
   `type: pending_action` — zero boundary violations reported.
3. **Given** a complete lifecycle for any platform, **When** the vault is inspected,
   **Then** each lifecycle stage is represented: `Pending_Approval/` (awaiting sign-off),
   `Approved/` (authorized), `Done/` (published), and `Logs/` (audit trail).

---

### User Story 5 — Publisher Architecture Consistency (Priority: P3)

As a developer, I want all three platform publishers to follow the same vault-pattern
architecture established by the LinkedIn and Facebook executor implementations, so
that adding a fourth platform in a future phase requires minimal new code.

**Why this priority**: Architectural consistency is the long-term payoff. If all three
platforms share the same config, models, executor, and drafter structure, future
platform additions can be done by copying and modifying a single template.

**Independent Test**: Verify that `instagram_publisher/` and `x_publisher/` each contain
the same module set as `linkedin_publisher/` and `facebook_publisher/`. Verify that a
shared `social_drafters/` module provides `draft_post()` for each platform without
duplicating frontmatter logic.

**Acceptance Scenarios**:

1. **Given** a new platform publisher module, **When** it is reviewed, **Then** it follows
   the config → models → executor pattern from the existing LinkedIn and Facebook
   implementations with no ad-hoc vault writes outside the shared drafter.
2. **Given** the social post drafter modules for all three platforms, **When** each is
   examined, **Then** frontmatter generation, slug construction, and vault directory
   resolution are handled by a single shared function — not duplicated per platform.
3. **Given** the executor modules for all three platforms, **When** reviewed, **Then**
   the Ralph Wiggum Loop, vault file lifecycle (Approved → Done/Needs_Action), and audit
   log writing are consistent across Facebook, Instagram, and X.

---

### Edge Cases

- Post content is empty or blank → draft module rejects the request, writes an error
  log to `vault/Logs/` with `outcome: failure`, and does not create a `Pending_Approval`
  file.
- Duplicate draft written (same platform + content slug) → drafter appends a counter
  suffix; never silently overwrites an existing proposal.
- File moved to both `Approved/` and rejected simultaneously (race condition) → executor
  acts on whichever it detects first; logs a conflict warning for any duplicate.
- Platform session expired mid-publish → executor catches the auth error, logs
  `outcome: failure`, retries once after session refresh attempt, routes to
  `Needs_Action/<platform>/` if re-auth fails.
- Image path in Instagram/X proposal points to a non-existent file → executor rejects
  execution, moves file to `Needs_Action/<platform>/` with `details: image not found`.
- Publish succeeds but post URL cannot be extracted → `Done/` file records `post_url: null`
  and the log captures the success without URL.
- Missing platform credentials in `.env` at executor startup → log error with
  `outcome: failure`, skip all operations for that platform, do NOT crash the orchestrator.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST write every Facebook, Instagram, and X post draft to
  `vault/Pending_Approval/<platform>/<slug>.md` with `type: pending_action`,
  `action_type: publish_post`, `platform: <platform>`, and `status: awaiting_approval`
  before any content is submitted to a social platform.
- **FR-002**: The system MUST detect files moved to `vault/Approved/<platform>/` and
  execute the corresponding social publish action — no publish is triggered by any
  other mechanism.
- **FR-003**: The system MUST NOT self-approve any post proposal — moving a file from
  `Pending_Approval/` to `Approved/` is a human-only action.
- **FR-004**: After successful publication, the system MUST move the approved file from
  `vault/Approved/<platform>/` to `vault/Done/<platform>/` and update the frontmatter
  with `status: published` and `post_url` (if retrievable).
- **FR-005**: The system MUST follow the Ralph Wiggum Loop (3 attempts with back-off)
  for all platform publish failures before routing to `vault/Needs_Action/<platform>/`.
- **FR-006**: Every social publishing operation MUST produce a log entry in
  `vault/Logs/` containing all six required fields: `timestamp`, `action_type`,
  `source_path`, `dest_path`, `outcome`, `details`.
- **FR-007**: The system MUST create all missing canonical vault subdirectories
  (`Pending_Approval/<platform>/`, `Approved/<platform>/`, `Done/<platform>/`,
  `Needs_Action/<platform>/`) at executor startup — no manual directory creation required.
- **FR-008**: Any path that would write a vault file outside the configured vault root
  MUST be rejected and logged as a boundary violation.
- **FR-009**: Platform session state (Playwright storage) MUST be stored in
  `.watcher-state/<platform>/` and MUST NOT be committed to source control.
- **FR-010**: Missing platform credentials or a failed session at startup MUST be logged
  with `outcome: failure` and skipped gracefully — the orchestrator MUST NOT crash due to
  a single platform's credential failure.
- **FR-011**: The Instagram publisher and X publisher MUST follow the same
  config → models → executor module structure as `linkedin_publisher` and
  `facebook_publisher`.
- **FR-012**: Frontmatter generation, slug construction, and vault directory resolution
  for social post proposals MUST be handled by a shared `social_drafters` module —
  not duplicated per platform.
- **FR-013**: The Instagram executor MUST validate that any referenced image path exists
  before attempting to publish. A missing image path MUST route the file to
  `vault/Needs_Action/instagram/` without contacting Instagram.
- **FR-014**: The X drafter MUST record `char_count: N` in the proposal frontmatter.
  Content exceeding 280 characters MUST also set `warning: exceeds_char_limit` — the
  draft is still created for human review.

### Key Entities

- **SocialPostDraft**: A pending social post in `vault/Pending_Approval/<platform>/`.
  Required frontmatter: `type: pending_action`, `platform`, `action_type: publish_post`,
  `status: awaiting_approval`, `source_path`, `dest_path`, `captured_at`,
  `content_preview` (first 100 chars).

- **SocialApprovedPost**: An authorized post in `vault/Approved/<platform>/`. Same schema
  as SocialPostDraft; executor reads `platform`, `content`, and optional `image_path` /
  `char_count` to execute the publish.

- **SocialPublishRecord**: A completion record in `vault/Done/<platform>/`. Contains:
  `status: published`, `post_url` (or null), `published_at` (ISO 8601), `platform`.

- **SocialLogEntry**: A log record in `vault/Logs/` after every publishing operation.
  Required fields: `timestamp`, `action_type`, `source_path`, `dest_path`, `outcome`,
  `details` (includes platform, post URL or error).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of social post publish operations are preceded by a proposal in
  `vault/Pending_Approval/<platform>/` — zero direct platform publishes without a
  corresponding proposal file.
- **SC-002**: 100% of log entries produced during a complete social post cycle contain
  all six required fields — no partial log entries across any of the three platforms.
- **SC-003**: A complete Facebook, Instagram, and X post lifecycle (draft → proposal →
  approval → publish → done) completes end-to-end without manual intervention beyond
  the human approval step.
- **SC-004**: All three platform flows share the `social_drafters` shared module —
  zero duplicated frontmatter generation logic confirmed by code review.
- **SC-005**: `vault_audit.py` boundary scan reports zero violations across
  `Pending_Approval/facebook/`, `Pending_Approval/instagram/`, and `Pending_Approval/x/`.
- **SC-006**: Platform credential failures are handled gracefully — no uncaught exception
  reaches the orchestrator; every failure produces a log entry and routes a triage item
  to `vault/Needs_Action/<platform>/`.

---

## Out of Scope

The following are explicitly excluded from Phase 3:

- Reading social media feeds, DMs, or comments (no monitoring in this phase)
- Scheduling posts for a future time (immediate publish only, after approval)
- Multi-image carousels for Instagram or X
- LinkedIn modifications or new LinkedIn features (Silver Tier — closed)
- WhatsApp publishing
- CEO briefing generation (Phase 4)
- Reliability and autonomous completion improvements (Phase 5)
- Broad pytest suite creation (testing handled at project end)
- Any new SpecifyPlus modifications (`.specify/`, `.claude/`)
- Any implementation work not covered by an approved Phase 3 spec

---

## Dependencies and Assumptions

**Dependencies**:

- Gold Phase 2 complete (vault writer pattern, boundary guard, audit logger confirmed) — confirmed 2026-04-15.
- Constitution v3.0.0 ratified — confirmed 2026-04-14.
- `linkedin_publisher` and `facebook_publisher` packages available as architectural reference.
- `sentinel.logger.write_log_entry` (6-field) available and tested.
- `vault_mcp/server.py` `_safe_resolve()` path guard available for reuse.
- `.watcher-state/` in `.gitignore` — Playwright session state must not be committed.
- `watchdog>=6.0` and `playwright` already installed.
- `VAULT_PATH` environment variable set.

**Assumptions**:

- Instagram and X publishing uses Playwright browser automation — consistent with
  LinkedIn and Facebook patterns. API-based publishing (Meta Graph API, X API v2)
  requires developer tokens out of scope for this phase.
- Facebook drafter is the gap to close — the `facebook_publisher` executor already
  handles `Approved/facebook/` and is reused without modification.
- X authentication uses session persistence via `.watcher-state/x/` (same as other
  platforms).
- Post images for Instagram and X are referenced by local file path in the proposal
  frontmatter — the image file must exist on the local filesystem at execution time.
- A new `src/social_drafters/` package provides the shared draft writing function used
  by all three platform drafters.
- Character limit enforcement for X is advisory at the draft stage only.
