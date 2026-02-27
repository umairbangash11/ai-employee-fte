# Tasks: Inbox → Needs_Action Router

**Input**: Design documents from `/specs/002-inbox-router/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/router-api.md

**Tests**: Test tasks included (TDD approach per plan.md recommendation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Priority | Description |
|-------|----------|-------------|
| US1 | P1 | Route Important/Starred Emails (flag-based) |
| US2 | P2 | Route Emails Matching Keywords |
| US3 | P3 | Route SLA-Breaching Emails |
| US4 | P1 | Claim-by-Move Pattern (foundational — merged into Phase 2) |
| US5 | P2 | Audit Trail for Routing (cross-cutting — merged into Phase 2) |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency configuration

- [x] T001 Create `src/router/` directory structure per plan.md
- [x] T002 Create `src/router/__init__.py` with public API exports (route_inbox, evaluate_file, RouterConfig)
- [x] T003 [P] Add `pyyaml>=6.0` to `pyproject.toml` dependencies
- [x] T004 [P] Create `tests/unit/router/` directory for test files
- [x] T005 [P] Create `tests/unit/router/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by ALL user stories (includes US4 claim-by-move and US5 logging)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration

- [x] T006 [P] Create `src/router/config.py` with RouterConfig dataclass and `load_router_config()` function per contracts/router-api.md
- [x] T007 [P] Write test `tests/unit/router/test_config.py` for configuration loading with default values and .env overrides

### Parser (InboxFile + EmailFrontmatter entities)

- [x] T008 [P] Create `src/router/parser.py` with `parse_email_file()` function and InboxFile/EmailFrontmatter dataclasses per data-model.md
- [x] T009 [P] Write test `tests/unit/router/test_parser.py` for frontmatter parsing including valid YAML, malformed YAML, and missing fields
- [x] T010 Implement `extract_frontmatter()` helper in `src/router/parser.py` using PyYAML safe_load per research.md
- [x] T011 Add MalformedFrontmatterError exception class in `src/router/parser.py` per contracts/router-api.md

### Claim-by-Move (US4 — Foundational for all routing)

- [x] T012 [P] Write test `tests/unit/router/test_mover.py` for atomic move, claimed scenario, and error handling
- [x] T013 Create `move_file_to_needs_action()` function in `src/router/router.py` using `os.rename()` for atomic move per research.md
- [x] T014 Implement claim-by-move pattern: catch FileNotFoundError to detect already-claimed files per contracts/router-api.md
- [x] T015 Add MoveResult dataclass in `src/router/router.py` per contracts/router-api.md

### Logging (US5 — Foundational for audit trail)

- [x] T016 Integrate `sentinel.logger.write_log_entry()` into `move_file_to_needs_action()` for routing audit trail
- [x] T017 Add routing-specific log entry format with matched_rules field in `src/router/router.py`

### Rule Framework

- [x] T018 Create `src/router/rules.py` with RoutingRule dataclass and `evaluate_rules()` function per data-model.md
- [x] T019 Create RoutingResult dataclass in `src/router/rules.py` per data-model.md

**Checkpoint**: Foundation ready — parser, config, mover, logger, rule framework complete. User story implementation can now begin.

---

## Phase 3: User Story 1 - Route Important/Starred Emails (Priority: P1) 🎯 MVP

**Goal**: Route files with `urgency: urgent`, `starred: true`, or `important: true` flags to `/Needs_Action/email/`

**Independent Test**: Place a markdown file with `urgency: urgent` in `/Inbox/email/` and verify it moves to `/Needs_Action/email/` within one routing cycle.

### Tests for User Story 1

- [x] T020 [P] [US1] Write test `tests/unit/router/test_rules.py::test_flag_urgent_rule` for urgency=urgent matching
- [x] T021 [P] [US1] Write test `tests/unit/router/test_rules.py::test_flag_starred_rule` for starred=true matching
- [x] T022 [P] [US1] Write test `tests/unit/router/test_rules.py::test_flag_important_rule` for important=true matching
- [x] T023 [P] [US1] Write test `tests/unit/router/test_rules.py::test_flag_no_match` for files without flags (should not route)

### Implementation for User Story 1

- [x] T024 [US1] Implement `make_flag_rules()` in `src/router/rules.py` returning flag:urgent, flag:starred, flag:important rules
- [x] T025 [US1] Add flag rules to `get_default_rules()` in `src/router/rules.py`
- [x] T026 [US1] Implement `route_inbox()` core loop in `src/router/router.py`: scan /Inbox/email/, parse, evaluate, move matching files
- [x] T027 [US1] Add RoutingReport dataclass in `src/router/router.py` per contracts/router-api.md
- [x] T028 [US1] Write integration test `tests/unit/router/test_router.py::test_route_flag_urgent` with fixture vault

**Checkpoint**: User Story 1 complete. Flag-based routing functional. MVP achieved.

---

## Phase 4: User Story 2 - Route Emails Matching Keywords (Priority: P2)

**Goal**: Route files containing configured keywords (case-insensitive) in subject or body to `/Needs_Action/email/`

**Independent Test**: Place a markdown file with "URGENT" in the subject into `/Inbox/email/` and verify it moves to `/Needs_Action/email/`.

### Tests for User Story 2

- [x] T029 [P] [US2] Write test `tests/unit/router/test_rules.py::test_keyword_in_subject` for keyword match in subject
- [x] T030 [P] [US2] Write test `tests/unit/router/test_rules.py::test_keyword_in_body` for keyword match in body
- [x] T031 [P] [US2] Write test `tests/unit/router/test_rules.py::test_keyword_case_insensitive` for case-insensitive matching
- [x] T032 [P] [US2] Write test `tests/unit/router/test_rules.py::test_keyword_no_match` for files without keywords

