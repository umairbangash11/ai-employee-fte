# Implementation Plan: Human-in-the-Loop Approval System

**Feature**: 005-hitl-approval
**Phase**: 3 — HITL + Approval Workflow Hardening
**Based On**: phase-3/spec.md (approved)
**Created**: 2026-03-08
**Status**: Draft

---

## Overview

This plan implements a file-based approval workflow for sensitive external actions. The reasoning layer and orchestrator will create approval request files instead of executing actions directly. Human operators approve by moving files between directories.

**Key Integration Points**:
- `src/email_reasoner/engine.py` — integrates approval creation
- `src/orchestrator/brain.py` — integrates approval creation for LinkedIn
- New `src/hitl_approval/` package — core HITL logic

---

## Section 1: Folder/State Model

### 1.1 Directory Structure Extension

Extend the vault with approval-specific directories:

```
vault/
├── Pending_Approval/
│   ├── email/           # Email actions awaiting approval
│   └── linkedin/        # LinkedIn actions awaiting approval
├── Approved/
│   ├── email/           # Approved email actions
│   └── linkedin/        # Approved LinkedIn actions
├── Rejected/
│   ├── email/           # Rejected email actions
│   └── linkedin/        # Rejected LinkedIn actions
└── Logs/
    └── approvals/       # Approval lifecycle audit logs
```

### 1.2 State Transitions

```
(none) → pending     [File created in /Pending_Approval/<type>/]
pending → approved   [Human moves file to /Approved/<type>/]
pending → rejected   [Human moves file to /Rejected/<type>/]
```

**Invariant**: State is determined by file location, not frontmatter status field. Location is source of truth.

### 1.3 File Naming Convention

```
YYYYMMDD-HHMMSS_<action_type>_<slug>.md
```

Example: `20260308-143000_send_email_reply_interview_response.md`

**Slug rules**:
- Lowercase
- Spaces → underscores
- Max 50 characters
- Strip special characters except underscore

### 1.4 Deduplication Strategy

Each approval request gets a deterministic hash:
```
hash = sha256(action_type + target_recipient + subject + source_path)
```

Hash registry stored in `.watcher-state/approvals.json`:
```json
{
  "created_hashes": ["abc123...", "def456..."],
  "last_updated": "2026-03-08T14:30:00Z"
}
```

---

## Section 2: Approval File Generation

### 2.1 Approval Request Schema

**YAML Frontmatter** (FR-003, FR-008):

```yaml
---
type: approval_request
action_type: send_email_reply | send_email_followup | publish_linkedin_post
status: pending
created_at: "2026-03-08T14:30:00Z"
created_by: email_reasoner | orchestrator | manual

target:
  recipient: "recruiter@company.com"
  subject: "Re: Interview Invitation"
  # OR for LinkedIn:
  # platform: linkedin
  # post_type: text | article

source:
  type: email | task
  path: "[[Inbox/email/20260308-interview.md]]"

expected_outcome: "Email reply sent confirming interview attendance"
rollback_strategy: "No rollback needed; email cannot be unsent"

tags: [approval, email, interview]
expires_at: "2026-03-10T14:30:00Z"
---
```

**Markdown Body**:

```markdown
# Action: [Action Title]

## Summary
[1-2 sentence description of what this action will do]

## Content Preview

**To**: [recipient]
**Subject**: [subject]

---

[Full email/post content]

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

### 2.2 ApprovalRequest Model

```python
@dataclass
class ApprovalRequest:
    action_type: str  # send_email_reply | send_email_followup | publish_linkedin_post
    target_recipient: str
    target_subject: str
    content: str
    source_path: str
    source_type: str  # email | task
    reasoning: str
    expected_outcome: str
    rollback_strategy: str
    created_by: str  # email_reasoner | orchestrator
    tags: list[str]
    expires_at: Optional[datetime] = None
```

### 2.3 ApprovalWriter Module

```python
# src/hitl_approval/writer.py

def create_approval_request(
    request: ApprovalRequest,
    vault_path: Path,
) -> Path:
    """Create approval request file in /Pending_Approval/<type>/.

    Returns:
        Path to created approval file.

    Raises:
        DuplicateApprovalError: If identical request already exists.
    """
