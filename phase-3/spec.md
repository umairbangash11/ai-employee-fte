# Feature Specification: Human-in-the-Loop Approval System

**Feature Branch**: `005-hitl-approval`
**Phase**: 3 — HITL + Approval Workflow Hardening
**Created**: 2026-03-08
**Status**: Draft
**Constitution**: v2.0.0 (Principles II, IV, VI)
**Input**: Action requests from reasoning layer or orchestrator

## Overview

The Human-in-the-Loop (HITL) Approval System implements a file-based approval workflow for sensitive external actions. Instead of executing actions directly, the system creates approval request files in `/Pending_Approval/` subdirectories. Human operators review these requests and move approved files to `/Approved/` to authorize execution. This ensures no external action (email send, LinkedIn post) occurs without explicit human consent.

## Scope & Constraints

### In Scope

- File-based approval workflow using vault directories
- Approval request file schema (markdown with YAML frontmatter)
- State transitions: pending → approved, pending → rejected
- Logging of all approval lifecycle events
- CLI for listing and managing pending approvals
- Interface readiness for future MCP execution (no MCP implementation)

### Out of Scope

- MCP server implementation or execution
- Actual email sending or LinkedIn posting
- WhatsApp message sending
- Calendar event creation
- Automated approval (all approvals must be manual)
- Mobile/web approval interface

### Constraints

- All work limited to `/phase-3/` directory
- Must respect existing canonical folder structure (Constitution Principle II)
- Must follow Safety-First Execution (Constitution Principle IV)
- Must comply with Silver Tier Autonomy rules (Constitution Principle VI)
- No modification to `.specify/` or `.claude/` directories
- No execution of sensitive actions in this phase

---

## Canonical Folder Extensions

This phase extends the vault structure with approval-specific subdirectories:

```
vault/
├── Pending_Approval/
│   ├── email/           # Email actions awaiting approval
│   └── linkedin/        # LinkedIn actions awaiting approval
├── Approved/
│   ├── email/           # Approved email actions ready for execution
│   └── linkedin/        # Approved LinkedIn actions ready for execution
├── Rejected/
│   ├── email/           # Rejected email actions (archived)
│   └── linkedin/        # Rejected LinkedIn actions (archived)
└── Logs/
    └── approvals/       # Approval lifecycle audit logs
```

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reasoning Layer Creates Approval Request (Priority: P1)

When the reasoning layer or orchestrator determines a sensitive action is needed, it creates an approval request file instead of executing the action directly.

**Why this priority**: Core safety — no external action without human consent.

**Independent Test**: Trigger reasoning layer with an email requiring reply, verify approval request file created in `/Pending_Approval/email/`.

**Acceptance Scenarios**:

1. **Given** reasoning layer identifies email needing reply, **When** it processes the action, **Then** an approval request file is created in `/Pending_Approval/email/` (NOT executed).
2. **Given** an approval request is created, **Then** it contains valid YAML frontmatter with all required fields.
3. **Given** an approval request is created, **Then** it logs the creation event to `/Logs/approvals/`.

---

### User Story 2 - Human Approves Action via File Move (Priority: P1)

Human operator reviews a pending approval and moves the file to `/Approved/` to authorize execution.

**Why this priority**: Manual approval is the core HITL mechanism.

**Independent Test**: Create approval request in `/Pending_Approval/email/`, manually move to `/Approved/email/`, verify state transition is logged.

**Acceptance Scenarios**:

1. **Given** approval request exists in `/Pending_Approval/email/`, **When** human moves file to `/Approved/email/`, **Then** approval watcher detects the move.
2. **Given** file is moved to `/Approved/`, **Then** watcher logs state transition with timestamp.
3. **Given** file is in `/Approved/`, **Then** frontmatter `status` field reflects "approved" (or file location implies status).

---

### User Story 3 - Human Rejects Action via File Move (Priority: P1)

Human operator reviews a pending approval and moves the file to `/Rejected/` to deny execution.

**Why this priority**: Rejection must be a first-class workflow path.

**Independent Test**: Create approval request in `/Pending_Approval/linkedin/`, manually move to `/Rejected/linkedin/`, verify state transition is logged.

**Acceptance Scenarios**:

1. **Given** approval request exists in `/Pending_Approval/linkedin/`, **When** human moves file to `/Rejected/linkedin/`, **Then** rejection is logged.
2. **Given** file is rejected, **Then** it remains in `/Rejected/` for audit purposes (not deleted).
3. **Given** file is rejected, **Then** no execution occurs for that action.

---

### User Story 4 - CLI Lists Pending Approvals (Priority: P2)

Operator can use CLI to see all pending approval requests across action types.

**Why this priority**: Convenience for human operators managing approvals.

**Independent Test**: Create multiple approval requests, run CLI list command, verify all pending items shown.

**Acceptance Scenarios**:

1. **Given** 3 approval requests exist across `/Pending_Approval/email/` and `/Pending_Approval/linkedin/`, **When** operator runs `hitl-approval list`, **Then** all 3 are displayed.
2. **Given** CLI lists approvals, **Then** each shows: action type, target, created timestamp, summary.
3. **Given** no pending approvals exist, **When** operator runs `hitl-approval list`, **Then** "No pending approvals" is displayed.

