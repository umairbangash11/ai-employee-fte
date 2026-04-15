# Implementation Plan: Vault MCP Server

**Branch**: `009-vault-mcp-server` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/009-vault-mcp-server/spec.md`

## Summary

Implement a minimal MCP server (`src/vault_mcp/`) that exposes three tools — `list_files`, `read_file`, `write_file` — scoped exclusively to the Obsidian vault defined by `VAULT_PATH`. Register the server in `.mcp.json` at the project root so Claude Code can discover and connect to it automatically. Add the `mcp` Python package as a dependency in `pyproject.toml`. This satisfies the only remaining Silver-tier blocking requirement: at least one working MCP server.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: `mcp>=1.0` (MCP Python SDK — not yet installed), `python-dotenv>=1.0` (already installed)  
**Storage**: Local filesystem — vault directory defined by `VAULT_PATH` env var  
**Testing**: pytest (already configured in `pyproject.toml`)  
**Target Platform**: Linux (WSL2), local process launched by Claude Code  
**Project Type**: Single project — `src/` layout, `setuptools.packages.find` from `src/`  
**Performance Goals**: Cold start under 3 seconds; individual tool calls under 100ms for typical vault sizes  
**Constraints**: All paths must resolve inside vault root (path traversal prevention); no external network calls; no cloud dependencies  
**Scale/Scope**: Single local user; vault expected to contain hundreds of Markdown files

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First | ✅ PASS | MCP server is a local process; no cloud calls; only reads `.env` for `VAULT_PATH` |
| II. Canonical Folder Structure | ✅ PASS | Server exposes existing vault structure, does not create or rename canonical folders |
| III. Tiered Scope | ✅ PASS | Silver Tier compliance work — MCP server is an explicit Silver requirement |
| IV. Safety-First Execution | ✅ PASS | `write_file` is constrained to vault root only; no execution plans, deletions, or moves |
| V. Ralph Wiggum Loop | ✅ N/A | Server returns structured errors on failure; caller handles retries; no autonomous task execution |
| VI. Silver Tier Autonomy | ✅ PASS | Server performs vault file I/O only — no external messaging, no API calls with side effects |
| VII. Phased Development | ✅ PASS | This is Silver completion work, not a new phase; no phase boundary crossed |
| VIII. Gmail API Migration Safety | ✅ N/A | Gmail unrelated to this feature |

**Gate result: PASS — all principles satisfied. No violations.**

## Phase 0: Research

### Findings

**Decision 1: MCP Python SDK**
- **Chosen**: `mcp` package from PyPI (`pip install mcp`)
- **Rationale**: Official Anthropic Python SDK for MCP servers. Provides `Server`, `stdio_server()` context manager, and `@server.list_tools()` / `@server.call_tool()` decorators. Minimal boilerplate.
- **Alternatives**: Raw JSON-RPC over stdio (rejected — unnecessary complexity; SDK handles framing, schema, and lifecycle)

**Decision 2: Transport**
- **Chosen**: stdio (stdin/stdout)
- **Rationale**: Claude Code spawns local MCP servers as child processes communicating over stdio. This is the standard and only supported transport for locally registered servers in `.mcp.json`.
- **Alternatives**: HTTP/SSE (rejected — requires a running server port; not needed for local use)

**Decision 3: Entry point**
- **Chosen**: `python3 -m vault_mcp` (module entry point)
- **Rationale**: No venv is present (`venv/bin/activate` does not exist); system Python 3.12.3 is used. Module entry point is portable and does not depend on a PATH-installed script.
- **Alternatives**: CLI script via `pyproject.toml` `[project.scripts]` (acceptable addition, but module entry is sufficient and simpler for `.mcp.json`)

**Decision 4: Path traversal prevention**
- **Chosen**: `Path.resolve()` on the input path joined to vault root, then check `resolved.is_relative_to(vault_root)`
- **Rationale**: `is_relative_to()` is available in Python 3.9+ and is the idiomatic stdlib check. Covers all traversal forms including `..`, symlinks, and absolute path injections.
- **Alternatives**: String prefix check (rejected — fragile; bypassed by symlinks and unicode normalization)

**Decision 5: `.mcp.json` format**
- **Chosen**: Project-scoped `.mcp.json` at repo root (Claude Code project-level MCP config)
- **Rationale**: Claude Code loads `.mcp.json` from the project root automatically. No user-level config changes required.
- **Format**:
  ```json
  {
    "mcpServers": {
      "vault": {
        "command": "python3",
        "args": ["-m", "vault_mcp"],
        "cwd": "/home/umair/ai-employee-fte"
      }
    }
  }
  ```

**Output**: All NEEDS CLARIFICATION resolved. No blockers.

## Phase 1: Design & Contracts

### Data Model

See [`data-model.md`](./data-model.md).

**Entities**:
- **VaultRoot**: The absolute `Path` resolved from `VAULT_PATH` env var at server startup. Immutable for the server's lifetime.
- **RelativePath**: A string provided by the tool caller, always interpreted relative to `VaultRoot`. Must survive `is_relative_to(vault_root)` check after `resolve()`.
- **FileEntry**: A name string (filename or directory name) returned by `list_files`.
- **FileContent**: A UTF-8 string returned by `read_file` or accepted by `write_file`.

**Validation rules**:
- `RelativePath` must not be empty for `read_file` and `write_file`
- Resolved path must satisfy `resolved.is_relative_to(vault_root)` — raises `ValueError` otherwise
- `read_file` content must be decodable as UTF-8 — raises `ValueError` on binary files
- `write_file` content must be a string — type enforced by tool schema

### API Contracts

See [`contracts/vault-mcp-tools.md`](./contracts/vault-mcp-tools.md).

**Tool: `list_files`**
```
Input:  { path: string }           # relative path from vault root; "" = root
Output: { files: [string] }        # names of all entries at that path
Errors: none (returns [] for missing path)
```

**Tool: `read_file`**
```
Input:  { path: string }           # relative path to a specific file
Output: { content: string }        # full UTF-8 file content
Errors: "File not found: {path}" | "Path escapes vault root" | "Cannot decode file as UTF-8"
```

**Tool: `write_file`**
```
Input:  { path: string, content: string }   # relative path + content to write
Output: { written: true, path: string }     # confirmation
Errors: "Path escapes vault root" | "Write failed: {reason}"
```

### Project Structure

```text
specs/009-vault-mcp-server/
├── plan.md              ← this file
├── research.md          ← Phase 0 output (inline above)
├── data-model.md        ← Phase 1 output
├── contracts/
│   └── vault-mcp-tools.md
└── tasks.md             ← Phase 2 output (/sp.tasks)
```

```text
src/
└── vault_mcp/           ← NEW module (3 files only)
    ├── __init__.py      ← empty
    ├── __main__.py      ← entry point: loads env, starts server
    └── server.py        ← MCP server: 3 tools, path safety, error handling

