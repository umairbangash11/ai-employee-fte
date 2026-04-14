# Feature Specification: LinkedIn Publish Execution

**Feature Branch**: `006-linkedin-publish`
**Created**: 2026-03-12
**Status**: Draft
**Phase**: 4 — LinkedIn Publish Execution
**Prerequisite**: 005-hitl-approval (complete)

---

## Overview

This specification defines the execution layer that publishes approved LinkedIn posts from the vault. It bridges the gap between the existing HITL approval workflow (which creates approved files in `/Approved/linkedin/`) and actual publication to LinkedIn.

**Confirmed Baseline** (already implemented):
- HITL approval workflow exists (`src/hitl_approval/`)
- LinkedIn approval request generation exists (`request_linkedin_post_approval()`)
- Approved and Rejected folder monitoring exists (`ApprovalWatcher`)
- Approved LinkedIn post files land in `/Approved/linkedin/`

**Gap Being Addressed**:
- No execution path currently processes approved LinkedIn files
- Approved files sit idle in `/Approved/linkedin/` indefinitely
- No audit trail for successful or failed publish attempts

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish Approved LinkedIn Post (Priority: P1)

As a user who has approved a LinkedIn post by moving it to `/Approved/linkedin/`, I want the system to automatically detect and publish that post to LinkedIn, so that I don't have to manually copy-paste content to the LinkedIn interface.

**Why this priority**: This is the core value proposition — automating the final step of post publication after human approval.

**Independent Test**: Can be fully tested by placing a valid approved LinkedIn post file in `/Approved/linkedin/`, running the executor, and verifying the post appears on LinkedIn with the correct content.

**Acceptance Scenarios**:

1. **Given** a valid approved LinkedIn post file in `/Approved/linkedin/`, **When** the executor runs, **Then** the post is published to LinkedIn with the exact content from the file.

2. **Given** a successfully published post, **When** publication completes, **Then** the file is moved to `/Done/linkedin/` with `status: published` in frontmatter.

3. **Given** a successfully published post, **When** publication completes, **Then** an audit log entry is written to `/Logs/linkedin/` with timestamp, file path, and LinkedIn post URL (if available).

---

### User Story 2 - Handle Publication Failure (Priority: P1)

As a user, when a LinkedIn post fails to publish (network error, auth failure, rate limit), I want the system to preserve the approved file and log the failure, so that I can retry or investigate without losing the approved content.

**Why this priority**: Failure handling is critical to prevent silent data loss of approved content.

**Independent Test**: Can be tested by simulating a network failure during publish and verifying the file remains in `/Approved/linkedin/` with failure details logged.

**Acceptance Scenarios**:

1. **Given** an approved LinkedIn post file and a transient failure (network timeout), **When** publication fails after retry attempts, **Then** the file remains in `/Approved/linkedin/` with `status: failed` and `last_error` added to frontmatter.

2. **Given** a failed publication attempt, **When** failure is logged, **Then** the log entry includes: timestamp, file path, error type, error message, and retry count.

3. **Given** a recoverable failure, **When** the executor runs again later, **Then** it retries the failed file (respecting retry limits).

---

### User Story 3 - Detect Approved Files (Priority: P1)

As the system, I need to detect when files appear in `/Approved/linkedin/` either via real-time watching or periodic polling, so that approved posts are processed promptly.

**Why this priority**: Detection is the trigger for the entire execution flow.

**Independent Test**: Can be tested by placing a file in `/Approved/linkedin/` and verifying the executor detects and processes it within the expected timeframe.

**Acceptance Scenarios**:

1. **Given** a file is moved to `/Approved/linkedin/`, **When** the executor is running, **Then** the file is detected within 30 seconds.

2. **Given** multiple files in `/Approved/linkedin/`, **When** the executor runs, **Then** files are processed in chronological order (oldest first).

3. **Given** a file with invalid frontmatter in `/Approved/linkedin/`, **When** detected, **Then** the file is moved to `/Needs_Action/linkedin/` with an error note.

---

### User Story 4 - CLI Manual Trigger (Priority: P2)

As a user, I want to manually trigger publication of pending approved posts via CLI, so that I can control exactly when posts go live.

**Why this priority**: Provides user control and debugging capability; not required for core automated flow.

**Independent Test**: Can be tested by running the CLI command and verifying it processes approved files.

**Acceptance Scenarios**:

1. **Given** approved LinkedIn posts in `/Approved/linkedin/`, **When** I run `linkedin-publish run`, **Then** all approved posts are processed and results are displayed.

2. **Given** no approved posts, **When** I run `linkedin-publish run`, **Then** a message indicates "No approved posts to publish".

3. **Given** approved posts, **When** I run `linkedin-publish list`, **Then** I see a list of pending approved posts with their creation dates.

---

### User Story 5 - Move to Done After Success (Priority: P1)

