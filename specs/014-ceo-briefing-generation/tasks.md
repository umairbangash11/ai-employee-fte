# Tasks: Gold Phase 4 — CEO Briefing Generation

**Input**: Design documents from `/specs/014-ceo-briefing-generation/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md

**Tests**: Not explicitly requested in spec. Tests are optional and not included by default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5, US6)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/briefing_generator/`, tests at `tests/` (per plan.md)
- Source structure: `src/briefing_generator/{readers/,analyzers/,*.py}`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and package structure

- [X] T001 Create briefing_generator package structure in `src/briefing_generator/`
- [X] T002 [P] Create `src/briefing_generator/__init__.py` with public API exports
- [X] T003 [P] Create `src/briefing_generator/config.py` with VAULT_PATH config and thresholds
- [X] T004 [P] Create `src/briefing_generator/models.py` with all dataclass definitions from data-model.md
- [X] T005 Register `sentinel-briefing` CLI command in `pyproject.toml` project.scripts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create `src/briefing_generator/readers/__init__.py` with reader module exports
- [X] T007 [P] Create `src/briefing_generator/analyzers/__init__.py` with analyzer module exports
- [X] T008 [P] Create `src/briefing_generator/vault_writer.py` with `_unique_path()` and `write_briefing()` functions
- [X] T009 [P] Create `src/briefing_generator/logger.py` wrapping `sentinel.logger.write_log_entry()` for briefing-specific logging
- [X] T010 Create `src/briefing_generator/__main__.py` with Click CLI skeleton (`generate` and `status` commands)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Weekly Briefing Generation (Priority: P1) 🎯 MVP

**Goal**: Generate a complete weekly briefing from vault data with all required sections

**Independent Test**: Populate test vault with fixtures, run `sentinel-briefing generate`, verify output file created with all sections

### Implementation for User Story 1

- [X] T011 [P] [US1] Create `src/briefing_generator/readers/done_reader.py` with `read_completed_items()` function
- [X] T012 [P] [US1] Create `src/briefing_generator/readers/needs_action_reader.py` with `read_pending_items()` function
- [X] T013 [US1] Create `src/briefing_generator/writer.py` with `generate_briefing_markdown()` function rendering all sections
- [X] T014 [US1] Implement `generate_briefing()` main function in `src/briefing_generator/__init__.py` orchestrating readers → writer → vault_writer → logger
- [X] T015 [US1] Implement `generate` CLI command in `src/briefing_generator/__main__.py` calling `generate_briefing()`
- [X] T016 [US1] Add graceful handling for missing/empty data sources in writer.py (return "No items this period" text)
- [X] T017 [US1] Add audit logging to `generate_briefing()` with all 6 required fields

**Checkpoint**: User Story 1 complete — can generate briefing from vault data with all sections

---

## Phase 4: User Story 2 — On-Demand Briefing Generation (Priority: P1)

**Goal**: Support adhoc briefing generation on any day with proper filename handling

**Independent Test**: Run `sentinel-briefing generate` on non-Monday, verify `YYYY-MM-DD_Adhoc_Briefing.md` created

### Implementation for User Story 2

- [X] T018 [US2] Update `src/briefing_generator/config.py` to detect day of week and set briefing_type ("Monday" vs "Adhoc")
- [X] T019 [US2] Update `src/briefing_generator/vault_writer.py` filename logic for Monday vs Adhoc briefing types
- [X] T020 [US2] Add `--force-adhoc` flag to CLI in `src/briefing_generator/__main__.py`
- [X] T021 [US2] Implement deduplication in `vault_writer.py` using `_unique_path()` pattern (append `-2`, `-3` suffix)

**Checkpoint**: User Story 2 complete — can generate adhoc briefings with unique filenames

---

## Phase 5: User Story 3 — Business Goals Integration (Priority: P2)

**Goal**: Parse Business_Goals.md and show goal progress in briefing

