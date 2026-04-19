# Tasks: Vault MCP Server (009)

**Input**: Design documents from `specs/009-vault-mcp-server/`
**Branch**: `009-vault-mcp-server`
**Date**: 2026-04-14

**Prerequisites**: plan.md ✅ | spec.md ✅ | data-model.md ✅ | contracts/ ✅

**User Stories**:
- US1 (P1): List Files in Vault — `list_files` tool
- US2 (P1): Read a File from the Vault — `read_file` tool
- US3 (P2): Write a File to the Vault — `write_file` tool

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Parallelisable (touches different files, no unresolved upstream dependency)
- **[US1/2/3]**: User story this task belongs to

---

## Phase 1: Setup

**Purpose**: Add the `mcp` dependency and create the empty module skeleton. Nothing works until these are done.

- [x] T001 Add `"mcp>=1.0,<2.0"` to `[project.dependencies]` in `pyproject.toml`
- [x] T002 Install updated dependencies — run `pip install -e .` from project root
- [x] T003 Validate `mcp` import — run `python3 -c "import mcp; print(mcp.__version__)"` and confirm a version is printed
- [x] T004 [P] Create empty `src/vault_mcp/__init__.py`
- [x] T005 [P] Create empty `tests/unit/vault_mcp/__init__.py`