---

### User Story 5 - Approval Request Includes Rollback Strategy (Priority: P2)

Each approval request must document what happens if the action fails or needs reversal.

**Why this priority**: Constitution Principle IV requires rollback strategy.

**Independent Test**: Create approval request, verify it contains rollback_strategy field.

**Acceptance Scenarios**:

1. **Given** approval request for send email, **Then** frontmatter includes `rollback_strategy` describing what to do if send fails.
2. **Given** approval request for LinkedIn post, **Then** frontmatter includes `rollback_strategy` (e.g., "Delete post manually").

---

### Edge Cases

- **Duplicate action request**: If identical action request already exists in Pending, do not create duplicate. Log warning.
- **File manually deleted**: If pending file is deleted (not moved to Approved/Rejected), log as "abandoned" and do not execute.
- **Invalid frontmatter**: If file in Pending has invalid/missing frontmatter, log error and skip processing.
- **Approval without execution capability**: In this phase, approved files remain in `/Approved/` for future MCP executor to process.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create approval request files in `/Pending_Approval/<action_type>/` for sensitive actions.
- **FR-002**: System MUST NOT execute sensitive actions directly; only create approval requests.
- **FR-003**: Approval requests MUST use the defined markdown schema with YAML frontmatter.
- **FR-004**: System MUST detect file moves from `/Pending_Approval/` to `/Approved/` or `/Rejected/`.
- **FR-005**: System MUST log all approval lifecycle events (created, approved, rejected) to `/Logs/approvals/`.
- **FR-006**: System MUST create approval directories if they don't exist.
- **FR-007**: System MUST validate frontmatter before processing approval requests.
- **FR-008**: System MUST include rollback_strategy in all approval requests.
- **FR-009**: CLI MUST provide `list` command showing all pending approvals.
- **FR-010**: System MUST prevent duplicate approval requests for identical actions.

### Non-Functional Requirements

- **NFR-001**: Approval file creation completes in under 1 second.
- **NFR-002**: Approval watcher detects file moves within 5 seconds.
- **NFR-003**: All approval logs use JSON lines format for machine readability.

---

## Action Types Requiring Approval

| Action Type | Source Directory | Description |
|-------------|------------------|-------------|
| `send_email_reply` | `/Pending_Approval/email/` | Reply to an existing email |
| `send_email_followup` | `/Pending_Approval/email/` | Send follow-up email |
| `publish_linkedin_post` | `/Pending_Approval/linkedin/` | Publish post to LinkedIn |

---

## Approval Request Schema

### File Naming Convention

```
YYYYMMDD-HHMMSS_<action_type>_<short_slug>.md
```

Example: `20260308-143000_send_email_reply_interview_response.md`

### YAML Frontmatter Schema

```yaml
---
type: approval_request
action_type: send_email_reply | send_email_followup | publish_linkedin_post
status: pending
created_at: "2026-03-08T14:30:00Z"
created_by: email_reasoner | orchestrator | manual

# Target information
target:
  recipient: "recruiter@company.com"
  subject: "Re: Interview Invitation"
  # or for LinkedIn:
  # platform: linkedin
  # post_type: text | article

# Source reference
source:
  type: email | task
  path: "[[Inbox/email/20260308-interview.md]]"

# Safety fields (Constitution Principle IV)
expected_outcome: "Email reply sent confirming interview attendance"
rollback_strategy: "No rollback needed; email cannot be unsent"

# Metadata
tags: [approval, email, interview]
expires_at: "2026-03-10T14:30:00Z"  # Optional: auto-expire if not reviewed
---
```

### Markdown Body Schema

```markdown
# Action: [Action Title]

## Summary

[1-2 sentence description of what this action will do]

## Content Preview

[Full content that will be sent/posted]

---

**For email:**
To: [recipient]
Subject: [subject]
Body:
[email body content]

---

**For LinkedIn:**
Post Type: [text/article]
Content:
[post content]

---

## Context

- Source: [[link to source email/task]]
- Reasoning: [Why this action is recommended]

## Risk Assessment

- Impact: [low/medium/high]
- Reversible: [yes/no]
- Rollback: [rollback strategy]

## Approval Instructions

To approve: Move this file to `/Approved/email/` (or `/Approved/linkedin/`)
To reject: Move this file to `/Rejected/email/` (or `/Rejected/linkedin/`)
```

---

## State Transitions

```
                    ┌─────────────┐
                    │   Created   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
        ┌───────────│   Pending   │───────────┐
        │           └─────────────┘           │
        │ (move to /Approved/)    (move to /Rejected/)
        ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│  Approved   │                       │  Rejected   │
└─────────────┘                       └─────────────┘
        │
        │ (Future: MCP executor picks up)
        ▼
┌─────────────┐
│  Executed   │  ← Out of scope for this phase
└─────────────┘
```

### Valid Transitions