```

**Implementation**:
1. Compute deduplication hash
2. Check hash registry — raise `DuplicateApprovalError` if exists (FR-010)
3. Generate filename with timestamp and slug
4. Create directory if missing (FR-006)
5. Write frontmatter and body
6. Update hash registry
7. Log creation event (FR-005)
8. Return file path

---

## Section 3: Orchestrator/Reasoner Integration

### 3.1 Email Reasoner Integration

Modify `src/email_reasoner/engine.py` to create approval requests instead of executing:

**Current flow**:
```
email → classify → write_task_file (if actionable)
```

**New flow** (for reply/followup actions):
```
email → classify → [if needs_external_action]:
                      create_approval_request → /Pending_Approval/email/
                   [else]:
                      write_task_file → /Needs_Action/tasks/
```

**Detection criteria** for external action:
- `action` field contains "reply", "respond", "send", "forward"
- `is_multi_step` is False (single external action)
- `priority` is "high" or "critical"

**Integration point**: `engine.py:_process_email()`

```python
# New import
from hitl_approval.writer import create_approval_request
from hitl_approval.models import ApprovalRequest

# In _process_email, after classification:
if self._requires_approval(result):
    approval = ApprovalRequest(
        action_type=self._detect_action_type(result),
        target_recipient=email.sender,
        target_subject=f"Re: {email.subject}",
        content=result.draft_reply or "",
        source_path=str(email.file_path),
        source_type="email",
        reasoning=result.reasoning,
        expected_outcome=result.action,
        rollback_strategy="Email cannot be unsent once sent",
        created_by="email_reasoner",
        tags=["email", result.classification],
    )
    create_approval_request(approval, self.config.vault_path)
else:
    # Existing task creation flow
    write_task_file(email, result, self.config.vault_path)
```

### 3.2 Orchestrator Integration (LinkedIn)

Modify `src/orchestrator/brain.py` to route LinkedIn posts through approval:

**Integration point**: When LinkedIn post generation is triggered

```python
from hitl_approval.writer import create_approval_request
from hitl_approval.models import ApprovalRequest

def request_linkedin_post_approval(
    post_content: str,
    source_task_path: str,
    reasoning: str,
) -> Path:
    approval = ApprovalRequest(
        action_type="publish_linkedin_post",
        target_recipient="linkedin",
        target_subject="LinkedIn Post",
        content=post_content,
        source_path=source_task_path,
        source_type="task",
        reasoning=reasoning,
        expected_outcome="LinkedIn post published",
        rollback_strategy="Delete post manually from LinkedIn",
        created_by="orchestrator",
        tags=["linkedin", "post"],
    )
    return create_approval_request(approval, vault_path)
```

### 3.3 No Direct Execution

**Critical Safety Constraint** (Constitution Principle IV, VI):

The system MUST NOT:
- Send emails via SMTP/API
- Post to LinkedIn via API
- Execute any external action

In this phase, all external actions terminate at `/Approved/`. The approved files wait for a future MCP executor (out of scope).

---

## Section 4: Approval State Detection (Watcher)

### 4.1 ApprovalWatcher

Use `watchdog` to monitor `/Pending_Approval/`, `/Approved/`, `/Rejected/` for file moves.

```python
# src/hitl_approval/watcher.py

class ApprovalWatcher:
    """Watches for file moves between approval directories.

    Detects:
    - /Pending_Approval/<type>/file.md → /Approved/<type>/file.md (approved)
    - /Pending_Approval/<type>/file.md → /Rejected/<type>/file.md (rejected)
    - File deleted from /Pending_Approval/ (abandoned)
    """

    def __init__(self, vault_path: Path, log_callback: Callable):
        self.vault_path = vault_path
        self.log_callback = log_callback
        self.observer = Observer()

    def start(self):
        """Start watching approval directories."""

    def stop(self):
        """Stop the watcher."""
```

### 4.2 Event Detection Logic

**Move Detection Strategy**:

Since `watchdog` doesn't have a native "move" event across directories, detect moves via:
1. Track files in `/Pending_Approval/` on startup
2. On `FileDeletedEvent` in `/Pending_Approval/`, check if file appeared in `/Approved/` or `/Rejected/`
3. Use file modification time and content hash to confirm move (not copy-delete)

**NFR-002**: Detection must occur within 5 seconds of file move.

### 4.3 FileSystemEventHandler

```python
class ApprovalEventHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path, logger: ApprovalLogger):
        self.vault_path = vault_path
        self.logger = logger
        self._pending_files = {}  # filename -> (hash, mtime)

    def on_deleted(self, event):
        """Handle file deleted from /Pending_Approval/."""
        if self._is_pending_approval_path(event.src_path):
            filename = Path(event.src_path).name
            self._schedule_move_check(filename)

    def on_created(self, event):
        """Handle file created in /Approved/ or /Rejected/."""
        if self._is_approved_path(event.src_path):
            self._handle_approval(event.src_path)
        elif self._is_rejected_path(event.src_path):
            self._handle_rejection(event.src_path)

    def _handle_approval(self, path: str):
        """Log approval event."""
        self.logger.log_event(
            event="approved",
            file_path=path,
            actor="human",
        )

    def _handle_rejection(self, path: str):
        """Log rejection event."""
        self.logger.log_event(
            event="rejected",
            file_path=path,
            actor="human",
        )
