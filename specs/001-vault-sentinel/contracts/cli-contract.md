# CLI Contract: Vault Sentinel

**Feature**: 001-vault-sentinel
**Date**: 2026-02-11

## Commands

### `vault init`

Initialize the canonical folder structure in a vault directory.

**Usage**:
```
python -m sentinel init [--vault-path PATH]
```

**Arguments**:

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--vault-path` | No | Current directory | Path to vault root |

**Behavior**:
- Creates `Inbox`, `Needs_Action`, `Approved`, `Done`, `Logs`
  in the specified directory.
- Idempotent: skips existing folders, creates missing ones.
- Exits with code 0 on success.
- Exits with code 1 if the vault path does not exist or is not
  writable.

**Output (stdout)**:
```
Vault initialized at /path/to/vault
  Created: Inbox, Needs_Action
  Existing: Approved, Done, Logs
```

**Errors (stderr)**:
```
Error: Vault path '/nonexistent' does not exist.
Error: No write permission on '/readonly'.
```

---

### `vault watch`

Start the Sentinel file watcher on an initialized vault.

**Usage**:
```
python -m sentinel watch [--vault-path PATH] [--poll-interval SECONDS]
```

**Arguments**:

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--vault-path` | No | Current directory | Path to vault root |
| `--poll-interval` | No | 1.0 | Seconds between stability checks |

**Behavior**:
- Validates that the vault is initialized (all 5 folders exist).
  Exits with error if not.
- Watches `Inbox/` for new `.txt` and `.pdf` files.
- For each detected file:
  1. Waits for file stability (size unchanged for 0.5s).
  2. Writes execution plan to `Approved/`.
  3. Moves file to `Needs_Action/` (deduplicating name if needed).
  4. Writes log entry to `Logs/`.
- Retries failed operations up to 3 times (Ralph Wiggum loop).
- Runs until interrupted (Ctrl+C / SIGINT).

**Output (stdout)**:
```
Sentinel watching: /path/to/vault/Inbox
  Extensions: .txt, .pdf
  Press Ctrl+C to stop.

[2026-02-11 14:30:01] Moved: report.txt → Needs_Action/report.txt
[2026-02-11 14:30:05] Moved: data.pdf → Needs_Action/data.pdf
[2026-02-11 14:31:00] Renamed: report.txt → Needs_Action/report_1.txt (conflict)
```

**Errors (stderr)**:
```
Error: Vault not initialized at '/path'. Run 'vault init' first.
Error: Failed to move 'large.pdf' after 3 attempts. See Logs/.
```

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Clean shutdown (Ctrl+C) |
| 1 | Vault not initialized or invalid path |
| 2 | Unrecoverable error during watch |
