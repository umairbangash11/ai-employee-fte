# Quickstart: Vault Sentinel

## Prerequisites

- Python 3.12+
- pip (included with Python)

## Install

```bash
# Clone the repository
git clone <repo-url>
cd ai-employee-fte

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

## Initialize Your Vault

```bash
# Initialize in current directory
python -m sentinel init

# Or specify a path
python -m sentinel init --vault-path ~/my-vault
```

Expected output:
```
Vault initialized at /home/user/my-vault
  Created: Inbox, Needs_Action, Approved, Done, Logs
```

## Start the Sentinel

```bash
# Watch the vault's Inbox folder
python -m sentinel watch --vault-path ~/my-vault
```

Expected output:
```
Sentinel watching: /home/user/my-vault/Inbox
  Extensions: .txt, .pdf
  Press Ctrl+C to stop.
```

## Test It

In a separate terminal:

```bash
# Drop a text file into Inbox
echo "Hello world" > ~/my-vault/Inbox/test.txt
```

The Sentinel should output:
```
[2026-02-11 14:30:01] Moved: test.txt → Needs_Action/test.txt
```

Verify:
```bash
# File moved to Needs_Action
ls ~/my-vault/Needs_Action/
# test.txt

# Log entry created
ls ~/my-vault/Logs/
# 2026-02-11T14-30-01_moved_test.txt.md

# Execution plan recorded
ls ~/my-vault/Approved/
# 2026-02-11T14-30-00_plan_move_test.txt.md
```

## Stop the Sentinel

Press `Ctrl+C` in the Sentinel terminal.

## Folder Structure

After initialization, your vault looks like:

```
my-vault/
├── Inbox/          ← Drop .txt and .pdf files here
├── Needs_Action/   ← Sentinel moves files here
├── Approved/       ← Execution plans (audit trail)
├── Done/           ← (Future use: completed items)
└── Logs/           ← Action logs (Obsidian-compatible)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Vault not initialized" | Run `python -m sentinel init` first |
| File not detected | Ensure file is `.txt` or `.pdf`; other extensions are ignored |
| Slow detection on WSL2 | Ensure vault is on WSL2 filesystem (`~/...`), not `/mnt/c/` |
| Permission error | Check read/write permissions on vault directory |
