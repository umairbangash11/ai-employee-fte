# Feature Specification: Vault MCP Server (Silver Tier Compliance)

**Feature Branch**: `009-vault-mcp-server`
**Created**: 2026-04-14
**Status**: Draft
**Input**: User description: "Implement a minimal MCP server for the local Obsidian vault exposing list_files, read_file, and write_file operations to satisfy the Silver-tier MCP server requirement"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — List Files in Vault (Priority: P1)

A developer or Claude agent needs to discover what files exist inside the vault. The system exposes a tool that accepts a relative folder path and returns all file names within that folder.

**Why this priority**: File listing is the foundation of all other operations. Without it, read and write cannot be meaningfully targeted. It is the smallest unit of working MCP integration.

**Independent Test**: Start the MCP server, connect a client, call `list_files` with `path: "Inbox"`. The tool returns a list of file names in that folder. Delivers immediate verifiable value on its own.

**Acceptance Scenarios**:

1. **Given** the vault contains files at `Inbox/email/msg1.md`, **When** a client calls `list_files` with `path: "Inbox/email"`, **Then** the response contains `["msg1.md"]`
2. **Given** a path that does not exist in the vault, **When** a client calls `list_files`, **Then** the server returns an empty list (not an error)
3. **Given** the vault root is provided as the path (`""`), **When** a client calls `list_files`, **Then** the server returns all top-level folder and file names

---

### User Story 2 — Read a File from the Vault (Priority: P1)

Claude or any MCP client needs to read the full text content of a specific Markdown file inside the vault to reason over it (e.g., triage an email, review a draft).

**Why this priority**: Reading vault content is required for the orchestrator to function as an AI agent via MCP. It enables Claude to access vault state directly without custom integration code.

**Independent Test**: Call `read_file` with a known relative path. The response contains the exact file content as a string. Can be tested independently without `write_file`.

**Acceptance Scenarios**:

1. **Given** a file exists at `Inbox/email/test.md`, **When** a client calls `read_file` with `path: "Inbox/email/test.md"`, **Then** the response contains the full file content as a UTF-8 string
2. **Given** a file does not exist, **When** a client calls `read_file`, **Then** the server returns a clear error message indicating the file was not found
3. **Given** a path that points outside the vault root (e.g., `../../etc/passwd`), **When** a client calls `read_file`, **Then** the server rejects the request with an error

---

### User Story 3 — Write a File to the Vault (Priority: P2)

Claude or an MCP client needs to create or overwrite a Markdown file in the vault (e.g., write a draft reply, create a plan, emit a log entry).

**Why this priority**: Write capability closes the loop — the AI agent can produce outputs into the vault, not just consume them. Dependent on listing and reading being functional first.

**Independent Test**: Call `write_file` with a path and content string. Verify the file exists on disk with the correct content immediately after the call.

**Acceptance Scenarios**:

1. **Given** the vault exists, **When** a client calls `write_file` with `path: "Needs_Action/test-plan.md"` and a content string, **Then** a file is created at that path with that exact content
2. **Given** a file already exists at the target path, **When** a client calls `write_file`, **Then** the existing file is overwritten with the new content
3. **Given** the parent directory does not exist, **When** a client calls `write_file`, **Then** the server creates intermediate directories and writes the file successfully
4. **Given** a path that escapes the vault root, **When** a client calls `write_file`, **Then** the server rejects the request with an error

---

### Edge Cases

- What happens when `list_files` is called on a path containing only subdirectories (no files)? Returns directory names in the listing.
- How does `read_file` handle a non-UTF-8 binary file? Return an error with a clear message.
- What if `VAULT_PATH` is not set or points to a non-existent directory at server startup? Server exits with a clear error message.
- What if two clients call `write_file` on the same path simultaneously? Last-write-wins is acceptable for this scope.
- What if a path contains spaces or special characters? Handled as a standard filesystem path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a single MCP server process implementing the MCP protocol over stdio transport
- **FR-002**: The server MUST expose exactly three tools: `list_files`, `read_file`, `write_file` — no additional tools
- **FR-003**: `list_files` MUST accept a `path` parameter (relative to vault root) and return names of all entries (files and directories) at that path
- **FR-004**: `read_file` MUST accept a `path` parameter and return the full UTF-8 text content of the specified file
- **FR-005**: `write_file` MUST accept `path` and `content` parameters, write the content to the file, and create parent directories if they do not exist
- **FR-006**: All three tools MUST validate that the resolved absolute path remains inside the vault root — path traversal attempts MUST be rejected with an error
- **FR-007**: The server MUST read `VAULT_PATH` from the environment (or `.env` file) at startup and use it as the vault root; if absent or invalid, the server MUST exit with a clear error
- **FR-008**: The server MUST be registered in `.mcp.json` at the project root, pointing to the server entry point and the correct command to start it
- **FR-009**: The server MUST NOT modify, read, or list any files outside the vault root
- **FR-010**: The server MUST return structured error messages (not crash) for all invalid inputs: file-not-found, path-traversal, unreadable content

### Key Entities

- **Vault Root**: The absolute directory path defined by `VAULT_PATH`. All file operations are scoped exclusively to this directory tree.
- **Relative Path**: A path string provided by the MCP client, interpreted relative to the vault root. Must resolve to a location within the vault root.
- **MCP Tool**: A named callable operation exposed by the server with a defined input schema and a return value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three tools respond successfully when called with valid inputs against an initialized vault — zero tool failures on valid input
- **SC-002**: Path traversal attempts are rejected with an error in 100% of cases — zero successful escapes from vault root
- **SC-003**: The server process starts and is ready to accept connections in under 3 seconds from a cold launch
- **SC-004**: `.mcp.json` is present at the project root and Claude Code connects to the server without any manual configuration beyond the file
- **SC-005**: A round-trip test (write a file → read it back → list its directory) completes successfully and returns consistent results

## Assumptions

- The vault has been initialized via `sentinel init` before the MCP server is used in production.
- `VAULT_PATH` is set in the project's `.env` file; if absent the server fails at startup with a clear message.
- Transport is stdio (not HTTP/SSE), consistent with Claude Code's local MCP server model.
- Python 3.12 and the existing `venv/` are used — no new language runtime is introduced.
- The `mcp` Python package will be added as a dependency in `pyproject.toml`.
- The server is local-only; no network exposure, authentication, or access control beyond path-traversal prevention is required.

## Out of Scope

- No additional tools beyond `list_files`, `read_file`, `write_file`
- No Gold-tier features of any kind
- No refactoring of existing modules
- No HTTP/SSE transport
- No authentication or multi-user access control
- No real-time file watching or push notifications from the MCP server
- No changes to `.specify/` internal folders or SpecifyPlus infrastructure
