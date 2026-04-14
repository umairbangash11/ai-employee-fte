# Implementation Plan: Email Reasoning Layer

**Feature Branch**: `004-email-reasoning`
**Phase**: 2 — Email Reasoning Layer
**Created**: 2026-03-07
**Status**: Draft
**Constitution**: v2.0.0 (Principles II, IV, VI, VII)

## Overview

This plan defines the architecture and implementation strategy for the Email Reasoning Layer. The system reads email markdown files from `/Inbox/email/`, classifies them using GPT-4o, and generates task/plan files for actionable emails.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      email-reasoner CLI                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Config  │  │  Scanner │  │Classifier│  │     Writer       │ │
│  │  Loader  │  │          │  │  (LLM)   │  │  (Tasks/Plans)   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │             │             │                  │           │
│       ▼             ▼             ▼                  ▼           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Reasoner Engine                       │   │
│  │  (Orchestrates: scan → filter → classify → generate)      │   │
│  └────────────────────────────────┬─────────────────────────┘   │
│                                   │                              │
└───────────────────────────────────┼──────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ /Inbox/email/ │          │ /Needs_Action │          │  /Plans/      │
│   (read)      │          │  /tasks/      │          │   (write)     │
└───────────────┘          │   (write)     │          └───────────────┘
                           └───────────────┘
