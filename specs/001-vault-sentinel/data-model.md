# Data Model: Vault Sentinel

**Feature**: 001-vault-sentinel
**Date**: 2026-02-11

## Entities

### Vault

The root directory containing the five canonical folders.

| Attribute | Type | Description |
|-----------|------|-------------|
| root_path | Path | Absolute path to the vault root directory |
| folders | list[str] | Fixed: `Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs` |

**Invariants**:
- All five folders MUST exist after initialization.
- Initialization MUST be idempotent.

### WatchedFile

A file detected in `Inbox` that matches the extension filter.

| Attribute | Type | Description |
|-----------|------|-------------|
| filename | str | Original filename including extension |
| extension | str | Lowercase file extension (`.txt` or `.pdf`) |
| size_bytes | int | File size in bytes |
| source_path | Path | Full path in `Inbox` |
| detected_at | datetime | Timestamp when file was first detected |

**State transitions**:
```
[detected in Inbox]
    → [stability check: waiting for write to complete]
    → [plan written to Approved]
    → [moved to Needs_Action]
    → [log written to Logs]
```

### ExecutionPlan

A Markdown file in `Approved/` documenting the intended action.

| Attribute | Type | Description |
|-----------|------|-------------|
| plan_id | str | ISO timestamp-based identifier |
| action | str | Action type (`move_file`) |
| source | Path | Source file path |
| destination | Path | Destination file path |
| rollback | str | Rollback strategy description |
| expected_outcome | str | Description of expected result |
| created_at | datetime | When the plan was written |

**File format** (Markdown with YAML frontmatter):
```markdown
---
plan_id: "2026-02-11T14-30-00-move-report-txt"
action: move_file
source: "Inbox/report.txt"
destination: "Needs_Action/report.txt"
created_at: "2026-02-11T14:30:00"
---

## Action

Move `report.txt` from `Inbox` to `Needs_Action`.

## Rollback

Move `Needs_Action/report.txt` back to `Inbox/report.txt`.

## Expected Outcome

File appears in `Needs_Action/`; removed from `Inbox/`.
```

### LogEntry

A Markdown file in `Logs/` recording a completed Sentinel action.

| Attribute | Type | Description |
|-----------|------|-------------|
| log_id | str | ISO timestamp-based identifier |
| timestamp | datetime | When the action occurred |
| action_type | str | `file_moved`, `file_renamed`, `error` |
| source_path | Path | Original file location |
| dest_path | Path | Destination file location |
| file_size | int | Size in bytes |
| outcome | str | `success` or `failure` |
| details | str | Additional context (e.g., rename reason) |

**File format** (Markdown with YAML frontmatter):
```markdown
---
log_id: "2026-02-11T14-30-01-moved-report-txt"
timestamp: "2026-02-11T14:30:01"
action: file_moved
outcome: success
---

## File Moved

- **File**: report.txt
- **From**: Inbox/
- **To**: Needs_Action/
- **Size**: 2,048 bytes
- **Detected**: 2026-02-11T14:30:00
- **Processed**: 2026-02-11T14:30:01
```

## Relationships

```
Vault
  └── contains → Inbox/
        └── produces → WatchedFile
                         ├── triggers → ExecutionPlan (in Approved/)
                         ├── moves to → Needs_Action/
                         └── generates → LogEntry (in Logs/)
```
