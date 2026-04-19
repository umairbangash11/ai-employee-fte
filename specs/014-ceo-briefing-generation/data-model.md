# Data Model: Gold Phase 4 — CEO Briefing Generation

**Feature Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-18
**Status**: Complete

---

## Overview

This document defines the data structures used by the CEO Briefing Generator. All models
are Python dataclasses used internally; no database or external persistence is required.
Data flows from vault files → reader models → aggregated BriefingData → markdown output.

---

## Core Entities

### BriefingData

The central aggregation structure passed to the briefing writer.

```python
@dataclass
class BriefingData:
    """Aggregated data for CEO Briefing generation."""

    # Metadata
    generated_at: datetime
    period_start: date       # 7 days before generated_at
    period_end: date         # generated_at date
    briefing_type: str       # "Monday" or "Adhoc"

    # Business goals
    goals: list[BusinessGoal]
    goal_progress: list[GoalProgress]

    # Completed work
    completed_items: list[CompletedItem]

    # Accounting
    accounting_summary: AccountingSummary

    # Issues
    bottlenecks: list[Bottleneck]
    upcoming_deadlines: list[UpcomingDeadline]

    # Intelligence
    suggestions: list[ProactiveSuggestion]

    # Metadata for audit
    data_gaps: list[str]     # Files that couldn't be read
```

---

### BusinessGoal

Parsed from `vault/Business_Goals.md`.

```python
@dataclass
class BusinessGoal:
    """A business goal extracted from Business_Goals.md."""

    title: str               # e.g., "Increase Revenue"
    slug: str                # e.g., "increase-revenue"
    description: str         # Full description text
    target: str | None       # Optional target metric
```

**Source**: `## Goal: <title>` headings in `vault/Business_Goals.md`

**Parsing rules**:
- Regex: `^## Goal:\s*(.+)$`
- Slug: lowercase, replace non-alphanumeric with hyphen, strip trailing hyphens

---

### GoalProgress

Computed by aligning completed items to business goals.

```python
@dataclass
class GoalProgress:
    """Progress status for a business goal."""

    goal_slug: str
    goal_title: str
    status: Literal["on_track", "at_risk", "blocked", "no_activity"]
    completed_count: int     # Items completed in period
    pending_count: int       # Items in Needs_Action for this goal
    reason: str              # Human-readable explanation
```

**Computation**:
- `on_track`: completed_count > 0 and pending_count <= 2
- `at_risk`: completed_count > 0 but pending_count > 2
- `blocked`: completed_count == 0 and pending_count > 0
- `no_activity`: completed_count == 0 and pending_count == 0

---

### CompletedItem

Represents a completed task from `vault/Done/`.

```python
@dataclass
class CompletedItem:
    """A completed item from Done/."""

    file_path: Path
    subject: str             # From subject: or filename
    goal_slug: str | None    # From goal: frontmatter
    completed_at: datetime   # From published_at or captured_at
    source_type: str         # email, facebook, instagram, x, odoo, etc.
```

**Source**: Files in `vault/Done/**/*.md`

**Frontmatter fields used**:
- `subject:` or filename
- `goal:` (optional)
- `published_at:` or `completed_at:` or `captured_at:`
- `platform:` or `source:` or inferred from path

---

### Bottleneck

An item stuck in `Needs_Action/` or with an overdue deadline.

```python
@dataclass
class Bottleneck:
    """An item identified as a bottleneck."""

    file_path: Path
    subject: str
    days_stale: int          # Days since captured_at
    reason: str              # "stale" or "overdue"
    category: str            # email, whatsapp, odoo, plans, etc.
    captured_at: datetime
    deadline: date | None    # If overdue
```

**Identification rules**:
- **Stale**: `captured_at` > 7 days ago AND file is in `Needs_Action/`
- **Overdue**: `deadline:` frontmatter < today

---

### AccountingSummary

Aggregated accounting data from `vault/Accounting/`.

```python
@dataclass
class AccountingSummary:
    """Summary of accounting activity in the period."""

    total_invoiced: Decimal      # Sum of invoice amounts
    invoice_count: int
    total_paid: Decimal          # Sum of payment amounts
    payment_count: int
    overdue_invoices: list[OverdueInvoice]
    has_data: bool               # False if Accounting/ empty or missing
```

```python
@dataclass
class OverdueInvoice:
    """An overdue invoice flagged in Bottlenecks."""

    file_path: Path
    partner: str
    amount: Decimal
    due_date: date
    days_overdue: int
```

**Source**: Files in `vault/Accounting/invoices/` and `vault/Accounting/payments/`

**Frontmatter fields used**:
- `amount:` (parsed as Decimal)
- `status:` (overdue detection)
- `odoo_partner:` or `partner:`
- `due_date:` or inferred

