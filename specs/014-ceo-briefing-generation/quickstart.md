# Quickstart: CEO Briefing Generator

**Feature Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-18

---

## Prerequisites

- Python 3.12+
- Project dependencies installed (`pip install -e .`)
- `VAULT_PATH` environment variable set
- Vault initialized with canonical directories

---

## Setup

### 1. Activate Virtual Environment

```bash
cd /path/to/ai-employee-fte
source venv/bin/activate
```

### 2. Set Environment Variable

```bash
export VAULT_PATH=/path/to/your/vault
```

Or add to `.env`:

```env
VAULT_PATH=/path/to/your/vault
```

### 3. Verify Vault Structure

The briefing generator reads from these directories:

```
vault/
├── Business_Goals.md        # Optional: business goals
├── Done/                    # Completed items
│   ├── email/
│   ├── facebook/
│   ├── instagram/
│   ├── x/
│   └── odoo/
├── Needs_Action/            # Pending items (for bottleneck detection)
│   ├── email/
│   ├── plans/
│   └── ...
├── Accounting/              # Optional: accounting data
│   ├── invoices/
│   └── payments/
├── Briefings/               # Output directory (created if missing)
└── Logs/                    # Audit logs
```

---

## Generate Briefing

### Weekly Briefing (Monday)

```bash
sentinel-briefing generate
```

Output: `vault/Briefings/2026-04-18_Monday_Briefing.md`

### Adhoc Briefing (Any Day)

```bash
sentinel-briefing generate
# Automatically generates Adhoc on non-Monday days
```

Output: `vault/Briefings/2026-04-18_Adhoc_Briefing.md`

### Force Adhoc on Monday

```bash
sentinel-briefing generate --force-adhoc
```

### Preview Without Writing

```bash
sentinel-briefing generate --dry-run
```

### Check Vault Status

```bash
sentinel-briefing status
```

---

## Business Goals (Optional)

Create `vault/Business_Goals.md` to enable goal progress tracking:

```markdown
# Business Goals

## Goal: Increase Revenue

Target: $100k MRR by Q3 2026
Description: Focus on enterprise sales and upselling.

## Goal: Launch Product V2

Target: July 2026
Description: Complete advanced analytics and API.

## Goal: Improve Retention

Target: <5% monthly churn
Description: Proactive support and success programs.
```

### Tag Items to Goals

Add `goal:` frontmatter to Done/ items:

```yaml
---
status: published
goal: increase-revenue
completed_at: "2026-04-17T10:00:00Z"
---
```

---

## Example Output

```markdown
---
type: ceo_briefing
generated_at: "2026-04-18T09:00:00Z"
period_start: "2026-04-11"
period_end: "2026-04-18"
status: generated
---

# CEO Briefing: Week of April 11–18, 2026

## Executive Summary

- 12 tasks completed this week
- Revenue: $8,500 received, $4,000 outstanding
- 2 items require attention (stale email backlog)
- 3 deadlines upcoming in next 7 days

## Goals Progress

| Goal | Status | Completed | Pending |
|------|--------|-----------|---------|
| Increase Revenue | ✅ On Track | 4 | 1 |
| Launch Product V2 | ⚠️ At Risk | 2 | 5 |
| Improve Retention | ⏸️ No Activity | 0 | 0 |

## Revenue/Business Summary

- **Invoiced**: $12,500 (3 invoices)
- **Received**: $8,500 (2 payments)
- **Outstanding**: $4,000

## Completed Tasks

### Increase Revenue
- Closed enterprise deal with Acme Corp
- Sent renewal proposal to Beta Inc
...

## Bottlenecks

| Item | Days Stale | Category |
|------|------------|----------|
| Re: Project proposal | 9 days | email |
| Invoice #1042 | overdue 3 days | accounting |

## Proactive Suggestions

- ⚠️ **Email backlog**: 6 items in Needs_Action/email/. Consider scheduling time to process.
- ℹ️ **Strong social week**: 12 posts published. Review content calendar for sustainability.

## Upcoming Deadlines

| Item | Due | Days |
|------|-----|------|
| Contract renewal | Apr 22 | 4 |
| Q1 report | Apr 25 | 7 |
```

---

## Troubleshooting

### "VAULT_PATH not set"

```bash
export VAULT_PATH=/path/to/vault
# or
sentinel-briefing generate --vault-path /path/to/vault
```

### "No accounting data available"

This is expected if `vault/Accounting/` is empty or doesn't exist. The briefing still
generates with other sections.

### "No business goals defined"

Create `vault/Business_Goals.md` with `## Goal: <title>` headings, or the Goals Progress
section will show this message.

### Malformed vault files

Files with invalid YAML frontmatter are skipped. Check `vault/Logs/` for warnings.

---

## Programmatic Usage

```python
from briefing_generator import generate_briefing
from pathlib import Path
import os

briefing_path = generate_briefing(
    vault_path=Path(os.environ["VAULT_PATH"]),
    force_adhoc=False,
)
print(f"Briefing written to: {briefing_path}")
```

---

## Next Steps

1. Set up Business_Goals.md for goal tracking
2. Tag Done/ items with `goal:` frontmatter
3. Add `deadline:` frontmatter to track upcoming deadlines
4. Run `sentinel-briefing generate` weekly (or on-demand)
