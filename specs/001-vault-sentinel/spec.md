# Feature Specification: Vault Sentinel — Obsidian Structure & File Watcher

**Feature Branch**: `001-vault-sentinel`
**Created**: 2026-02-11
**Status**: Draft
**Input**: User description: "Create a system that initializes an Obsidian vault structure with folders for Inbox, Needs_Action, Approved, Done, and Logs. It must also include a basic Python-based 'Sentinel' script that watches the /Inbox folder for new .txt or .pdf files and moves them to /Needs_Action while creating a log entry."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Initialize Vault Structure (Priority: P1)

A user runs a single command to create the canonical folder
structure inside a specified directory (or the current directory
by default). After running the command, the five required folders
(`Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs`) exist and
are ready for use with Obsidian.

**Why this priority**: Without the folder structure, no other
feature (including the Sentinel watcher) can operate. This is
the foundational prerequisite for the entire Digital FTE system.

**Independent Test**: Run the initialization command on an empty
directory and verify all five folders are created with correct
names. Open the directory in Obsidian and confirm it loads as a
valid vault.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** the user runs the
   vault initialization command, **Then** five folders are
   created: `Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs`.
2. **Given** a directory that already contains some of the
   folders, **When** the user runs the initialization command,
   **Then** missing folders are created and existing folders are
   left untouched (no data loss).
3. **Given** a directory that already has all five folders,
   **When** the user runs the initialization command, **Then**
   the command completes successfully without errors or data
   modification (idempotent behavior).

---

### User Story 2 — Sentinel Watches Inbox for New Files (Priority: P2)

A user starts the Sentinel script, pointing it at the vault root.
The Sentinel continuously watches the `Inbox` folder. When a new
`.txt` or `.pdf` file appears, the Sentinel moves it to
`Needs_Action` and writes a timestamped log entry to the `Logs`
folder.

**Why this priority**: This is the core automation behavior — the
reason the Sentinel exists. It depends on the vault structure
(US1) being in place but delivers the primary business value of
automated file triage.

**Independent Test**: Start the Sentinel, drop a `.txt` file into
`Inbox`, and verify within a few seconds that (a) the file
appears in `Needs_Action`, (b) it no longer exists in `Inbox`,
and (c) a log entry exists in `Logs`.

**Acceptance Scenarios**:

1. **Given** the Sentinel is running and the vault is initialized,
   **When** a `.txt` file is placed in `Inbox`, **Then** the file
   is moved to `Needs_Action` and a log entry is created in `Logs`.
2. **Given** the Sentinel is running, **When** a `.pdf` file is
   placed in `Inbox`, **Then** the file is moved to `Needs_Action`
   and a log entry is created in `Logs`.
3. **Given** the Sentinel is running, **When** a file with an
   unsupported extension (e.g., `.jpg`, `.zip`) is placed in
   `Inbox`, **Then** the file remains in `Inbox` and no log entry
   is created for it.
4. **Given** the Sentinel is running, **When** a file is moved to
   `Needs_Action`, **Then** the log entry includes: timestamp,
   original filename, source folder, destination folder, and file
   size.

---

### User Story 3 — Sentinel Handles Naming Conflicts (Priority: P3)

When the Sentinel moves a file from `Inbox` to `Needs_Action`, a
file with the same name may already exist in `Needs_Action`. The
Sentinel MUST handle this gracefully without overwriting or losing
data.

**Why this priority**: Data loss prevention. While not part of the
happy path, this is critical for trust in the automated system.

**Independent Test**: Place a file named `report.txt` in
`Needs_Action` manually, then drop another `report.txt` into
`Inbox`. Verify both files are preserved (the new one is renamed)
and the log records the conflict resolution.

**Acceptance Scenarios**:

1. **Given** `Needs_Action` already contains `report.txt`,
   **When** a new `report.txt` appears in `Inbox`, **Then** the
   new file is moved to `Needs_Action` with a deduplicated name
   (e.g., `report_1.txt`) and a log entry records the rename.
