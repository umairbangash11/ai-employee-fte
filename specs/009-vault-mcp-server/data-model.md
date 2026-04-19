# Data Model: Vault MCP Server

**Feature**: 009-vault-mcp-server
**Date**: 2026-04-14

## Entities

### VaultRoot

The absolute filesystem path that is the root of the Obsidian vault. Resolved once at server startup from the `VAULT_PATH` environment variable.

| Attribute | Type | Description |
|-----------|------|-------------|
| `path` | `pathlib.Path` (absolute) | Resolved vault root directory |

**Constraints**:
- Must exist as a directory at server startup
- Must be readable and writable by the server process
- If absent or invalid, server exits with a non-zero code and an error message

---

### RelativePath

A path string provided by an MCP tool caller, interpreted relative to `VaultRoot`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `value` | `str` | Raw path string from the caller |
| `resolved` | `pathlib.Path` (absolute) | `(vault_root / value).resolve()` |

**Validation rules**:
- `resolved.is_relative_to(vault_root)` MUST be `True` — if not, reject with `"Path escapes vault root"`
- Empty string (`""`) is valid for `list_files` (means vault root); invalid for `read_file` and `write_file`

---

### FileEntry

A single name (file or directory) returned as part of a `list_files` response.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Filename or directory name (not a full path) |

---

### FileContent

The UTF-8 text content of a vault file.

| Attribute | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Full file content decoded as UTF-8 |

**Constraints**:
- Must be decodable as UTF-8; binary files are rejected with an error
- No maximum size enforced at this scope (vault files are Markdown — typically small)

---

## State Transitions

The server is stateless. Each tool call is independent. No session state, no cache, no in-memory index.

```
Tool call received
      │
      ▼
Validate RelativePath (traversal check)
      │
   ┌──┴──────────────┐
   │                 │
INVALID           VALID
   │                 │
Return error     Execute filesystem operation
                     │
              Return result or error
```
