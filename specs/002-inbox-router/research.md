# Research: Inbox → Needs_Action Router

**Feature**: 002-inbox-router
**Date**: 2026-02-27
**Status**: Complete

## Research Summary

This document consolidates research findings for implementing the rule-based router that moves Markdown files from `/Inbox/email/` to `/Needs_Action/email/` based on urgency flags, keyword matching, and SLA breaches.

---

## 1. YAML Frontmatter Parsing

### Decision
Use Python's `yaml` module (PyYAML) with `safe_load` for parsing frontmatter.

### Rationale
- Already implied by existing codebase pattern (gmail_watcher.py generates YAML frontmatter)
- `safe_load` prevents arbitrary code execution from malformed YAML
- PyYAML is lightweight and battle-tested for this use case

### Alternatives Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| PyYAML (safe_load) | Standard, secure, lightweight | Slower than C extensions | **Selected** |
| ruamel.yaml | Better round-trip preservation | Heavier dependency, not needed | Rejected |
| regex extraction | No dependency | Fragile, error-prone | Rejected |

### Implementation Pattern
```python
import re
import yaml

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown content."""
    match = re.match(r'^---\n(.*?)\n---\n?(.*)', content, re.DOTALL)
    if not match:
        return {}, content
    try:
        metadata = yaml.safe_load(match.group(1))
        return metadata or {}, match.group(2)
    except yaml.YAMLError:
        return {}, content
```

---

## 2. Atomic File Move (Claim-by-Move Pattern)

### Decision
Use `os.rename()` for atomic moves on same filesystem; fallback to `shutil.move()` for cross-filesystem (not expected in this feature).

### Rationale
- `os.rename()` is atomic on POSIX when source and destination are on the same filesystem
- Claim-by-move: if source is missing when we attempt rename, another process already claimed it
- Existing codebase uses `shutil.move()` (mover.py:98) — we can follow the same pattern but optimize for same-filesystem case

### Alternatives Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| os.rename() | Atomic on same FS, fast | Fails cross-FS | **Selected** (same FS expected) |
| shutil.move() | Cross-FS safe | Not atomic, copy-then-delete | Fallback only |
| pathlib.Path.rename() | OOP, readable | Same as os.rename() | Equivalent |
| File locking (fcntl) | Explicit lock | Platform-dependent, complex | Rejected |

### Implementation Pattern
```python
from pathlib import Path
import os

def claim_and_move(source: Path, dest: Path) -> bool:
    """Atomically move file; return True if successful, False if already claimed."""
    try:
        os.rename(source, dest)
        return True
    except FileNotFoundError:
        # Source already claimed by another process
        return False
    except OSError:
        # Cross-filesystem or other error — caller handles retry
        raise
```

---

## 3. SLA Threshold Calculation

### Decision
Parse `captured_at` as ISO 8601 timestamp; compare to `datetime.now(timezone.utc)`.

### Rationale
- Gmail watcher already writes `captured_at` in ISO 8601 format (gmail_watcher.py:284)
- Using UTC avoids timezone ambiguity
- Python's `datetime.fromisoformat()` handles ISO 8601 natively

### Alternatives Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| datetime.fromisoformat() | Native, no deps | Python 3.11+ for full ISO | **Selected** (Python 3.12 in use) |
| dateutil.parser.parse() | Flexible | Extra dependency | Rejected |
| Unix timestamps | Simple math | Not human-readable in files | Rejected |

### Implementation Pattern
```python
from datetime import datetime, timezone, timedelta

def is_sla_breached(captured_at: str, threshold_hours: int = 24) -> bool:
    """Check if captured_at timestamp exceeds SLA threshold."""
    try:
        # Handle both 'Z' suffix and '+00:00' formats
        captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - captured) > timedelta(hours=threshold_hours)
    except (ValueError, TypeError):
        return False  # Invalid timestamp, skip SLA check
```

---

## 4. Keyword Matching Strategy

### Decision
Case-insensitive substring match against subject and body; keywords configurable via list.

### Rationale
- Simple substring match (`keyword.lower() in text.lower()`) is sufficient for urgency detection
- No need for regex complexity — urgency keywords are simple phrases
- Configuration via `.env` or Python list maintains flexibility

### Alternatives Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Substring match | Simple, fast, readable | No word boundary | **Selected** |
| Regex patterns | Flexible, word boundary | Overkill, slower | Rejected |
| NLP/ML classification | Context-aware | Heavy, external API | Out of scope |