### Implementation for User Story 2

- [x] T033 [US2] Implement `make_keyword_matcher()` factory in `src/router/rules.py` per research.md
- [x] T034 [US2] Implement `make_keyword_rules()` in `src/router/rules.py` generating rules from config.urgency_keywords
- [x] T035 [US2] Add keyword rules to `get_default_rules()` in `src/router/rules.py`
- [x] T036 [US2] Write integration test `tests/unit/router/test_router.py::test_route_keyword_match` with fixture vault

**Checkpoint**: User Story 2 complete. Keyword-based routing functional.

---

## Phase 5: User Story 3 - Route SLA-Breaching Emails (Priority: P3)

**Goal**: Route files where `captured_at` timestamp exceeds configurable SLA threshold to `/Needs_Action/email/`

**Independent Test**: Place a markdown file with `captured_at` older than 24 hours (default SLA) and verify it moves after the router runs.

### Tests for User Story 3

- [x] T037 [P] [US3] Write test `tests/unit/router/test_rules.py::test_sla_breach_default` for 24-hour SLA breach
- [x] T038 [P] [US3] Write test `tests/unit/router/test_rules.py::test_sla_within_threshold` for files within SLA (should not route)
- [x] T039 [P] [US3] Write test `tests/unit/router/test_rules.py::test_sla_custom_threshold` for custom 4-hour SLA breach
- [x] T040 [P] [US3] Write test `tests/unit/router/test_rules.py::test_sla_invalid_timestamp` for malformed captured_at handling

### Implementation for User Story 3

- [x] T041 [US3] Implement `is_sla_breached()` helper in `src/router/rules.py` using datetime.fromisoformat() per research.md
- [x] T042 [US3] Implement `make_sla_matcher()` factory in `src/router/rules.py`
- [x] T043 [US3] Implement `make_sla_rule()` in `src/router/rules.py` using config.sla_threshold_hours
- [x] T044 [US3] Add SLA rule to `get_default_rules()` in `src/router/rules.py`
- [x] T045 [US3] Write integration test `tests/unit/router/test_router.py::test_route_sla_breach` with fixture vault and backdated captured_at

**Checkpoint**: User Story 3 complete. SLA-based routing functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: CLI, edge cases, and final integration

### CLI Entry Point

- [x] T046 [P] Create `src/router/__main__.py` with click command per contracts/router-api.md
- [x] T047 Add `route-inbox` script entry to `pyproject.toml` under `[project.scripts]`

### Edge Cases & Error Handling

- [x] T048 [P] Implement dry_run mode in `route_inbox()` in `src/router/router.py`
- [x] T049 [P] Add destination directory auto-creation in `move_file_to_needs_action()` per FR-011
- [x] T050 Write test `tests/unit/router/test_router.py::test_multiple_rules_match` for file matching multiple rules (log all, move once)
- [x] T051 Write test `tests/unit/router/test_router.py::test_malformed_frontmatter_skipped` for graceful handling per FR-012
- [x] T052 Implement `evaluate_file()` standalone function in `src/router/router.py` per contracts/router-api.md

### Documentation & Validation

- [x] T053 Run quickstart.md validation: create test email, run router, verify moved to /Needs_Action/email/
- [x] T054 Verify all tests pass: `pytest tests/unit/router/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3)
  - Or in parallel if staffed
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — No dependencies on US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — No dependencies on US1/US2

All user stories share the foundational components but are otherwise independent.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Rule factory → Rule implementation → get_default_rules() integration → Integration test
- Story complete before moving to next priority

### Parallel Opportunities

| Phase | Parallel Tasks |
|-------|---------------|
| Phase 1 | T003, T004, T005 |
| Phase 2 | T006-T007, T008-T009, T012 |
| Phase 3 (US1) | T020-T023 (tests) |
| Phase 4 (US2) | T029-T032 (tests) |
| Phase 5 (US3) | T037-T040 (tests) |
| Phase 6 | T046, T048, T049 |

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Write test tests/unit/router/test_rules.py::test_flag_urgent_rule"
Task: "Write test tests/unit/router/test_rules.py::test_flag_starred_rule"
Task: "Write test tests/unit/router/test_rules.py::test_flag_important_rule"
Task: "Write test tests/unit/router/test_rules.py::test_flag_no_match"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T019)
3. Complete Phase 3: User Story 1 (T020-T028)
4. **STOP and VALIDATE**: Test US1 with real email file
5. Deploy/demo if ready — flag-based routing works!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP achieved**
3. Add User Story 2 → Test independently → Keyword routing added
4. Add User Story 3 → Test independently → SLA routing added
5. Add Polish → CLI, edge cases, documentation

Each story adds routing capability without breaking previous stories.

---

## Summary

| Phase | Task Range | Count | Key Deliverable |
|-------|-----------|-------|-----------------|
| Phase 1: Setup | T001-T005 | 5 | Project structure, dependencies |
| Phase 2: Foundational | T006-T019 | 14 | Parser, config, mover, logger, rule framework |
| Phase 3: US1 (P1) | T020-T028 | 9 | Flag-based routing (MVP) |
| Phase 4: US2 (P2) | T029-T036 | 8 | Keyword matching |
| Phase 5: US3 (P3) | T037-T045 | 9 | SLA breach detection |
| Phase 6: Polish | T046-T054 | 9 | CLI, edge cases, validation |
| **Total** | T001-T054 | **54** | Full router implementation |

**MVP Scope**: Phases 1-3 (28 tasks) — delivers flag-based routing
**Parallel Opportunities**: 22 tasks marked [P]
