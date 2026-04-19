# Feature Specification: Gold Phase 4 — CEO Briefing Generation

**Feature Branch**: `014-ceo-briefing-generation`
**Created**: 2026-04-18
**Status**: Draft
**Phase**: Gold Phase 4 (of 5)
**Constitution**: v3.0.0
**Prerequisite**: Gold Phase 3 complete (social media expansion, vault lifecycle confirmed)

## Overview

Build a weekly CEO Briefing system that aggregates business goals, completed work, pending
work, and accounting/activity data from the vault, then generates a concise executive
markdown briefing. The briefing provides the CEO with a single-page summary of business
health, progress, blockers, and recommendations — all derived from existing vault data.

The system is **read-only with respect to external systems**: it reads from the vault,
generates a briefing markdown file, and writes only to `vault/Briefings/`. It does not
send emails, post to social media, execute payments, or modify any external system. Human
distribution of the briefing (if desired) is out of scope.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Weekly Briefing Generation (Priority: P1)

As a CEO, I want the AI Employee to generate a weekly briefing document every Monday (or
on demand) that summarizes business goals, completed work, pending items, revenue/accounting
data, and proactive suggestions — so that I can review the state of the business in under
5 minutes without reading individual vault files.

**Why this priority**: The core value of Phase 4 is the briefing document itself. Without
this capability, no other feature in the phase delivers value. This must work end-to-end
before any enhancements.

**Independent Test**: Populate a test vault with fixture files in `Business_Goals.md`,
`Done/`, `Needs_Action/`, and `Accounting/`. Trigger briefing generation. Verify a file
is created at `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md` with all required sections
and no placeholder text.

**Acceptance Scenarios**:

1. **Given** the vault contains `Business_Goals.md`, completed items in `Done/`, pending
   items in `Needs_Action/`, and accounting data in `Accounting/`, **When** the briefing
   generator runs, **Then** a markdown file is created at
   `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md` with the current date.
2. **Given** the briefing generator runs, **When** the output file is inspected, **Then**
   it contains all required sections: Executive Summary, Revenue/Business Summary,
   Completed Tasks, Bottlenecks, Proactive Suggestions, and Upcoming Deadlines.
3. **Given** the briefing is generated, **When** reviewed, **Then** no section contains
   placeholder text like `[TODO]`, `[PLACEHOLDER]`, or template markers — all content is
   derived from vault data.
4. **Given** the vault contains no items in a particular category (e.g., empty `Done/`),
   **When** the briefing is generated, **Then** the corresponding section states "No items
   this period" rather than being omitted or showing an error.
5. **Given** the briefing generator completes, **When** the operation finishes, **Then**
   a log entry is written to `vault/Logs/` with `action_type: briefing_generation`,
   `outcome: success`, and all six required fields.

---

### User Story 2 — On-Demand Briefing Generation (Priority: P1)

As a CEO, I want to be able to generate a briefing at any time (not just Mondays), so that
I can get an up-to-date summary before investor meetings, board calls, or weekly reviews
regardless of the day.

**Why this priority**: Flexibility in briefing timing is essential for real-world use.
Limiting to Mondays only would reduce utility significantly.

**Independent Test**: Trigger on-demand briefing generation on a Wednesday. Verify the
file is created at `vault/Briefings/YYYY-MM-DD_Adhoc_Briefing.md` with the correct date
and all required sections.

**Acceptance Scenarios**:

1. **Given** an on-demand briefing request, **When** the generator runs, **Then** a file
   is created at `vault/Briefings/YYYY-MM-DD_Adhoc_Briefing.md` with today's date.
2. **Given** multiple on-demand briefings are requested on the same day, **When** each
   generates, **Then** files are created with unique suffixes (e.g., `_Adhoc_Briefing_2.md`)
   — no overwrites occur.
3. **Given** an on-demand briefing is generated, **When** compared to a Monday briefing,
   **Then** both contain the same section structure and the same data aggregation logic —
   only the filename differs.

---

