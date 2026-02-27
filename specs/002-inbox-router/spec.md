# Feature Specification: Inbox → Needs_Action Router

**Feature Branch**: `002-inbox-router`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Inbox → Needs_Action Router — Implement rule-based router that moves markdown files from /Inbox/email/ to /Needs_Action/email/ based on flags (important, starred, keyword match, SLA breach). Must not delete source data. Movement must follow claim-by-move pattern."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route Important/Starred Emails (Priority: P1)

As a user, I want emails marked as important or starred to be automatically routed from `/Inbox/email/` to `/Needs_Action/email/` so that I can focus on high-priority items without manual triage.

**Why this priority**: Important and starred flags are explicit user/system indicators of urgency. Routing these first ensures the most critical items surface immediately without any configuration.

**Independent Test**: Can be fully tested by placing a markdown file with `urgency: urgent` or `starred: true` in frontmatter into `/Inbox/email/` and verifying it moves to `/Needs_Action/email/` within one routing cycle.

**Acceptance Scenarios**:

1. **Given** a markdown file in `/Inbox/email/` with frontmatter `urgency: urgent`, **When** the router runs, **Then** the file is moved to `/Needs_Action/email/` and the original location contains no copy of the file.
2. **Given** a markdown file in `/Inbox/email/` with frontmatter `starred: true`, **When** the router runs, **Then** the file is moved to `/Needs_Action/email/`.
3. **Given** a markdown file in `/Inbox/email/` with frontmatter `important: true`, **When** the router runs, **Then** the file is moved to `/Needs_Action/email/`.

---

### User Story 2 - Route Emails Matching Keywords (Priority: P2)

As a user, I want emails containing specific keywords (in subject or body) to be automatically routed to `/Needs_Action/email/` so that I can catch urgent messages even when the sender didn't flag them.

**Why this priority**: Keyword matching catches urgency signals that senders may not have explicitly flagged (e.g., "URGENT", "ASAP", "deadline"). This extends coverage beyond explicit flags.

**Independent Test**: Can be fully tested by placing a markdown file with "URGENT" in the subject or body into `/Inbox/email/` and verifying it moves to `/Needs_Action/email/`.

**Acceptance Scenarios**:

1. **Given** a markdown file in `/Inbox/email/` with subject containing "URGENT", **When** the router runs, **Then** the file is moved to `/Needs_Action/email/`.
2. **Given** a markdown file in `/Inbox/email/` with body containing a configured keyword (e.g., "deadline"), **When** the router runs, **Then** the file is moved to `/Needs_Action/email/`.
3. **Given** a markdown file in `/Inbox/email/` with no matching keywords, **When** the router runs, **Then** the file remains in `/Inbox/email/`.

---

### User Story 3 - Route SLA-Breaching Emails (Priority: P3)

As a user, I want emails that have been sitting in `/Inbox/email/` beyond a configurable time threshold (SLA breach) to be automatically routed to `/Needs_Action/email/` so that nothing gets forgotten.

**Why this priority**: SLA breach is a safety net for items that slipped through other rules. It ensures no email sits unattended indefinitely.

**Independent Test**: Can be fully tested by placing a markdown file with `captured_at` timestamp older than the SLA threshold and verifying it moves after the router runs.

**Acceptance Scenarios**:

1. **Given** a markdown file in `/Inbox/email/` with `captured_at` older than 24 hours (default SLA), **When** the router runs, **Then** the file is moved to `/Needs_Action/email/`.
2. **Given** a markdown file in `/Inbox/email/` with `captured_at` within the SLA threshold, **When** the router runs, **Then** the file remains in `/Inbox/email/`.
3. **Given** a custom SLA threshold of 4 hours is configured, **When** the router runs on a file older than 4 hours, **Then** the file is moved to `/Needs_Action/email/`.

---

### User Story 4 - Claim-by-Move Pattern (Priority: P1)

As a user, I want the router to use a claim-by-move pattern to prevent race conditions and ensure no data loss during file movement.

**Why this priority**: Data integrity is foundational. Without safe file movement, all other routing rules risk corrupting or losing files. Tied P1 with Story 1.

**Independent Test**: Can be tested by triggering concurrent routing operations on the same file and verifying exactly one move succeeds with no data loss.

**Acceptance Scenarios**:

1. **Given** a file in `/Inbox/email/`, **When** the router moves it, **Then** the file appears in `/Needs_Action/email/` with identical content and is removed from the source location.
2. **Given** a file being moved by one process, **When** a second process attempts to move the same file, **Then** only one process succeeds and the other gracefully handles the conflict.
3. **Given** a move operation fails mid-transfer, **When** recovery occurs, **Then** the original file remains intact in `/Inbox/email/` (no partial state).

---

### User Story 5 - Audit Trail for Routing (Priority: P2)

As a user, I want every routing action to be logged to `/Logs` so that I can audit what was moved and why.

**Why this priority**: Observability is essential for debugging and compliance. Logs enable troubleshooting without impacting core routing function.