2. **Given** `Needs_Action` contains `report.txt` and
   `report_1.txt`, **When** another `report.txt` appears in
   `Inbox`, **Then** it is renamed to `report_2.txt` (incrementing
   the suffix).

---

### Edge Cases

- What happens when the `Inbox` folder is deleted while the
  Sentinel is running? The Sentinel MUST log an error and exit
  gracefully (or pause and retry per the Ralph Wiggum loop).
- What happens when the user lacks write permissions on
  `Needs_Action`? The Sentinel MUST log the permission error,
  leave the file in `Inbox`, and continue watching.
- What happens when a file is still being written to `Inbox`
  (partial write)? The Sentinel MUST wait for the file to be
  fully written before moving it (e.g., by checking that the
  file size has stabilized).
- What happens when multiple files arrive in `Inbox`
  simultaneously? The Sentinel MUST process each file
  individually without skipping any.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create the five canonical folders
  (`Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs`) in a
  user-specified or default vault directory.
- **FR-002**: Vault initialization MUST be idempotent — running
  it multiple times MUST NOT destroy existing data or folders.
- **FR-003**: The Sentinel MUST watch the `Inbox` folder for
  newly created files with `.txt` or `.pdf` extensions.
- **FR-004**: The Sentinel MUST move matched files from `Inbox`
  to `Needs_Action`.
- **FR-005**: The Sentinel MUST create a human-readable log entry
  in the `Logs` folder for each file moved, including timestamp,
  filename, source, destination, and file size.
- **FR-006**: The Sentinel MUST ignore files with extensions other
  than `.txt` and `.pdf`.
- **FR-007**: The Sentinel MUST handle filename conflicts in
  `Needs_Action` by appending an incrementing numeric suffix
  (e.g., `_1`, `_2`) without overwriting existing files.
- **FR-008**: The Sentinel MUST retry failed file operations up to
  3 times (per constitution Principle V) before logging a failure
  and moving the task to `Needs_Action` (human review).
- **FR-009**: The Sentinel MUST write an execution plan to
  `/Approved` before performing any file move operation (per
  constitution Principle IV). At Bronze Tier, this plan MAY be a
  structured log entry written atomically before the move.
- **FR-010**: Log entries MUST be valid Markdown files compatible
  with Obsidian (per constitution Operational Constraints).

### Key Entities

- **Vault**: The root directory containing the five canonical
  folders. Represents the workspace managed by the Digital FTE.
- **Watched File**: A `.txt` or `.pdf` file detected in `Inbox`.
  Key attributes: filename, extension, size, creation timestamp.
- **Log Entry**: A Markdown file in `Logs` recording a Sentinel
  action. Key attributes: timestamp, action type, source path,
  destination path, file metadata, outcome (success/failure).
- **Execution Plan**: A record in `Approved` documenting the
  intended action before execution. Key attributes: action
  description, affected paths, rollback strategy, expected
  outcome.

### Assumptions

- The vault directory is on a local filesystem (not a network
  share or cloud-synced folder during active monitoring).
- The user has read/write permissions on the vault directory.
- File sizes are reasonable for local operations (under 100 MB
  per file).
- The Sentinel runs as a foreground process; daemonization is
  out of scope for Bronze Tier.
- Log files accumulate without automatic rotation; log management
  is out of scope for Bronze Tier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can initialize the vault structure in under
  5 seconds on a standard local filesystem.
- **SC-002**: The Sentinel detects and processes a new file in
  `Inbox` within 10 seconds of it being fully written.
- **SC-003**: 100% of `.txt` and `.pdf` files placed in `Inbox`
  are moved to `Needs_Action` with a corresponding log entry
  (zero silent drops).
- **SC-004**: Zero data loss — no files are overwritten or
  deleted during move operations, including naming conflicts.
- **SC-005**: The Sentinel runs continuously for at least 24 hours
  without crashing under normal operating conditions.
- **SC-006**: Every Sentinel action produces a human-readable log
  entry viewable in Obsidian.