```

### Module Structure

```
src/email_reasoner/
├── __init__.py          # Package init, version
├── __main__.py          # CLI entry point
├── config.py            # Configuration loading
├── scanner.py           # Email file discovery and parsing
├── classifier.py        # LLM classification with OpenAI
├── writer.py            # Task and plan file generation
├── state.py             # Deduplication state management
├── models.py            # Data models (Pydantic + dataclasses)
└── engine.py            # Main orchestration logic
```

## Implementation Phases

### Phase 1: Foundation (T001-T010)

**Objective**: Set up package structure, models, and configuration.

| ID | Task | Acceptance |
|----|------|------------|
| T001 | Create `src/email_reasoner/` package directory | Directory exists |
| T002 | Create `__init__.py` with version 0.1.0 | Import works |
| T003 | Create `models.py` with EmailFile, ClassificationResult | Types validate |
| T004 | Create `models.py` with TaskFile, PlanFile | Types validate |
| T005 | Create `models.py` with ReasonerState | Serialization works |
| T006 | Create `config.py` with ReasonerConfig dataclass | Config loads |
| T007 | Add vault_path, dry_run, limit options to config | All options present |
| T008 | Create `.env` template with OPENAI_API_KEY | Template exists |
| T009 | Add email-reasoner to pyproject.toml scripts | Entry point defined |
| T010 | Create package README with usage | Documentation exists |

### Phase 2: Scanner (T011-T018)

**Objective**: Discover and parse email files from Inbox.

| ID | Task | Acceptance |
|----|------|------------|
| T011 | Create `scanner.py` module | Module imports |
| T012 | Implement `scan_inbox()` to find all .md files | Returns file list |
| T013 | Implement `parse_email_file()` with frontmatter | Parses YAML |
| T014 | Handle missing frontmatter gracefully | Returns None + warning |
| T015 | Handle missing message_id | Returns None + warning |
| T016 | Handle empty body | Returns EmailFile with empty body |
| T017 | Extract wikilink path for source reference | Wikilink format correct |
| T018 | Add unit tests for scanner | Tests pass |

### Phase 3: State Management (T019-T025)

**Objective**: Track processed emails to prevent duplicates.

| ID | Task | Acceptance |
|----|------|------------|
| T019 | Create `state.py` module | Module imports |
| T020 | Implement `load_state()` from JSON | Loads or creates new |
| T021 | Implement `save_state()` to JSON | Persists to file |
| T022 | Implement `is_processed()` check | Returns bool |
| T023 | Implement `mark_processed()` update | State updated |
| T024 | Create `.watcher-state/` directory if missing | Auto-creates |
| T025 | Add unit tests for state management | Tests pass |

### Phase 4: Classifier (T026-T038)

**Objective**: Classify emails using OpenAI GPT-4o.

| ID | Task | Acceptance |
|----|------|------------|
| T026 | Create `classifier.py` module | Module imports |
| T027 | Implement OpenAI client initialization | Client connects |
| T028 | Create system prompt constant | Prompt defined |
| T029 | Create user prompt template | Template defined |
| T030 | Implement `classify_email()` single email | Returns ClassificationResult |
| T031 | Enable JSON mode for structured output | JSON response |
| T032 | Parse LLM response to Pydantic model | Validates |
| T033 | Implement confidence threshold check | Low confidence → informational |
| T034 | Implement retry with backoff (Ralph Wiggum) | 3 attempts |
| T035 | Handle API errors gracefully | Fallback to informational |
| T036 | Truncate long bodies to 4000 tokens | Truncation works |
| T037 | Implement `classify_batch()` for multiple | Batch processing |
| T038 | Add unit tests with mock responses | Tests pass |

### Phase 5: Writer (T039-T050)

**Objective**: Generate task and plan markdown files.

| ID | Task | Acceptance |
|----|------|------------|
| T039 | Create `writer.py` module | Module imports |
| T040 | Implement `generate_task_filename()` | Correct format |
| T041 | Implement `generate_task_frontmatter()` | Valid YAML |
| T042 | Implement `generate_task_body()` | Markdown content |
| T043 | Implement `write_task_file()` | File created |
| T044 | Create `/Needs_Action/tasks/` if missing | Auto-creates |
| T045 | Implement `generate_plan_filename()` | Correct format |
| T046 | Implement `generate_plan_content()` | Steps as checkboxes |
| T047 | Implement `write_plan_file()` | File created |
| T048 | Create `/Plans/` if missing | Auto-creates |
| T049 | Link plan to task via wikilink | Cross-reference works |
| T050 | Add unit tests for writer | Tests pass |

### Phase 6: Engine (T051-T060)

**Objective**: Orchestrate the full reasoning pipeline.

| ID | Task | Acceptance |
|----|------|------------|
| T051 | Create `engine.py` module | Module imports |
| T052 | Implement `ReasonerEngine` class | Class instantiates |
| T053 | Implement `run()` method orchestration | Full pipeline |
| T054 | Integrate scanner → filter → classify → write | End-to-end |
| T055 | Skip already-processed emails | Idempotent |
| T056 | Log classification decisions to `/Logs/` | Log file created |
| T057 | Implement dry-run mode (no file writes) | Preview only |
| T058 | Implement limit option (max N emails) | Honors limit |
| T059 | Handle empty inbox gracefully | No errors |
| T060 | Add integration tests | Tests pass |

### Phase 7: CLI (T061-T070)

**Objective**: Complete CLI with all options.

| ID | Task | Acceptance |
|----|------|------------|
| T061 | Create `__main__.py` with Click | CLI runs |
| T062 | Add `--vault-path` option | Override works |
| T063 | Add `--dry-run` flag | Preview mode |
| T064 | Add `--limit N` option | Limits emails |
| T065 | Add `--state` path override | Custom state path |
| T066 | Add `--verbose` flag | Detailed output |
| T067 | Add `--version` flag | Shows version |
| T068 | Add `--help` flag | Shows help |
| T069 | Load OPENAI_API_KEY from env | API key works |
| T070 | Handle missing API key error | Clear error message |

### Phase 8: Documentation (T071-T075)

**Objective**: Document usage and update project files.

| ID | Task | Acceptance |
|----|------|------------|
| T071 | Create `docs/email-reasoner-setup.md` | Setup guide |
| T072 | Update `phase-2/README.md` with completion | Status updated |
| T073 | Add email-reasoner to pyproject.toml deps | Dependencies listed |
| T074 | Update .gitignore for reasoner state | State excluded |
| T075 | Create example email files for testing | Examples in docs |

## Dependencies

### Internal

| Module | Dependency |
|--------|------------|
| engine | scanner, classifier, writer, state, config |
| __main__ | engine, config |
| writer | models |
| classifier | models |
| scanner | models |
| state | models |

### External

```toml
[project.dependencies]
openai = ">=1.0"
pyyaml = ">=6.0"
python-frontmatter = ">=1.0"
pydantic = ">=2.0"
click = ">=8.0"
python-dotenv = ">=1.0"
```

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Local-First | PASS | All processing local, only OpenAI API external |
| II. Canonical Folders | PASS | Output to /Needs_Action/tasks/, /Plans/, /Logs/ |
| III. Tiered Scope | PASS | Within Silver Tier (email processing) |
| IV. Safety-First | PASS | Read-only on source, no auto-execution |
| V. Ralph Wiggum Loop | PASS | 3 retries with backoff on API failures |
| VI. Silver Tier Autonomy | PASS | Tasks for human review only, no email sending |
| VII. Phased Development | PASS | Scoped to /phase-2/ only |
| VIII. Gmail API Migration Safety | N/A | Not applicable (Phase 1 complete) |

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM misclassification | Medium | Low | Human reviews tasks, can adjust |
| API rate limits | Low | Medium | Batch processing, backoff |
| Large email bodies | Medium | Low | Truncation to 4000 tokens |
| State file corruption | Low | Medium | JSON validation, backup |

## Non-Goals

- Email sending or replying
- Gmail label modification
- Real-time push processing
- Calendar integration
- WhatsApp processing (separate phase)

## Complexity Tracking

| Change | Justification |
|--------|---------------|
| None | Plan follows spec exactly |

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | Actionable emails create tasks | AT-01 |
| SC-002 | Promotional emails don't create tasks | AT-02 |
| SC-003 | Multi-step emails create plans | AT-03 |
| SC-004 | Original emails unchanged | AT-04 |
| SC-005 | Idempotent processing | AT-05 |
| SC-006 | Dry-run creates no files | AT-06 |

---

**Total Tasks**: 75 (T001-T075)

**Next Step**: Run `/sp.tasks` to generate dependency-ordered tasks.md