### User Story 3 — Business Goals Integration (Priority: P2)

As a CEO, I want the briefing to include my stated business goals and progress against them,
so that I can see whether the week's work aligned with strategic priorities.

**Why this priority**: Connecting daily execution to strategic goals is the value-add
beyond simple task listing. Without this, the briefing is just a status report.

**Independent Test**: Create a `Business_Goals.md` with 3 goals. Populate `Done/` with
items tagged to those goals. Generate a briefing. Verify the Executive Summary or a
dedicated Goals Progress section references each goal and summarizes progress.

**Acceptance Scenarios**:

1. **Given** `vault/Business_Goals.md` exists with defined goals, **When** the briefing
   is generated, **Then** the Executive Summary or Goals Progress section lists each goal
   and a brief progress indicator (on track / at risk / blocked).
2. **Given** completed items in `Done/` have `goal:` frontmatter tags, **When** the
   briefing is generated, **Then** those items are grouped under their corresponding goal
   in the Completed Tasks section.
3. **Given** a goal has no completed items and no pending items, **When** the briefing is
   generated, **Then** the goal is flagged as "No activity this period" in the summary.

---

### User Story 4 — Accounting Data Summary (Priority: P2)

As a CEO, I want the briefing to include a revenue/accounting summary derived from vault
accounting data, so that I can see financial health alongside operational status.

**Why this priority**: Financial visibility is a core CEO need. Separating accounting
data into the briefing closes the loop between Odoo integration (Phase 2) and executive
reporting.

**Independent Test**: Populate `vault/Accounting/` with invoice and payment markdown files.
Generate a briefing. Verify the Revenue/Business Summary section includes total revenue,
outstanding invoices, and recent payments.

**Acceptance Scenarios**:

1. **Given** `vault/Accounting/invoices/` contains invoice files with `amount:` frontmatter,
   **When** the briefing is generated, **Then** the Revenue/Business Summary includes
   total invoiced amount for the period.
2. **Given** `vault/Accounting/payments/` contains payment files with `amount:` frontmatter,
   **When** the briefing is generated, **Then** the Revenue/Business Summary includes
   total payments received for the period.
3. **Given** accounting data is missing or `vault/Accounting/` does not exist, **When**
   the briefing is generated, **Then** the Revenue/Business Summary states "No accounting
   data available" rather than failing.
4. **Given** invoice or payment files have `status: overdue` frontmatter, **When** the
   briefing is generated, **Then** the Bottlenecks section flags overdue items.

---

### User Story 5 — Bottleneck and Deadline Identification (Priority: P2)

As a CEO, I want the briefing to proactively identify bottlenecks (items stuck in
`Needs_Action/` for extended periods) and upcoming deadlines, so that I can intervene
before problems escalate.

**Why this priority**: Proactive alerting differentiates a useful briefing from a passive
summary. This enables the CEO to take action rather than just consume information.

**Independent Test**: Populate `Needs_Action/` with items, some with `captured_at` older
than 7 days and some with `deadline:` frontmatter. Generate a briefing. Verify the
Bottlenecks section lists stale items and the Upcoming Deadlines section lists items due
within 7 days.

**Acceptance Scenarios**:

1. **Given** items in `Needs_Action/` have `captured_at` older than 7 days, **When** the
   briefing is generated, **Then** the Bottlenecks section lists these items as "stale"
   with the number of days pending.
2. **Given** items anywhere in the vault have `deadline:` frontmatter within the next
   7 days, **When** the briefing is generated, **Then** the Upcoming Deadlines section
   lists these items sorted by deadline date (soonest first).
3. **Given** no bottlenecks or deadlines exist, **When** the briefing is generated,
   **Then** the corresponding sections state "No bottlenecks identified" and "No upcoming
   deadlines" respectively.
4. **Given** a deadline is overdue (date in the past), **When** the briefing is generated,
   **Then** the item appears in Bottlenecks with "overdue by N days" rather than Upcoming
   Deadlines.

---

### User Story 6 — Proactive Suggestions (Priority: P3)

