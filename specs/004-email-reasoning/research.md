# Phase 2: Email Reasoning Layer — Technical Research

**Feature Branch**: `004-email-reasoning`
**Phase**: 2 — Email Reasoning Layer
**Created**: 2026-03-07

## Overview

This document captures technical research and decisions for the Email Reasoning Layer. It informs the architecture choices in `plan.md`.

## LLM Selection

### Decision: OpenAI GPT-4o

**Rationale**:
- Already integrated in Phase 1 orchestrator (`brain.py` uses OpenAI SDK)
- GPT-4o supports structured JSON output mode natively
- Sufficient reasoning capability for email classification
- Cost-effective for batch processing (vs GPT-4 Turbo)

**Alternatives Considered**:

| Model | Pros | Cons |
|-------|------|------|
| GPT-4o | Fast, cheap, JSON mode, already integrated | Slightly less nuanced than GPT-4 |
| GPT-4 Turbo | Better reasoning | Slower, more expensive |
| Claude 3 | Strong reasoning | Requires new SDK integration |
| Local LLM | No API costs | Requires GPU, slower, less accurate |

**Decision**: Use GPT-4o with JSON mode for reliable structured output.

## Classification Prompt Engineering

### Classification System Prompt

The LLM will receive a system prompt defining the classification task:

```
You are an email classification assistant. Your task is to analyze emails and classify them into exactly one category.

Categories:
1. actionable - Requires user response or action (job opportunities, payment alerts, meeting requests, deadlines, security alerts)
2. informational - FYI content, no action needed (order confirmations, status updates, receipts, newsletters from trusted sources)
3. promotional - Marketing and sales content (discounts, offers, advertisements, product announcements)
4. ignore - Low-value content (spam, auto-replies, social notifications, unsubscribe confirmations)

For actionable emails, also extract:
- action: Clear 1-sentence description of required action
- priority: high | medium | low
- due_date: ISO date if deadline mentioned, else null
- is_multi_step: true if multiple distinct actions needed

Respond in JSON format only.
```

### User Prompt Template

```
Classify this email:

From: {sender}
Subject: {subject}
Date: {date}
Body:
{body}

Respond with JSON only.
```

### Expected Output Schema

```json
{
  "classification": "actionable" | "informational" | "promotional" | "ignore",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "action": "Required action if actionable, else null",
  "priority": "high" | "medium" | "low" | null,
  "due_date": "YYYY-MM-DD" | null,
  "is_multi_step": true | false,
  "steps": ["step1", "step2"] | null
}
```

## Structured Output Strategy

### OpenAI JSON Mode

Use `response_format={"type": "json_object"}` parameter:

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"},
    temperature=0.1  # Low temp for consistency
)
```

### Validation

1. Parse JSON response
2. Validate against Pydantic model
3. Fallback to "informational" if parsing fails

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ClassificationResult(BaseModel):
    classification: Literal["actionable", "informational", "promotional", "ignore"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    action: Optional[str] = None
    priority: Optional[Literal["high", "medium", "low"]] = None
    due_date: Optional[str] = None
    is_multi_step: bool = False
    steps: Optional[list[str]] = None
```

## Email File Parsing

### Input Format (from Phase 1 gmail-watcher)

Email files in `/Inbox/email/` have this structure:

```yaml
---
source: gmail
message_id: "abc123..."
thread_id: "xyz789..."
captured_at: "2026-03-07T10:00:00Z"
sender: "recruiter@company.com"
subject: "Interview Invitation"
urgency: normal
status: unread
tags: [inbox, gmail]
attachments: []
---

# Interview Invitation

Email body content here...
```

### Parsing Strategy

1. Use `python-frontmatter` to parse YAML + body
2. Extract `message_id` for deduplication key
3. Pass `sender`, `subject`, `body` to LLM

```python
import frontmatter

def parse_email_file(path: Path) -> dict:
    post = frontmatter.load(path)
    return {
        "message_id": post.metadata.get("message_id"),
        "sender": post.metadata.get("sender"),
        "subject": post.metadata.get("subject"),
        "date": post.metadata.get("captured_at"),
        "body": post.content,
        "file_path": path
    }
```

## Task File Generation

### Output Format

Task files follow Obsidian conventions with wikilinks:

```yaml
---
type: task
created_at: "2026-03-07T10:00:00Z"
source_email: "[[Inbox/email/20260307-093000_interview_invitation.md]]"
priority: high
due_date: "2026-03-10"
status: pending
tags: [task, email-derived]
---

# Respond to Interview Invitation

## Context

Interview invitation from Company X for Software Engineer role.

## Action Required

Reply to confirm interview availability for March 10th.

## Source

- Email: [[Inbox/email/20260307-093000_interview_invitation.md]]
- From: recruiter@company.com
- Subject: Interview Invitation
```

### Filename Convention

`YYYYMMDD-HHMMSS_<slug>.md`

Where `<slug>` is derived from the action (slugified, max 50 chars).

## Plan File Generation (Multi-Step)

For `is_multi_step: true` responses:

```yaml
---
type: plan
created_at: "2026-03-07T10:00:00Z"
source_email: "[[Inbox/email/20260307-093000_onboarding.md]]"
related_task: "[[Needs_Action/tasks/20260307-100000_complete_onboarding.md]]"
status: pending
tags: [plan, email-derived]
---

# Complete Onboarding Process

## Overview

Multi-step onboarding process from HR email.

## Steps

- [ ] Sign employment documents
- [ ] Complete I-9 verification
- [ ] Set up direct deposit

## Source

- Email: [[Inbox/email/20260307-093000_onboarding.md]]
```

## Deduplication Strategy

### State File Schema

`.watcher-state/reasoner.json`:

```json
{
  "version": 1,
  "last_run": "2026-03-07T10:00:00Z",
  "processed": {
    "message_id_1": {
      "classified_at": "2026-03-07T10:00:00Z",
      "classification": "actionable",
      "task_file": "Needs_Action/tasks/20260307-100000_respond.md"
    },
    "message_id_2": {
      "classified_at": "2026-03-07T10:00:05Z",
      "classification": "promotional",
      "task_file": null
    }
  }
}
```

### Dedup Logic

1. Load state file
2. Scan `/Inbox/email/` for all `.md` files
3. For each file:
   - Parse frontmatter, extract `message_id`
   - If `message_id` in state → skip
   - Else → classify and process
4. Save updated state

## Error Handling

### LLM API Failures

Per Constitution Principle V (Ralph Wiggum Loop):

1. Attempt 1: Standard API call
2. Attempt 2: Reduce body to first 2000 chars, retry
3. Attempt 3: Use only subject for classification
4. After 3 failures: Log error, skip email, continue batch

### Malformed Emails

- Missing frontmatter → Log warning, skip
- Empty body → Classify on subject only, note in task
- Missing message_id → Generate hash from sender+subject+date

## Performance Considerations

### Batch Processing

- Process up to 10 emails per batch (configurable via `--limit`)
- Parallel API calls using `asyncio.gather` for throughput
- Respect NFR-001: 10 emails in under 60 seconds

### Token Optimization

- Truncate body to 4000 tokens max
- Use sender + subject + first paragraph for very long emails
- Log token usage per classification

## Dependencies

### Python Packages

```toml
[project.dependencies]
openai = ">=1.0"
pyyaml = ">=6.0"
python-frontmatter = ">=1.0"
pydantic = ">=2.0"
```

### Internal Dependencies

| Module | Import | Usage |
|--------|--------|-------|
| `gmail_watcher.models` | `EmailMessage` | Type hints (optional) |

## Security Considerations

- OpenAI API key via `OPENAI_API_KEY` env var
- No email content logged to `/Logs` (only classification result)
- No PII in error messages
- State file in `.watcher-state/` excluded from git

## Integration Points

### Input

- Reads from: `/Inbox/email/*.md` (Phase 1 output)
- Reads from: `.watcher-state/reasoner.json` (self-managed)

### Output

- Writes to: `/Needs_Action/tasks/*.md`
- Writes to: `/Plans/*.md`
- Writes to: `/Logs/reasoner-YYYYMMDD.log`
- Writes to: `.watcher-state/reasoner.json`

## Test Strategy

### Unit Tests

- Email parsing (valid/invalid frontmatter)
- Classification result validation (Pydantic)
- Task file generation (correct format)
- Plan file generation (multi-step)
- State management (load/save/update)

### Integration Tests

- End-to-end with mock LLM responses
- Dry-run mode verification
- Idempotency check (run twice, same output)

### Manual Acceptance Tests

Per spec.md AT-01 through AT-06.

---

**Next Step**: Create `data-model.md` with entity definitions, then `plan.md` with implementation architecture.