| From | To | Trigger |
|------|-----|---------|
| (none) | Pending | Approval request created |
| Pending | Approved | Human moves file to `/Approved/` |
| Pending | Rejected | Human moves file to `/Rejected/` |

### Invalid Transitions

- Approved → Pending (no reversal)
- Rejected → Pending (no reversal)
- Approved → Rejected (must reject before approving)
- Any state → Executed (not in this phase)

---

## Logging Requirements

### Log Location

`/Logs/approvals/approval-YYYYMMDD.log`

### Log Entry Schema (JSON Lines)

```json
{
  "timestamp": "2026-03-08T14:30:00Z",
  "event": "created" | "approved" | "rejected" | "expired" | "error",
  "action_type": "send_email_reply",
  "file_path": "Pending_Approval/email/20260308-143000_send_email_reply.md",
  "actor": "email_reasoner" | "human" | "system",
  "details": {
    "target": "recruiter@company.com",
    "subject": "Re: Interview"
  }
}
```

### Required Log Events

| Event | When | Details |
|-------|------|---------|
| `created` | Approval request file written | action_type, target, source |
| `approved` | File moved to /Approved/ | original_path, new_path |
| `rejected` | File moved to /Rejected/ | original_path, new_path |
| `expired` | Pending request past expires_at | action_type, created_at |
| `error` | Invalid frontmatter or processing error | error_message |

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of sensitive actions create approval requests (no direct execution).
- **SC-002**: All approval requests contain valid frontmatter per schema.
- **SC-003**: All state transitions (created, approved, rejected) are logged.
- **SC-004**: CLI `list` command shows all pending approvals accurately.
- **SC-005**: No duplicate approval requests for identical actions.
- **SC-006**: Rollback strategy present in 100% of approval requests.

---

## Safety & Non-Goals *(mandatory)*

### Prohibited Actions

- **NO direct execution**: System MUST NOT send emails, post to LinkedIn, or perform any external action.
- **NO auto-approval**: All approvals require human action (file move).
- **NO approval reversal**: Once approved/rejected, state cannot change.
- **NO approval expiry execution**: Expired approvals are logged, not auto-rejected.

### Out of Scope for This Phase

- MCP server integration or execution
- Actual email/LinkedIn API calls
- WhatsApp message approval (future phase)
- Calendar event approval (future phase)
- Mobile/web approval interface
- Approval delegation or multi-approver workflows
- Scheduled/timed approval automation

---

## Assumptions

- Email reasoning layer (Phase 2) is operational and can call approval creation.
- Human operator has filesystem access to move files between directories.
- Vault path is provided via `VAULT_PATH` environment variable.
- Obsidian or file manager is used to review and move approval files.

---

## Acceptance Tests

| Test ID | Scenario | Input | Expected Output |
|---------|----------|-------|-----------------|
| AT-01 | Create email reply approval | Reasoning triggers reply | File in `/Pending_Approval/email/` |
| AT-02 | Create LinkedIn post approval | Orchestrator triggers post | File in `/Pending_Approval/linkedin/` |
| AT-03 | Approve email action | Move to `/Approved/email/` | Approval logged |
| AT-04 | Reject LinkedIn action | Move to `/Rejected/linkedin/` | Rejection logged |
| AT-05 | List pending approvals | Multiple pending files | CLI shows all |
| AT-06 | Prevent duplicate | Same action twice | Second request rejected |
| AT-07 | Invalid frontmatter | Malformed approval file | Error logged, skipped |

---

## CLI Interface

```
hitl-approval [OPTIONS] COMMAND

Commands:
  list       List all pending approval requests
  show ID    Show details of specific approval request
  stats      Show approval statistics

Options:
  --vault-path PATH    Path to Obsidian vault (default: VAULT_PATH env)
  --verbose            Show detailed output
  --version            Show version
  --help               Show help

Examples:
  hitl-approval list
  hitl-approval list --vault-path ./vault
  hitl-approval show 20260308-143000_send_email_reply
  hitl-approval stats
```

---

## Dependencies

### Internal

| Module | Usage |
|--------|-------|
| `email_reasoner` | Calls approval creator for reply/followup actions |
| `orchestrator` | Calls approval creator for LinkedIn posts |

### External

| Package | Version | Purpose |
|---------|---------|---------|
| pyyaml | >=6.0 | Frontmatter parsing |
| watchdog | >=6.0 | Directory monitoring for file moves |
| click | >=8.0 | CLI framework |

---

## Constitution Compliance

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I. Local-First | PASS | All files local, no cloud dependency |
| II. Canonical Folders | PASS | Uses /Approved/, extends with /Pending_Approval/, /Rejected/ |
| IV. Safety-First | PASS | No execution without /Approved/ file |
| V. Ralph Wiggum Loop | N/A | No retries needed for file operations |
| VI. Silver Tier Autonomy | PASS | Enforces HITL for all external actions |
| VII. Phased Development | PASS | Scoped to /phase-3/ only |

---

**End of Phase 3 Specification**

**Next Step**: User confirmation "Phase 3 HITL spec ready", then `/sp.plan`