---

### UpcomingDeadline

An item with a deadline in the next 7 days.

```python
@dataclass
class UpcomingDeadline:
    """An item with an upcoming deadline."""

    file_path: Path
    subject: str
    deadline: date
    days_until: int          # Negative if overdue (should be in Bottlenecks)
    category: str
```

**Source**: Any vault file with `deadline:` frontmatter

**Rules**:
- Include if `deadline:` is within [today, today + 7 days]
- Exclude if `deadline:` < today (goes to Bottlenecks instead)
- Sort by deadline date ascending

---

### ProactiveSuggestion

A rule-based suggestion for the CEO.

```python
@dataclass
class ProactiveSuggestion:
    """A proactive suggestion based on observed patterns."""

    category: str            # email_backlog, social_activity, accounting, etc.
    message: str             # Human-readable suggestion
    severity: Literal["info", "warning"]
    threshold_met: str       # e.g., ">5 items in Needs_Action/email/"
```

**Suggestion rules** (hardcoded thresholds):

| Rule | Threshold | Message |
|------|-----------|---------|
| Email backlog | >5 items in Needs_Action/email/ | Consider scheduling time to process email backlog |
| WhatsApp backlog | >3 items in Needs_Action/whatsapp/ | WhatsApp messages need attention |
| High social activity | >10 posts in Done/facebook/ + Done/instagram/ + Done/x/ | Strong social media week; consider content calendar review |
| Overdue invoices | >0 overdue invoices | Outstanding invoices require follow-up |
| Stale plans | >3 items in Needs_Action/plans/ older than 7 days | Triage backlog accumulating |

---

## Output Entities

### CEOBriefing

The final markdown file written to `vault/Briefings/`.

**Filename format**: `YYYY-MM-DD_Monday_Briefing.md` or `YYYY-MM-DD_Adhoc_Briefing.md`

**Frontmatter**:

```yaml
---
type: ceo_briefing
generated_at: "2026-04-18T09:00:00Z"
period_start: "2026-04-11"
period_end: "2026-04-18"
status: generated
---
```

**Sections** (in order):

1. **Executive Summary** — 3–5 bullet points
2. **Goals Progress** — Table of goals with status indicators (if Business_Goals.md exists)
3. **Revenue/Business Summary** — Accounting totals and notable items
4. **Completed Tasks** — Grouped by goal if tags exist, otherwise by source type
5. **Bottlenecks** — Stale items and overdue deadlines
6. **Proactive Suggestions** — Rule-based recommendations
7. **Upcoming Deadlines** — Items due in next 7 days

---

### BriefingLogEntry

Log entry written to `vault/Logs/` after briefing generation.

**Frontmatter**:

```yaml
---
log_id: "2026-04-18T09-00-00-briefing_generation-monday-briefing"
timestamp: "2026-04-18T09:00:00"
action_type: briefing_generation
source_path: "/path/to/vault"
dest_path: "Briefings/2026-04-18_Monday_Briefing.md"
outcome: success
details: "Generated Monday briefing with 12 completed items, 3 bottlenecks, 2 suggestions"
---
```

---

## Entity Relationships

```
Business_Goals.md ──► BusinessGoal ──┐
                                     │
                                     ├──► GoalProgress
Done/**/*.md ────► CompletedItem ────┤
                                     │
                                     ├──► BriefingData ──► BriefingWriter ──► CEOBriefing
Needs_Action/**/*.md ──► Bottleneck ─┤                                              │
                                     │                                              ▼
Accounting/**/*.md ──► AccountingSummary                                    vault/Briefings/
                                     │
*.md with deadline: ──► UpcomingDeadline
                                     │
(Rule engine) ──► ProactiveSuggestion
```

---

## Validation Rules

### CompletedItem

- `captured_at` or `completed_at` MUST be parseable ISO 8601
- Items outside the 7-day period are excluded
- Malformed YAML: skip file, add to `data_gaps`

### Bottleneck

- `captured_at` MUST be parseable
- `days_stale` computed as (today - captured_at).days
- Only include if days_stale > 7 OR deadline is overdue

### AccountingSummary

- `amount:` MUST be numeric (int or float)
- Non-numeric amounts: skip file, add to `data_gaps`
- Missing `vault/Accounting/`: set `has_data = False`

### UpcomingDeadline

- `deadline:` MUST be parseable YYYY-MM-DD
- Invalid dates: skip file, add to `data_gaps`
- Past deadlines: route to Bottlenecks, not UpcomingDeadlines

---

## No External Persistence

All data structures are in-memory only. No database, cache, or external storage is used.
The briefing generator is stateless — each run reads from vault and writes output fresh.
