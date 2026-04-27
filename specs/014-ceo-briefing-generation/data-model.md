# Data Model: Gold Phase 4 — CEO Briefing Generation

**Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-17
**Phase**: Phase 1 output of `/sp.plan`

---

## Entities

### 1. BriefingConfig

Runtime configuration loaded from `.env` at startup. Immutable after construction.

```python
@dataclass
class BriefingConfig:
    vault_path: Path                  # from VAULT_PATH
    openai_api_key: str               # from OPENAI_API_KEY
    openai_model: str                 # from OPENAI_MODEL (default: gpt-4o)
    lookback_days: int                # from BRIEFING_LOOKBACK_DAYS (default: 7)
    bottleneck_days: int              # from BRIEFING_BOTTLENECK_DAYS (default: 7)
    goals_max_chars: int              # from BRIEFING_GOALS_MAX_CHARS (default: 4000)
    context_max_tokens: int           # from BRIEFING_CONTEXT_MAX_TOKENS (default: 6000)
    schedule: str | None              # from BRIEFING_SCHEDULE (default: None → on-demand)
    briefing_time: str                # from BRIEFING_TIME (default: "08:00")
    headless: bool                    # from BRIEFING_HEADLESS (unused; for convention)

    # Derived properties
    @property def briefings_dir(self) -> Path   # vault_path / "Briefings"
    @property def signals_dir(self) -> Path     # vault_path / "Signals"
    @property def logs_dir(self) -> Path        # vault_path / "Logs"
    @property def done_dir(self) -> Path        # vault_path / "Done"
    @property def needs_action_dir(self) -> Path  # vault_path / "Needs_Action"
    @property def pending_approval_dir(self) -> Path  # vault_path / "Pending_Approval"
    @property def accounting_dir(self) -> Path  # vault_path / "Accounting"
    @property def goals_file(self) -> Path      # vault_path / "Business_Goals.md"

    @classmethod
    def from_env(cls) -> "BriefingConfig": ...
```

**Validation rules**:
- `vault_path` must be a valid directory path (need not exist yet; `ensure_vault_dirs` creates it).
- `lookback_days` must be >= 1.
- `bottleneck_days` must be >= 1.
- `openai_api_key` is optional — if absent, synthesiser falls back to template mode.

---

### 2. VaultRecord

A single file read from a vault source directory. Lightweight — stores only the fields
needed for briefing synthesis.

```python
@dataclass
class VaultRecord:
    file_path: Path
    title: str                       # filename stem or frontmatter title
    captured_at: datetime | None     # from frontmatter captured_at, or mtime
    platform: str | None             # from frontmatter platform (social posts)
    status: str | None               # from frontmatter status
    content_preview: str | None      # first 200 chars of body, or frontmatter content_preview
    amount: float | None             # from frontmatter amount (Accounting records)
    transaction_type: str | None     # from frontmatter type field (invoice/payment/other)
    age_days: int                    # computed: (now - captured_at).days
```

**Sources**: `Done/`, `Needs_Action/`, `Pending_Approval/`, `Accounting/`

---

### 3. GoalsRecord

Parsed representation of `vault/Business_Goals.md`.

```python
@dataclass
class GoalsRecord:
    raw_text: str                    # full goals content (capped at goals_max_chars)
    goals: list[str]                 # list of extracted goal lines (numbered/bulleted)
    goal_count: int                  # len(goals)
```

**Parsing**: Extract lines that match `^\s*\d+[\.\)]\s+` (numbered) or `^\s*[-*]\s+`
(bulleted) as individual goal strings.

---

### 4. BriefingContext

Aggregated, structured data assembled from all vault sources before the LLM call.
Serialisable to JSON for logging, debugging, and token-capping.

