# Email Reasoning Layer MVP Completion Plan

**Feature**: 004-email-reasoning
**Scope**: Complete missing modules only (classifier, writer, engine)
**Date**: 2026-04-12
**Status**: Ready for Implementation

---

## Executive Summary

This plan addresses **only** the remaining implementation work to complete the Email Reasoning MVP. The foundation already exists (models, config, scanner, state). This plan covers the three missing modules required to complete the reasoning pipeline.

**Existing Foundation:**
- ✅ `src/email_reasoner/models.py` - Data models (EmailFile, ClassificationResult, TaskFile, PlanFile, ReasonerState)
- ✅ `src/email_reasoner/config.py` - Configuration loading (ReasonerConfig)
- ✅ `src/email_reasoner/scanner.py` - Email discovery and parsing
- ✅ `src/email_reasoner/state.py` - Deduplication state management

**Missing Components (this plan):**
- ❌ `src/email_reasoner/classifier.py` - LLM email classification
- ❌ `src/email_reasoner/writer.py` - Task markdown generation
- ❌ `src/email_reasoner/engine.py` - Pipeline orchestration

---

## Target MVP Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Email Reasoning Flow                      │
└─────────────────────────────────────────────────────────────┘

  Input: Email markdown files in /Inbox/email/

    ↓ [scanner.py - EXISTING]

  List[Path] → parse → List[EmailFile]

    ↓ [state.py - EXISTING]

  Filter already-processed (skip duplicates)

    ↓ [classifier.py - NEW]

  EmailFile → classify via LLM → ClassificationResult
    - label: ignore | respond | follow_up | urgent
    - confidence: float
    - reason: str
    - suggested_action: str
    - priority: high | medium | low

    ↓ [writer.py - NEW]

  For non-ignore: ClassificationResult → generate → TaskFile markdown

    ↓ [engine.py - NEW]

  Orchestrate: scan → filter → classify → write → update state

  Output: Task files in /Needs_Action/tasks/
```

---

## Module 1: classifier.py

### Responsibility

Classify emails using OpenAI GPT-4o and return structured classification results.

### Interface Contract

```python
def classify_email(
    email: EmailFile,
    api_key: str,
    model: str = "gpt-4o"
) -> ClassificationResult:
    """Classify a single email using LLM.

    Args:
        email: Parsed email file
        api_key: OpenAI API key
        model: Model name (default: gpt-4o)

    Returns:
        ClassificationResult with label, confidence, action, priority

    Raises:
        ClassificationError: After 3 retry attempts fail
    """
```

### Classification Labels (MVP)

Based on locked scope, use these exact labels:

1. **ignore** - No action needed (spam, auto-replies, duplicates)
2. **respond** - Requires direct reply or acknowledgment
3. **follow_up** - Requires action but no immediate response
4. **urgent** - Time-sensitive action required

**Mapping to existing spec categories:**
- `actionable` (spec) → `respond` or `follow_up` or `urgent` (MVP)
- `informational` (spec) → `ignore` (MVP - no task created)
- `promotional` (spec) → `ignore` (MVP)
- `ignore` (spec) → `ignore` (MVP)

### Implementation Requirements

1. **OpenAI Client Initialization**
   - Initialize client with API key from config
   - Use `gpt-4o` model
   - Enable JSON mode: `response_format={"type": "json_object"}`

2. **System Prompt** (Classification Criteria)
```text
You are an email classification assistant. Classify emails into exactly one category:

- ignore: Spam, auto-replies, duplicates, promotional, informational
- respond: Requires direct reply (questions, meeting invites, personal messages)
- follow_up: Actionable but no reply needed (tasks, reminders, alerts)
- urgent: Time-sensitive (deadlines, payments, security alerts)

Return JSON:
{
  "label": "ignore|respond|follow_up|urgent",
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "suggested_action": "clear next step or null",
  "priority": "high|medium|low|null"
}

