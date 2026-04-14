# Tasks: Email Reasoning MVP Completion

**Feature**: 004-email-reasoning
**Scope**: Complete remaining MVP modules only (classifier, writer, engine)
**Date**: 2026-04-12
**Prerequisites**: mvp-completion-plan.md

---

## Context

This task list covers **only** the remaining work to complete the Email Reasoning MVP.

**Foundation Already Complete (31 tasks):**
- ✅ Phase 1: Setup (T001-T006)
- ✅ Phase 2: Foundational (T007-T031)
  - Models, config, scanner, state all implemented

**This Document: Remaining MVP Work (22 tasks)**
- Phase 3: Classifier module (11 tasks)
- Phase 4: Writer module (6 tasks)
- Phase 5: Engine module (5 tasks)

---

## Task Format

`- [ ] TXXX [Module] Description`

**Modules**: CLASSIFIER | WRITER | ENGINE

**Acceptance Criteria**: Included at end of each phase

**Out of Scope** (will NOT have tasks):
- Multi-step plan generation
- Advanced CLI polish
- Logging to /Logs/
- Batch optimization
- Custom templates
- Priority folders
- WhatsApp/Facebook/LinkedIn integration

---

## Phase 3: Classifier Module (T032-T042)

**Goal**: Implement email classification using OpenAI GPT-4o

**File**: `src/email_reasoner/classifier.py`

**Interface Contract**:
```python
def classify_email(
    email: EmailFile,
    api_key: str,
    model: str = "gpt-4o"
) -> ClassificationResult
```

**Labels**: `ignore`, `respond`, `follow_up`, `urgent`

### Tasks

- [ ] T032 [CLASSIFIER] Create `src/email_reasoner/classifier.py` module skeleton with imports
  - **Acceptance**: File exists, imports openai, models.EmailFile, models.ClassificationResult

- [ ] T033 [CLASSIFIER] Implement `_init_openai_client(api_key: str) -> OpenAI` helper function
  - **Acceptance**: Returns OpenAI client instance with API key configured

- [ ] T034 [CLASSIFIER] Define `SYSTEM_PROMPT` constant with classification criteria
  - **Content**: Classify into ignore|respond|follow_up|urgent, return JSON with label, confidence, reason, suggested_action, priority
  - **Acceptance**: Constant string defined, includes all 4 labels and JSON schema

- [ ] T035 [CLASSIFIER] Implement `_build_user_prompt(email: EmailFile) -> str` helper function
  - **Acceptance**: Returns formatted prompt with subject, sender, body preview (truncated to 4000 chars)

- [ ] T036 [CLASSIFIER] Implement `_truncate_body(body: str, max_chars: int = 4000) -> str` helper function
  - **Acceptance**: Returns truncated body, preserves start and end if truncated

- [ ] T037 [CLASSIFIER] Implement core `classify_email()` function with OpenAI API call
  - **Acceptance**: Calls client.chat.completions.create with gpt-4o, JSON mode enabled, returns response

- [ ] T038 [CLASSIFIER] Implement `_parse_llm_response(response: str) -> ClassificationResult` helper function
  - **Acceptance**: Parses JSON string to ClassificationResult Pydantic model, validates schema

- [ ] T039 [CLASSIFIER] Add confidence threshold check in classify_email()
  - **Logic**: If confidence < 0.5, override label to "ignore"
  - **Acceptance**: Low-confidence results become label="ignore"

- [ ] T040 [CLASSIFIER] Implement retry logic with exponential backoff (Ralph Wiggum Loop)
  - **Behavior**: 3 attempts total, backoff delays: 1s, 2s, 4s
  - **Acceptance**: API failures retry 3 times with increasing delays

- [ ] T041 [CLASSIFIER] Add error fallback handler in classify_email()
  - **Behavior**: After 3 failed retries, return ClassificationResult(label="ignore", confidence=0.0, reason="API failure")
  - **Acceptance**: Unrecoverable errors return fallback result instead of raising