### Default Keywords
```python
DEFAULT_URGENCY_KEYWORDS = [
    "urgent", "asap", "deadline", "critical", "time-sensitive",
    "immediate", "priority", "emergency", "action required"
]
```

---

## 5. Configuration Management

### Decision
Use environment variables via `.env` (python-dotenv) for runtime configuration.

### Rationale
- Consistent with existing gmail_watcher.py pattern
- No secrets in code (constitution constraint)
- Simple override without code changes

### Configuration Keys
| Key | Default | Description |
|-----|---------|-------------|
| `ROUTER_SLA_HOURS` | 24 | Hours before SLA breach triggers routing |
| `ROUTER_URGENCY_KEYWORDS` | See above | Comma-separated keyword list |
| `ROUTER_VERBOSE_LOG` | false | Log no-match files if true |
| `VAULT_PATH` | . | Path to vault root |

---

## 6. Logging Strategy

### Decision
Reuse existing `sentinel.logger.write_log_entry()` function.

### Rationale
- Consistent log format across all sentinels
- Already compliant with constitution (audit trail to `/Logs`)
- No new code for logging infrastructure

### Log Entry Structure
- `action_type`: `"routed"`, `"skipped"`, `"error"`
- `source_path`: Original file path in `/Inbox/email/`
- `dest_path`: Target path in `/Needs_Action/email/`
- `details`: Matched rule(s) — e.g., "Rules matched: starred, keyword:URGENT"

---

## 7. Directory Watching vs. Poll-on-Demand

### Decision
Implement as poll-on-demand (single scan function); leave watch mode integration to existing watchdog infrastructure.

### Rationale
- The router is a pure function: scan → evaluate → move
- Scheduling (interval, trigger) is orthogonal — can be invoked by:
  - Manual CLI call
  - Watchdog event handler
  - Cron/scheduled task
- Simpler to test in isolation

### Integration Points
- `src/sentinel/watcher.py` can call `route_inbox()` on file create events
- Alternatively, run as periodic job via `brain.py` orchestrator

---

## 8. Error Handling & Ralph Wiggum Loop

### Decision
Router itself does not implement retry loop; each move is atomic. Caller (watcher/orchestrator) handles retries.

### Rationale
- Atomic rename either succeeds or fails immediately
- No transient failures expected for local file operations
- Malformed frontmatter → skip file, log warning (not a retry scenario)
- Keeping router stateless simplifies testing

### Error Categories
| Error | Handling |
|-------|----------|
| File not found | Claimed by another process — skip silently |
| Malformed YAML | Log warning, leave file in Inbox |
| Permission denied | Log error, leave file in Inbox |
| Disk full | Log error, leave file in Inbox |

---

## 9. Performance Considerations

### Decision
Process files in a single iterator pass; no batching or threading needed.

### Rationale
- NFR-001 requires <5s for 1000 files
- Single-pass iteration: O(n) for n files
- YAML parsing + file move is fast (<5ms per file)
- 1000 files × 5ms = 5s — within budget with margin

### Optimization Notes
- Avoid reading full file contents for initial flag checks (frontmatter is at top)
- Use `Path.iterdir()` instead of `glob()` for minimal overhead
- Short-circuit evaluation: check flags first, then keywords, then SLA

---

## Dependencies Summary

| Dependency | Purpose | Already in pyproject.toml? |
|------------|---------|---------------------------|
| PyYAML | YAML frontmatter parsing | No — **needs to be added** |
| watchdog | Filesystem events (existing) | Yes |
| python-dotenv | Configuration loading | Yes |

**Action**: Add `pyyaml>=6.0` to `pyproject.toml` dependencies.

---

## Resolved Unknowns

All technical context unknowns have been resolved:

- [x] YAML parsing library → PyYAML
- [x] Atomic move strategy → os.rename() with claim semantics
- [x] SLA calculation method → datetime.fromisoformat() with UTC
- [x] Keyword matching approach → Case-insensitive substring
- [x] Configuration mechanism → .env via python-dotenv
- [x] Logging approach → Reuse sentinel.logger
- [x] Integration pattern → Poll-on-demand function
- [x] Error handling → Skip + log, no retry loop in router

---

**Research complete. Ready for Phase 1: Data Model & Contracts.**
