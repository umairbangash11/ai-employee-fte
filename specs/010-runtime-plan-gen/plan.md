# Implementation Plan: Runtime Plan Generation

**Branch**: `010-runtime-plan-gen` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/010-runtime-plan-gen/spec.md`

## Summary

Add a `write_runtime_plan()` function in a new `src/orchestrator/plan_writer.py` module. Call it from `brain.py`'s `_route_reply_needed()` method immediately after `write_execution_plan()` and before the email is moved. The plan file is written to `vault/Needs_Action/plans/` and contains all seven required fields. Write failure is caught and logged without halting the triage flow. This closes the final Silver-tier reasoning-loop gap.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: stdlib only (`pathlib`, `datetime`, `re`) — no new packages
**Storage**: Local filesystem — `vault/Needs_Action/plans/` subdirectory
**Testing**: pytest (already installed)
**Target Platform**: Linux (WSL2), same as existing orchestrator
**Project Type**: Single project — `src/` layout, existing `src/orchestrator/` package
**Performance Goals**: Plan file written in under 500ms (filesystem write only — no AI call)
**Constraints**: Write failure MUST NOT halt the triage flow; plan written BEFORE email is moved; no second AI call for plan content
**Scale/Scope**: One plan file per actionable email; typical vault has hundreds of files

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | ✅ PASS | Plan writer is a pure filesystem write — no external calls whatsoever |
| II. Canonical Folder Structure | ✅ PASS | `Needs_Action/plans/` is a new subdirectory within canonical `Needs_Action/` — spec justifies it; no canonical folder is renamed or bypassed |
| III. Tiered Scope | ✅ PASS | Silver Tier completion work — reasoning loop creating Plan.md files is an explicit Silver requirement |
| IV. Safety-First Execution | ✅ PASS | Runtime plan is written AFTER `write_execution_plan()` (safety plan) and BEFORE the email is moved — ordering is preserved |
| V. Ralph Wiggum Loop | ✅ PASS | Plan write failure is caught in a try/except, logged to `Logs/`, and does NOT halt the triage flow — already covered by the outer retry loop in `_process_email()` |
| VI. Silver Tier Autonomy | ✅ PASS | Plan file documents the decision locally — no external message sent; `requires_approval: true` is explicit in every plan |
| VII. Phased Development | ✅ PASS | Silver completion work; no new phase started |
| VIII. Gmail API Migration Safety | ✅ N/A | Gmail unrelated to this feature |

**Gate result: PASS — all principles satisfied. No violations.**

## Phase 0: Research

### Findings

**Decision 1: New module vs. adding to `brain.py`**
- **Chosen**: New file `src/orchestrator/plan_writer.py`
- **Rationale**: Keeps `brain.py` focused on orchestration logic. `plan_writer.py` is independently importable for unit tests — no need to instantiate `InboxTriageHandler` or mock OpenAI. Follows the same pattern as `sentinel/planner.py` (which is also a standalone writer module).
- **Alternatives**: Inline function in `brain.py` (rejected — harder to test in isolation; `brain.py` already has 507 lines)

**Decision 2: Where the plan file lives**
- **Chosen**: `vault/Needs_Action/plans/`
- **Rationale**: `Needs_Action/` is the canonical location for items requiring human decision. The `plans/` subdirectory is clearly named, Constitution Principle II explicitly permits new subdirectories when justified by spec.
- **Alternatives**: `vault/Approved/plans/` (rejected — Approved/ is for execution-cleared items, not decision-pending items); `vault/Inbox/plans/` (rejected — Inbox/ is for incoming, unprocessed items)

**Decision 3: Plan content derivation**
- **Chosen**: Derive action steps from the classification result already in hand — no second AI call
- **Rationale**: The classification result from `classify_email()` already contains `reason` and `draft`. Action steps can be constructed deterministically from these fields. A second AI call would add latency, cost, and failure modes for no material benefit.
- **Alternatives**: Second OpenAI call to generate a structured plan (rejected — violates minimal scope; adds dependency)

**Decision 4: Filename format**
- **Chosen**: `{timestamp}_plan_{safe_subject_slug}.md` — e.g., `2026-04-14T10-30-00_plan_re-project-update.md`
- **Rationale**: Consistent with existing naming in `sentinel/planner.py`. Timestamp prefix ensures chronological ordering. Subject slug makes files human-identifiable in the vault.
- **Alternatives**: UUID-based names (rejected — not human-readable in Obsidian); hash-based (rejected — same reason)

**Decision 5: Failure handling**
- **Chosen**: `try/except OSError` around the write, log error to `Logs/`, return `None` to caller
- **Rationale**: FR-008 is explicit — plan write failure must not halt triage. The caller (`_route_reply_needed`) checks for `None` return and logs a warning, then continues with the email move and draft reply.
- **Alternatives**: Raise exception and let outer retry loop handle it (rejected — the retry loop retries the entire classification, not just the write; wasting AI calls for a filesystem error)

**Output**: All decisions resolved. No NEEDS CLARIFICATION items.

## Phase 1: Design & Contracts

### Data Model

See [`data-model.md`](./data-model.md).

**Input to `write_runtime_plan()`**:

| Parameter | Type | Description |
|---|---|---|
| `plans_dir` | `Path` | Absolute path to `vault/Needs_Action/plans/` |
| `source_filename` | `str` | Original email filename (for slug and metadata) |
| `email_meta` | `dict` | Keys: `sender`, `subject`, `source`, `urgency` |
| `classification` | `dict` | Keys: `needs_reply` (bool), `reason` (str), `draft` (str\|None) |

**Output**: `Path` to the written plan file, or `None` if write failed.

**Plan file YAML frontmatter**:

```yaml
---
type: runtime_plan
status: pending
created_at: "2026-04-14T10:30:00"
source_file: "{source_filename}"
requires_approval: true
email_sender: "{sender}"
email_subject: "{subject}"
---
```

**Plan file body sections** (in order):
1. `# Triage Plan: {subject}` — H1 title
2. `## Objective` — one sentence stating the action
3. `## Source Context` — sender, subject, source, classification reason
4. `## Action Steps` — Markdown checkboxes derived from classification
5. `## Approval Requirement` — fixed HITL warning text
6. `## Status` — `pending — Awaiting human review and approval.`

