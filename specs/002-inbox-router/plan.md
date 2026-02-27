# Implementation Plan: Inbox → Needs_Action Router

**Branch**: `002-inbox-router` | **Date**: 2026-02-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-inbox-router/spec.md`

## Summary

Implement a rule-based router that scans `/Inbox/email/` for markdown files and moves matching files to `/Needs_Action/email/` based on urgency flags (urgent, starred, important), keyword matching (configurable list), and SLA breach (configurable threshold). Uses atomic claim-by-move pattern for safe concurrent operation. All actions logged to `/Logs/`.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: PyYAML >=6.0 (new), watchdog >=6.0 (existing), python-dotenv >=1.0 (existing)
**Storage**: Local filesystem (Markdown files with YAML frontmatter)
**Testing**: pytest >=7.0
**Target Platform**: Linux (WSL2)
**Project Type**: Single project (extends existing src/ structure)
**Performance Goals**: Process 1000 files in <5 seconds
**Constraints**: No external network calls; atomic file operations; Obsidian-compatible output
**Scale/Scope**: Typical inbox: 10-100 files per scan cycle

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Local-First Operations | ✅ PASS | Router operates entirely on local filesystem; no cloud dependencies |
| II. Canonical Folder Structure | ✅ PASS | Uses `/Inbox`, `/Needs_Action`, `/Logs` without modification |
| III. Tiered Scope | ✅ PASS | Local file routing is within Bronze Tier (file monitoring); extends Silver Tier email workflow |
| IV. Safety-First Execution | ⚠️ NOTE | File moves are local operations, not system-modifying scripts requiring `/Approved`. Atomic rename is safe. |
| V. Persistent Retry Logic | ✅ PASS | Router is idempotent; caller (watcher/CLI) can implement retry. Failures logged to `/Logs`. |
| VI. Silver Tier Autonomy | ✅ PASS | No external actions (no sending, replying); read-only monitoring of local files. |

**Constitution Check Result**: **PASS** — No violations. Principle IV note: file moves between vault directories are not "system-modifying scripts" requiring `/Approved` plans; they are internal triage operations.

## Project Structure

### Documentation (this feature)

```text
specs/002-inbox-router/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity definitions
├── quickstart.md        # Developer quickstart
├── contracts/           # API contracts
│   └── router-api.md    # Python module API
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec validation checklist
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── router/                    # NEW: Router module
│   ├── __init__.py           # Public API exports
│   ├── __main__.py           # CLI entry point
│   ├── router.py             # Main routing logic
│   ├── rules.py              # Routing rule definitions
│   ├── config.py             # Configuration loading
│   └── parser.py             # Frontmatter parsing
├── sentinel/                  # EXISTING: File watcher
│   ├── mover.py              # (reference for claim-by-move)
│   ├── logger.py             # (reused for logging)
│   └── ...
└── orchestrator/              # EXISTING: AI brain
    └── brain.py              # (can trigger router)

tests/
├── unit/
│   └── router/
│       ├── test_parser.py    # Frontmatter parsing tests
│       ├── test_rules.py     # Rule evaluation tests
│       └── test_router.py    # Integration tests
└── conftest.py               # Shared fixtures
```

**Structure Decision**: New `src/router/` module added to existing single-project structure. Reuses `sentinel.logger` for audit trails. Consistent with existing sentinel/orchestrator organization.

## Complexity Tracking

> **No violations — table not required**

All implementation choices follow minimal complexity:
- Single module with clear responsibilities
- Reuses existing logging infrastructure
- No external services or APIs
- No database or state management beyond filesystem

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Entry Points                          │
├─────────────┬─────────────────────┬─────────────────────────┤
│   CLI       │    Watchdog Event   │    Orchestrator (brain) │
│ __main__.py │  sentinel/watcher   │    orchestrator/brain   │
└──────┬──────┴──────────┬──────────┴───────────┬─────────────┘
       │                 │                      │
       └────────────────►├◄─────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │      route_inbox()     │
            │      router/router.py  │
            └───────────┬────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ parse_email  │ │evaluate_rules│ │  move_file   │
│ parser.py    │ │  rules.py    │ │  router.py   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PyYAML       │ │ RouterConfig │ │ os.rename()  │
│ (frontmatter)│ │ config.py    │ │ (atomic)     │
└──────────────┘ └──────────────┘ └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │sentinel.logger│
                                  │  (audit log) │
                                  └──────────────┘
```

### Data Flow