As the system, after successfully publishing a LinkedIn post, I must move the file to `/Done/linkedin/` to prevent re-publication and maintain an audit trail.

**Why this priority**: Essential for idempotency and preventing duplicate posts.

**Independent Test**: Can be tested by publishing a post and verifying the file no longer exists in `/Approved/linkedin/` but exists in `/Done/linkedin/`.

**Acceptance Scenarios**:

1. **Given** a post is published successfully, **When** the executor completes, **Then** the original file is moved from `/Approved/linkedin/` to `/Done/linkedin/`.

2. **Given** a file moved to `/Done/linkedin/`, **When** the executor runs again, **Then** the file is not reprocessed.

3. **Given** a file in `/Done/linkedin/`, **Then** the file contains updated frontmatter with `status: published`, `published_at`, and optionally `linkedin_post_url`.

---

### Edge Cases

- What happens when `/Done/linkedin/` directory doesn't exist? System creates it automatically.
- What happens when a file has malformed YAML frontmatter? File is moved to `/Needs_Action/linkedin/` with error details.
- What happens when LinkedIn auth token is expired? Auth failure is logged, files are not processed, user is alerted via log.
- What happens when a file is modified while being processed? File is skipped with log entry, retried on next cycle.
- What happens when the same post content is approved twice (duplicate)? Content hash deduplication; duplicate is skipped and logged.
- What happens when `/Approved/linkedin/` contains non-markdown files? Non-`.md` files are ignored silently.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect files in `/Approved/linkedin/` within 30 seconds of placement (via watching or polling).

- **FR-002**: System MUST validate frontmatter schema before attempting publication.

- **FR-003**: System MUST publish post content to LinkedIn using browser automation (Playwright) as the execution method.

- **FR-004**: System MUST move successfully published files to `/Done/linkedin/` immediately after publication.

- **FR-005**: System MUST write an audit log entry to `/Logs/linkedin/` for every publish attempt (success or failure).

- **FR-006**: System MUST update file frontmatter with publication status (`published`, `failed`) and timestamp.

- **FR-007**: System MUST preserve failed files in `/Approved/linkedin/` with error metadata appended to frontmatter.

- **FR-008**: System MUST retry transient failures up to 3 times following the Ralph Wiggum Loop pattern (Constitution Principle V).

- **FR-009**: System MUST move files with invalid frontmatter or unrecoverable errors to `/Needs_Action/linkedin/`.

- **FR-010**: System MUST NOT process files in `/Pending_Approval/linkedin/` — only `/Approved/linkedin/`.

- **FR-011**: System MUST NOT process the same file twice (idempotency via tracking processed file hashes).

- **FR-012**: System MUST provide a CLI with commands: `run` (process approved), `list` (show pending), `status` (show last run stats).

- **FR-013**: System MUST create `/Done/linkedin/` directory if it does not exist.

### Input Schema: Approved LinkedIn Post File

The executor expects files in `/Approved/linkedin/` with this structure:

**YAML Frontmatter (required fields)**:

```yaml
---
type: approval_request
action_type: publish_linkedin_post
status: pending
created_at: "2026-03-12T14:30:00Z"
created_by: orchestrator

target:
  platform: linkedin
  post_type: text

source:
  type: task
  path: "[[Needs_Action/tasks/some-task.md]]"

expected_outcome: "LinkedIn post published"
rollback_strategy: "Delete post manually from LinkedIn"

tags: [linkedin, post]
---
```

**Markdown Body (required)**:

The executor extracts post content from the body section labeled `## Content Preview` or uses the entire body after frontmatter if no section header exists.

### Output Schema: Published File (in `/Done/linkedin/`)

After successful publication, frontmatter is updated:

```yaml
---
type: approval_request
action_type: publish_linkedin_post
status: published
created_at: "2026-03-12T14:30:00Z"
published_at: "2026-03-12T15:00:00Z"
created_by: orchestrator
executed_by: linkedin_publisher

target:
  platform: linkedin
  post_type: text

source:
  type: task
  path: "[[Needs_Action/tasks/some-task.md]]"

linkedin_post_url: "https://www.linkedin.com/feed/update/urn:li:share:123456789"
execution_log: "[[Logs/linkedin/20260312-150000_publish.log]]"

tags: [linkedin, post, published]
---
```

### Key Entities

- **ApprovedPost**: Represents a file in `/Approved/linkedin/` ready for publication. Contains: file_path, content, frontmatter, created_at.
- **PublishResult**: Outcome of a publish attempt. Contains: success (bool), post_url (optional), error (optional), timestamp.
- **ExecutionLog**: Audit entry for publish attempts. Contains: timestamp, file_path, action, result, error_details.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Approved LinkedIn posts are published within 5 minutes of file detection (excluding retry delays).

- **SC-002**: 100% of successfully published posts are moved to `/Done/linkedin/` without manual intervention.

