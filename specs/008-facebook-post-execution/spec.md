# Feature Specification: Facebook Post Execution

**Feature Branch**: `008-facebook-post-execution`
**Created**: 2026-03-22
**Status**: Draft
**Phase**: Silver Tier — Facebook Publish Execution (Approval-Based)
**Prerequisite**: HITL approval workflow (complete)
**Constitution**: v2.0.0 (Principle IV: Safety-First, Principle VI: Silver Tier Autonomy)
**Input**: User description: "Define the Facebook post approval file schema, folder locations, detection mechanism, execution path for approved posts, metadata fields, success/failure behavior, and safety boundaries. Approval-based execution only — no Facebook inbox monitoring."

---

## Overview

This specification defines the execution layer that publishes approved Facebook posts from the vault. It bridges the gap between the existing HITL approval workflow (which manages approved files) and actual publication to Facebook.

**Confirmed Baseline** (already implemented):
- HITL approval workflow exists
- Vault is the system of record
- Approved and Rejected state folders exist or are supported
- The project supports approval-based action patterns (e.g., LinkedIn publisher)

**Gap Being Addressed**:
- No execution path currently processes approved Facebook post files
- Approved files would sit idle indefinitely without an executor
- No audit trail for Facebook publish attempts

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish Approved Facebook Post (Priority: P1)

As a user who has approved a Facebook post by moving it to `/Approved/facebook/`, I want the system to automatically detect and publish that post to Facebook, so that I don't have to manually copy-paste content to the Facebook interface.

**Why this priority**: This is the core value proposition — automating the final step of post publication after human approval.

**Independent Test**: Can be fully tested by placing a valid approved Facebook post file in `/Approved/facebook/`, running the executor, and verifying the post appears on Facebook with the correct content.

**Acceptance Scenarios**:

1. **Given** a valid approved Facebook post file in `/Approved/facebook/`, **When** the executor runs, **Then** the post is published to Facebook with the exact content from the file.

2. **Given** a successfully published post, **When** publication completes, **Then** the file is moved to `/Done/facebook/` with `status: published` in frontmatter.

3. **Given** a successfully published post, **When** publication completes, **Then** an audit log entry is written to `/Logs/facebook/` with timestamp, file path, and Facebook post URL (if available).

---

### User Story 2 - Handle Publication Failure (Priority: P1)

As a user, when a Facebook post fails to publish (network error, auth failure, rate limit), I want the system to preserve the approved file and log the failure, so that I can retry or investigate without losing the approved content.

**Why this priority**: Failure handling is critical to prevent silent data loss of approved content.

**Independent Test**: Can be tested by simulating a network failure during publish and verifying the file remains in `/Approved/facebook/` with failure details logged.

**Acceptance Scenarios**:

1. **Given** an approved Facebook post file and a transient failure (network timeout), **When** publication fails after retry attempts, **Then** the file remains in `/Approved/facebook/` with `status: failed` and `last_error` added to frontmatter.

2. **Given** a failed publication attempt, **When** failure is logged, **Then** the log entry includes: timestamp, file path, error type, error message, and retry count.

3. **Given** a recoverable failure, **When** the executor runs again later, **Then** it retries the failed file (respecting retry limits).

---

### User Story 3 - Detect Approved Files (Priority: P1)

As the system, I need to detect when files appear in `/Approved/facebook/` either via real-time watching or periodic polling, so that approved posts are processed promptly.

**Why this priority**: Detection is the trigger for the entire execution flow.

**Independent Test**: Can be tested by placing a file in `/Approved/facebook/` and verifying the executor detects and processes it within the expected timeframe.

**Acceptance Scenarios**:

1. **Given** a file is moved to `/Approved/facebook/`, **When** the executor is running, **Then** the file is detected within 30 seconds.

2. **Given** multiple files in `/Approved/facebook/`, **When** the executor runs, **Then** files are processed in chronological order (oldest first).

3. **Given** a file with invalid frontmatter in `/Approved/facebook/`, **When** detected, **Then** the file is moved to `/Needs_Action/facebook/` with an error note.

---

### User Story 4 - CLI Manual Trigger (Priority: P2)

As a user, I want to manually trigger publication of pending approved posts via CLI, so that I can control exactly when posts go live.

**Why this priority**: Provides user control and debugging capability; not required for core automated flow.

**Independent Test**: Can be tested by running the CLI command and verifying it processes approved files.

**Acceptance Scenarios**:

1. **Given** approved Facebook posts in `/Approved/facebook/`, **When** I run `facebook-publish run`, **Then** all approved posts are processed and results are displayed.

2. **Given** no approved posts, **When** I run `facebook-publish run`, **Then** a message indicates "No approved posts to publish".

3. **Given** approved posts, **When** I run `facebook-publish list`, **Then** I see a list of pending approved posts with their creation dates.

---

### User Story 5 - Move to Done After Success (Priority: P1)

As the system, after successfully publishing a Facebook post, I must move the file to `/Done/facebook/` to prevent re-publication and maintain an audit trail.

**Why this priority**: Essential for idempotency and preventing duplicate posts.

**Independent Test**: Can be tested by publishing a post and verifying the file no longer exists in `/Approved/facebook/` but exists in `/Done/facebook/`.

**Acceptance Scenarios**:

1. **Given** a post is published successfully, **When** the executor completes, **Then** the original file is moved from `/Approved/facebook/` to `/Done/facebook/`.

2. **Given** a file moved to `/Done/facebook/`, **When** the executor runs again, **Then** the file is not reprocessed.

3. **Given** a file in `/Done/facebook/`, **Then** the file contains updated frontmatter with `status: published`, `published_at`, and optionally `facebook_post_url`.

---

### User Story 6 - One-Time Session Authentication (Priority: P1)

As a user setting up the executor for the first time, I need to authenticate with Facebook via a headed browser session, so that subsequent executions can run headlessly with the stored session.

**Why this priority**: Facebook requires authentication; this enables headless automation after initial setup.

**Independent Test**: Can be tested by running `--auth`, logging in to Facebook manually, and verifying the session is stored for headless use.

**Acceptance Scenarios**:

1. **Given** no session exists, **When** I run `facebook-publish --auth`, **Then** a visible browser window opens to Facebook login.

2. **Given** I complete Facebook login, **When** the session is saved, **Then** subsequent runs work headlessly without requiring login.

3. **Given** an expired session, **When** the executor detects auth failure, **Then** it logs an actionable error: "Run `facebook-publish --auth` to re-authenticate."

---

### Edge Cases

- What happens when `/Done/facebook/` directory doesn't exist? System creates it automatically.
- What happens when a file has malformed YAML frontmatter? File is moved to `/Needs_Action/facebook/` with error details.
- What happens when Facebook auth session is expired? Auth failure is logged, files are not processed, user is alerted via log.
- What happens when a file is modified while being processed? File is skipped with log entry, retried on next cycle.
- What happens when the same post content is approved twice (duplicate)? Content hash deduplication; duplicate is skipped and logged.
- What happens when `/Approved/facebook/` contains non-markdown files? Non-`.md` files are ignored silently.
- What happens when Facebook temporarily blocks posting? Logged as transient error, file preserved for retry.
- What happens if internet connection is lost mid-publish? Transient failure handling; file preserved, logged, retried.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect files in `/Approved/facebook/` within 30 seconds of placement (via watching or polling).

- **FR-002**: System MUST validate frontmatter schema before attempting publication.

- **FR-003**: System MUST publish post content to Facebook using browser automation (Playwright) as the execution method.

- **FR-004**: System MUST move successfully published files to `/Done/facebook/` immediately after publication.

- **FR-005**: System MUST write an audit log entry to `/Logs/facebook/` for every publish attempt (success or failure).

- **FR-006**: System MUST update file frontmatter with publication status (`published`, `failed`) and timestamp.

- **FR-007**: System MUST preserve failed files in `/Approved/facebook/` with error metadata appended to frontmatter.

- **FR-008**: System MUST retry transient failures up to 3 times following the Ralph Wiggum Loop pattern (Constitution Principle V).

- **FR-009**: System MUST move files with invalid frontmatter or unrecoverable errors to `/Needs_Action/facebook/`.

- **FR-010**: System MUST NOT process files in `/Pending_Approval/facebook/` — only `/Approved/facebook/`.

- **FR-011**: System MUST NOT process the same file twice (idempotency via tracking processed file hashes).

- **FR-012**: System MUST provide a CLI with commands: `run` (process approved), `list` (show pending), `status` (show last run stats), `--auth` (session setup).

- **FR-013**: System MUST create `/Done/facebook/` and `/Logs/facebook/` directories if they do not exist.

- **FR-014**: System MUST provide `--auth` flag to launch headed browser for initial Facebook login.

- **FR-015**: System MUST persist Facebook session data (cookies) to `.watcher-state/facebook/` for headless reuse.