- [ ] T042 [CLASSIFIER] Add logging for classification decisions
  - **Log**: Email subject, classification label, confidence
  - **Acceptance**: Logger statements in classify_email() for each classification

### Phase 3 Acceptance Criteria

✅ **Classifier Complete When**:
1. `classify_email()` accepts EmailFile and returns ClassificationResult
2. All 4 labels (ignore, respond, follow_up, urgent) are supported
3. OpenAI API is called with JSON mode enabled
4. Retry logic handles transient failures (3 attempts)
5. Error fallback returns label="ignore" instead of crashing
6. Body truncation limits input to 4000 chars
7. Confidence threshold (0.5) filters low-confidence results

**Verification Test**:
```python
email = EmailFile(
    message_id="test-123",
    subject="Interview at Company X",
    sender="hr@company.com",
    body="We'd like to schedule an interview..."
)
result = classify_email(email, api_key="sk-...")
assert result.label in ["ignore", "respond", "follow_up", "urgent"]
assert 0.0 <= result.confidence <= 1.0
```

---

## Phase 4: Writer Module (T043-T048)

**Goal**: Generate task markdown files for non-ignore classifications

**File**: `src/email_reasoner/writer.py`

**Interface Contract**:
```python
def write_task_file(
    email: EmailFile,
    classification: ClassificationResult,
    vault_path: Path,
    dry_run: bool = False
) -> Optional[Path]
```

### Tasks

- [ ] T043 [WRITER] Create `src/email_reasoner/writer.py` module skeleton with imports
  - **Acceptance**: File exists, imports Path, EmailFile, ClassificationResult

- [ ] T044 [WRITER] Implement `_generate_filename(label: str, action: str, timestamp: datetime) -> str` helper
  - **Format**: `{YYYYMMDD}-{HHMMSS}_{label}_{slug}.md`
  - **Acceptance**: Returns valid filename with timestamp, label, slugified action (max 50 chars)

- [ ] T045 [WRITER] Implement `_generate_frontmatter(email: EmailFile, classification: ClassificationResult) -> str` helper
  - **Fields**: type, created_at, source_email (wikilink), classification, priority, due_date, status, tags
  - **Acceptance**: Returns valid YAML frontmatter block with all required fields

- [ ] T046 [WRITER] Implement `_generate_body(email: EmailFile, classification: ClassificationResult) -> str` helper
  - **Sections**: Heading (action), Context (sender, subject, reason), Action Required, Source Email (wikilink)
  - **Acceptance**: Returns markdown body with all sections populated

- [ ] T047 [WRITER] Implement `write_task_file()` orchestration function
  - **Logic**: Check if label=="ignore" → return None early, ensure /Needs_Action/tasks/ exists, combine frontmatter + body, write file
  - **Acceptance**: Creates task file in correct location, returns Path to created file

- [ ] T048 [WRITER] Add dry-run mode handling in write_task_file()
  - **Behavior**: If dry_run=True, log what would be created, return None without writing
  - **Acceptance**: Dry-run logs filename and location, does not create file

### Phase 4 Acceptance Criteria

✅ **Writer Complete When**:
1. `write_task_file()` accepts EmailFile, ClassificationResult, vault_path
2. Task files created in `/Needs_Action/tasks/` directory
3. Filename format: `{YYYYMMDD}-{HHMMSS}_{label}_{slug}.md`
4. Frontmatter includes all required fields (type, source_email wikilink, priority, tags)
5. Body includes action heading, context, source wikilink
6. Ignore label returns None (no file created)
7. Dry-run mode prevents file writes
8. Directory creation handled automatically

**Verification Test**:
```python
classification = ClassificationResult(
    label="respond",
    confidence=0.9,
    reason="Interview invitation",
    suggested_action="Reply to schedule interview",
    priority="high"
)
task_path = write_task_file(email, classification, vault_path)
assert task_path.exists()
assert task_path.parent.name == "tasks"
assert "respond" in task_path.name
```

---

## Phase 5: Engine Module (T049-T053)

