# Quickstart: Inbox → Needs_Action Router

**Feature**: 002-inbox-router
**Date**: 2026-02-27

## Prerequisites

- Python 3.12+
- Vault with canonical folder structure (`/Inbox`, `/Needs_Action`, `/Logs`)
- Gmail sentinel running (or test markdown files in `/Inbox/email/`)

## Installation

```bash
# From project root
pip install -e .
```

The router will be installed as part of the sentinel package.

## Configuration

Create or update `.env` in your vault directory:

```bash
# Required
VAULT_PATH=/path/to/your/vault

# Optional (with defaults)
ROUTER_SLA_HOURS=24
ROUTER_URGENCY_KEYWORDS=urgent,asap,deadline,critical,time-sensitive
ROUTER_VERBOSE_LOG=false
```

## Usage

### CLI

```bash
# Route all eligible files
python -m router --vault /path/to/vault

# Preview without moving files
python -m router --vault /path/to/vault --dry-run

# Verbose output
python -m router --vault /path/to/vault --verbose
```

### Programmatic

```python
from router import route_inbox

# Basic usage
report = route_inbox("/path/to/vault")
print(f"Routed {report.routed_count} files to /Needs_Action/email/")

# Dry run
report = route_inbox("/path/to/vault", dry_run=True)
print(f"Would route {report.routed_count} files")
```

## How It Works

1. **Scan**: Router scans `/Inbox/email/` for `.md` files
2. **Parse**: Each file's YAML frontmatter is parsed for urgency indicators
3. **Evaluate**: Rules are applied in order:
   - Flag rules: `urgency: urgent`, `starred: true`, `important: true`
   - Keyword rules: subject/body contains urgency keywords
   - SLA rule: `captured_at` exceeds threshold (default: 24 hours)
4. **Route**: Matching files are atomically moved to `/Needs_Action/email/`
5. **Log**: Each action is logged to `/Logs/`

## Testing

### Create a Test Email

```bash
cat > /path/to/vault/Inbox/email/test-urgent.md << 'EOF'
---
source: gmail
captured_at: 2026-02-27T10:00:00Z
sender: "Test Sender"
subject: "URGENT: Test email"
urgency: normal
starred: false
important: false
status: unread
tags: [inbox, gmail]
---

# URGENT: Test email

This is a test email with the URGENT keyword.
EOF
```

### Run Router

```bash
python -m router --vault /path/to/vault
```

### Verify

```bash
# File should be in Needs_Action
ls /path/to/vault/Needs_Action/email/
# test-urgent.md

# Log should exist
ls /path/to/vault/Logs/
# *_routed_test-urgent-md.md
```

## Troubleshooting

### File Not Routing

1. Check frontmatter is valid YAML
2. Check urgency keywords match (case-insensitive)
3. Check SLA threshold hasn't been reached (default: 24 hours)
4. Enable verbose logging: `ROUTER_VERBOSE_LOG=true`

### Permission Errors

Ensure the router has write access to:
- `/Inbox/email/` (to read and delete source)
- `/Needs_Action/email/` (to write destination)
- `/Logs/` (to write audit logs)

### Malformed Frontmatter

Files with invalid YAML frontmatter are skipped and logged as warnings. Check `/Logs/` for details.

## Next Steps

- Integrate with watchdog for automatic routing on new files
- Configure custom urgency keywords in `.env`
- Adjust SLA threshold based on your workflow
