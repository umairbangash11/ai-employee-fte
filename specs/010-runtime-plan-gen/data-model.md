# Data Model: Runtime Plan Generation

**Feature**: 010-runtime-plan-gen
**Date**: 2026-04-14

## Entities

### RuntimePlan

A Markdown file written to `vault/Needs_Action/plans/` when the orchestrator determines an email requires a reply. Represents the AI's triage decision as a human-readable, actionable document.

| Attribute | Type | Source |
|---|---|---|
| `type` | `"runtime_plan"` (literal) | hardcoded |
| `status` | `"pending"` \| `"error"` | classification result |
| `created_at` | ISO 8601 datetime string | `datetime.now()` at write time |
| `source_file` | `str` | email filename passed by caller |
| `requires_approval` | `true` (literal) | hardcoded per Constitution VI |
| `email_sender` | `str` | `email_meta["sender"]` |
| `email_subject` | `str` | `email_meta["subject"]` |

**Constraints**:
- Always written before the source email is moved
- Always written in `Needs_Action/plans/` — never in `Approved/` or `Inbox/`
- `requires_approval` is always `true` — non-negotiable per Constitution Principle VI
- If write fails, `None` is returned; no exception propagates to caller

---

### PlanFilename

The filename of the RuntimePlan on disk. Deterministic from timestamp + subject slug.

| Attribute | Type | Description |
|---|---|---|
| `timestamp_prefix` | `str` | `YYYY-MM-DDTHH-MM-SS` formatted datetime |
| `subject_slug` | `str` | email subject sanitised to `[a-z0-9-]`, max 40 chars |
| `full_name` | `str` | `{timestamp_prefix}_plan_{subject_slug}.md` |

**Validation rules**:
- Subject slug: lowercase, alphanumeric + hyphens only; truncated at 40 chars; leading/trailing hyphens stripped
- If a file with the computed name already exists in `plans_dir`, `deduplicate_filename()` appends `_1`, `_2`, etc.

---

### ActionStep

A single checkbox line in the RuntimePlan body. Represents one discrete task.

| Attribute | Type | Description |
|---|---|---|
| `text` | `str` | Human-readable instruction |
| `format` | `"- [ ] {text}"` | Standard Markdown task list syntax |

**Standard steps for reply-needed email** (in order):
1. `Review the AI-generated draft reply in Needs_Action/drafts/`
2. `Edit the draft as needed`
3. `Approve by moving to Approved/email/ to authorise sending`

**Fallback steps for error classification**:
1. `Human review required — automated classification failed`
2. `Inspect the source email and determine required action manually`

---

## State Transitions

The RuntimePlan is stateless after creation — `brain.py` writes it and moves on. Status values:

```
write_runtime_plan() called
        │
        ▼
   status = "pending"   ← normal reply-needed path
        │
        │  (human opens vault, reviews plan)
        │
        ▼
   [out of scope for this feature — human manages status manually]


write_runtime_plan() called with error/fallback classification
        │
        ▼
   status = "error"    ← classification failed after 3 retries
```

The plan file is never updated by the system after creation. Human edits are out of scope.