For ignore: set suggested_action and priority to null.
```

3. **User Prompt Template**
```python
f"""
Subject: {email.subject}
From: {email.sender}
Body preview: {truncated_body[:4000]}

Classify this email.
"""
```

4. **Response Parsing**
   - Parse JSON response to ClassificationResult Pydantic model
   - Validate all required fields present
   - If confidence < 0.5: override label to "ignore"

5. **Error Handling (Ralph Wiggum Loop)**
   - Retry up to 3 attempts on transient errors
   - Exponential backoff: 1s, 2s, 4s
   - After 3 failures: return ClassificationResult(label="ignore", confidence=0.0, reason="API failure")

6. **Body Truncation**
   - Limit email body to 4000 characters for API efficiency
   - Truncate middle, preserve start and end

### Implementation Sequence

```
1. Create classifier.py module skeleton
2. Implement OpenAI client initialization
3. Define SYSTEM_PROMPT constant
4. Implement classify_email() core logic
5. Add JSON response parsing and validation
6. Implement retry with backoff
7. Add body truncation helper
8. Add error fallback to "ignore"
```

### Error Boundaries

- **API failures** → Fallback to `label="ignore"`, log error, continue processing
- **Invalid JSON** → Retry once, then fallback to `label="ignore"`
- **Missing API key** → Raise immediately (fail fast, not recoverable)

---

## Module 2: writer.py

### Responsibility

Generate task markdown files for non-ignore classifications.

### Interface Contract

```python
def write_task_file(
    email: EmailFile,
    classification: ClassificationResult,
    vault_path: Path,
    dry_run: bool = False
) -> Optional[Path]:
    """Generate and write task markdown file.

    Args:
        email: Source email
        classification: Classification result
        vault_path: Vault root path
        dry_run: If True, don't write file (preview only)

    Returns:
        Path to created task file, or None if dry_run or ignored
    """
```

### Task File Schema

**Filename Format:**
```
{YYYYMMDD}-{HHMMSS}_{label}_{slug}.md
Example: 20260412-143022_respond_interview_invitation.md
```

**Frontmatter:**
```yaml
---
type: task
created_at: "2026-04-12T14:30:22Z"
source_email: "[[Inbox/email/20260412-140000_sender_subject.md]]"
classification: respond | follow_up | urgent
priority: high | medium | low
due_date: "YYYY-MM-DD" | null
status: pending
tags: [task, email-derived, {classification}]
---
```

**Body Template:**
```markdown
# {suggested_action or "Review email: {subject}"}

## Context

Email from: {sender}
Subject: {subject}
Classification: {label} (confidence: {confidence:.2f})

Reason: {classification.reason}

## Action Required

{classification.suggested_action or "Review the source email and determine next steps."}

## Source Email

{email.wikilink}
```

### Implementation Requirements

1. **Filename Generation**
   - Use current timestamp
   - Slugify action text (lowercase, replace spaces with `_`, strip special chars)
   - Max 50 chars for slug

2. **Directory Handling**
   - Ensure `/Needs_Action/tasks/` exists (create if missing)
   - No subdirectories for MVP

3. **Frontmatter Generation**
   - Use YAML format
   - Map classification.priority → task priority
   - Extract due_date from classification if present
   - Generate wikilink to source email using `email.wikilink`

4. **Body Generation**
   - Clear heading with action
   - Context section with sender, subject, reason
   - Action section with suggested next step
   - Source section with wikilink

5. **Dry-Run Mode**
   - If `dry_run=True`: log what would be created, return None
   - Don't write file in dry-run

6. **Ignore Handling**
   - If classification.label == "ignore": return None immediately
   - Don't create any file

### Implementation Sequence

```
1. Create writer.py module skeleton
2. Implement generate_filename() helper
3. Implement generate_frontmatter() helper
4. Implement generate_body() helper
5. Implement write_task_file() orchestration
6. Add directory creation logic
7. Add dry-run mode handling
8. Add ignore label early exit
```

### Output Location

All task files → `<vault_path>/Needs_Action/tasks/`

**Out of scope for MVP:**
- Plan files (multi-step) - defer to future iteration
- Priority folders (/Needs_Action/urgent/, etc.) - single folder only
- Custom templates - use fixed template above

---

## Module 3: engine.py

### Responsibility

Orchestrate the full reasoning pipeline: scan → filter → classify → write → state update.

### Interface Contract

```python
class ReasonerEngine:
    """Main orchestration engine for email reasoning."""

    def __init__(self, config: ReasonerConfig):
        """Initialize engine with config."""

    def run(self) -> ReasonerRunResult:
        """Execute one reasoning pass.

        Returns:
            ReasonerRunResult with stats (processed, skipped, created, errors)
        """
```

### Data Flow (One Pass)

```
1. Load state from .watcher-state/reasoner.json
2. Scan /Inbox/email/ for .md files (scanner.scan_inbox)
3. Parse each file to EmailFile (scanner.parse_email_file)
4. Filter: skip if message_id in state.processed
5. For each unprocessed email:
   a. Classify via classifier.classify_email()
   b. If label != "ignore":
      - Write task via writer.write_task_file()
      - Mark as processed in state
   c. If label == "ignore":
      - Mark as processed (no task)
   d. Save state after EACH email (incremental persistence)