```

---

## Section 5: Logging

### 5.1 Log Location

```
/Logs/approvals/approval-YYYYMMDD.log
```

Daily log rotation. JSON lines format (NFR-003).

### 5.2 ApprovalLogger Module

```python
# src/hitl_approval/logger.py

class ApprovalLogger:
    """Logs approval lifecycle events to /Logs/approvals/."""

    def __init__(self, logs_path: Path):
        self.logs_path = logs_path / "approvals"
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event: str,  # created | approved | rejected | expired | error
        file_path: str,
        actor: str,  # email_reasoner | orchestrator | human | system
        action_type: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log an approval lifecycle event."""
```

### 5.3 Log Entry Schema

```json
{
  "timestamp": "2026-03-08T14:30:00Z",
  "event": "created",
  "action_type": "send_email_reply",
  "file_path": "Pending_Approval/email/20260308-143000_send_email_reply.md",
  "actor": "email_reasoner",
  "details": {
    "target": "recruiter@company.com",
    "subject": "Re: Interview"
  }
}
```

### 5.4 Required Log Events (FR-005)

| Event | Trigger | Actor |
|-------|---------|-------|
| `created` | Approval request file written | email_reasoner / orchestrator |
| `approved` | File moved to /Approved/ | human |
| `rejected` | File moved to /Rejected/ | human |
| `expired` | Pending request past expires_at | system |
| `error` | Invalid frontmatter or processing error | system |

---

## Section 6: CLI Interface

### 6.1 CLI Design

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
```

### 6.2 CLI Implementation

```python
# src/hitl_approval/__main__.py

import click
from pathlib import Path

@click.group()
@click.option("--vault-path", envvar="VAULT_PATH", type=click.Path(exists=True))
@click.option("--verbose", is_flag=True)
@click.pass_context
def cli(ctx, vault_path, verbose):
    ctx.ensure_object(dict)
    ctx.obj["vault_path"] = Path(vault_path) if vault_path else None
    ctx.obj["verbose"] = verbose

@cli.command()
@click.pass_context
def list(ctx):
    """List all pending approval requests."""
    # FR-009: List all files in /Pending_Approval/email/ and /Pending_Approval/linkedin/

@cli.command()
@click.argument("approval_id")
@click.pass_context
def show(ctx, approval_id):
    """Show details of specific approval request."""

@cli.command()
@click.pass_context
def stats(ctx):
    """Show approval statistics."""

if __name__ == "__main__":
    cli()
```

### 6.3 Entry Point

Add to `pyproject.toml`:

```toml
[project.scripts]
hitl-approval = "hitl_approval.__main__:cli"
```

---

## Section 7: Testing

### 7.1 Unit Tests

| Test ID | Module | Description |
|---------|--------|-------------|
| T-01 | models | ApprovalRequest validation |
| T-02 | writer | Approval file creation |
| T-03 | writer | Duplicate detection |
| T-04 | writer | Directory creation |
| T-05 | logger | Log event writing |
| T-06 | logger | JSON lines format |
| T-07 | watcher | Approval detection |
| T-08 | watcher | Rejection detection |
| T-09 | cli | List command |
| T-10 | cli | Stats command |

### 7.2 Integration Tests

| Test ID | Scenario | Verification |
|---------|----------|--------------|
| IT-01 | Email reasoner creates approval | File in /Pending_Approval/email/ |
| IT-02 | Orchestrator creates LinkedIn approval | File in /Pending_Approval/linkedin/ |
| IT-03 | Human approves via file move | Log shows "approved" event |
| IT-04 | Human rejects via file move | Log shows "rejected" event |
| IT-05 | Duplicate request rejected | Second request raises error |

### 7.3 Acceptance Tests (from spec)

| AT-ID | Scenario | Status |
|-------|----------|--------|
| AT-01 | Create email reply approval | Pending |
| AT-02 | Create LinkedIn post approval | Pending |
| AT-03 | Approve email action | Pending |
| AT-04 | Reject LinkedIn action | Pending |
| AT-05 | List pending approvals | Pending |
| AT-06 | Prevent duplicate | Pending |
| AT-07 | Invalid frontmatter | Pending |

---

## Section 8: Package Structure

```
src/hitl_approval/
├── __init__.py
├── __main__.py          # CLI entry point
├── models.py            # ApprovalRequest, ApprovalState
├── writer.py            # create_approval_request()
├── watcher.py           # ApprovalWatcher, event handlers
├── logger.py            # ApprovalLogger
├── validator.py         # Frontmatter validation
└── exceptions.py        # DuplicateApprovalError, etc.

tests/
├── test_approval_models.py
├── test_approval_writer.py
├── test_approval_watcher.py
├── test_approval_logger.py
└── test_approval_cli.py
```

---

## Section 9: Dependencies

### 9.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyyaml | >=6.0 | YAML frontmatter parsing |
| watchdog | >=6.0 | Directory monitoring |
| click | >=8.0 | CLI framework |

### 9.2 Internal Dependencies

| Module | Usage |
|--------|-------|
| email_reasoner.engine | Calls approval creator |
| orchestrator.brain | Calls approval creator for LinkedIn |

---

## Section 10: Constitution Compliance Check

| Principle | Status | Justification |
|-----------|--------|---------------|
| I. Local-First | PASS | All files local, no cloud dependency |
| II. Canonical Folders | PASS | Extends /Approved/, adds /Pending_Approval/, /Rejected/ |
| III. Tiered Scope | PASS | Silver Tier read + approval workflow |
| IV. Safety-First | PASS | No execution without /Approved/ file |
| V. Ralph Wiggum Loop | N/A | Not applicable to file operations |
| VI. Silver Tier Autonomy | PASS | Enforces HITL for all external actions |
| VII. Phased Development | PASS | Scoped to /phase-3/ only |
| VIII. Gmail API Migration | N/A | Not applicable to this phase |

---

## Section 11: Non-Goals (Explicit)

The following are explicitly OUT OF SCOPE for this phase:

1. **No MCP execution** — Approved files wait for future executor
2. **No email sending** — No SMTP/Gmail API integration
3. **No LinkedIn posting** — No LinkedIn API integration
4. **No auto-approval** — All approvals require human file move
5. **No approval reversal** — Once approved/rejected, state is final
6. **No mobile/web interface** — File-based approval only
7. **No WhatsApp/Calendar approval** — Future phases

---

## Section 12: Future-Ready Boundaries

### 12.1 MCP Executor Interface

While not implemented, the design supports future MCP integration:

```python
# Future: src/mcp_executor/email_executor.py (NOT in this phase)

def process_approved_emails(approved_dir: Path):
    """Process approved email actions.

    Reads files from /Approved/email/, executes via MCP,
    moves to /Done/email/ on success.
    """
    # Future implementation
```

### 12.2 Approval File Contract

Approved files in `/Approved/<type>/` are self-contained:
- Full email content in markdown body
- Target recipient in frontmatter
- Source email linked for context
- Rollback strategy documented

This allows any future executor to process without additional context.

---

## Section 13: Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| File watcher misses move | Medium | Poll-based fallback every 30 seconds |
| Duplicate hash collision | Low | SHA256 with 4 unique fields |
| Human modifies file before moving | Low | Re-validate frontmatter on detection |
| Orphaned files in Pending | Low | Optional expiry logging (no auto-reject) |

---

## Section 14: Implementation Order

Recommended task execution order:

1. **Foundation** (T001-T010)
   - Package structure
   - Models and exceptions
   - Directory utilities

2. **Writer** (T011-T020)
   - ApprovalRequest model
   - Frontmatter generation
   - File writing
   - Deduplication

3. **Logger** (T021-T030)
   - ApprovalLogger class
   - JSON lines output
   - Event types

4. **Watcher** (T031-T040)
   - ApprovalWatcher class
   - Event detection
   - Move tracking

5. **Integration** (T041-T050)
   - Email reasoner integration
   - Orchestrator integration

6. **CLI** (T051-T060)
   - List command
   - Show command
   - Stats command

7. **Testing** (T061-T080)
   - Unit tests
   - Integration tests
   - Acceptance tests

---

**End of Implementation Plan**

**Next Step**: `/sp.tasks` to generate dependency-ordered tasks from this plan
