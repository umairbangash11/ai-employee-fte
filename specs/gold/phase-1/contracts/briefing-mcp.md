# MCP Contract: CEO Briefing Generation (Stub)

**Domain**: `briefing`
**Phase**: Gold Phase 4 (stub — tools TBD)
**Status**: Planned — not yet implemented
**Requires approval**: No (read-only generation; output is a local file, not an external action)

---

## Overview

The Briefing MCP server will provide tools for generating structured CEO briefing
documents from vault data (triage summaries, action statuses, log digests). Briefings
are **read-only generation** — they read vault state and write a new Markdown file to
`vault/Briefings/`. No external actions are taken; no approval gate is required.

---

## Planned Tools (Phase 4 scope — names and schemas TBD)

| Tool | Description | Requires Approval |
|------|-------------|-------------------|
| `briefing_generate_daily` | Generate a daily CEO briefing from yesterday's vault activity | No |
| `briefing_generate_weekly` | Generate a weekly audit/summary briefing | No |
| `briefing_get_last` | Read the most recent briefing file | No |
| `briefing_list` | List all briefing files | No |

*Tool names and parameters will be finalized in the Gold Phase 4 spec.*

---

## Output Format

Briefings are written to `vault/Briefings/<YYYYMMDD>-<type>-briefing.md` with:

```yaml
---
type: briefing
generated_at: <ISO 8601>
period: daily | weekly
source_dirs: [Needs_Action, Approved, Logs]
---
```

Followed by structured Markdown sections covering:
- Actions taken (from `Approved/` log)
- Items still pending (from `Needs_Action/`)
- Errors / failures (from `Logs/` where `outcome: failure`)
- Draft replies awaiting approval

---

## Error Behavior

| Condition | Response |
|-----------|----------|
| No vault activity in period | Generate briefing with "no activity" note |
| Vault directory missing | Skip missing dir; note in briefing |
| LLM API unreachable | Log failure; route placeholder briefing to `Needs_Action/` |
| Write failure | Log with `outcome: failure`; retry once |

---

## Notes

- No credentials required for vault reads.
- LLM inference credentials (`OPENAI_API_KEY` or equivalent) required for AI-generated summaries.
- Phase 4 spec will define briefing template, section structure, and delivery mechanism.