6. Return stats: processed, tasks_created, ignored, errors
```

### Implementation Requirements

1. **Engine Class Initialization**
   ```python
   def __init__(self, config: ReasonerConfig):
       self.config = config
       self.state_path = Path(config.state_path or ".watcher-state/reasoner.json")
       self.inbox_path = Path(config.vault_path) / "Inbox" / "email"
       self.vault_path = Path(config.vault_path)
   ```

2. **Run Method Orchestration**
   ```python
   def run(self) -> ReasonerRunResult:
       # 1. Load state
       state = load_state(self.state_path)

       # 2. Scan inbox
       email_paths = scan_inbox(self.inbox_path)

       # 3. Process each email
       stats = {"processed": 0, "tasks": 0, "ignored": 0, "errors": 0}

       for path in email_paths[:self.config.limit if self.config.limit else None]:
           email = parse_email_file(path)
           if not email or is_processed(state, email.message_id):
               continue

           try:
               result = classify_email(email, self.config.api_key)

               if result.label != "ignore":
                   task_path = write_task_file(
                       email, result, self.vault_path, self.config.dry_run
                   )
                   stats["tasks"] += 1
               else:
                   stats["ignored"] += 1

               mark_processed(state, email.message_id, result.label, task_path)
               save_state(state, self.state_path)
               stats["processed"] += 1

           except Exception as e:
               logger.error(f"Failed to process {path}: {e}")
               stats["errors"] += 1

       return ReasonerRunResult(**stats)
   ```

3. **Idempotency Strategy**
   - Check `state.is_processed(message_id)` before classification
   - Skip already-processed emails
   - Save state after EACH successful processing (not batch at end)
   - Use message_id from email frontmatter as dedup key

4. **Limit Handling**
   - If `config.limit` is set, process at most N emails
   - Apply limit BEFORE processing (slice email_paths list)

5. **Dry-Run Mode**
   - Pass `dry_run=True` to writer
   - Still classify, still log, but no files written
   - Still update state (so dry-run is idempotent too)

6. **Logging**
   - Log each classification decision: `logger.info(f"{email.subject} → {result.label}")`
   - Log task creation: `logger.info(f"Created task: {task_path}")`
   - Log skipped (already processed)
   - Log errors with stack trace

### Implementation Sequence

```
1. Create engine.py module skeleton
2. Implement ReasonerEngine.__init__()
3. Implement run() method structure (load state, scan, loop)
4. Integrate scanner calls
5. Integrate classifier calls
6. Integrate writer calls
7. Integrate state updates (is_processed, mark_processed)
8. Add error handling (try/except per email)
9. Add stats tracking
10. Add logging statements
```

### Error Strategy

- **Per-email errors**: Log and continue (don't fail entire batch)
- **State save errors**: Log warning, continue (state persists from previous save)
- **Scanner errors**: Return empty list (graceful degradation)
- **Missing API key**: Fail fast at engine init (not recoverable)

---

## Integration Points

### scanner.py → classifier.py
```python
# scanner provides
email: EmailFile = parse_email_file(path)

# classifier consumes
result: ClassificationResult = classify_email(email, api_key)
```

### classifier.py → writer.py
```python
# classifier provides
result: ClassificationResult

# writer consumes
task_path: Optional[Path] = write_task_file(email, result, vault_path)
```

### state.py ↔ engine.py
```python
# engine loads state once at start
state: ReasonerState = load_state(state_path)

# engine checks before processing
if is_processed(state, email.message_id):
    continue

