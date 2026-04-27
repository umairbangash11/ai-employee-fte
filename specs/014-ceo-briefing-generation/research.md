# Research: Gold Phase 4 — CEO Briefing Generation

**Feature Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-18
**Status**: Complete

---

## Research Task 1: Vault YAML Frontmatter Patterns

### Findings

Examined existing vault file patterns across the codebase:

**Email files** (`gmail_watcher/writer.py`):
```yaml
source: gmail
captured_at: "2026-04-18T14:30:00Z"
sender: "Name <email@example.com>"
subject: "Subject line"
urgency: normal | urgent
status: unread
tags: [inbox, email]
```

**Social post files** (`social_drafters/drafter.py`):
```yaml
type: pending_action
action_type: publish_post
platform: facebook | instagram | x
status: awaiting_approval | published
source_path: "..."
dest_path: "..."
captured_at: "2026-04-18T14:30:00Z"
content_preview: "First 100 chars..."
```

**Done files** (moved from Approved):
```yaml
status: published | executed
post_url: "https://..." (optional)
published_at: "2026-04-18T14:30:00Z"
```

**Accounting files** (`odoo_accounting/vault_writer.py`):
```yaml
type: pending_action | accounting_record
action_type: create_invoice | prepare_payment | reconcile_payment
status: awaiting_approval | executed
odoo_partner: "Partner Name"
odoo_payload: "{...}" (JSON string)
amount: 1234.56 (added in proposal body, not frontmatter)
```

**Log files** (`sentinel/logger.py`):
```yaml
log_id: "timestamp-action-slug"
timestamp: "2026-04-18T14:30:00Z"
action_type: file_move | briefing_generation | ...
source_path: "..."
dest_path: "..."
outcome: success | failure | partial
details: "..."
```

### Decision

**Use `captured_at` as the canonical timestamp field** for determining item age.
- For Done/ items, use `published_at` or `completed_at` if present, fallback to `captured_at`
- For deadline detection, use `deadline:` frontmatter field (ISO 8601 date)
- For goal alignment, use `goal:` frontmatter field (slug matching Business_Goals.md)

**Rationale**: Consistent with existing patterns; no new field names needed.

**Alternatives considered**:
- `created_at` — not used consistently; rejected
- File modification time — unreliable after moves; rejected

---

## Research Task 2: Slug/Deduplication Patterns

### Findings

**Pattern 1: `orchestrator/plan_writer.py`**

```python
def _safe_slug(subject: str) -> str:
    slug = subject.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:40].rstrip("-")

def _deduplicate_path(plans_dir: Path, filename: str) -> Path:
    candidate = plans_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        candidate = plans_dir / new_name
        if not candidate.exists():
            return candidate
        counter += 1
```

**Pattern 2: `odoo_accounting/vault_writer.py`**

```python
def _unique_path(target: Path) -> Path:
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
```

### Decision

**Adopt Pattern 2 (`_unique_path`) for briefing filenames**.

Filename format: `YYYY-MM-DD_Monday_Briefing.md` or `YYYY-MM-DD_Adhoc_Briefing.md`
Deduplication: `YYYY-MM-DD_Adhoc_Briefing-2.md`, `YYYY-MM-DD_Adhoc_Briefing-3.md`, etc.

**Rationale**: Consistent with Odoo accounting pattern; hyphen separator is cleaner than underscore for counters.

**Alternatives considered**:
- Underscore counter (`_2.md`) — used by plan_writer but hyphen is more readable
- UUID suffix — rejected; less human-readable

---

## Research Task 3: Logging Integration

### Findings

**`sentinel/logger.py` signature**:

```python
def write_log_entry(
    logs_dir: Path,
    action_type: str,
    source_path: Path,
    dest_path: Path,
    file_size: int,
    outcome: str,
    details: str = "",
) -> Path:
```

**Required fields** (per Constitution Principle IX):
1. `timestamp` — auto-generated in ISO 8601
2. `action_type` — passed as parameter
3. `source_path` — passed as parameter
4. `dest_path` — passed as parameter
5. `outcome` — `success` | `failure` | `partial`
6. `details` — human-readable description

### Decision

**Use `action_type: briefing_generation`** for all CEO briefing log entries.

Briefing-specific logging wrapper:

```python
def log_briefing_generation(
    logs_dir: Path,
    vault_path: Path,
    briefing_path: Path,
    outcome: str,
    details: str = "",
) -> Path:
    return write_log_entry(
        logs_dir=logs_dir,
        action_type="briefing_generation",
        source_path=vault_path,  # vault root as source
        dest_path=briefing_path,
        file_size=briefing_path.stat().st_size if briefing_path.exists() else 0,
        outcome=outcome,
        details=details,
    )
```

**Rationale**: Reuses existing logger; adds briefing-specific context.

**Alternatives considered**:
- Custom briefing logger — rejected; unnecessary duplication
- Separate log file — rejected; violates single `/Logs` directory principle

---

## Research Task 4: Business_Goals.md Format

### Findings

No existing `Business_Goals.md` template in the codebase. Per spec assumption:

> `Business_Goals.md` is a single markdown file in the vault root with a consistent format:
> `## Goal: <title>` headings with descriptive text underneath.

### Decision

**Define canonical Business_Goals.md format**:

```markdown
# Business Goals

## Goal: Increase Revenue

Target: $100k MRR by Q3 2026
Description: Focus on enterprise sales and upselling existing customers.

## Goal: Launch Product V2

Target: July 2026
Description: Complete feature set including advanced analytics and API.

## Goal: Improve Customer Retention

Target: <5% monthly churn
Description: Implement proactive support and success programs.
```

**Goal parsing rules**:
1. Look for `## Goal: <title>` headings
2. Extract title as slug: lowercase, replace non-alphanumeric with hyphen
3. Match `goal:` frontmatter in Done/ items against slug

**Example matching**:
- `## Goal: Increase Revenue` → slug: `increase-revenue`
- `goal: increase-revenue` frontmatter → matches

**Rationale**: Simple, human-readable, easy to parse with regex.

**Alternatives considered**:
- YAML frontmatter for goals — rejected; more complex, less readable
- Separate goal files — rejected; single file is simpler for CEO to maintain

---

## Summary of Research Outcomes

| Topic | Decision | Status |
|-------|----------|--------|
| Frontmatter patterns | Use existing `captured_at`, `deadline:`, `goal:` fields | Resolved |
| Deduplication | Adopt `_unique_path` pattern with hyphen counter | Resolved |
| Logging | Use `action_type: briefing_generation` with existing logger | Resolved |
| Business_Goals.md | `## Goal: <title>` headings with slug matching | Resolved |

All NEEDS CLARIFICATION items from Phase 0 are now resolved. Proceed to Phase 1.