As a CEO, I want the briefing to include proactive suggestions based on observed patterns
(e.g., many items stuck in `Needs_Action/email/`, high volume of social posts approved),
so that I can consider process improvements.

**Why this priority**: Suggestions add intelligence beyond data aggregation. Lower priority
because the briefing is valuable without them, but they differentiate the AI Employee.

**Independent Test**: Populate `Needs_Action/email/` with 10+ items. Generate a briefing.
Verify the Proactive Suggestions section includes a suggestion about email backlog.

**Acceptance Scenarios**:

1. **Given** `Needs_Action/email/` contains more than 5 items, **When** the briefing is
   generated, **Then** the Proactive Suggestions section includes a recommendation to
   address email backlog.
2. **Given** `Done/facebook/` + `Done/instagram/` + `Done/x/` contain more than 10 items
   in the period, **When** the briefing is generated, **Then** a suggestion acknowledges
   high social media activity and suggests content calendar review.
3. **Given** no notable patterns are detected, **When** the briefing is generated, **Then**
   the Proactive Suggestions section states "No suggestions this period" rather than
   being omitted.

---

### Edge Cases

- `Business_Goals.md` does not exist → briefing is still generated; Goals Progress section
  states "No business goals defined."
- `vault/Accounting/` does not exist → Revenue/Business Summary states "No accounting data
  available."
- `vault/Done/` is empty → Completed Tasks section states "No items completed this period."
- Briefing file already exists for today's date → append numeric suffix (e.g., `_2.md`,
  `_3.md`); never overwrite.
- Frontmatter in vault files is malformed (missing fields) → skip the file, log a warning,
  continue generating the briefing with available data.
- `vault/Briefings/` directory does not exist → create it before writing; do not fail.
- Generator encounters a file read error → log the error, continue with available data,
  include a "Data Gaps" note in the briefing footer.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST generate a weekly briefing file at
  `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md` when triggered on a Monday (scheduled
  or manual).
- **FR-002**: The system MUST generate an on-demand briefing file at
  `vault/Briefings/YYYY-MM-DD_Adhoc_Briefing.md` when triggered on any other day.
- **FR-003**: The briefing MUST contain the following sections in order: Executive Summary,
  Goals Progress (if `Business_Goals.md` exists), Revenue/Business Summary, Completed
  Tasks, Bottlenecks, Proactive Suggestions, Upcoming Deadlines.
- **FR-004**: The system MUST read from vault sources: `Business_Goals.md`, `Done/`,
  `Needs_Action/`, `Accounting/`, and existing `Briefings/` (for continuity reference).
- **FR-005**: The system MUST NOT modify any external system — it is read-only with
  respect to email, social media, accounting platforms, and all external services.
- **FR-006**: The system MUST NOT send the briefing via email, post it to social media,
  or distribute it in any way — distribution is a human responsibility.
- **FR-007**: The system MUST append a numeric suffix to the filename if a briefing for
  the same date already exists — never overwrite.
- **FR-008**: The system MUST create `vault/Briefings/` if it does not exist.
- **FR-009**: The system MUST log every briefing generation to `vault/Logs/` with all
  six required fields: `timestamp`, `action_type`, `source_path`, `dest_path`, `outcome`,
  `details`.
- **FR-010**: The system MUST gracefully handle missing data sources (empty directories,
  missing files) by including "No data available" text in the corresponding section —
  never fail the entire briefing due to partial data.
- **FR-011**: Items in `Needs_Action/` with `captured_at` older than 7 days MUST be
  flagged as bottlenecks in the Bottlenecks section.
- **FR-012**: Items with `deadline:` frontmatter within the next 7 days MUST be listed
  in the Upcoming Deadlines section, sorted by date (soonest first).
- **FR-013**: Overdue deadlines (past date) MUST appear in the Bottlenecks section, not
  Upcoming Deadlines.
- **FR-014**: Malformed vault files (missing or invalid frontmatter) MUST be skipped with
  a warning log, not cause the briefing to fail.
