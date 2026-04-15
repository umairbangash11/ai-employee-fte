# MCP Tool Contracts: Vault Server

**Feature**: 009-vault-mcp-server
**Date**: 2026-04-14
**Transport**: stdio
**Server name**: `vault`

---

## Tool: `list_files`

List all entries (files and directories) at a path relative to the vault root.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path from vault root. Use empty string or '.' for the vault root itself."
    }
  },
  "required": []
}
```

### Output

Returns a text response containing a newline-separated list of entry names.
Returns an empty response (no entries) if the path does not exist or is empty.

### Behaviour

| Condition | Response |
|-----------|----------|
| Path exists, has entries | Names of all files and subdirectories at that path, one per line |
| Path does not exist | Empty list (no error) |
| Path is empty string or `"."` | Entries at vault root |
| Path resolves outside vault root | Error: `"Path escapes vault root: {path}"` |

---

## Tool: `read_file`

Read the full UTF-8 text content of a file inside the vault.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path to the file from vault root (e.g. 'Inbox/email/msg.md')."
    }
  },
  "required": ["path"]
}
```

### Output

Returns the full file content as a text string.

### Behaviour

| Condition | Response |
|-----------|----------|
| File exists, UTF-8 readable | Full file content as string |
| File does not exist | Error: `"File not found: {path}"` |
| Path resolves outside vault root | Error: `"Path escapes vault root: {path}"` |
| File exists but is not UTF-8 decodable | Error: `"Cannot decode file as UTF-8: {path}"` |
| Path is a directory, not a file | Error: `"Path is a directory, not a file: {path}"` |

---

## Tool: `write_file`

Write (create or overwrite) a file inside the vault with provided text content.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path for the file from vault root (e.g. 'Needs_Action/plan.md')."
    },
    "content": {
      "type": "string",
      "description": "UTF-8 text content to write to the file."
    }
  },
  "required": ["path", "content"]
}
```

### Output

Returns a confirmation message: `"Written: {path}"`.

### Behaviour

| Condition | Response |
|-----------|----------|
| Parent directories exist | File created/overwritten with provided content |
| Parent directories missing | Intermediate directories created automatically, then file written |
| File already exists | Overwritten (last-write-wins) |
| Path resolves outside vault root | Error: `"Path escapes vault root: {path}"` |
| OS write failure | Error: `"Write failed: {reason}"` |

---

## Error Format

All errors are returned as MCP `isError: true` tool results with a single text content block:

```
Error: {error message}
```

No exceptions are raised to the MCP layer — all errors are caught and returned as structured tool results.
