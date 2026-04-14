# Feature Specification: Email Reasoning Layer

**Feature Branch**: `004-email-reasoning`
**Phase**: 2 — Email Reasoning Layer
**Created**: 2026-03-07
**Status**: Draft
**Constitution**: v2.0.0 (Principles II, IV, VI, VII)
**Input**: Markdown email files in `<VAULT>/Inbox/email/` created by Phase 1 Gmail watcher

## Overview

The Email Reasoning Layer reads captured email markdown files from the vault's Inbox, classifies them by intent, and generates actionable task files for emails requiring follow-up. This layer operates entirely on local markdown files — it does not interact with Gmail, send emails, or modify any external state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Actionable Email Creates Task (Priority: P1)

When an actionable email (job opportunity, payment alert, meeting request) is captured in the Inbox, the reasoning layer creates a corresponding task file in `/Needs_Action/` with a clear next step.

**Why this priority**: Core value — users need actionable items surfaced without manual triage.

**Independent Test**: Place a job-related email markdown in `/Inbox/email/`, run the reasoner, verify a task file appears in `/Needs_Action/tasks/` linking back to the original email.

**Acceptance Scenarios**:

1. **Given** an email with subject "Interview invitation for Software Engineer role" exists in `/Inbox/email/`, **When** the reasoner runs, **Then** a task file is created in `/Needs_Action/tasks/` with action "Respond to interview invitation".
2. **Given** an email about a payment due exists in `/Inbox/email/`, **When** the reasoner runs, **Then** a task file is created with urgency "high" and action referencing the payment.
3. **Given** a meeting request email exists, **When** the reasoner runs, **Then** a task file is created with action "Confirm or decline meeting".

---

### User Story 2 - Promotional Email Does Not Create Task (Priority: P1)

Marketing emails, newsletters, and promotional content should be classified but NOT create task files. They remain in Inbox for manual review if desired.

**Why this priority**: Prevents task noise — users should not see tasks for promotional spam.

**Independent Test**: Place a promotional email markdown in `/Inbox/email/`, run the reasoner, verify NO task file is created in `/Needs_Action/`.

**Acceptance Scenarios**:

1. **Given** an email with subject "50% off sale today only!" exists in `/Inbox/email/`, **When** the reasoner runs, **Then** no task file is created.
2. **Given** a newsletter digest email exists, **When** the reasoner runs, **Then** no task file is created.
3. **Given** a social notification email (e.g., "John liked your post"), **When** the reasoner runs, **Then** no task file is created.

---

### User Story 3 - Multi-Step Email Creates Plan (Priority: P2)

Complex actionable emails that require multiple steps (e.g., "Complete application: upload resume, fill form, schedule interview") generate both a task file AND a plan file outlining the steps.

**Why this priority**: Helps users break down complex requests without manual planning.

**Independent Test**: Place a multi-step request email in `/Inbox/email/`, run the reasoner, verify both a task file in `/Needs_Action/tasks/` and a plan file in `/Plans/` are created.

**Acceptance Scenarios**:

1. **Given** an email requesting "Complete the onboarding checklist: sign documents, set up payroll, attend orientation", **When** the reasoner runs, **Then** a task file AND a plan file with 3 steps are created.
2. **Given** a simple one-step actionable email, **When** the reasoner runs, **Then** only a task file is created (no plan file).
3. **Given** a plan file is created, **Then** it MUST link back to the original email file and the task file.

---

### User Story 4 - Original Email Files Unchanged (Priority: P1)

The reasoning layer MUST NOT modify, move, or delete original email files in `/Inbox/email/`. It is read-only on source files.

**Why this priority**: Safety-first — users must trust that captured emails are preserved.

**Independent Test**: Run the reasoner on multiple emails, verify all original email files remain unchanged (same content, same path, same timestamp).

**Acceptance Scenarios**:

1. **Given** 5 email files exist in `/Inbox/email/`, **When** the reasoner runs, **Then** all 5 files still exist with identical content.
2. **Given** the reasoner classifies an email as "ignore", **When** processing completes, **Then** the original email file is NOT deleted.
3. **Given** the reasoner creates a task, **Then** the original email file is NOT moved to `/Needs_Action/`.

---

### User Story 5 - Idempotent Processing (Priority: P2)

Running the reasoner multiple times on the same email should not create duplicate tasks. Previously processed emails are tracked and skipped.

**Why this priority**: Prevents duplicate tasks if the reasoner runs on a schedule.

