# MCP Contract: Vault File Server

**Domain**: `vault`
**Phase**: Gold Phase 1 (fully specified — existing tools)
**Status**: Active
**Server**: `src/vault_mcp/server.py`

---

## Overview

The Vault MCP Server is the **sole interface** for all external clients (Claude Code,
future Gold-tier integrations) reading or writing vault files. No component may bypass
this server to access vault files directly from outside its process.

All operations are scoped to the vault root defined by the `VAULT_PATH` environment
variable. Any path that would escape the vault root is rejected with a `ValueError`
and logged.

---

## Tools

### `list_files`

List all Markdown files under a path within the vault.

| Field | Value |
|-------|-------|
| **Tool name** | `list_files` |
| **Requires approval** | No |
| **Approval gate** | None — read-only operation |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `string` | Yes | Relative path within the vault (e.g. `"Inbox/email"`) |

**Output**:

```json
{
  "files": ["Inbox/email/20260415-120000-gmail.md", "..."]
}
```

Returns a list of relative file paths (strings) under the given path.
Returns an empty list if the directory does not exist or contains no `.md` files.

**Error behavior**:

| Condition | Response |
|-----------|----------|
| Path escapes vault root | `ValueError` raised; operation rejected; violation logged |
| Directory does not exist | Returns `{"files": []}` (non-blocking) |
| Permission error | Error logged; exception propagated to caller |

---

### `read_file`

Read the content of a single Markdown file from the vault.

| Field | Value |
|-------|-------|
| **Tool name** | `read_file` |
| **Requires approval** | No |
| **Approval gate** | None — read-only operation |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `string` | Yes | Relative path to the file within the vault |

**Output**:

```json
{
  "content": "---\nsource: gmail-api\n...\n---\n\nEmail body here."
}
```

Returns the full file content as a string (UTF-8).

**Error behavior**:

| Condition | Response |
|-----------|----------|
| Path escapes vault root | `ValueError` raised; operation rejected; violation logged |
| File does not exist | `FileNotFoundError` raised; propagated to caller |
| Permission error | Error logged; exception propagated |

---

### `write_file`

Write (create or overwrite) a Markdown file in the vault.

| Field | Value |
|-------|-------|
| **Tool name** | `write_file` |
| **Requires approval** | No (within vault boundary) |
| **Approval gate** | None for internal vault writes; external actions require `Approved/` gate |

**Input parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `string` | Yes | Relative path to the target file within the vault |
| `content` | `string` | Yes | Full file content to write (UTF-8) |

**Output**:

```json
{
  "written": "Inbox/email/20260415-120000-gmail.md"
}
```

Returns the relative path of the written file on success.

**Error behavior**:

| Condition | Response |
|-----------|----------|
| Path escapes vault root | `ValueError` raised; operation rejected; violation logged |
| Parent directory missing | Created automatically (`mkdir -p`) before write |
| Write permission error | Error logged; exception propagated |

---

## Logging

Every operation MUST produce a log entry in `vault/Logs/` with all 6 required fields:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 UTC timestamp |
| `action_type` | One of: `list_files`, `read_file`, `write_file` |
| `source_path` | Input path parameter |
| `dest_path` | Output path (same as source for reads; written path for writes) |
| `outcome` | `success` or `failure` |
| `details` | Human-readable summary including tool name and any error context |

---

## Security

- Vault root is set once at server startup via `VAULT_PATH` env var.
- `_safe_resolve()` enforces that all resolved paths are children of the vault root.
- No credentials are required or stored by this server.
- Server runs locally; no network exposure.
