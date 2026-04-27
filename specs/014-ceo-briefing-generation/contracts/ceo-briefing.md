# Contract: CEO Briefing Generator

**Feature**: Gold Phase 4 — CEO Briefing Generation
**Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-17
**Type**: Vault file contract + CLI contract

---

## Overview

The `ceo_briefing` package has no network API. Its contracts are:
1. **CLI contract** — the commands, flags, and exit codes exposed by `__main__.py`
2. **Briefing file contract** — the structure of `vault/Briefings/*.md`
3. **Signal file contract** — the structure of `vault/Signals/*.md`
4. **Log entry contract** — the 6-field format appended to `vault/Logs/`

---

## 1. CLI Contract

### Entry point

```
python -m ceo_briefing [OPTIONS] COMMAND
```

Installed entry point: `ceo-briefing` (registered in `pyproject.toml`).

### Global options

| Option | Default | Description |
|--------|---------|-------------|
| `--vault-path PATH` | `$VAULT_PATH` env | Override vault root |
| `--debug / --no-debug` | `False` | Enable debug logging |

### Commands

#### `run` — One-shot briefing generation

```
ceo-briefing run [--vault-path PATH]
```

**Behaviour**:
1. Load config from `.env` + optional CLI overrides
2. Call `ensure_vault_dirs` (creates `Briefings/`, `Signals/`, `Logs/` if absent)
3. Scan vault sources within lookback window
4. Build `BriefingContext`
5. Detect bottlenecks → write signal files
6. Synthesise briefing (LLM or template fallback)
7. Write `vault/Briefings/<date>_Monday_Briefing.md`
8. Write 6-field log entry
9. Print path of written briefing to stdout
10. Exit 0 on success, 1 on unrecoverable failure

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Briefing written successfully (LLM or template mode) |
| 1 | Unrecoverable error (vault_path missing/invalid, config error) |

**Stdout** (on success):
```
Briefing written: vault/Briefings/2026-04-21_Monday_Briefing.md
Signals written: 2
Log entry: vault/Logs/ceo_briefing-2026-04-21.md
```

#### `watch` — Scheduled execution (stays alive)

```
ceo-briefing watch [--vault-path PATH]
```

**Behaviour**:
1. Load config (requires `BRIEFING_SCHEDULE=monday` or similar)
2. Schedule briefing generation at `BRIEFING_TIME` on the configured day
3. Log next scheduled time to stdout
4. Enter `schedule.run_pending()` loop with 60-second sleep intervals
5. On SIGINT/SIGTERM: log shutdown and exit 0

**Stdout** (after start):
```
CEO Briefing Watch mode started.
Next briefing scheduled for: 2026-04-28 08:00:00
Press Ctrl+C to stop.
```

#### `status` — Show last run stats

```
ceo-briefing status [--vault-path PATH]
```

**Behaviour**: Read the most recent briefing file in `vault/Briefings/` and print its
frontmatter fields. If no briefing exists, print "No briefings found."

**Stdout** (on success):
```
Last Briefing: 2026-04-21_Monday_Briefing.md
Generated at: 2026-04-21T08:01:23Z
Synthesis: llm
Completed tasks: 14
Bottlenecks: 2
Accounting total: 4250.00
```

---

## 2. Briefing File Contract

### Path

```
vault/Briefings/<YYYY-MM-DD>_Monday_Briefing.md
```

Where `YYYY-MM-DD` is the actual date of generation (`datetime.utcnow().date()`).

### YAML Frontmatter (all fields required)

```yaml
---
type: briefing
generated_at: <ISO-8601 UTC>         # e.g., 2026-04-21T08:01:23Z
lookback_days: <int>                 # e.g., 7
sources_scanned:                     # list of vault dirs actually read
  - vault/Done/
  - vault/Needs_Action/
  - vault/Accounting/
sources_missing:                     # list of vault dirs that did not exist
  - vault/Pending_Approval/
synthesis: llm                       # or: template_fallback
completed_count: <int>               # len(BriefingContext.completed)
bottleneck_count: <int>              # len(BriefingContext.bottlenecks)
accounting_total: <float>            # BriefingContext.total_revenue (paid invoices)
---
```