**Independent Test**: Run the reasoner twice on the same email set, verify no duplicate task files are created.

**Acceptance Scenarios**:

1. **Given** an email was already processed and a task exists, **When** the reasoner runs again, **Then** no new task is created for that email.
2. **Given** processing state is tracked in `.watcher-state/reasoner.json`, **When** checking processed emails, **Then** message_id from email frontmatter is used as the key.
3. **Given** a new email arrives after the first run, **When** the reasoner runs again, **Then** only the new email is processed.

---

### Edge Cases

- **Email missing frontmatter**: Log warning, skip classification, do not create task.
- **Email body is empty**: Classify based on subject only; note "empty body" in task if created.
- **Classification confidence is low**: Default to "informational" (no task); log for review.
- **Vault directories don't exist**: Create `/Needs_Action/tasks/` and `/Plans/` automatically.
- **Email already has a linked task**: Skip (idempotent).
- **Rate limit on LLM API**: Retry with backoff (Ralph Wiggum Loop), then log and continue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read email markdown files from `<VAULT>/Inbox/email/` directory.
- **FR-002**: System MUST classify each email into one of: `actionable`, `informational`, `promotional`, `ignore`.
- **FR-003**: System MUST create a task file in `<VAULT>/Needs_Action/tasks/` for emails classified as `actionable`.
- **FR-004**: System MUST create a plan file in `<VAULT>/Plans/` for actionable emails requiring multiple steps.
- **FR-005**: System MUST NOT modify, move, or delete original email files in `/Inbox/email/`.
- **FR-006**: System MUST link task files back to the original email file using `[[wikilink]]` syntax.
- **FR-007**: System MUST track processed emails in `.watcher-state/reasoner.json` to prevent duplicate tasks.
- **FR-008**: System MUST use the `message_id` from email frontmatter as the deduplication key.
- **FR-009**: System MUST use an LLM (OpenAI GPT-4o) for email classification and action extraction.
- **FR-010**: System MUST support `--dry-run` flag to preview classifications without creating files.
- **FR-011**: System MUST log classification decisions to `<VAULT>/Logs/` for auditability.
- **FR-012**: System MUST create output directories (`/Needs_Action/tasks/`, `/Plans/`) if they don't exist.

### Non-Functional Requirements

- **NFR-001**: Classification of 10 emails completes in under 60 seconds.
- **NFR-002**: LLM API calls use structured output (JSON mode) for reliable parsing.
- **NFR-003**: System gracefully handles LLM API failures with retry and fallback to "informational".

### Classification Criteria

#### Actionable (creates task)

- Direct personal or business communication requiring response
- Job opportunities (applications, interviews, offers)
- Payment or finance alerts (invoices, bills, transfers)
- Invitations requiring RSVP (meetings, events, calls)
- Requests with explicit deadlines or follow-up needed
- Account security alerts (password reset, suspicious activity)

#### Informational (no task)

- Order confirmations and shipping updates
- Read receipts and delivery notifications
- Automated reports and summaries
- News digests from subscribed sources
- System status notifications

#### Promotional (no task)

- Marketing emails and sales promotions
- Newsletter content without personal relevance
- Discount codes and offers
- App feature announcements
- Survey requests from brands

#### Ignore (no task)

- Spam that passed filters
- Duplicate notifications
- Auto-replies and out-of-office messages
- Unsubscribe confirmations
- Generic platform notifications (social likes, follows)

### Key Entities

- **EmailFile**: Markdown file in `/Inbox/email/` with YAML frontmatter (source, message_id, sender, subject, urgency, etc.).
- **Classification**: Result object containing category (`actionable`|`informational`|`promotional`|`ignore`), confidence score, reasoning.
- **TaskFile**: Markdown file in `/Needs_Action/tasks/` with action description, priority, deadline (if any), and link to source email.
- **PlanFile**: Markdown file in `/Plans/` with ordered steps, links to source email and task file.
- **ReasonerState**: JSON registry in `.watcher-state/reasoner.json` tracking processed message_ids.

## Output Schemas

### Task File Schema (`/Needs_Action/tasks/*.md`)

```yaml
---
type: task
created_at: "2026-03-07T10:00:00Z"
source_email: "[[Inbox/email/20260307-093000_interview_invitation.md]]"
priority: high | medium | low
due_date: "2026-03-10" | null
status: pending
tags: [task, email-derived]
---

# [Action Title]

## Context

Brief summary of why this task was created.

## Action Required

Clear, specific next step(s) the user should take.

## Source

- Email: [[Inbox/email/20260307-093000_interview_invitation.md]]
- From: sender@example.com
- Subject: Interview invitation for Software Engineer role
```

