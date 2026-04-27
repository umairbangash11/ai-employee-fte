# Feature Specification: Gold Phase 4 — CEO Briefing Generation

**Feature Branch**: `014-ceo-briefing-generation`
**Created**: 2026-04-17
**Status**: Draft
**Phase**: Gold Phase 4 (of 5)
**Constitution**: v3.0.0
**Prerequisite**: Gold Phase 3 complete (social media expansion confirmed; vault lifecycle
patterns for Done/, Needs_Action/, Pending_Approval/ stable and in use)

---

## Overview

Implement the Weekly CEO Briefing system for the AI Employee. This phase adds a
**read-only synthesis layer** that scans the vault — goals, completed work, pending items,
accounting events, and prior briefings — and produces a single, concise executive Markdown
file every week: `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md`.

No post is sent. No email is dispatched. No payment is touched. The briefing system is
strictly an intelligence-gathering and report-writing tool; all its outputs land inside
the vault. Side-effect-free by design.

A secondary output stream — proactive signals and bottleneck flags — is written to
`vault/Signals/` so that detected anomalies are available for triage separately from the
narrative briefing.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Weekly CEO Briefing Generation (Priority: P1)

As the human operator, I want to run a single command on Monday morning and receive a
freshly generated executive briefing that summarises the week's business activity — goals
progress, completed work, revenue/accounting events, open bottlenecks, and proactive
suggestions — so that I can start the week with full situational awareness without
manually reading every vault folder.

**Why this priority**: This is the primary deliverable of Gold Phase 4. Every other user
story either feeds into this one or extends it. Without the briefing generator, the phase
has no value.

**Independent Test**: With a populated vault (containing at least one file in `Done/`,
one in `Needs_Action/`, one in `Accounting/`, and a `Business_Goals.md`), run:
`python -m ceo_briefing run`. Confirm `vault/Briefings/<date>_Monday_Briefing.md` is
created with all six required sections and valid YAML frontmatter. Confirm a 6-field log
entry appears in `vault/Logs/`.

**Acceptance Scenarios**:

1. **Given** the vault contains `Business_Goals.md`, files in `Done/`, `Needs_Action/`,
   and `Accounting/`, **When** `python -m ceo_briefing run` is executed,
   **Then** a briefing file is written to `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md`
   containing all six sections, and a 6-field log entry is appended to `vault/Logs/`.

2. **Given** the briefing generator is run twice in the same week,
   **When** the output filename already exists,
   **Then** the existing file is overwritten (idempotent re-run) without error, and a
   new log entry is appended (not replacing the previous one).