**Independent Test**: Create Business_Goals.md with 3 goals, tag Done/ items with `goal:`, verify Goals Progress section in briefing

### Implementation for User Story 3

- [X] T022 [US3] Create `src/briefing_generator/readers/goals_reader.py` with `read_business_goals()` parsing `## Goal:` headings
- [X] T023 [US3] Create `src/briefing_generator/analyzers/goal_progress.py` with `compute_goal_progress()` aligning items to goals
- [X] T024 [US3] Update `src/briefing_generator/readers/done_reader.py` to extract `goal:` frontmatter from completed items
- [X] T025 [US3] Update `src/briefing_generator/writer.py` to render Goals Progress section (table with status indicators)
- [X] T026 [US3] Add "No business goals defined" fallback text in writer.py when Business_Goals.md missing

**Checkpoint**: User Story 3 complete — briefing shows goal progress with status indicators

---

## Phase 6: User Story 4 — Accounting Data Summary (Priority: P2)

**Goal**: Aggregate accounting data into Revenue/Business Summary section

**Independent Test**: Populate Accounting/invoices/ and payments/ with fixtures, verify totals in briefing

### Implementation for User Story 4

- [X] T027 [P] [US4] Create `src/briefing_generator/readers/accounting_reader.py` with `read_accounting_data()` parsing invoices and payments
- [X] T028 [US4] Update `src/briefing_generator/models.py` to include `AccountingSummary` and `OverdueInvoice` dataclasses (if not already present)
- [X] T029 [US4] Update `src/briefing_generator/writer.py` to render Revenue/Business Summary section with totals
- [X] T030 [US4] Add "No accounting data available" fallback text in writer.py when Accounting/ missing

**Checkpoint**: User Story 4 complete — briefing includes accounting totals

---

## Phase 7: User Story 5 — Bottleneck and Deadline Identification (Priority: P2)

**Goal**: Flag stale items (>7 days in Needs_Action) and upcoming/overdue deadlines

**Independent Test**: Add items to Needs_Action/ older than 7 days, add deadline: frontmatter, verify Bottlenecks and Upcoming Deadlines sections

### Implementation for User Story 5

- [X] T031 [US5] Create `src/briefing_generator/analyzers/bottleneck_analyzer.py` with `identify_bottlenecks()` finding stale items
- [X] T032 [P] [US5] Create `src/briefing_generator/readers/deadline_reader.py` with `read_deadlines()` scanning vault for deadline: frontmatter
- [X] T033 [US5] Update `src/briefing_generator/analyzers/bottleneck_analyzer.py` to include overdue deadlines in bottlenecks
- [X] T034 [US5] Update `src/briefing_generator/writer.py` to render Bottlenecks section (table with days stale/overdue)
- [X] T035 [US5] Update `src/briefing_generator/writer.py` to render Upcoming Deadlines section (sorted by date)
- [X] T036 [US5] Add "No bottlenecks identified" and "No upcoming deadlines" fallback text in writer.py

**Checkpoint**: User Story 5 complete — briefing flags bottlenecks and deadlines

---

## Phase 8: User Story 6 — Proactive Suggestions (Priority: P3)

**Goal**: Generate rule-based suggestions based on observed patterns

**Independent Test**: Add 10+ items to Needs_Action/email/, verify suggestion about email backlog appears

### Implementation for User Story 6

- [X] T037 [US6] Create `src/briefing_generator/analyzers/suggestion_generator.py` with `generate_suggestions()` implementing threshold rules
- [X] T038 [US6] Implement email backlog rule (>5 items in Needs_Action/email/) in suggestion_generator.py
- [X] T039 [US6] Implement social activity rule (>10 posts in Done/facebook/+instagram/+x/) in suggestion_generator.py
- [X] T040 [US6] Implement overdue invoice rule (>0 overdue invoices) in suggestion_generator.py
- [X] T041 [US6] Implement stale plans rule (>3 items in Needs_Action/plans/ >7 days) in suggestion_generator.py
- [X] T042 [US6] Update `src/briefing_generator/writer.py` to render Proactive Suggestions section
- [X] T043 [US6] Add "No suggestions this period" fallback text in writer.py