**Goal**: Orchestrate full reasoning pipeline

**File**: `src/email_reasoner/engine.py`

**Interface Contract**:
```python
class ReasonerEngine:
    def __init__(self, config: ReasonerConfig):
        ...

    def run(self) -> dict:
        """Returns stats: {processed, tasks_created, ignored, errors}"""
```

### Tasks

- [ ] T049 [ENGINE] Create `src/email_reasoner/engine.py` module with ReasonerEngine class skeleton
  - **Acceptance**: File exists, ReasonerEngine class defined with __init__ method

- [ ] T050 [ENGINE] Implement ReasonerEngine.__init__() with config injection
  - **Setup**: Load config, set inbox_path, vault_path, state_path
  - **Acceptance**: All paths configured from ReasonerConfig

- [ ] T051 [ENGINE] Implement ReasonerEngine.run() method structure
  - **Flow**: load_state → scan_inbox → loop emails → save_state → return stats
  - **Acceptance**: Method exists with full pipeline structure (can be stubbed initially)

- [ ] T052 [ENGINE] Wire pipeline in run(): integrate scanner, classifier, writer, state
  - **Per email**: parse → check is_processed → classify → write_task_file (if not ignore) → mark_processed → save_state
  - **Acceptance**: Full pipeline executes end-to-end for one email

- [ ] T053 [ENGINE] Add error handling, logging, and stats tracking in run()
  - **Per-email try/except**: Log errors, increment error counter, continue processing
  - **Logging**: Classification decision, task creation, skip reasons
  - **Stats**: Track processed, tasks_created, ignored, errors
  - **Acceptance**: Errors don't crash pipeline, stats returned correctly

### Phase 5 Acceptance Criteria

✅ **Engine Complete When**:
1. ReasonerEngine class instantiates with ReasonerConfig
2. `run()` method executes full pipeline: scan → filter → classify → write → state
3. State loaded at start, saved after each email
4. Already-processed emails skipped (idempotency)
5. Errors logged per-email, processing continues
6. Stats returned: processed, tasks_created, ignored, errors
7. Limit option honored (process at most N emails)
8. Dry-run mode passed to writer

**Verification Test**:
```python
config = ReasonerConfig(
    vault_path="/path/to/vault",
    api_key="sk-...",
    limit=5
)
engine = ReasonerEngine(config)
stats = engine.run()
assert "processed" in stats
assert "tasks_created" in stats
assert stats["errors"] == 0
```

---

## Integration Checkpoint

**After T053 Complete, Full MVP Pipeline Works**:

```
Input: Email markdown files in /Inbox/email/

↓ [scanner.scan_inbox - EXISTING]

List[Path] of email files

↓ [scanner.parse_email_file - EXISTING]

List[EmailFile]

↓ [state.is_processed - EXISTING]

Filter out duplicates

↓ [classifier.classify_email - T032-T042]

ClassificationResult per email

↓ [writer.write_task_file - T043-T048]

Task markdown created (if not ignore)

↓ [state.mark_processed, save_state - EXISTING]

State updated, no duplicates

↓ [engine.run - T049-T053]

Stats returned: {processed, tasks_created, ignored, errors}

Output: Task files in /Needs_Action/tasks/
```

---

## Final Verification Tests (MVP Complete)

Run these tests to verify MVP completion:

### Test 1: Actionable Email Creates Task
```
1. Place email file: /Inbox/email/test-interview.md
   Subject: "Interview at Company X"
   Body: "We'd like to schedule an interview next week"
2. Run: email-reasoner
3. Verify: Task file created in /Needs_Action/tasks/
4. Verify: Task has label="respond" or "follow_up"
5. Verify: Task includes wikilink to source email
```

### Test 2: Ignore Email Creates No Task
```
1. Place email file: /Inbox/email/test-promo.md
   Subject: "50% off sale today only!"
   Body: "Limited time offer..."
2. Run: email-reasoner
3. Verify: No task file created
4. Verify: State shows email as processed with label="ignore"
```