**Checkpoint**: `python3 -c "import mcp"` exits 0. Module skeleton exists under `src/vault_mcp/` and `tests/unit/vault_mcp/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Path-safety helper, startup loader, and `.mcp.json` registration. All user story phases depend on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Implement `_safe_resolve(vault_root: Path, relative_path: str) -> Path` in `src/vault_mcp/server.py` — resolves `(vault_root / relative_path).resolve()`, raises `ValueError("Path escapes vault root: {relative_path}")` if result is not relative to vault_root; raises `ValueError("Path must not be empty")` if relative_path is empty string and caller is read_file or write_file
- [x] T007 Implement `load_vault_root() -> Path` in `src/vault_mcp/__main__.py` — calls `load_dotenv()`, reads `VAULT_PATH` from env, resolves to absolute path, raises `SystemExit(1)` with message `"Error: VAULT_PATH not set or directory does not exist"` if absent or not a directory
- [x] T008 Create `src/vault_mcp/__main__.py` `main()` entry point — calls `load_vault_root()`, instantiates the MCP server from `server.py`, starts stdio transport with `mcp.server.stdio.stdio_server()`
- [x] T009 Create `.mcp.json` at project root with content:
  ```json
  {
    "mcpServers": {
      "vault": {
        "command": "python3",
        "args": ["-m", "vault_mcp"],
        "cwd": "/home/umair/ai-employee-fte",
        "env": {
          "PYTHONPATH": "/home/umair/ai-employee-fte/src"
        }
      }
    }
  }
  ```

### Validation — Server Startup

- [x] T010 Validate `.mcp.json` is parseable — run `python3 -c "import json; d=json.load(open('.mcp.json')); assert 'mcpServers' in d; assert 'vault' in d['mcpServers']; print('ok')"` — must print `ok`
- [x] T011 Validate server starts with valid `VAULT_PATH` — run `VAULT_PATH=/home/umair/ai-employee-fte/vault python3 -m vault_mcp` (Ctrl-C after 2s); confirm no startup error is printed and process does not crash immediately
- [x] T012 Validate server exits with clear error when `VAULT_PATH` is unset — run `python3 -m vault_mcp` with no `VAULT_PATH` in env (unset it if needed); confirm output contains `"Error: VAULT_PATH"` and exit code is non-zero

**Checkpoint**: `.mcp.json` validates. Server starts cleanly with a valid vault. Server exits gracefully without a vault.

---

## Phase 3: User Story 1 — `list_files` (Priority: P1) 🎯 MVP

**Goal**: Claude can discover what files and folders exist anywhere in the vault.

**Independent Test**: Start the server with `VAULT_PATH` pointing to an initialized vault. Call `list_files` with `path: "Inbox"`. Response contains names of entries in that folder.

### Implementation — US1

- [x] T013 [US1] Implement `list_files` tool handler in `src/vault_mcp/server.py`:
  - Register tool with name `"list_files"`, description, and input schema `{"path": {"type": "string"}}`
  - Call `_safe_resolve(vault_root, args["path"])` — catch `ValueError` and return error text
  - If resolved path does not exist: return empty text (no error)
  - If resolved path exists: return `"\n".join(entry.name for entry in sorted(resolved.iterdir()))` as text content

### Unit Tests — US1

- [x] T014 [P] [US1] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_list_files_existing_path` — create a temp vault dir with `Inbox/email/msg.md`, call `list_files(path="Inbox/email")`, assert response contains `"msg.md"`
- [x] T015 [P] [US1] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_list_files_missing_path` — call `list_files(path="NoSuchFolder")`, assert response is empty (not an error)
- [x] T016 [P] [US1] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_list_files_vault_root` — call `list_files(path="")`, assert response contains top-level vault folder names
- [x] T017 [P] [US1] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_list_files_traversal_rejected` — call `list_files(path="../../etc")`, assert response text contains `"Path escapes vault root"`

### Validation — `list_files`

- [x] T018 [US1] Run `pytest tests/unit/vault_mcp/test_server.py -v -k "list_files"` — all 4 list_files tests must pass

**Checkpoint**: `list_files` is independently functional. US1 is complete and tested.

---

## Phase 4: User Story 2 — `read_file` (Priority: P1)

**Goal**: Claude can read the full content of any Markdown file in the vault by relative path.

**Independent Test**: Write a file to the vault manually. Call `read_file` with its path. Response contains the exact file content.

### Implementation — US2

- [x] T019 [US2] Implement `read_file` tool handler in `src/vault_mcp/server.py`:
  - Register tool with name `"read_file"`, description, and input schema `{"path": {"type": "string"}}` (required)
  - Call `_safe_resolve(vault_root, args["path"])` — catch `ValueError` (includes empty path and traversal) and return error text
  - If resolved path does not exist: return `f"Error: File not found: {args['path']}"`
  - If resolved path is a directory: return `f"Error: Path is a directory, not a file: {args['path']}"`
  - Read file with `resolved.read_text(encoding="utf-8")` — catch `UnicodeDecodeError` and return `f"Error: Cannot decode file as UTF-8: {args['path']}"`
  - Return file content as text

### Unit Tests — US2

- [x] T020 [P] [US2] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_read_file_success` — write `Inbox/test.md` with known content, call `read_file(path="Inbox/test.md")`, assert response equals file content
- [x] T021 [P] [US2] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_read_file_not_found` — call `read_file(path="Inbox/ghost.md")`, assert response contains `"File not found"`
- [x] T022 [P] [US2] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_read_file_traversal_rejected` — call `read_file(path="../../etc/passwd")`, assert response contains `"Path escapes vault root"`
- [x] T023 [P] [US2] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_read_file_directory_rejected` — call `read_file(path="Inbox")` where Inbox is a dir, assert response contains `"Path is a directory"`

### Validation — `read_file`

- [x] T024 [US2] Run `pytest tests/unit/vault_mcp/test_server.py -v -k "read_file"` — all 4 read_file tests must pass

**Checkpoint**: `read_file` is independently functional. US2 is complete and tested.

---

## Phase 5: User Story 3 — `write_file` (Priority: P2)

**Goal**: Claude can create or overwrite any Markdown file inside the vault, including creating intermediate directories.

**Independent Test**: Call `write_file` with a new path and content. Confirm the file exists on disk with that exact content immediately after the call.

### Implementation — US3

- [x] T025 [US3] Implement `write_file` tool handler in `src/vault_mcp/server.py`:
  - Register tool with name `"write_file"`, description, and input schema `{"path": {"type": "string"}, "content": {"type": "string"}}` (both required)
  - Call `_safe_resolve(vault_root, args["path"])` — catch `ValueError` and return error text
  - Create parent directories: `resolved.parent.mkdir(parents=True, exist_ok=True)`
  - Write content: `resolved.write_text(args["content"], encoding="utf-8")`
  - Catch `OSError` and return `f"Error: Write failed: {e}"`
  - Return `f"Written: {args['path']}"`

### Unit Tests — US3

- [x] T026 [P] [US3] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_write_file_creates_new` — call `write_file(path="Needs_Action/new.md", content="hello")`, assert file exists on disk with content `"hello"`
- [x] T027 [P] [US3] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_write_file_overwrites_existing` — create a file with old content, call `write_file` with new content on same path, assert disk content equals new content
- [x] T028 [P] [US3] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_write_file_creates_parent_dirs` — call `write_file(path="Deep/Sub/Dir/note.md", content="x")`, assert file exists at that nested path
- [x] T029 [P] [US3] Write unit test in `tests/unit/vault_mcp/test_server.py`: `test_write_file_traversal_rejected` — call `write_file(path="../../evil.md", content="x")`, assert response contains `"Path escapes vault root"` and no file is written outside vault

### Validation — `write_file`