- **FR-015**: The briefing generator MUST follow the Ralph Wiggum Loop (3 attempts) for
  any vault read failures before logging a failure and continuing.

### Key Entities

- **CEOBriefing**: A markdown file in `vault/Briefings/` containing the executive summary.
  Required frontmatter: `type: ceo_briefing`, `generated_at` (ISO 8601), `period_start`,
  `period_end`, `status: generated`.

- **BusinessGoal**: An entry in `vault/Business_Goals.md` with a goal title, description,
  and optional target date. Used to align completed work with strategic priorities.

- **BriefingDataSource**: Canonical vault directories read during briefing generation:
  `Business_Goals.md`, `Done/`, `Needs_Action/`, `Accounting/`, `Briefings/`.

- **BriefingLogEntry**: A log record in `vault/Logs/` after briefing generation. Required
  fields: `timestamp`, `action_type: briefing_generation`, `source_path` (vault root),
  `dest_path` (briefing file path), `outcome`, `details`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A CEO can review the weekly briefing and understand business status in under
  5 minutes — measured by briefing length (target: under 500 lines) and section clarity.
- **SC-002**: 100% of briefing files contain all required sections — no missing or empty
  sections except where explicitly documented as "No data available."
- **SC-003**: 100% of briefing generation operations produce a log entry with all six
  required fields — no partial logs.
- **SC-004**: Briefing generation completes successfully even when one or more data sources
  are empty or missing — zero failures due to partial data.
- **SC-005**: Items flagged as bottlenecks in the briefing correlate 100% with items in
  `Needs_Action/` older than 7 days or with overdue deadlines — no false positives or
  missed items.
- **SC-006**: Duplicate briefing requests on the same day produce unique filenames —
  zero overwrites.

---

## Out of Scope

The following are explicitly excluded from Phase 4:

- Sending the briefing via email, Slack, or any messaging platform
- Posting the briefing to social media
- Generating briefings for time periods other than the current week
- Historical trend analysis across multiple weeks
- Interactive dashboards or visualizations
- Real-time or continuous briefing updates (batch generation only)
- Odoo API calls or any external accounting system queries (reads vault `Accounting/` only)
- Modifying any vault files except writing to `Briefings/` and `Logs/`
- Any Platinum-tier or cloud features
- Any SpecifyPlus modifications (`.specify/`, `.claude/`)
- Reliability or autonomous completion improvements (Phase 5)
- Any implementation work not covered by this spec

---

## Dependencies and Assumptions

**Dependencies**:

- Gold Phase 3 complete (social media expansion, vault lifecycle) — required for
  `Done/<platform>/` data to exist.
- Gold Phase 2 complete (Odoo accounting) — required for `vault/Accounting/` data to exist.
- Gold Phase 1 complete (vault boundaries, audit logger) — required for consistent vault
  structure and logging.
- Constitution v3.0.0 ratified — confirmed 2026-04-14.
- `sentinel.logger.write_log_entry` (6-field) available and tested.
- `VAULT_PATH` environment variable set.

**Assumptions**:

- `Business_Goals.md` is a single markdown file in the vault root with a consistent format:
  `## Goal: <title>` headings with descriptive text underneath. Goal alignment for `Done/`
  items uses `goal:` frontmatter matching the goal title slug.
- Accounting data in `vault/Accounting/` follows the structure from Phase 2: `invoices/`
  and `payments/` subdirectories with markdown files containing `amount:`, `status:`, and
  `date:` frontmatter.
- The briefing period is the past 7 days from the generation date. Items with `captured_at`
  or `completed_at` outside this window are excluded from the Completed Tasks section but
  included in Bottlenecks/Deadlines if relevant.
- Briefing generation is triggered manually (CLI command or MCP tool call) — no cron
  scheduler is implemented in this phase.
- The briefing output is plain markdown compatible with Obsidian — no custom plugins or
  dataview queries required.
- Proactive suggestions are rule-based (threshold checks), not AI-generated — no LLM calls
  during briefing generation.
