# Implementation Plan: Gold Phase 4 — CEO Briefing Generation

**Branch**: `014-ceo-briefing-generation` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-ceo-briefing-generation/spec.md`

## Summary

Build a weekly CEO Briefing system that reads from vault data sources (Business_Goals.md,
Done/, Needs_Action/, Accounting/, Briefings/) and generates an executive markdown summary
at `vault/Briefings/YYYY-MM-DD_<type>_Briefing.md`. The system is read-only with respect
to external systems — it aggregates existing vault data into a single briefing document.

Technical approach: Python 3.12 module following existing orchestrator/sentinel patterns.
Uses the established vault reader utilities, YAML frontmatter parsing (python-frontmatter),
and audit logger. No external API calls; all data is local vault files.

## Technical Context

**Language/Version**: Python 3.12 (project standard)
**Primary Dependencies**:
- `python-frontmatter>=1.0` (existing) — parse vault file YAML frontmatter
- `pyyaml>=6.0` (existing) — YAML handling
- `python-dotenv>=1.0` (existing) — `VAULT_PATH` environment variable
- `click>=8.0` (existing) — CLI interface

**Storage**: Local filesystem (vault directories under `VAULT_PATH`)
**Testing**: `pytest>=7.0` with `pytest-asyncio>=0.21` (existing dev dependencies)
**Target Platform**: Linux/macOS local execution
**Project Type**: Single project (extends existing `src/` structure)
**Performance Goals**: Generate briefing in under 30 seconds for typical vault (1000 files)
**Constraints**: Read-only vault access except for `Briefings/` and `Logs/` writes
**Scale/Scope**: Single-user local vault; typical volume: 50–500 items per week

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | ✅ PASS | Pure filesystem reads from vault; no cloud dependencies |
| II. Canonical Folders | ✅ PASS | Reads from standard dirs; writes only to `/Briefings` and `/Logs` |
| III. Tiered Scope | ✅ PASS | Phase 4 CEO briefing is explicitly Gold Tier item #10 |
| IV. Safety-First | ✅ PASS | No external actions; briefing is informational output only |
| V. Ralph Wiggum Loop | ✅ PASS | File read failures retry 3 times before fallback text |
| VI. HITL Approval | ✅ PASS | No external actions; briefing distribution is human choice |
| VII. Credential Isolation | ✅ PASS | No credentials needed; reads local vault files only |
| VIII. Agent Skills/MCP | ✅ PASS | Briefing generator is a named skill callable by orchestrator |
| IX. Audit Logging | ✅ PASS | Every briefing generation logged to `/Logs` with 6 fields |
| X. Graceful Degradation | ✅ PASS | Missing data sources produce "No data" text, not failures |
| XI. Phased Development | ✅ PASS | Phase 4 spec; Phases 1–3 complete per spec prerequisites |
| XII. Scope Boundary | ✅ PASS | Work scoped to Phase 4 only; no SpecifyPlus modifications |

**Gate Result**: PASS — all 12 principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/014-ceo-briefing-generation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contract, no MCP for this phase)
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── briefing_generator/          # NEW — Phase 4 briefing module
│   ├── __init__.py              # Public API: generate_briefing()
│   ├── __main__.py              # CLI entry point (sentinel-briefing command)
│   ├── config.py                # Configuration (VAULT_PATH, thresholds)
│   ├── models.py                # Data classes: BriefingData, GoalProgress, etc.
│   ├── readers/                 # Vault data readers
│   │   ├── __init__.py
│   │   ├── goals_reader.py      # Parse Business_Goals.md
│   │   ├── done_reader.py       # Scan Done/ for completed items
│   │   ├── needs_action_reader.py  # Scan Needs_Action/ for bottlenecks
│   │   ├── accounting_reader.py # Parse Accounting/invoices/ and payments/
│   │   └── deadline_reader.py   # Scan vault for deadline: frontmatter
│   ├── analyzers/               # Data analysis and suggestion generation
│   │   ├── __init__.py
│   │   ├── bottleneck_analyzer.py   # Identify stale items (>7 days)
│   │   ├── suggestion_generator.py  # Rule-based proactive suggestions
│   │   └── goal_progress.py         # Align completed work to goals
│   ├── writer.py                # Generate briefing markdown
│   ├── vault_writer.py          # Write to Briefings/, handle deduplication
│   └── logger.py                # Wrap sentinel.logger for briefing-specific logs
├── sentinel/
│   └── logger.py                # (existing) write_log_entry — reused
├── orchestrator/
│   └── plan_writer.py           # (existing) _safe_slug, _deduplicate_path — patterns reused

tests/
├── unit/
│   └── briefing_generator/
│       ├── test_readers.py      # Unit tests for vault readers
│       ├── test_analyzers.py    # Unit tests for analyzers
│       └── test_writer.py       # Unit tests for briefing output
└── integration/
    └── test_briefing_e2e.py     # End-to-end briefing generation test
```

**Structure Decision**: Single project extension. The `briefing_generator` module follows
the same pattern as `email_reasoner` and `orchestrator` — a self-contained package with
`__main__.py` CLI entry point, config, models, and specialized submodules.

## Complexity Tracking

> **No violations to justify** — all Constitution checks passed without exceptions.

## Phase 0: Research

### Research Tasks

