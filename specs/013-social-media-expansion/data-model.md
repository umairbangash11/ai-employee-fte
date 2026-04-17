# Data Model: Gold Phase 3 — Social Media Expansion

**Branch**: `013-social-media-expansion` | **Date**: 2026-04-17

---

## Entities

### SocialPostDraft

Written by `social_drafters.draft_post()` to `vault/Pending_Approval/<platform>/<slug>.md`.

**Frontmatter schema:**

```yaml
---
type: pending_action
platform: facebook | instagram | x
action_type: publish_post
status: awaiting_approval
source_path: ""          # caller-provided or empty string
dest_path: "vault/Pending_Approval/<platform>/<slug>.md"
captured_at: "2026-04-17T10:00:00Z"    # ISO 8601 UTC
content_preview: "First 100 chars of post content"
# Platform-specific optional fields:
image_path: ""           # Instagram / X only; empty string if not provided
char_count: 0            # X only; integer
warning: ""              # X only; "exceeds_char_limit" when char_count > 280
---

## Content

<full post content>
```

**Validation rules:**
- `type` MUST be `pending_action`
- `action_type` MUST be `publish_post`
- `platform` MUST be one of `facebook`, `instagram`, `x`
- `status` MUST be `awaiting_approval`
- `content_preview` MUST be first 100 characters of content (truncated, not ellipsized)
- `captured_at` MUST be ISO 8601 with Z suffix
- `image_path` MUST be present for Instagram (may be empty string if not provided)
- `char_count` MUST be present for X (integer, length of content)

---

### SocialApprovedPost

Human-moved from `Pending_Approval/<platform>/` to `vault/Approved/<platform>/`. Same schema as SocialPostDraft. The executor reads `platform`, `content` (from Markdown body), and optional `image_path` / `char_count`.

**Fields read by executor:**
- `platform` — determines which executor handles the file
- `action_type` — MUST be `publish_post`
- `status` — MUST be `awaiting_approval` (set by drafter; executor does not re-validate status at pickup)
- `image_path` — Instagram/X: executor validates file exists before proceeding
- `char_count` — X: informational; executor does not enforce at publish time
- Content body under `## Content` heading

---

### SocialPublishRecord

Updated in-place by `handlers.update_frontmatter_published()` after a successful publish; the file is then moved to `vault/Done/<platform>/<slug>.md`.

**Added/updated frontmatter fields:**

```yaml
status: published
published_at: "2026-04-17T10:05:00Z"   # ISO 8601 UTC
executed_by: instagram_publisher | x_publisher | facebook_publisher
post_url: "https://..."                 # or null if not extractable
```

---

### SocialFailureRecord

Updated in-place by `handlers.update_frontmatter_failed()` after Ralph Wiggum Loop exhaustion; file moved to `vault/Needs_Action/<platform>/<slug>.md`.

**Added/updated frontmatter fields:**

```yaml
status: failed
last_error: "human-readable error message"
last_error_type: "SessionExpiredError | PublishTimeoutError | ..."
last_attempt_at: "2026-04-17T10:04:58Z"
retry_count: 3
```

---

### SocialLogEntry

Written by `sentinel.logger.write_log_entry()` (existing 6-field logger) to `vault/Logs/` after every social publishing operation.

**Required fields (all mandatory — FR-006, Constitution Principle IX):**

```yaml
timestamp: "2026-04-17T10:05:00Z"
action_type: "publish_post"
source_path: "vault/Approved/instagram/<slug>.md"
dest_path: "vault/Done/instagram/<slug>.md"
outcome: "success | failure | partial"
details: "platform=instagram; post_url=https://...; error=none"
```

---

## State Transitions

```
[draft_post() called]
        │
        ▼
vault/Pending_Approval/<platform>/<slug>.md   (status: awaiting_approval)
        │
        │  [human moves to Approved/]
        ▼
vault/Approved/<platform>/<slug>.md            (status: awaiting_approval)
        │
   ┌────┴────┐
   │         │
   ▼         ▼
[success]  [failure after 3 retries]
   │         │
   ▼         ▼
vault/Done/<platform>/   vault/Needs_Action/<platform>/
(status: published)      (status: failed)
```

---

## Slug Construction

`social_drafters.slugger.make_slug(platform, content)` produces:

```
<platform>-<YYYYMMDD>-<first-5-words-of-content-lowercased-hyphenated>
```

Example: `facebook-20260417-ai-employee-quarterly-update-draft`

On collision (file already exists), append `-2`, `-3`, etc.

---

## Vault Directory Mapping

| Directory | Purpose |
|-----------|---------|
| `vault/Pending_Approval/facebook/` | Facebook drafts awaiting human approval |
| `vault/Pending_Approval/instagram/` | Instagram drafts awaiting human approval |
| `vault/Pending_Approval/x/` | X drafts awaiting human approval |
| `vault/Approved/facebook/` | Human-approved Facebook posts |
| `vault/Approved/instagram/` | Human-approved Instagram posts |
| `vault/Approved/x/` | Human-approved X posts |
| `vault/Done/facebook/` | Successfully published Facebook posts |
| `vault/Done/instagram/` | Successfully published Instagram posts |
| `vault/Done/x/` | Successfully published X posts |
| `vault/Needs_Action/facebook/` | Failed/triage Facebook posts |
| `vault/Needs_Action/instagram/` | Failed/triage Instagram posts |
| `vault/Needs_Action/x/` | Failed/triage X posts |
| `vault/Logs/` | Audit log entries (all platforms, append-only) |