### Test 3: Idempotency (No Duplicates)
```
1. Place email file: /Inbox/email/test-job.md
2. Run: email-reasoner (first time)
3. Verify: 1 task file created
4. Run: email-reasoner (second time)
5. Verify: Still only 1 task file (no duplicate)
6. Verify: Stats show 1 processed first run, 0 processed second run
```

### Test 4: API Failure Fallback
```
1. Set invalid API key
2. Place email file: /Inbox/email/test-any.md
3. Run: email-reasoner
4. Verify: No crash (pipeline completes)
5. Verify: Stats show 1 error
6. Verify: State shows email as processed with label="ignore" (fallback)
```

### Test 5: Dry-Run Mode
```
1. Place email file: /Inbox/email/test-dry.md
2. Run: email-reasoner --dry-run
3. Verify: No task file created
4. Verify: Log shows "would create task: ..." message
5. Verify: State NOT updated (dry-run is preview only)
```

---

## Task Summary

| Phase | Tasks | Module | LOC Estimate |
|-------|-------|--------|--------------|
| Phase 3: Classifier | T032-T042 (11 tasks) | classifier.py | ~250 LOC |
| Phase 4: Writer | T043-T048 (6 tasks) | writer.py | ~200 LOC |
| Phase 5: Engine | T049-T053 (5 tasks) | engine.py | ~150 LOC |
| **Total** | **22 tasks** | **3 modules** | **~600 LOC** |

---

## Dependencies

**Task Dependencies**:
- T032-T042 (Classifier) can start immediately (no blockers)
- T043-T048 (Writer) can run in parallel with Classifier
- T049-T053 (Engine) requires T042 and T048 complete

**Parallel Opportunities**:
- T032-T042 and T043-T048 can be implemented in parallel (different modules)
- Within Classifier: T033, T034, T035, T036 can be done in any order (all helpers)
- Within Writer: T044, T045, T046 can be done in any order (all helpers)

**Recommended Sequence** (risk-first):
1. Phase 3: Classifier (T032-T042) - highest risk (external API)
2. Phase 4: Writer (T043-T048) - medium risk
3. Phase 5: Engine (T049-T053) - low risk (orchestration only)

---

## Out of Scope (No Tasks)

The following are explicitly **excluded** from this MVP task list:

- ❌ Multi-step plan generation (PlanFile, /Plans/ directory)
- ❌ CLI implementation (__main__.py with Click)
- ❌ Logging to /Logs/ directory
- ❌ Batch classification optimization
- ❌ Custom prompt templates
- ❌ Priority-based task folders
- ❌ Advanced error recovery
- ❌ Performance optimization
- ❌ Comprehensive test suite (unit tests for each function)
- ❌ Documentation updates
- ❌ WhatsApp/Facebook/LinkedIn integration
- ❌ MCP server integration
- ❌ Calendar event creation
- ❌ Auto-task execution

These items may be added in future iterations **after** MVP validation.

---

## Definition of Done

The Email Reasoning MVP is **complete** when:

1. ✅ All 22 tasks (T032-T053) marked complete
2. ✅ All 3 modules implemented: classifier.py, writer.py, engine.py
3. ✅ All 5 verification tests pass
4. ✅ `email-reasoner` CLI runs without errors
5. ✅ No duplicate tasks created on repeated runs
6. ✅ Original email files unchanged after processing

**Sign-off Criteria**:
- Demo to user with real email samples
- User confirms task quality meets expectations
- No blocking bugs in core pipeline

---

## Next Steps After Completion

Once MVP is complete and verified:

1. Update tasks.md to mark T032-T053 as complete
2. Update phase-2/README.md status to "MVP Complete"
3. Create PHR for implementation session
4. Decide on next iteration:
   - Option A: Add multi-step plan generation
   - Option B: Polish CLI with full options
   - Option C: Add comprehensive test coverage
   - Option D: Move to next phase (WhatsApp watcher)

---

**END OF MVP COMPLETION TASKS**