**Checkpoint**: User Story 6 complete — briefing includes proactive suggestions

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T044 [P] Implement `status` CLI command in `src/briefing_generator/__main__.py` showing vault statistics
- [X] T045 [P] Add `--dry-run` flag to CLI for preview without writing
- [X] T046 [P] Add `--verbose` flag to CLI for debug output
- [X] T047 Implement Ralph Wiggum Loop (3 retries) in readers for file read failures
- [X] T048 Add data_gaps tracking in BriefingData for skipped malformed files
- [X] T049 Add Data Gaps footer in writer.py listing files that couldn't be parsed
- [X] T050 Ensure vault/Briefings/ directory is created if missing in vault_writer.py
- [X] T051 Run quickstart.md validation — verify end-to-end workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–8)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (both P1)
  - US3, US4, US5 can proceed in parallel after US1/US2 (all P2)
  - US6 can proceed after US5 (uses bottleneck data)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Can Parallelize With |
|-------|----------|------------|---------------------|
| US1 | P1 | Foundational | US2 |
| US2 | P1 | Foundational | US1 |
| US3 | P2 | US1 (uses done_reader) | US4, US5 |
| US4 | P2 | US1 (uses writer) | US3, US5 |
| US5 | P2 | US1 (uses needs_action_reader) | US3, US4 |
| US6 | P3 | US5 (uses bottleneck data) | — |

### Within Each User Story

- Readers before analyzers
- Analyzers before writer updates
- Writer updates before integration
- Integration before fallback text

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different files)
- T006, T007, T008, T009 can run in parallel (different modules)
- T011, T012 can run in parallel (different readers)
- T027, T032 can run in parallel (different readers)
- T044, T045, T046 can run in parallel (CLI additions)

---

## Parallel Example: Foundational Phase

```bash
# Launch these foundational tasks together:
Task: "Create src/briefing_generator/readers/__init__.py with reader module exports"
Task: "Create src/briefing_generator/analyzers/__init__.py with analyzer module exports"
Task: "Create src/briefing_generator/vault_writer.py with _unique_path() and write_briefing() functions"
Task: "Create src/briefing_generator/logger.py wrapping sentinel.logger.write_log_entry()"
```

## Parallel Example: User Story 1 Readers

```bash
# Launch these reader tasks together:
Task: "Create src/briefing_generator/readers/done_reader.py with read_completed_items() function"
Task: "Create src/briefing_generator/readers/needs_action_reader.py with read_pending_items() function"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (core briefing generation)
4. Complete Phase 4: User Story 2 (adhoc briefings)
5. **STOP and VALIDATE**: Test end-to-end with `sentinel-briefing generate`
6. Deploy/demo if ready

**MVP delivers**: A working CEO briefing with all sections, Monday or adhoc

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 + US2 → **MVP!** Core briefing works
3. Add US3 → Goals integration
4. Add US4 → Accounting summary
5. Add US5 → Bottlenecks and deadlines
6. Add US6 → Proactive suggestions
7. Polish → CLI enhancements, error handling

### Task Count Summary

| Phase | Task Count |
|-------|------------|
| Setup | 5 |
| Foundational | 5 |
| US1 (P1 MVP) | 7 |
| US2 (P1) | 4 |
| US3 (P2) | 5 |
| US4 (P2) | 4 |
| US5 (P2) | 6 |
| US6 (P3) | 7 |
| Polish | 8 |
| **Total** | **51** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after completion
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file writes use `_unique_path()` to avoid overwrites
- All readers handle missing directories gracefully (return empty list)
- All writer sections have fallback text for missing data