1. **Vault YAML Frontmatter Patterns**
   - Examine existing vault files to confirm frontmatter field names
   - Document `captured_at`, `completed_at`, `deadline:`, `goal:`, `amount:`, `status:` patterns

2. **Existing Slug/Deduplication Patterns**
   - Review `orchestrator.plan_writer._safe_slug()` and `_deduplicate_path()`
   - Review `odoo_accounting.vault_writer._unique_path()`
   - Adopt consistent pattern for briefing filenames

3. **Logging Integration**
   - Confirm `sentinel.logger.write_log_entry()` signature
   - Plan briefing-specific `action_type: briefing_generation`

4. **Business_Goals.md Format**
   - Define expected format: `## Goal: <title>` headings
   - Spec assumption: goal alignment via `goal:` frontmatter in Done/ items

### Research Findings

**Documented in**: `research.md`

## Phase 1: Design & Contracts

### Data Model

**Documented in**: `data-model.md`

Key entities:
- `BriefingData`: Aggregated data from all sources
- `GoalProgress`: Goal title + status (on track / at risk / blocked)
- `CompletedItem`: Subject, goal tag, completed date
- `Bottleneck`: Item path, days stale, reason
- `AccountingSummary`: Total invoiced, total paid, overdue items
- `UpcomingDeadline`: Item path, deadline date, days until
- `ProactiveSuggestion`: Suggestion text, category

### CLI Contract

**Documented in**: `contracts/cli.md`

Command: `sentinel-briefing generate`
- `--vault-path`: Override `VAULT_PATH` env var
- `--force-adhoc`: Generate Adhoc briefing even on Monday
- Output: Path to generated briefing file

### Quickstart

**Documented in**: `quickstart.md`

Local development steps:
1. Activate venv
2. Set `VAULT_PATH`
3. Run `sentinel-briefing generate`
4. Verify output in `vault/Briefings/`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        briefing_generator                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │goals_reader │   │ done_reader │   │ accounting  │               │
│  │             │   │             │   │   _reader   │               │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘               │
│         │                 │                 │                       │
│         │    ┌────────────┴────────────┐    │                       │
│         │    │  needs_action_reader    │    │                       │
│         │    │  deadline_reader        │    │                       │
│         │    └────────────┬────────────┘    │                       │
│         │                 │                 │                       │
│         └────────────────►│◄────────────────┘                       │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │  BriefingData   │                                │
│                  │  (aggregated)   │                                │
│                  └────────┬────────┘                                │
│                           │                                         │
│         ┌─────────────────┼─────────────────┐                       │
│         ▼                 ▼                 ▼                       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │ bottleneck  │   │  goal       │   │ suggestion  │               │
│  │ _analyzer   │   │ _progress   │   │ _generator  │               │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘               │
│         │                 │                 │                       │
│         └────────────────►│◄────────────────┘                       │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │     writer      │                                │
│                  │ (markdown gen)  │                                │
│                  └────────┬────────┘                                │
│                           │                                         │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │  vault_writer   │──────►  vault/Briefings/       │
│                  └────────┬────────┘                                │
│                           │                                         │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │     logger      │──────►  vault/Logs/            │
│                  └─────────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Data flow:
1. Readers scan vault directories and parse YAML frontmatter
2. BriefingData aggregates all reader outputs
3. Analyzers compute bottlenecks, goal progress, suggestions
4. Writer renders markdown sections
5. Vault_writer writes to Briefings/ with deduplication
6. Logger records action to Logs/
```

## Key Implementation Decisions

### Decision 1: Briefing Period Window

**Choice**: Past 7 days from generation date
**Rationale**: Aligns with "weekly" briefing cadence; matches bottleneck threshold
**Alternative rejected**: Calendar week (Mon–Sun) — more complex date math, less flexible

### Decision 2: Goal Matching

**Choice**: Case-insensitive slug match between `goal:` frontmatter and `## Goal:` heading
**Rationale**: Simple, deterministic, no fuzzy matching required
**Alternative rejected**: Fuzzy string matching — complexity without clear benefit

### Decision 3: Suggestion Rules

**Choice**: Hardcoded threshold rules (e.g., >5 items in Needs_Action/email/)
**Rationale**: Predictable, testable, no LLM dependency; matches spec
**Alternative rejected**: LLM-generated suggestions — adds latency and API dependency

### Decision 4: Filename Format

**Choice**: `YYYY-MM-DD_Monday_Briefing.md` or `YYYY-MM-DD_Adhoc_Briefing.md`
**Rationale**: Sortable, clear type indicator, matches spec exactly
**Alternative rejected**: UUID suffix — less readable, harder to find manually

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Malformed vault files (bad YAML) | Medium | Low | Skip file with warning; continue processing |
| Very large vault (>10,000 files) | Low | Medium | Add early exit if scan exceeds 60s |
| Missing vault directories | Medium | Low | Create Briefings/ if missing; graceful fallback |

## Dependencies

**Blocking**:
- Gold Phase 3 complete (for Done/<platform>/ social data)
- Gold Phase 2 complete (for Accounting/ data)
- Gold Phase 1 complete (for consistent vault structure)

**Non-blocking**:
- `sentinel.logger.write_log_entry()` — existing, tested
- `python-frontmatter` — existing dependency
