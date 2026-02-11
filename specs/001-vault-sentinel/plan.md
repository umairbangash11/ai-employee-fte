# Implementation Plan: Vault Sentinel

**Branch**: `001-vault-sentinel` | **Date**: 2026-02-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-vault-sentinel/spec.md`

## Summary

Build a Python CLI tool with two commands: `init` (creates the
five canonical vault folders idempotently) and `watch` (monitors
`Inbox/` for new `.txt`/`.pdf` files, writes an execution plan
to `Approved/`, moves the file to `Needs_Action/`, and logs the
action to `Logs/`). Uses `watchdog` for filesystem events with a
size-stability check before moving. Implements the Ralph Wiggum
retry loop (3 attempts) and Safety-First execution plans per
constitution.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: watchdog >=6.0 (filesystem monitoring)
**Storage**: Local filesystem (Markdown files in vault folders)
**Testing**: pytest (using built-in `tmp_path` fixture)
**Target Platform**: Linux (WSL2), macOS (secondary)
**Project Type**: Single project
**Performance Goals**: File detection within 10 seconds of
write completion (SC-002)
**Constraints**: Local-first, no network dependencies for core
operations, vault on WSL2-native filesystem
**Scale/Scope**: Single vault, single Inbox folder, moderate
file throughput (<100 files/day)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after
Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | PASS | All operations are local filesystem; no cloud/network deps |
| II. Canonical Folders | PASS | `init` creates exactly the 5 required folders |
| III. Bronze Tier Scope | PASS | Obsidian vault management + local file monitoring only |
| IV. Safety-First | PASS | Execution plan written to `Approved/` before every move (FR-009) |
| V. Ralph Wiggum Loop | PASS | 3-retry logic with escalation to `Needs_Action` (FR-008) |
| Audit Trail | PASS | Every action logged to `Logs/` as Obsidian-compatible Markdown |
| Obsidian Compat | PASS | Log/plan files use YAML frontmatter + standard Markdown |
| No Secrets | PASS | No API keys or credentials needed for Bronze Tier |

**Post-design re-check**: PASS — no violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-vault-sentinel/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli-contract.md  # CLI interface contract
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── sentinel/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point (argparse)
│   ├── vault.py         # Vault initialization logic
│   ├── watcher.py       # Sentinel file watcher (watchdog)
│   ├── mover.py         # File move with dedup + retry
│   ├── planner.py       # Execution plan writer (Approved/)
│   └── logger.py        # Log entry writer (Logs/)

tests/
├── unit/
│   ├── test_vault.py    # Vault init tests
│   ├── test_mover.py    # File move + dedup tests
│   ├── test_planner.py  # Execution plan tests
│   └── test_logger.py   # Log entry tests
├── integration/
│   └── test_watcher.py  # End-to-end watcher tests
└── conftest.py          # Shared fixtures (tmp vault)
```

**Structure Decision**: Single project layout. The tool is a
standalone CLI with no frontend or API server. All source lives
under `src/sentinel/`, all tests under `tests/`. The package is
runnable via `python -m sentinel`.

## Design Decisions

### D1: Module Separation

The Sentinel is decomposed into focused modules:

- **vault.py**: Only folder creation. No file operations.
- **watcher.py**: Only event detection. Delegates to mover.
- **mover.py**: File move + deduplication + retry loop. Calls
  planner before moving and logger after.
- **planner.py**: Writes execution plan to `Approved/`. Pure
  file I/O — no move logic.
- **logger.py**: Writes log entries to `Logs/`. Pure file I/O.

**Rationale**: Each module is independently testable. The retry
loop lives in `mover.py` wrapping the move+plan+log sequence.

### D2: Retry Logic (Ralph Wiggum Loop)

```
attempt 1: execute as planned
attempt 2: re-read file metadata, adjust dest path, retry
attempt 3: simplify (skip dedup check, use timestamp suffix)
failure:   log to Logs/, move task description to Needs_Action/
```

**Rationale**: Constitution Principle V. Three attempts with
progressive simplification before human escalation.

### D3: File Stability Check

Before moving, the watcher waits for file size to stabilize
(unchanged for 0.5s, checked every 0.1s, timeout 30s). This
prevents moving partially-written files.

### D4: Naming Conflict Resolution

When `Needs_Action/report.txt` exists:
1. Try `report_1.txt`, `report_2.txt`, ... up to `_999`.
2. If all taken (unlikely), use timestamp suffix as fallback.

### D5: Execution Plan (Constitution Principle IV)

Before every file move, a Markdown file is written to `Approved/`
containing: action description, source/dest paths, rollback
strategy, and expected outcome. This happens atomically before
the move. The plan file persists as an audit record.

## Complexity Tracking

> No violations detected — no entries needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