**Standard action steps for reply-needed email**:
```markdown
- [ ] Review the AI-generated draft reply in Needs_Action/drafts/
- [ ] Edit the draft as needed
- [ ] Approve by moving to Approved/email/ to authorise sending
```

**Action steps for error/fallback classification**:
```markdown
- [ ] Human review required — automated classification failed
- [ ] Inspect the source email and determine required action manually
```

### Integration Point in `brain.py`

The single change to `brain.py` is in `_route_reply_needed()`. Current order:

```
1. write_execution_plan()    ← safety plan (Approved/)
2. shutil.move()             ← email moved to drafts/
3. write_draft_reply()       ← draft reply written
4. write_log_entry()         ← logged
```

New order after this change:

```
1. write_execution_plan()    ← safety plan (Approved/) — UNCHANGED
2. write_runtime_plan()      ← NEW: reasoning plan (Needs_Action/plans/)
3. shutil.move()             ← email moved to drafts/ — UNCHANGED
4. write_draft_reply()       ← draft reply written — UNCHANGED
5. write_log_entry()         ← logged, now includes plan path — UNCHANGED
```

One additional change: `InboxTriageHandler.__init__` gains `self.plans_dir = self.needs_action_dir / "plans"`.

### Project Structure

```text
specs/010-runtime-plan-gen/
├── plan.md              ← this file
├── data-model.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/sp.tasks)
```

```text
src/
└── orchestrator/
    ├── brain.py         ← MODIFIED: add plans_dir attr + call write_runtime_plan()
    └── plan_writer.py   ← NEW: write_runtime_plan() function (standalone, testable)

tests/
└── unit/
    └── orchestrator/
        ├── __init__.py  ← NEW (empty)
        └── test_plan_writer.py  ← NEW: unit tests for write_runtime_plan()
```

**Total diff surface**: 1 new file (`plan_writer.py`), 1 modified file (`brain.py`), 1 new test file.

**Structure Decision**: Single-project layout. New module `src/orchestrator/plan_writer.py` matches the pattern of `src/sentinel/planner.py`.

## Implementation Sequence

### Task 1 — Create `src/orchestrator/plan_writer.py`
Implement `write_runtime_plan(plans_dir, source_filename, email_meta, classification)`:
- Sanitise subject to a filename slug
- Build YAML frontmatter and body sections per the contract above
- Create `plans_dir` if absent
- Deduplicate filename using `sentinel.mover.deduplicate_filename`
- Write file; catch `OSError`; return `Path` or `None`
- **Verify**: `PYTHONPATH=src python3 -c "from orchestrator.plan_writer import write_runtime_plan; print('ok')"`

### Task 2 — Write unit tests in `tests/unit/orchestrator/test_plan_writer.py`
Tests (no OpenAI, no watcher):
- `test_plan_created_for_actionable_email` — call with `needs_reply=True`, assert file exists with all required fields
- `test_no_plan_created_when_not_needed` — confirm caller contract (function still creates the plan; caller decides whether to call)
- `test_all_required_fields_present` — parse frontmatter, assert 7 fields
- `test_filename_deduplication` — call twice with same subject; assert two distinct files
- `test_error_classification_uses_fallback_steps` — call with error/fallback classification, assert `Human review required` step present
- `test_write_failure_returns_none` — pass read-only directory, assert `None` returned and no exception raised
- `test_plans_dir_created_if_missing` — pass non-existent `plans_dir`, assert it is created
- **Verify**: `PYTHONPATH=src pytest tests/unit/orchestrator/ -v` — all pass

### Task 3 — Modify `brain.py`: add `plans_dir` and call `write_runtime_plan`
- In `InboxTriageHandler.__init__`: add `self.plans_dir = self.needs_action_dir / "plans"`
- In `_route_reply_needed()`: import `write_runtime_plan` at top of file; add call after `write_execution_plan()` and before `shutil.move()`; wrap in try/except; log failure if `None` returned
- **Verify**: `PYTHONPATH=src python3 -c "from orchestrator.brain import InboxTriageHandler; print('ok')"`

### Task 4 — Validate end-to-end (no live AI call needed)
- Create a test email file in `vault/Inbox/email/test-email.md` with YAML frontmatter
- Manually call `write_runtime_plan()` with a mock classification and real `vault/Needs_Action/plans/` path
- Assert plan file exists at `vault/Needs_Action/plans/`
- Open plan file and verify all 7 sections are present and readable as Markdown
- **Verify**: `ls vault/Needs_Action/plans/` shows the new plan file

## Complexity Tracking

No constitution violations. No complexity justifications required.

## Risks

1. **`brain.py` import chain**: `plan_writer.py` imports `sentinel.mover.deduplicate_filename`. Ensure `PYTHONPATH=src` is set for tests so the import resolves correctly.
2. **Filename sanitisation edge cases**: Email subjects with non-ASCII characters (emoji, CJK) must be handled by the slug function — use `re.sub(r'[^\w\s-]', '', subject)` pattern, same approach as existing planner.
3. **Plans dir vs drafts dir confusion**: The plan goes to `Needs_Action/plans/`, the draft reply goes to `Needs_Action/drafts/`. These are distinct. The log entry should record both paths clearly to avoid human confusion in the vault.