```python
@dataclass
class BriefingContext:
    run_date: datetime
    lookback_days: int
    goals: GoalsRecord | None
    completed: list[VaultRecord]           # Done/ files within lookback window
    needs_action: list[VaultRecord]        # Needs_Action/ files (all, for bottleneck scan)
    pending_approval: list[VaultRecord]    # Pending_Approval/ files (all, for bottleneck scan)
    accounting: list[VaultRecord]          # Accounting/ files within lookback window
    bottlenecks: list[VaultRecord]         # subset of needs_action + pending_approval older than bottleneck_days
    sources_scanned: list[str]             # list of directory paths that were read
    sources_missing: list[str]             # list of directories that did not exist
    total_revenue: float                   # sum of accounting amounts (type: invoice, status: paid)
    total_pending_invoices: float          # sum of amounts (type: invoice, status: draft/sent)

    def to_json(self, max_tokens: int) -> str: ...  # truncate to token budget before LLM call
```

---

### 5. Briefing (vault output)

File written to `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md`.

**YAML frontmatter**:

```yaml
---
type: briefing
generated_at: 2026-04-21T08:00:00Z
lookback_days: 7
sources_scanned:
  - vault/Done/
  - vault/Needs_Action/
  - vault/Accounting/
sources_missing: []
synthesis: llm            # or: template_fallback
completed_count: 14
bottleneck_count: 2
accounting_total: 4250.00
---
```

**Body sections** (all six required):

```markdown
## Executive Summary
<!-- Goals progress + overall week narrative -->

## Revenue / Business Summary
<!-- Accounting events from past 7 days, total -->

## Completed Tasks
<!-- Done/ files from past 7 days, grouped by platform/type -->

## Bottlenecks
<!-- Items in Needs_Action/ and Pending_Approval/ older than threshold -->

## Proactive Suggestions
<!-- LLM-generated or template recommendations based on context -->

## Upcoming Deadlines
<!-- Items with due_date frontmatter field within next 7 days -->
```

---

### 6. Signal (vault output)

File written to `vault/Signals/<YYYY-MM-DD>-<signal_type>-<8-char-hash>.md`.

**YAML frontmatter**:

```yaml
---
type: signal
signal_type: bottleneck           # or: stale_approval | suggestion
source_path: vault/Needs_Action/email/2026-04-10-invoice-followup.md
age_days: 11
captured_at: 2026-04-10T09:30:00Z
generated_at: 2026-04-21T08:00:00Z
---
```

**Body**: One-line description of the detected signal.

---

### 7. LogEntry (vault audit)

Appended to `vault/Logs/ceo_briefing-YYYY-MM-DD.md` (date-partitioned log file).
Follows the 6-field Constitution Principle IX format.

```yaml
timestamp: 2026-04-21T08:01:23Z
action_type: generate_briefing
source_path: vault/
dest_path: vault/Briefings/2026-04-21_Monday_Briefing.md
outcome: success                # or: failure | partial
details: "lookback_days=7; completed=14; bottlenecks=2; synthesis=llm; signals_written=2"
```

---

## State Transitions

### Briefing File Lifecycle

```
[Not exists]
    │
    ▼  ceo_briefing run
[vault/Briefings/YYYY-MM-DD_Monday_Briefing.md]   ← overwritten on same-day re-run
```

### Signal File Lifecycle

```
[Not exists]
    │
    ▼  ceo_briefing run (bottleneck detected)
[vault/Signals/<date>-<type>-<hash>.md]   ← overwritten on re-run (same source → same filename)
```

### Source Files (read-only)

```
vault/Done/          ──read──►  BriefingContext.completed
vault/Needs_Action/  ──read──►  BriefingContext.needs_action + bottlenecks
vault/Pending_Approval/ ──read──►  BriefingContext.pending_approval + bottlenecks
vault/Accounting/    ──read──►  BriefingContext.accounting
vault/Business_Goals.md ──read──►  BriefingContext.goals

[NO STATE CHANGE on source files]
```

---

## Relationships

```
BriefingConfig
    │ drives
    ▼
VaultSource readers ──produces──► VaultRecord (list)
                                           │
                                           ▼
                                  BriefingContext (aggregated)
                                           │
                          ┌────────────────┼───────────────────┐
                          ▼                ▼                   ▼
                    Synthesiser        SignalWriter         LogEntry
                          │                │                   │
                          ▼                ▼                   ▼
                     Renderer        vault/Signals/      vault/Logs/
                          │
                          ▼
                  vault/Briefings/
```
