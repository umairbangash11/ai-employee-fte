# CLI Contract: CEO Briefing Generator

**Feature Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-18
**Command**: `sentinel-briefing`

---

## Overview

The `sentinel-briefing` CLI command generates CEO briefings from vault data. It is a
read-only operation with respect to external systems — it reads vault files and writes
only to `vault/Briefings/` and `vault/Logs/`.

---

## Installation

Registered in `pyproject.toml`:

```toml
[project.scripts]
sentinel-briefing = "briefing_generator.__main__:cli"
```

After installation: `pip install -e .`

---

## Commands

### `sentinel-briefing generate`

Generate a CEO briefing from current vault data.

**Synopsis**:

```bash
sentinel-briefing generate [OPTIONS]
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--vault-path` | PATH | `$VAULT_PATH` | Path to vault directory |
| `--force-adhoc` | FLAG | False | Generate Adhoc briefing even on Monday |
| `--dry-run` | FLAG | False | Print briefing to stdout without writing |
| `--verbose` | FLAG | False | Print debug information during generation |

**Output**:
- On success: Path to generated briefing file
- On error: Error message to stderr, exit code 1

**Examples**:

```bash
# Generate weekly briefing (Monday) or adhoc (other days)
sentinel-briefing generate

# Generate adhoc briefing on Monday
sentinel-briefing generate --force-adhoc

# Preview without writing
sentinel-briefing generate --dry-run

# Use specific vault path
sentinel-briefing generate --vault-path /path/to/vault
```

---

### `sentinel-briefing status`

Show current vault statistics relevant to briefing generation.

**Synopsis**:

```bash
sentinel-briefing status [OPTIONS]
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--vault-path` | PATH | `$VAULT_PATH` | Path to vault directory |

**Output**:

```
Vault Status: /path/to/vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Business Goals: 3 defined
Completed (7 days): 12 items
Needs Action: 5 items (2 stale)
Accounting: $12,500 invoiced, $8,000 paid
Upcoming Deadlines: 3 items

Last briefing: 2026-04-11_Monday_Briefing.md
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VAULT_PATH` | Yes* | Path to vault directory (*unless `--vault-path` provided) |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid vault path, write failure, etc.) |
| 2 | Invalid arguments |

---

## File Outputs

### Briefing File

**Location**: `vault/Briefings/YYYY-MM-DD_<type>_Briefing.md`

**Filename rules**:
- Monday: `YYYY-MM-DD_Monday_Briefing.md`
- Other days: `YYYY-MM-DD_Adhoc_Briefing.md`
- Duplicates: append `-2`, `-3`, etc. (e.g., `2026-04-18_Adhoc_Briefing-2.md`)

### Log Entry

**Location**: `vault/Logs/YYYY-MM-DDTHH-MM-SS_briefing_generation_<slug>.md`

**Content**: Standard 6-field log entry per Constitution Principle IX

---

## Integration

### MCP Tool (Future)

This phase does not define an MCP tool. The CLI is the primary interface. A future phase
may expose `briefing_generator.generate_briefing()` as an MCP tool for orchestrator
integration.

### Orchestrator Integration (Future)

The orchestrator can call `briefing_generator.generate_briefing()` programmatically:

```python
from briefing_generator import generate_briefing
from pathlib import Path

briefing_path = generate_briefing(
    vault_path=Path(os.environ["VAULT_PATH"]),
    force_adhoc=False,
)
```

---

## Error Handling

| Error | Behavior |
|-------|----------|
| `VAULT_PATH` not set | Exit with error message |
| Vault directory not found | Exit with error message |
| `Briefings/` cannot be created | Exit with error message |
| Malformed vault files | Skip file, log warning, continue |
| No data sources available | Generate briefing with "No data" sections |

---

## Telemetry

No external telemetry. All logging is local to `vault/Logs/`.