### Plan File Schema (`/Plans/*.md`)

```yaml
---
type: plan
created_at: "2026-03-07T10:00:00Z"
source_email: "[[Inbox/email/20260307-093000_onboarding_checklist.md]]"
related_task: "[[Needs_Action/tasks/20260307-100000_complete_onboarding.md]]"
status: pending
tags: [plan, email-derived]
---

# [Plan Title]

## Overview

Brief description of the multi-step process.

## Steps

- [ ] Step 1: Description
- [ ] Step 2: Description
- [ ] Step 3: Description

## Source

- Email: [[Inbox/email/20260307-093000_onboarding_checklist.md]]
```

### Reasoner State Schema (`.watcher-state/reasoner.json`)

```json
{
  "version": 1,
  "last_run": "2026-03-07T10:00:00Z",
  "processed": {
    "abc123messageId": {
      "classified_at": "2026-03-07T10:00:00Z",
      "classification": "actionable",
      "task_file": "Needs_Action/tasks/20260307-100000_respond_to_interview.md"
    },
    "def456messageId": {
      "classified_at": "2026-03-07T10:00:05Z",
      "classification": "promotional",
      "task_file": null
    }
  }
}
```

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of actionable emails (per classification criteria) result in task files.
- **SC-002**: 0% of promotional/ignore emails result in task files.
- **SC-003**: 100% of multi-step actionable emails result in both task and plan files.
- **SC-004**: 0% of original email files are modified or deleted.
- **SC-005**: Running the reasoner twice on the same emails produces 0 duplicate tasks.
- **SC-006**: All task files contain valid wikilinks to source emails.

## Safety & Non-Goals *(mandatory)*

### Prohibited Actions

- **NO email sending**: System MUST NOT send, reply to, or forward emails.
- **NO Gmail state changes**: System MUST NOT modify Gmail labels, mark as read, archive, or delete.
- **NO auto-approval**: System MUST NOT auto-approve any execution plans. Tasks are created for human review.
- **NO file deletion**: System MUST NOT delete email files or any vault content.
- **NO external actions**: System MUST NOT call external APIs except OpenAI for classification.

### Out of Scope for Phase 2

- WhatsApp message processing (separate phase)
- MCP server integration
- Calendar event creation
- Automated task execution
- Email archival or cleanup
- Gmail label synchronization
- Real-time push processing (batch only)

## Assumptions

- Phase 1 Gmail watcher is operational and creating email files in `/Inbox/email/`.
- Email files have valid YAML frontmatter with `message_id` field.
- OpenAI API key is configured in `.env` as `OPENAI_API_KEY`.
- User will manually review and act on created tasks.
- Vault path is provided via `VAULT_PATH` environment variable or CLI flag.

## Acceptance Tests

| Test ID | Scenario | Input | Expected Output |
|---------|----------|-------|-----------------|
| AT-01 | Job email creates task | Email: "Interview at Company X" | Task file in `/Needs_Action/tasks/` |
| AT-02 | Promo email no task | Email: "50% off sale!" | No task file created |
| AT-03 | Multi-step creates plan | Email: "Complete onboarding: 3 steps" | Task file + Plan file |
| AT-04 | Original unchanged | Any email | Email file unmodified |
| AT-05 | Idempotent run | Same email, run twice | Single task file only |
| AT-06 | Dry-run no files | Any email + `--dry-run` | Classification logged, no files |

## CLI Interface

```
email-reasoner [OPTIONS]

Options:
  --vault-path PATH    Path to Obsidian vault (default: VAULT_PATH env)
  --dry-run            Preview classifications without creating files
  --limit N            Process at most N emails (default: all)
  --state PATH         Path to reasoner state file
  --verbose            Show detailed classification reasoning
  --version            Show version
  --help               Show help
```

## Dependencies

### Internal

| Module | Usage |
|--------|-------|
| `gmail_watcher.models` | EmailMessage dataclass for parsing |
| `sentinel.logger` | Write classification logs to `/Logs/` |

### External

| Package | Version | Purpose |
|---------|---------|---------|
| openai | >=1.0 | LLM classification (GPT-4o) |
| pyyaml | >=6.0 | Frontmatter parsing |

---

**End of Phase 2 Specification**

**Next Step**: Wait for user confirmation "Phase 2 spec ready", then `/sp.plan`
