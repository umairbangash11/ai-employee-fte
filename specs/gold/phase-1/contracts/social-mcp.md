# MCP Contract: Social Media Publishing (Stub)

**Domain**: `social`
**Phase**: Gold Phase 3 (stub — tools TBD)
**Status**: Planned — not yet implemented
**Requires approval**: Yes (all social posts are external actions)

---

## Overview

The Social MCP server will provide tools for publishing content to social media
platforms (Facebook, Instagram, X/Twitter). All posts are **external actions**
that are visible to the public and MUST require human approval via the
`Pending_Approval/social/` → `Approved/social/` gate before execution.

---

## Planned Tools (Phase 3 scope — names and schemas TBD)

| Tool | Description | Requires Approval | Platform |
|------|-------------|-------------------|----------|
| `social_draft_post` | Generate a draft post for human review | No (draft only) | Any |
| `social_publish_facebook` | Publish approved post to Facebook Page | Yes | Facebook |
| `social_publish_instagram` | Publish approved image/caption to Instagram | Yes | Instagram |
| `social_publish_x` | Post approved tweet/thread to X | Yes | X (Twitter) |
| `social_get_post_status` | Check engagement/status of a published post | No | Any |

*Tool names and parameters will be finalized in the Gold Phase 3 spec.*

---

## Approval Gate

All publish tools (approval required = Yes):

1. Orchestrator writes a proposed post to `vault/Pending_Approval/social/<id>.md`
   with `status: awaiting_approval`, `type: pending_action`, and `platform: <name>`.
2. Human reviews the draft post content in `Pending_Approval/social/`.
3. Human moves the file to `vault/Approved/social/`.
4. Orchestrator detects the file in `Approved/social/`, publishes via the
   appropriate platform API, and logs the result to `vault/Logs/`.

---

## Error Behavior

| Condition | Response |
|-----------|----------|
| Platform API unreachable | Log failure; follow Ralph Wiggum retry (3 attempts); route to `Needs_Action/` |
| Authentication / token expired | Log error; route to `Needs_Action/` for credential refresh |
| Post rejected by platform | Log with `outcome: failure` and platform error details |
| Approval gate bypassed | Reject; log boundary violation |

---

## Notes

- Platform credentials stored in `.env`: `FACEBOOK_PAGE_TOKEN`, `INSTAGRAM_TOKEN`, `X_API_KEY`, etc.
- Phase 3 spec will define full input/output schemas, character limits, media requirements.
- Facebook Publisher module already exists in the codebase (`src/facebook_publisher/`) — Phase 3 will wrap it in the MCP boundary.