```
/Inbox/email/*.md
        │
        │ (1) scan directory
        ▼
    [InboxFile]
        │
        │ (2) parse frontmatter + body
        ▼
    [EmailFrontmatter, body]
        │
        │ (3) evaluate routing rules
        ▼
    [RoutingResult]
        │
        │ (4) if should_route=true
        ▼
/Needs_Action/email/*.md
        │
        │ (5) log action
        ▼
    /Logs/*.md
```

## Implementation Phases

### Phase 1: Core Parser (P1 — Foundation)

**Goal**: Parse markdown files with YAML frontmatter

**Files**:
- `src/router/__init__.py` — Module init
- `src/router/parser.py` — Frontmatter parsing
- `tests/unit/router/test_parser.py` — Parser tests

**Key Logic**:
```python
def parse_email_file(path: Path) -> InboxFile:
    content = path.read_text()
    frontmatter, body = extract_frontmatter(content)
    return InboxFile(path=path, frontmatter=frontmatter, body=body)
```

### Phase 2: Routing Rules (P1 — Core)

**Goal**: Implement flag, keyword, and SLA rules

**Files**:
- `src/router/config.py` — Configuration loading
- `src/router/rules.py` — Rule definitions
- `tests/unit/router/test_rules.py` — Rule tests

**Key Logic**:
```python
def get_default_rules(config: RouterConfig) -> list[RoutingRule]:
    return [
        RoutingRule("flag:urgent", lambda f: f.frontmatter.urgency == "urgent"),
        RoutingRule("flag:starred", lambda f: f.frontmatter.starred),
        RoutingRule("flag:important", lambda f: f.frontmatter.important),
        *[RoutingRule(f"keyword:{kw}", make_keyword_matcher(kw))
          for kw in config.urgency_keywords],
        RoutingRule(f"sla:{config.sla_threshold_hours}h",
                    make_sla_matcher(config.sla_threshold_hours)),
    ]
```

### Phase 3: Router Engine (P1 — Integration)

**Goal**: Scan inbox, evaluate rules, move files

**Files**:
- `src/router/router.py` — Main routing logic
- `tests/unit/router/test_router.py` — Integration tests

**Key Logic**:
```python
def route_inbox(vault_path: Path, config: RouterConfig) -> RoutingReport:
    inbox = vault_path / "Inbox" / "email"
    needs_action = vault_path / "Needs_Action" / "email"

    for md_file in inbox.glob("*.md"):
        file = parse_email_file(md_file)
        result = evaluate_rules(file, config)
        if result.should_route:
            move_file_to_needs_action(file.path, needs_action, logs_dir)
```

### Phase 4: CLI & Integration (P2 — Polish)

**Goal**: CLI entry point, pyproject.toml updates

**Files**:
- `src/router/__main__.py` — CLI
- `pyproject.toml` — Add pyyaml, script entry

**Key Logic**:
```python
@click.command()
@click.option("--vault", default=".")
@click.option("--dry-run", is_flag=True)
def main(vault: str, dry_run: bool):
    report = route_inbox(vault, dry_run=dry_run)
    click.echo(f"Routed: {report.routed_count}")
```

## Dependencies

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| pyyaml | >=6.0 | YAML frontmatter parsing | **NEW** — add to pyproject.toml |
| watchdog | >=6.0 | Filesystem events | Existing |
| python-dotenv | >=1.0 | Configuration | Existing |
| pytest | >=7.0 | Testing | Existing |

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Race condition on concurrent move | Low | Medium | Claim-by-move pattern handles gracefully |
| Malformed YAML causes crash | Medium | Low | Catch YAMLError, skip file, log warning |
| Large inbox causes timeout | Low | Medium | Single-pass iteration; 1000 files × 5ms = 5s |
| Disk full during move | Low | High | Atomic rename fails safely; original preserved |

## Success Criteria Mapping

| Success Criterion | Implementation |
|-------------------|----------------|
| SC-001: 100% rules match routed | `test_router.py` verifies all rule types |
| SC-002: Zero data loss | Atomic `os.rename()`, checksum test |
| SC-003: Audit log within 1s | `sentinel.logger` call after move |
| SC-004: 1000 files <5s | Performance test with fixture |
| SC-005: Malformed files logged | `test_parser.py` error handling |
| SC-006: SLA breach detection | `test_rules.py` SLA matcher |

## Next Steps

1. Run `/sp.tasks` to generate ordered task list
2. Implement Phase 1 (parser) first
3. Add pyyaml to pyproject.toml
4. TDD: Write tests before implementation

---

**Plan complete. Ready for `/sp.tasks`.**