**Independent Test**: Can be tested by routing a file and verifying a log entry appears in `/Logs` with timestamp, source, destination, and matched rule.

**Acceptance Scenarios**:

1. **Given** a file is routed from `/Inbox/email/` to `/Needs_Action/email/`, **When** the move completes, **Then** a log entry is written to `/Logs` containing timestamp, source path, destination path, and the rule that triggered the move.
2. **Given** a file is evaluated but not routed, **When** the router completes its cycle, **Then** no log entry is written for that file (or optionally a "no-match" entry if verbose logging is enabled).

---

### Edge Cases

- What happens when a file matches multiple rules (e.g., important AND keyword match)?
  - The file is moved once; the log records all matching rules.
- What happens when the destination `/Needs_Action/email/` directory doesn't exist?
  - The router creates it before moving.
- What happens when a file has malformed YAML frontmatter?
  - The router logs a warning and leaves the file in `/Inbox/email/` for manual review.
- What happens when the source file is deleted by another process during routing?
  - The router logs an error and continues processing other files.
- What happens when disk is full during move?
  - The move fails atomically; the original file remains in `/Inbox/email/`; error logged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST monitor `/Inbox/email/` for markdown files with `.md` extension.
- **FR-002**: System MUST parse YAML frontmatter to extract `urgency`, `starred`, `important`, and `captured_at` fields.
- **FR-003**: System MUST route files to `/Needs_Action/email/` when `urgency: urgent` is present in frontmatter.
- **FR-004**: System MUST route files to `/Needs_Action/email/` when `starred: true` is present in frontmatter.
- **FR-005**: System MUST route files to `/Needs_Action/email/` when `important: true` is present in frontmatter.
- **FR-006**: System MUST route files to `/Needs_Action/email/` when subject or body contains any configured keyword (case-insensitive match).
- **FR-007**: System MUST route files to `/Needs_Action/email/` when `captured_at` timestamp exceeds the configurable SLA threshold.
- **FR-008**: System MUST use claim-by-move pattern: attempt atomic rename; if rename fails due to source missing, treat as already claimed.
- **FR-009**: System MUST NOT delete source files; movement is the only permitted operation (atomic rename is acceptable).
- **FR-010**: System MUST log every routing action to `/Logs` with timestamp, source path, destination path, and matched rule(s).
- **FR-011**: System MUST create destination directory if it does not exist.
- **FR-012**: System MUST handle files with malformed frontmatter gracefully by logging a warning and skipping the file.
- **FR-013**: System MUST allow configurable list of urgency keywords (default: URGENT, ASAP, deadline, critical, time-sensitive).
- **FR-014**: System MUST allow configurable SLA threshold (default: 24 hours).
- **FR-015**: System MUST process files in a single pass per routing cycle without re-reading already-routed files.

### Non-Functional Requirements

- **NFR-001**: Router MUST complete a full scan of `/Inbox/email/` within 5 seconds for up to 1000 files.
- **NFR-002**: Router MUST be idempotent — running multiple times on the same state produces the same outcome.
- **NFR-003**: Router MUST not corrupt files during movement (byte-for-byte integrity).

### Key Entities

- **InboxFile**: A markdown file in `/Inbox/email/` with YAML frontmatter containing source metadata (sender, subject, captured_at, urgency, starred, etc.) and body content.
- **RoutingRule**: A condition that determines whether a file should be routed (flag-based, keyword-based, or SLA-based).
- **RoutingLog**: A log entry recording a routing action with timestamp, source, destination, and triggering rule(s).
- **Configuration**: User-modifiable settings including keyword list, SLA threshold, and verbose logging flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of files matching routing rules are moved to `/Needs_Action/email/` within one routing cycle.
- **SC-002**: Zero data loss — every moved file retains identical content (verified by checksum).
- **SC-003**: Every routing action produces an audit log entry in `/Logs` within 1 second of completion.
- **SC-004**: Router handles 1000 files in `/Inbox/email/` in under 5 seconds.
- **SC-005**: Files with malformed frontmatter are not silently dropped — 100% are logged with actionable error messages.
- **SC-006**: SLA-breaching emails are surfaced to `/Needs_Action/email/` within 1 routing cycle after threshold is exceeded.

## Assumptions

- The router operates on files already captured by the Gmail sentinel (Silver Tier) which produces standardized YAML frontmatter.
- Default SLA threshold of 24 hours is acceptable for most use cases; users can override via configuration.
- Default urgency keywords (URGENT, ASAP, deadline, critical, time-sensitive) cover common urgency indicators.
- The router runs on a schedule or trigger (e.g., filesystem watcher); scheduling mechanism is out of scope for this spec.
- Concurrent access to `/Inbox/email/` by other processes (e.g., the Gmail sentinel writing new files) is expected; the claim-by-move pattern handles this.

## Out of Scope

- Routing for `/Inbox/whatsapp/` (separate feature or future extension)
- Email replies or any external actions (per Constitution Principle VI)
- Real-time push notifications
- UI for configuring routing rules