3. **Given** one or more vault source directories do not exist (e.g., `Accounting/` is
   absent), **When** `ceo_briefing run` is executed,
   **Then** the briefing is generated with a note in the relevant section ("No
   accounting data available this week") and execution does not abort — graceful
   degradation per Constitution Principle X.

---

### User Story 2 — Bottleneck and Signal Detection (Priority: P1)

As the human operator, I want the system to automatically flag items that have been
sitting in `Needs_Action/` or `Pending_Approval/` beyond a configurable age threshold,
and write those flags as individual signal files to `vault/Signals/`, so that I can
triage stale items without manually inspecting every folder.

**Why this priority**: Bottleneck detection is rated P1 alongside briefing generation
because the briefing's "Bottlenecks" section is fed directly by the signals produced
here. If this story is absent, the briefing is incomplete.

**Independent Test**: Create vault files in `Needs_Action/` with `captured_at` dates
older than the configured threshold (default: 7 days). Run `python -m ceo_briefing run`.
Confirm one signal file per stale item appears in `vault/Signals/` with correct
frontmatter (`type: signal`, `signal_type: bottleneck`, `source_path`). Confirm the
briefing's Bottlenecks section lists those items.

**Acceptance Scenarios**:

1. **Given** a file in `Needs_Action/` has a `captured_at` date older than
   `BRIEFING_BOTTLENECK_DAYS` (default 7), **When** `ceo_briefing run` is executed,
   **Then** a signal file is written to `vault/Signals/<slug>-bottleneck.md` with
   `type: signal`, `signal_type: bottleneck`, `source_path`, `age_days`, and
   `captured_at` fields, and the item is listed in the briefing's Bottlenecks section.

2. **Given** a file in `Pending_Approval/` has been waiting longer than the threshold,
   **When** `ceo_briefing run` executes,
   **Then** a signal of `signal_type: stale_approval` is written to `vault/Signals/`
   and listed in the briefing's Bottlenecks section.

3. **Given** no items exceed the age threshold, **When** `ceo_briefing run` executes,
   **Then** no signal files are written and the Bottlenecks section reads
   "No bottlenecks detected this week."

---

### User Story 3 — Business Goals Progress Tracking (Priority: P2)

As the human operator, I want the briefing to map completed work (`Done/` files from the
past 7 days) against the goals defined in `vault/Business_Goals.md`, so that I can see
at a glance whether the week's output advanced my stated objectives.

**Why this priority**: Goals tracking elevates the briefing from a raw activity log to an
executive intelligence report. Rated P2 because the briefing is useful without it (US1
still delivers), but significantly more valuable with it.

**Independent Test**: Create `vault/Business_Goals.md` with two distinct goals. Add two
`Done/` files this week whose content mentions one goal and not the other. Run
`python -m ceo_briefing run`. Confirm the briefing's Executive Summary section references
goal progress and notes the unmapped goal as having no completed work this week.

**Acceptance Scenarios**:

1. **Given** `vault/Business_Goals.md` exists and contains numbered goals, **When**
   `ceo_briefing run` executes, **Then** the Executive Summary section includes a
   "Goals this week" sub-section listing each goal with: completed-count, completion
   status (✅ / ⚠️ / ❌), and relevant `Done/` file references.

2. **Given** `vault/Business_Goals.md` does not exist, **When** `ceo_briefing run`
   executes, **Then** the Executive Summary notes "Business_Goals.md not found — goals
   tracking skipped" and execution continues without error.

---

### User Story 4 — Accounting and Revenue Summary (Priority: P2)

As the human operator, I want the briefing to include a revenue and accounting summary
drawn from `vault/Accounting/` files created or modified in the past 7 days, so that I
have a financial snapshot alongside the operational summary.

**Why this priority**: P2 because the briefing is operationally useful without financial
data, but the CEO Briefing is incomplete without a revenue line.

**Independent Test**: Add two Markdown files to `vault/Accounting/` within the trailing
7-day window, each with `amount`, `type` (invoice/payment), and `status` frontmatter
fields. Run `python -m ceo_briefing run`. Confirm the briefing's Revenue/Business Summary
section lists both files, their amounts, and a total. Confirm zero files from outside the
7-day window are included.

**Acceptance Scenarios**:

1. **Given** `vault/Accounting/` contains files from the past 7 days with `amount` and
   `type` fields, **When** `ceo_briefing run` executes, **Then** the Revenue/Business
   Summary section lists each file (name, type, amount, status) and a weekly total.

2. **Given** `vault/Accounting/` is absent or empty, **When** `ceo_briefing run`
   executes, **Then** the Revenue/Business Summary section reads "No accounting
   activity recorded this week" and execution does not abort.

---

### User Story 5 — Scheduled and On-Demand Execution (Priority: P3)

As the human operator, I want to be able to run the briefing both on demand (via CLI) and
on a scheduled basis (every Monday at a configured time), so that I receive the briefing
automatically each week without remembering to run it manually.

**Why this priority**: P3 because the system is fully functional with manual execution.
Scheduling is a quality-of-life enhancement, not a prerequisite for correctness.

**Independent Test**: Configure `BRIEFING_SCHEDULE=monday` and `BRIEFING_TIME=08:00` in
`.env`. Run `python -m ceo_briefing watch` — confirm the process starts, logs its
schedule, and does not exit. Wait for the scheduled time (or mock the clock in a unit
test). Confirm the briefing is generated at the scheduled time.

**Acceptance Scenarios**:

1. **Given** `BRIEFING_SCHEDULE=monday` and `BRIEFING_TIME=08:00` are set, **When**
   `python -m ceo_briefing watch` is run, **Then** the process stays alive, logs
   "Next briefing scheduled for <datetime>", and generates the briefing at the
   configured time.

2. **Given** no schedule env vars are set, **When** `python -m ceo_briefing run` is
   executed, **Then** the briefing runs immediately (one-shot mode) and exits.

---

### Edge Cases

- What happens when `vault/Done/` contains thousands of files? — The scanner MUST apply
  a 7-day lookback window (configurable via `BRIEFING_LOOKBACK_DAYS`) to bound the
  read set. Only files with `captured_at` or `mtime` within the window are included.
- What happens when GPT-4o is unavailable (API key missing or rate limited)? — The
  system falls back to a template-based briefing (structured lists with no LLM
  synthesis) and writes `synthesis: template_fallback` in the briefing frontmatter. A
  log entry with `outcome: partial` is written. Execution does not abort.
- What happens when a vault source file has no YAML frontmatter? — The parser skips the
  file, logs a warning, and continues. The briefing notes the count of skipped files.
- What happens if `vault/Briefings/` does not exist? — `ensure_vault_dirs` creates it
  automatically at startup (same pattern as Gold Phase 3 publishers).
- What happens when `Business_Goals.md` is very long (>10,000 words)? — Only the first
  `BRIEFING_GOALS_MAX_CHARS` characters (default: 4000) are passed to the LLM context
  to stay within token budget.
- What happens if the briefing generator is run on a non-Monday? — It generates
  the briefing immediately in `run` mode (no guard). In `watch` mode, it waits for
  the next Monday trigger. The filename always reflects the actual run date.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scan `vault/Done/`, `vault/Needs_Action/`,
  `vault/Pending_Approval/`, `vault/Accounting/`, and `vault/Briefings/` as input sources.
- **FR-002**: System MUST read `vault/Business_Goals.md` when present; skip gracefully
  when absent.
- **FR-003**: System MUST produce a briefing file at
  `vault/Briefings/<YYYY-MM-DD>_Monday_Briefing.md` with valid YAML frontmatter and all
  six required sections.
- **FR-004**: The six required briefing sections are: **Executive Summary**, **Revenue /
  Business Summary**, **Completed Tasks**, **Bottlenecks**, **Proactive Suggestions**,
  **Upcoming Deadlines**.
- **FR-005**: System MUST apply a configurable lookback window (default: 7 days) when
  scanning `Done/` and `Accounting/` to limit the data set.
- **FR-006**: System MUST detect stale items in `Needs_Action/` and `Pending_Approval/`
  older than `BRIEFING_BOTTLENECK_DAYS` (default: 7 days) and write one signal file per
  stale item to `vault/Signals/`.
- **FR-007**: Signal files MUST use canonical frontmatter: `type: signal`,
  `signal_type: bottleneck | stale_approval | other`, `source_path`, `age_days`,
  `captured_at`, `generated_at`.
- **FR-008**: Briefing generation MUST be idempotent — re-running in the same week
  overwrites the existing briefing file without error.
- **FR-009**: System MUST use OpenAI GPT-4o (model configurable via `OPENAI_MODEL`) to
  synthesise the narrative sections of the briefing; fallback to template mode if the
  API is unavailable.
- **FR-010**: System MUST write a 6-field log entry to `vault/Logs/` on every run
  (success, failure, or partial) per Constitution Principle IX.
- **FR-011**: System MUST NOT write to any external system — no emails, no social posts,
  no Odoo writes, no payment calls. All outputs are vault-local files only.
- **FR-012**: System MUST NOT move, rename, or delete any vault files it reads. All vault
  source access is read-only.
- **FR-013**: System MUST expose a CLI with at least two subcommands: `run` (one-shot)
  and `watch` (scheduled, stays alive).
- **FR-014**: System MUST call `ensure_vault_dirs` at startup to create `Briefings/`,
  `Signals/`, and `Logs/` if absent.
- **FR-015**: System MUST handle missing source directories gracefully — absence of any
  source directory MUST produce a note in the relevant briefing section, not an abort.
- **FR-016**: System MUST redact any content that appears to contain credentials before
  writing to the briefing or signal files (per Constitution Principle VII).

### Key Entities

- **Briefing** (`vault/Briefings/YYYY-MM-DD_Monday_Briefing.md`): The primary output.
  Has YAML frontmatter (`type: briefing`, `generated_at`, `lookback_days`,
  `sources_scanned`, `synthesis: llm | template_fallback`) and six body sections.

- **Signal** (`vault/Signals/<slug>-<signal_type>.md`): A secondary output capturing a
  single detected anomaly or proactive suggestion. Has frontmatter (`type: signal`,
  `signal_type`, `source_path`, `age_days`, `captured_at`, `generated_at`).

- **VaultSource**: An abstract reader over a vault directory or file. Implemented per
  source type (Goals, Done, NeedsAction, Accounting, Briefings). Each returns a list of
  structured records for the synthesis layer.

- **BriefingContext**: The aggregated, structured data assembled from all VaultSources
  before the LLM synthesis call. Serialisable to JSON for logging and debugging.

- **BriefingConfig**: Runtime configuration loaded from `.env`. Fields: `vault_path`,
  `openai_api_key`, `openai_model`, `lookback_days`, `bottleneck_days`,
  `goals_max_chars`, `schedule`, `briefing_time`, `headless` (unused here, kept for
  convention).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `python -m ceo_briefing run` completes in under 60 seconds on a vault with
  ≤200 files across all source directories.
- **SC-002**: Generated briefing contains all six required sections; zero sections may
  be absent even when source data is missing (fallback text is acceptable).
- **SC-003**: Every stale item (age > threshold) in `Needs_Action/` and
  `Pending_Approval/` produces exactly one signal file in `vault/Signals/` — no
  duplicates on re-run (idempotent signal write).
- **SC-004**: If GPT-4o is unavailable, the briefing is still generated in template
  mode; `outcome: partial` is logged; no unhandled exception is raised.
- **SC-005**: Zero external writes — no network calls other than the OpenAI inference
  call; no emails, social posts, or Odoo operations triggered.
- **SC-006**: A 6-field log entry is present in `vault/Logs/` after every run
  (success or failure), confirming audit trail per Constitution Principle IX.

---

## Architecture Notes *(for planning)*

### Module structure (to be confirmed in plan.md)

Mirrors the Gold Phase 3 publisher pattern — a single `ceo_briefing` package under
`src/` with the following expected modules:

```
src/ceo_briefing/
  __init__.py
  __main__.py        — CLI (run, watch subcommands)
  config.py          — BriefingConfig.from_env()
  sources.py         — VaultSource readers (Goals, Done, NeedsAction, Accounting)
  context.py         — BriefingContext builder (aggregates sources)
  synthesiser.py     — GPT-4o synthesis + template fallback
  renderer.py        — Markdown briefing renderer (6-section layout)
  signals.py         — Signal file writer for bottleneck/stale_approval detection
  logger.py          — 6-field vault log entry writer
  utils.py           — ensure_vault_dirs, frontmatter helpers, date utils
  exceptions.py      — BriefingError, SourceReadError, SynthesisError
```

### Technology (subject to plan.md confirmation)

- **Python 3.12** — project standard
- **openai>=1.0** — already installed (used by email reasoning in Silver Tier)
- **pyyaml** — already installed
- **python-dotenv** — already installed
- **stdlib only** otherwise (`pathlib`, `datetime`, `re`, `json`, `schedule`)
  — no new packages expected; `schedule` lib for watch mode (to be confirmed in plan)

### Vault I/O contract

| Operation | Directories | Mode |
|-----------|-------------|------|
| Read | `Done/`, `Needs_Action/`, `Pending_Approval/`, `Accounting/`, `Briefings/`, `Business_Goals.md` | Read-only |
| Write | `Briefings/` (briefing file) | Write (overwrite on re-run) |
| Write | `Signals/` (signal files) | Write (idempotent by slug) |
| Write | `Logs/` (log entry) | Append-only |

### Constitution compliance preview

| Principle | Compliance |
|-----------|------------|
| I. Local-first | ✅ All outputs are local vault files; only external call is OpenAI inference |
| II. Canonical folders | ✅ Uses `/Briefings/`, `/Signals/`, `/Logs/` — all canonical |
| III. Tiered scope | ✅ Gold Phase 4 per constitution XI |
| IV. Safety-first | ✅ No external actions; read-only on vault sources |
| V. Ralph Wiggum Loop | ✅ LLM call retried 3× before template fallback |
| VI. HITL approval gates | ✅ Not applicable — no external actions to gate |
| VII. Credential isolation | ✅ OPENAI_API_KEY in `.env`; redaction in FR-016 |
| VIII. MCP orchestration | ⚠️ MCP contract in `contracts/` to be defined in plan |
| IX. Audit logging | ✅ 6-field log entry per run (FR-010) |
| X. Graceful degradation | ✅ Missing dirs → note in section; LLM down → template |
| XI. Phased development | ✅ Phase 4 only; Phase 3 confirmed closed |
| XII. Scope boundary | ✅ No email, social, Odoo, or Phase 5 work in scope |

---

## Out of Scope

- Sending the briefing by email or messaging (Phase 5 / future)
- Publishing the briefing to any social media platform
- Modifying Odoo records or executing any financial transaction
- Real-time / intraday briefings (weekly cadence only in this phase)
- Platinum / cloud features (no cloud storage, no hosted scheduler)
- WhatsApp or Gmail source integration beyond reading existing vault files
- Modifying `.specify/` or `.claude/` internal folders