- **FR-016**: System MUST run headless by default; headed mode only for `--auth`.

### Input Schema: Approved Facebook Post File

The executor expects files in `/Approved/facebook/` with this structure:

**YAML Frontmatter (required fields)**:

```yaml
---
type: approval_request
action_type: publish_facebook_post
status: pending
created_at: "2026-03-22T14:30:00Z"
created_by: orchestrator

target:
  platform: facebook
  post_type: text
  visibility: public  # public | friends | only_me

source:
  type: task
  path: "[[Needs_Action/tasks/some-task.md]]"

expected_outcome: "Facebook post published"
rollback_strategy: "Delete post manually from Facebook"

tags: [facebook, post]
---
```

**Markdown Body (required)**:

The executor extracts post content from the body section labeled `## Content Preview` or uses the entire body after frontmatter if no section header exists.

```markdown
## Content Preview

Your post content goes here. This is exactly what will be published to Facebook.

Hashtags and mentions are supported: #AI #Automation @FriendName
```

### Output Schema: Published File (in `/Done/facebook/`)

After successful publication, frontmatter is updated:

```yaml
---
type: approval_request
action_type: publish_facebook_post
status: published
created_at: "2026-03-22T14:30:00Z"
published_at: "2026-03-22T15:00:00Z"
created_by: orchestrator
executed_by: facebook_publisher

target:
  platform: facebook
  post_type: text
  visibility: public

source:
  type: task
  path: "[[Needs_Action/tasks/some-task.md]]"

facebook_post_url: "https://www.facebook.com/username/posts/123456789"
execution_log: "[[Logs/facebook/20260322-150000_publish.log]]"

tags: [facebook, post, published]
---
```

### Failed File Schema (remains in `/Approved/facebook/`)

After failed publication attempts:

```yaml
---
type: approval_request
action_type: publish_facebook_post
status: failed
created_at: "2026-03-22T14:30:00Z"
last_attempt_at: "2026-03-22T15:05:00Z"
retry_count: 3
last_error: "Network timeout after 30 seconds"
created_by: orchestrator

target:
  platform: facebook
  post_type: text
  visibility: public

source:
  type: task
  path: "[[Needs_Action/tasks/some-task.md]]"

tags: [facebook, post, failed]
---
```

### Vault Folder Structure

```
<VAULT_PATH>/
├── Pending_Approval/
│   └── facebook/                    # NOT processed — awaiting human review
├── Approved/
│   └── facebook/                    # Ready to publish — executor processes these
│       └── 2026-03-22-post-title.md
├── Done/
│   └── facebook/                    # Successfully published
│       └── 2026-03-22-post-title.md
├── Needs_Action/
│   └── facebook/                    # Invalid or permanently failed files
├── Logs/
│   └── facebook/                    # Audit logs
│       └── facebook-publish-2026-03-22.md
└── Rejected/
    └── facebook/                    # User-rejected posts (not processed)
```

### Key Entities

- **ApprovedPost**: Represents a file in `/Approved/facebook/` ready for publication. Contains: file_path, content, frontmatter, created_at.
- **PublishResult**: Outcome of a publish attempt. Contains: success (bool), post_url (optional), error (optional), timestamp.
- **ExecutionLog**: Audit entry for publish attempts. Contains: timestamp, file_path, action, result, error_details.
- **SessionState**: Playwright session data for Facebook authentication. Contains: cookies, storage_state path.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Approved Facebook posts are published within 5 minutes of file detection (excluding retry delays).

- **SC-002**: 100% of successfully published posts are moved to `/Done/facebook/` without manual intervention.

- **SC-003**: 100% of publish attempts (success or failure) produce an audit log entry in `/Logs/facebook/`.

- **SC-004**: Failed posts remain recoverable in `/Approved/facebook/` with error metadata; zero silent data loss.

- **SC-005**: System correctly refuses to process files from `/Pending_Approval/facebook/` (safety boundary).

- **SC-006**: Duplicate content detection prevents re-publishing identical posts (within 24-hour window).

- **SC-007**: System handles Facebook authentication gracefully — auth failures are logged and user is notified; no crash or infinite retry.

- **SC-008**: Session persists across executor restarts; re-authentication only required when session expires.

---

## Scope Boundaries

### In Scope

- Detection of approved Facebook post files in `/Approved/facebook/`
- Publication via Playwright browser automation to Facebook Web
- Audit logging to `/Logs/facebook/`
- File movement to `/Done/facebook/` on success
- Failure preservation with retry capability
- CLI for manual trigger, status, and auth
- Basic text post publication only
- Session management with `--auth` flag