.mcp.json                ← NEW at project root
pyproject.toml           ← MODIFIED: add mcp>=1.0 dependency
tests/
└── unit/
    └── vault_mcp/
        ├── __init__.py
        └── test_server.py  ← unit tests for all 3 tools + path traversal
```

**Structure Decision**: Single-project layout. New module `src/vault_mcp/` follows exact same pattern as all existing modules (`sentinel`, `gmail_watcher`, etc.). No new directories at repo root.

## Implementation Sequence

Tasks are ordered by dependency. Each task is independently verifiable.

### Task 1 — Add `mcp` dependency to `pyproject.toml`
- Add `"mcp>=1.0"` to `[project.dependencies]`
- Run `pip install -e .` to install
- **Verify**: `python3 -c "import mcp; print(mcp.__version__)"` prints a version

### Task 2 — Create `src/vault_mcp/` module skeleton
- Create `src/vault_mcp/__init__.py` (empty)
- Create `src/vault_mcp/__main__.py` (loads `.env`, reads `VAULT_PATH`, starts server)
- Create `src/vault_mcp/server.py` (MCP server with 3 tools)
- **Verify**: `python3 -m vault_mcp --help` exits without error (or starts and waits for stdio)

### Task 3 — Implement `server.py` with all 3 tools
- Implement `_safe_resolve(vault_root, relative_path)` helper with traversal check
- Implement `list_files` tool
- Implement `read_file` tool
- Implement `write_file` tool
- **Verify**: Import the module cleanly: `python3 -c "from vault_mcp.server import create_server; print('ok')"`

### Task 4 — Create `.mcp.json` at project root
- Write `.mcp.json` with `vault` server pointing to `python3 -m vault_mcp`
- **Verify**: `cat .mcp.json` is valid JSON; `python3 -c "import json; json.load(open('.mcp.json'))"` exits 0

### Task 5 — Write unit tests for all tools and path safety
- `tests/unit/vault_mcp/__init__.py`
- `tests/unit/vault_mcp/test_server.py` — tests for:
  - `list_files` on existing path, missing path, vault root
  - `read_file` on existing file, missing file, path traversal attempt
  - `write_file` creates file, overwrites file, creates missing parents, rejects traversal
- **Verify**: `pytest tests/unit/vault_mcp/ -v` — all tests pass

### Task 6 — End-to-end round-trip verification
- Initialize a test vault: `sentinel init` (or manually create `vault/` dirs)
- Run MCP server: `python3 -m vault_mcp`
- Confirm Claude Code detects the server via `.mcp.json`
- Call `write_file` → `read_file` → `list_files` in sequence
- **Verify**: Round-trip returns consistent data; no crashes; vault files visible on disk

## Complexity Tracking

No constitution violations. No complexity justifications required.

## Risks

1. **`mcp` package API stability**: The MCP Python SDK is relatively new. If the API differs from expected, `server.py` may need adjustment. Mitigation: pin to `mcp>=1.0,<2.0` and test with the installed version before writing tool handlers.
2. **No venv**: The project runs on system Python. If `python3` on the system is not 3.12, the module entry point in `.mcp.json` may behave differently. Mitigation: verify `python3 --version` is 3.12.x before running.
3. **`.mcp.json` `cwd`**: If Claude Code does not honour the `cwd` field, the module import may fail. Mitigation: use absolute path to Python and the module's `src/` parent in `PYTHONPATH` env in `.mcp.json` as a fallback.