# engine marks after processing
mark_processed(state, message_id, label, task_path)
save_state(state, state_path)
```

---

## Implementation Sequencing

**Low-Risk → High-Value Order:**

### Phase 1: Classifier (Highest Risk, Implement First)
1. Create `classifier.py` module
2. Implement OpenAI client initialization
3. Implement system prompt
4. Implement `classify_email()` core logic
5. Add retry with backoff
6. Add error fallback

**Checkpoint**: Unit test classifier with mock API responses

### Phase 2: Writer (Medium Risk)
1. Create `writer.py` module
2. Implement filename generation
3. Implement frontmatter generation
4. Implement body generation
5. Implement `write_task_file()` orchestration
6. Add directory creation
7. Add dry-run handling

**Checkpoint**: Unit test writer with sample classification results

### Phase 3: Engine (Low Risk, Highest Value)
1. Create `engine.py` module
2. Implement `ReasonerEngine` class
3. Implement `run()` method
4. Wire scanner → classifier → writer → state
5. Add error handling
6. Add logging
7. Add stats tracking

**Checkpoint**: Integration test full pipeline end-to-end

---

## Excluded from MVP Scope

### Explicitly Out of Scope:
- ❌ Multi-step plan generation (defer to future)
- ❌ CLI implementation (`__main__.py`) - basic invocation only
- ❌ Advanced logging to `/Logs/` - stderr only for MVP
- ❌ Batch classification optimization - process one-by-one
- ❌ Custom prompt templates - use fixed prompt
- ❌ Confidence threshold tuning - use 0.5 hardcoded
- ❌ Task priority folders - single `/Needs_Action/tasks/` only
- ❌ Email body summarization - use truncation only
- ❌ WhatsApp, Facebook, LinkedIn, Odoo integration
- ❌ MCP server integration
- ❌ Calendar event creation
- ❌ Auto-task execution
- ❌ Gmail label updates

---

## Success Criteria for MVP Completion

### Functional Criteria:

1. ✅ **Classifier works**: Given an EmailFile, returns valid ClassificationResult
2. ✅ **Writer works**: Given ClassificationResult (non-ignore), creates task file
3. ✅ **Engine works**: Full pipeline processes email → task
4. ✅ **Idempotency works**: Running twice produces no duplicates
5. ✅ **Ignore handling works**: Ignore emails create no tasks
6. ✅ **Error handling works**: API failures don't crash pipeline

### Verification Tests:

| Test | Input | Expected Output |
|------|-------|-----------------|
| T1 | Email: "Interview at Company X" | Task file created with label=respond |
| T2 | Email: "50% off sale!" | No task file (label=ignore) |
| T3 | Run engine twice on same email | Single task file only |
| T4 | Simulate API failure | Fallback to ignore, continue processing |
| T5 | Empty inbox | Engine completes with 0 processed |

### Code Quality Criteria:

- ✅ All modules have docstrings
- ✅ All functions have type hints
- ✅ Error handling for all external calls (OpenAI API)
- ✅ Logging for all key decisions
- ✅ No hardcoded paths (use config)
- ✅ Read-only on source files (scanner, engine)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM misclassification | Medium | Low | Human reviews tasks, can adjust |
| API rate limits | Low | Medium | Retry with backoff, process serially |
| API cost overrun | Low | Medium | Limit to N emails per run (config.limit) |
| State file corruption | Low | High | Save after each email (incremental) |
| Long email bodies | Medium | Low | Truncate to 4000 chars |

---

## Definition of Done

The Email Reasoning MVP is **complete** when:

1. ✅ `classifier.py` exists and classifies emails via OpenAI
2. ✅ `writer.py` exists and generates task markdown files
3. ✅ `engine.py` exists and orchestrates scan → classify → write → state
4. ✅ Running `email-reasoner` (basic CLI) processes inbox emails
5. ✅ All 5 verification tests pass
6. ✅ No duplicate tasks created on repeated runs
7. ✅ Original email files unchanged after processing

**Next Step After Completion:**
- Mark tasks T032-T053 as complete in tasks.md
- Update phase-2/README.md status to "MVP Complete"
- Demo to user with real email samples

---

## Dependencies Summary

### Internal Module Dependencies:
```
engine.py → scanner.py (existing)
engine.py → classifier.py (new)
engine.py → writer.py (new)
engine.py → state.py (existing)
engine.py → config.py (existing)

classifier.py → models.py (existing)
writer.py → models.py (existing)
```

### External Package Dependencies:
```python
# Already in pyproject.toml:
openai >= 1.0
pyyaml >= 6.0
python-frontmatter >= 1.0
pydantic >= 2.0
python-dotenv >= 1.0
```

---

**Total New Modules**: 3 (classifier, writer, engine)
**Total New Lines of Code (estimate)**: ~600 LOC
**Estimated Completion Time**: 3-4 hours (focused implementation)
**Risk Level**: Medium (OpenAI API dependency)

---

## Appendix: Classification Label Mapping

To align MVP labels with existing spec categories:

| Spec Category | MVP Label | Task Created? | Notes |
|---------------|-----------|---------------|-------|
| actionable | respond / follow_up / urgent | Yes | Split by urgency |
| informational | ignore | No | No action needed |
| promotional | ignore | No | Marketing/spam |
| ignore | ignore | No | Duplicates, auto-replies |

**Classifier logic:**
- If email requires reply → `respond`
- If email requires action (no reply) → `follow_up`
- If email has deadline/urgency → `urgent`
- Everything else → `ignore`

This keeps the MVP simple while maintaining compatibility with the broader spec vision.

---

**END OF PLAN**