- **SC-003**: 100% of publish attempts (success or failure) produce an audit log entry in `/Logs/linkedin/`.

- **SC-004**: Failed posts remain recoverable in `/Approved/linkedin/` with error metadata; zero silent data loss.

- **SC-005**: System correctly refuses to process files from `/Pending_Approval/linkedin/` (safety boundary).

- **SC-006**: Duplicate content detection prevents re-publishing identical posts (within 24-hour window).

- **SC-007**: System handles LinkedIn authentication gracefully — auth failures are logged and user is notified; no crash or infinite retry.

---

## Scope Boundaries

### In Scope

- Detection of approved LinkedIn post files in `/Approved/linkedin/`
- Publication via Playwright browser automation to LinkedIn Web
- Audit logging to `/Logs/linkedin/`
- File movement to `/Done/linkedin/` on success
- Failure preservation with retry capability
- CLI for manual trigger and status
- Basic text post publication only

### Out of Scope (Non-Goals)

- **No LinkedIn API integration** — Playwright browser automation only (consistent with Silver Tier architecture)
- **No article/document posts** — Text posts only in this phase
- **No image/video attachments** — Plain text content only
- **No scheduled posting** — Immediate publication only
- **No post analytics retrieval** — Publish and move on
- **No multi-account support** — Single LinkedIn account per installation
- **No approval workflow modifications** — HITL system is unchanged (005-hitl-approval)
- **No WhatsApp, email, or other platform publishing** — LinkedIn only
- **No rollback/undo automation** — Rollback is manual per approval file instructions
- **No mobile app posting** — Desktop browser automation only

---

## Assumptions

1. User has a LinkedIn account and can log in via browser.
2. Playwright is already installed and configured for browser automation (Silver Tier dependency).
3. LinkedIn session persistence is handled via `.watcher-state/linkedin/` cookies (similar to WhatsApp watcher pattern).
4. Initial LinkedIn authentication is performed manually in headed mode; subsequent runs use headless mode with stored session.
5. LinkedIn's web interface structure is stable enough for Playwright selectors (fragile assumption; may require maintenance).
6. `/Approved/linkedin/` directory exists (created by HITL system).
7. The vault path is configured via `VAULT_PATH` environment variable or CLI argument.

---

## Dependencies

- **005-hitl-approval**: Provides approved files in `/Approved/linkedin/`
- **Playwright (Python)**: Browser automation for LinkedIn Web
- **watchdog >=6.0**: File system watching (already a project dependency)
- **python-dotenv**: Environment configuration
- **pyyaml**: Frontmatter parsing

---

## Security Constraints

- LinkedIn session cookies MUST be stored in `.watcher-state/linkedin/` (excluded from git via `.gitignore`)
- No LinkedIn credentials (username/password) in code or `.env`
- Playwright runs headless by default; headed mode only for initial auth setup
- All publish attempts logged for audit trail

---

## Constitution Compliance

| Principle | Compliance |
|-----------|------------|
| I. Local-First | PASS — All processing local; LinkedIn API call is the only external interaction |
| II. Canonical Folders | PASS — Uses `/Approved/`, `/Done/`, `/Logs/`, `/Needs_Action/` |
| III. Tiered Scope | PASS — Silver Tier authorizes browser automation |
| IV. Safety-First | PASS — Executes only from `/Approved/`, never from `/Pending_Approval/` |
| V. Ralph Wiggum Loop | PASS — 3 retries on transient failure, then `/Needs_Action/` |
| VI. Silver Tier Autonomy | PASS — Human-approved posts only; no autonomous publishing |
| VII. Phased Development | PASS — Scoped to Phase 4 LinkedIn execution only |
| VIII. Gmail API Migration | N/A — Not applicable to LinkedIn |

---

## Acceptance Criteria Summary

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-01 | Approved file detected within 30 seconds | Automated test with timer |
| AC-02 | Post published to LinkedIn with correct content | Manual verification + screenshot |
| AC-03 | File moved to `/Done/linkedin/` after success | Automated test |
| AC-04 | Frontmatter updated with `published_at` | File inspection |
| AC-05 | Audit log written for every attempt | Log file inspection |
| AC-06 | Failed file remains in `/Approved/linkedin/` | Automated test |
| AC-07 | Failed file has error metadata in frontmatter | File inspection |
| AC-08 | Invalid frontmatter file moved to `/Needs_Action/` | Automated test |
| AC-09 | CLI `list` shows pending approved posts | CLI execution |
| AC-10 | CLI `run` processes approved posts | CLI execution + LinkedIn verification |
| AC-11 | Files in `/Pending_Approval/linkedin/` are ignored | Automated test |
| AC-12 | Duplicate content is not re-published | Automated test |

---

**End of Specification**

**Next Step**: `/sp.clarify` to resolve any ambiguities, or `/sp.plan` to generate implementation architecture.