- [x] T030 [US3] Run `pytest tests/unit/vault_mcp/test_server.py -v -k "write_file"` — all 4 write_file tests must pass

**Checkpoint**: `write_file` is independently functional. US3 is complete and tested.

---

## Phase 6: End-to-End Validation

**Purpose**: Verify the complete system — all tools, server lifecycle, `.mcp.json` registration — works as an integrated unit.

- [x] T031 Run full unit test suite — `pytest tests/unit/vault_mcp/ -v` — all 16 tests across US1, US2, US3 must pass with 0 failures
- [x] T032 Initialize vault if not already done — run `sentinel init` and confirm `vault/Inbox`, `vault/Needs_Action`, `vault/Done`, `vault/Approved`, `vault/Logs` all exist under `VAULT_PATH`
- [x] T033 End-to-end round-trip validation — with server running (`VAULT_PATH=/home/umair/ai-employee-fte/vault python3 -m vault_mcp`), execute in sequence via MCP client or direct tool-call test:
  1. `write_file(path="Inbox/round-trip-test.md", content="# Round Trip\nOK")` → expect `"Written: Inbox/round-trip-test.md"`
  2. `read_file(path="Inbox/round-trip-test.md")` → expect content `"# Round Trip\nOK"`
  3. `list_files(path="Inbox")` → expect `"round-trip-test.md"` in response
  4. Confirm `vault/Inbox/round-trip-test.md` exists on disk with correct content
- [ ] T034 Validate Claude Code server discovery — open Claude Code in this project, confirm `vault` MCP server appears in available tools list without manual configuration (verified by `.mcp.json` being present at project root)

**Checkpoint**: Silver-tier MCP requirement fully satisfied. All acceptance criteria from spec SC-001 through SC-005 are met.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup          → no dependencies, start immediately
Phase 2: Foundational   → requires Phase 1 complete (T001–T005)
Phase 3: US1            → requires Phase 2 complete (T006–T012)
Phase 4: US2            → requires Phase 2 complete; can run in parallel with Phase 3
Phase 5: US3            → requires Phase 2 complete; can run in parallel with Phase 3 & 4
Phase 6: Validation     → requires Phases 3, 4, 5 all complete
```

### Within Each Phase

- T013 (implement list_files) must complete before T014–T017 (its tests)
- T019 (implement read_file) must complete before T020–T023 (its tests)
- T025 (implement write_file) must complete before T026–T029 (its tests)
- T006 (_safe_resolve helper) must complete before T013, T019, T025 (all tool implementations depend on it)

### Parallel Opportunities

```bash
# Phase 1 — T004 and T005 can run together:
Task: "Create src/vault_mcp/__init__.py"
Task: "Create tests/unit/vault_mcp/__init__.py"

# Phase 3 — unit tests T014–T017 can all run together after T013:
Task: "test_list_files_existing_path"
Task: "test_list_files_missing_path"
Task: "test_list_files_vault_root"
Task: "test_list_files_traversal_rejected"

# Phase 4 — unit tests T020–T023 can all run together after T019:
Task: "test_read_file_success"
Task: "test_read_file_not_found"
Task: "test_read_file_traversal_rejected"
Task: "test_read_file_directory_rejected"

# Phase 5 — unit tests T026–T029 can all run together after T025:
Task: "test_write_file_creates_new"
Task: "test_write_file_overwrites_existing"
Task: "test_write_file_creates_parent_dirs"
Task: "test_write_file_traversal_rejected"
```

---

## Implementation Strategy

### MVP (US1 only — `list_files`)

1. Phase 1: Setup (T001–T005)
2. Phase 2: Foundational (T006–T012) — includes server startup validation
3. Phase 3: US1 (T013–T018) — `list_files` working end-to-end
4. **STOP**: confirm Silver tier MCP requirement is met at minimum viable level

### Full Silver Completion

1. Complete MVP above
2. Phase 4: US2 (T019–T024) — add `read_file`
3. Phase 5: US3 (T025–T030) — add `write_file`
4. Phase 6: Validation (T031–T034) — end-to-end + Claude Code integration

---

## Notes

- Total tasks: **34** (T001–T034)
- Tasks per phase: Setup 5 | Foundational 7 | US1 6 | US2 6 | US3 6 | Validation 4
- All path traversal tests are [P] parallelisable — they touch no shared mutable state
- `_safe_resolve()` (T006) is the single most critical task — all three tool implementations depend on it
- The `PYTHONPATH` env in `.mcp.json` (T009) ensures the `vault_mcp` module is importable when Claude Code spawns the server process
- Do not add any tools beyond `list_files`, `read_file`, `write_file` — spec FR-002 is explicit