### Body structure (all six sections mandatory)

```markdown
# CEO Briefing — <date>

## Executive Summary

<Goals progress + week narrative>

## Revenue / Business Summary

<Accounting events + totals>

## Completed Tasks

<Done/ files from lookback window>

## Bottlenecks

<Stale Needs_Action/ and Pending_Approval/ items>

## Proactive Suggestions

<LLM-generated or template recommendations>

## Upcoming Deadlines

<Files with due_date within next 7 days, or "No upcoming deadlines detected.">
```

**Invariants**:
- All six section headings (`## `) MUST be present even when their content is empty.
- When a section has no data, its body MUST contain a fallback phrase (e.g.,
  "No completed tasks recorded this week.").
- The file MUST be valid Obsidian-compatible Markdown (YAML frontmatter + body).
- The file MUST NOT contain any credential patterns (redacted before write).

---

## 3. Signal File Contract

### Path

```
vault/Signals/<YYYY-MM-DD>-<signal_type>-<8-char-hash>.md
```

Where `<8-char-hash>` is the first 8 hex chars of `sha1(source_path)`.

**Example**: `vault/Signals/2026-04-21-bottleneck-a3f2b1c4.md`

### YAML Frontmatter (all fields required)

```yaml
---
type: signal
signal_type: bottleneck            # or: stale_approval | suggestion
source_path: <absolute-or-relative path of the source vault file>
age_days: <int>                    # (now - captured_at).days
captured_at: <ISO-8601 UTC>        # from source file frontmatter or mtime
generated_at: <ISO-8601 UTC>       # when this signal was written
---
```

### Body

One sentence describing the detected signal. Example:

```markdown
File has been in Needs_Action/ for 11 days without resolution.
```

**Invariants**:
- `signal_type` MUST be one of: `bottleneck`, `stale_approval`, `suggestion`.
- `source_path` MUST refer to an existing vault file.
- File is idempotent: re-running with the same `source_path` overwrites the signal file.

---

## 4. Log Entry Contract

Appended to `vault/Logs/ceo_briefing-<YYYY-MM-DD>.md`.

### Format (inline YAML block per entry, separated by `---`)

```yaml
---
timestamp: 2026-04-21T08:01:23Z
action_type: generate_briefing
source_path: vault/
dest_path: vault/Briefings/2026-04-21_Monday_Briefing.md
outcome: success
details: "lookback_days=7; completed=14; bottlenecks=2; synthesis=llm; signals_written=2"
---
```

**Outcome values**:

| Value | Meaning |
|-------|---------|
| `success` | Briefing written with LLM synthesis |
| `partial` | Briefing written with template fallback (LLM unavailable) |
| `failure` | Briefing not written (config error or vault_path invalid) |

**Invariants**:
- All 6 fields mandatory per Constitution Principle IX.
- Log file is append-only; existing entries MUST NOT be modified.
- Each run produces exactly one log entry.

---

## 5. Environment Variables Contract

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_PATH` | Yes | — | Absolute path to vault root |
| `OPENAI_API_KEY` | No | — | If absent, template fallback mode |
| `OPENAI_MODEL` | No | `gpt-4o` | Model for synthesis |
| `BRIEFING_LOOKBACK_DAYS` | No | `7` | Days to look back for Done/ and Accounting/ |
| `BRIEFING_BOTTLENECK_DAYS` | No | `7` | Age threshold for bottleneck detection |
| `BRIEFING_GOALS_MAX_CHARS` | No | `4000` | Max chars from Business_Goals.md |
| `BRIEFING_CONTEXT_MAX_TOKENS` | No | `6000` | Token cap on BriefingContext JSON |
| `BRIEFING_SCHEDULE` | No | — | `monday` (or day name) for watch mode |
| `BRIEFING_TIME` | No | `08:00` | Time of day for scheduled execution (HH:MM) |