### Out of Scope (Non-Goals)

- **No Facebook inbox/message monitoring** — This phase is publish execution only
- **No comment moderation** — Publish and move on; no engagement features
- **No ad campaign features** — Organic posts only
- **No analytics dashboards** — No metrics retrieval
- **No cross-platform publishing** — Facebook only; no Instagram, LinkedIn, WhatsApp
- **No Facebook API integration** — Playwright browser automation only (consistent with Silver Tier architecture)
- **No image/video attachments** — Plain text content only in this phase
- **No scheduled posting** — Immediate publication only
- **No multi-account support** — Single Facebook account per installation
- **No approval workflow modifications** — HITL system is unchanged
- **No rollback/undo automation** — Rollback is manual per approval file instructions
- **No Facebook Pages posting** — Personal profile posts only in this phase
- **No Facebook Groups posting** — Personal timeline only in this phase

---

## Assumptions

1. User has a personal Facebook account and can log in via browser.
2. Playwright is already installed and configured for browser automation (Silver Tier dependency).
3. Facebook session persistence is handled via `.watcher-state/facebook/` cookies (similar to WhatsApp and LinkedIn watcher patterns).
4. Initial Facebook authentication is performed manually in headed mode; subsequent runs use headless mode with stored session.
5. Facebook's web interface structure is stable enough for Playwright selectors (fragile assumption; may require maintenance).
6. `/Approved/facebook/` directory will be created by HITL system or manually by user.
7. The vault path is configured via `VAULT_PATH` environment variable or CLI argument.
8. User understands Facebook's Terms of Service regarding automated posting.

---

## Dependencies

- **HITL approval workflow**: Provides the approval file pattern
- **Playwright (Python)**: Browser automation for Facebook Web
- **watchdog >=6.0**: File system watching (already a project dependency)
- **python-dotenv**: Environment configuration
- **pyyaml**: Frontmatter parsing

---

## Security Constraints

- Facebook session cookies MUST be stored in `.watcher-state/facebook/` (excluded from git via `.gitignore`)
- No Facebook credentials (username/password) in code or `.env`
- Playwright runs headless by default; headed mode only for initial auth setup (`--auth`)
- All publish attempts logged for audit trail
- System MUST NOT store or log Facebook passwords

---

## Constitution Compliance

| Principle | Compliance |
|-----------|------------|
| I. Local-First | PASS — All processing local; Facebook post is the only external interaction |
| II. Canonical Folders | PASS — Uses `/Approved/`, `/Done/`, `/Logs/`, `/Needs_Action/` |
| III. Tiered Scope | PASS — Browser automation is Silver Tier capability |
| IV. Safety-First | PASS — Executes only from `/Approved/`, never from `/Pending_Approval/` |
| V. Ralph Wiggum Loop | PASS — 3 retries on transient failure, then preserve for human review |
| VI. Silver Tier Autonomy | PASS — Human-approved posts only; no autonomous publishing |
| VII. Phased Development | PASS — Scoped to Facebook execution only |
| VIII. Gmail API Migration | N/A — Not applicable to Facebook |

---

## Acceptance Criteria Summary

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-01 | Approved file detected within 30 seconds | Automated test with timer |
| AC-02 | Post published to Facebook with correct content | Manual verification + screenshot |
| AC-03 | File moved to `/Done/facebook/` after success | Automated test |
| AC-04 | Frontmatter updated with `published_at` | File inspection |
| AC-05 | Audit log written for every attempt | Log file inspection |
| AC-06 | Failed file remains in `/Approved/facebook/` | Automated test |
| AC-07 | Failed file has error metadata in frontmatter | File inspection |
| AC-08 | Invalid frontmatter file moved to `/Needs_Action/` | Automated test |
| AC-09 | CLI `list` shows pending approved posts | CLI execution |
| AC-10 | CLI `run` processes approved posts | CLI execution + Facebook verification |
| AC-11 | Files in `/Pending_Approval/facebook/` are ignored | Automated test |
| AC-12 | Duplicate content is not re-published | Automated test |
| AC-13 | `--auth` opens headed browser for login | Manual verification |
| AC-14 | Session persists across restarts | Restart executor and verify headless operation |

---

**End of Specification**

**Next Step**: `/sp.plan` to generate implementation architecture, or `/sp.clarify` to resolve any ambiguities.
