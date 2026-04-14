# Data Model: Facebook Post Execution

**Feature**: 008-facebook-post-execution
**Date**: 2026-03-22

---

## Overview

This document defines the data entities used in the Facebook post execution phase. All entities are file-based (Markdown with YAML frontmatter) following the vault-first architecture.

---

## Entity 1: ApprovedFacebookPost

**Purpose**: Represents a Facebook post file approved for publication

**Location**: `/Approved/facebook/*.md`

**Frontmatter Schema**:

```yaml
---
# Core Identity
type: approval_request          # Required, literal value
action_type: publish_facebook_post  # Required, literal value
status: pending                 # Required: pending | failed

# Timestamps
created_at: "2026-03-22T14:30:00Z"  # Required, ISO 8601
last_attempt_at: null               # Optional, set on retry

# Attribution
created_by: orchestrator        # Required: orchestrator | user | brain

# Target Configuration
target:
  platform: facebook            # Required, literal value
  post_type: text               # Required: text (only supported type)
  visibility: public            # Required: public | friends | only_me

# Source Reference
source:
  type: task                    # Required: task | prompt | template
  path: "[[Needs_Action/tasks/task.md]]"  # Required, wikilink

# Execution Metadata
expected_outcome: "Facebook post published"  # Required
rollback_strategy: "Delete post manually from Facebook"  # Required

# Failure State (added on retry)
retry_count: 0                  # Optional, default 0
last_error: null                # Optional, error message

# Classification
tags: [facebook, post]          # Required, array
---
```

**Body Content**:

```markdown
## Content Preview

The actual post content to publish goes here.

Supports hashtags #like #this and text formatting.
```

**Validation Rules**:
- `type` must equal `"approval_request"`
- `action_type` must equal `"publish_facebook_post"`
- `status` must be `"pending"` or `"failed"` to be processed
- `target.platform` must equal `"facebook"`
- `target.visibility` must be one of: `public`, `friends`, `only_me`
- Body must contain non-empty content after frontmatter

---

## Entity 2: PublishedFacebookPost

**Purpose**: Represents a successfully published Facebook post

**Location**: `/Done/facebook/*.md`

**Frontmatter Schema** (extends ApprovedFacebookPost):

```yaml
---
type: approval_request
action_type: publish_facebook_post
status: published               # Changed from pending

created_at: "2026-03-22T14:30:00Z"
published_at: "2026-03-22T15:00:00Z"  # Added: publication timestamp
created_by: orchestrator
executed_by: facebook_publisher      # Added: executor identifier

target:
  platform: facebook
  post_type: text
  visibility: public

source:
  type: task
  path: "[[Needs_Action/tasks/task.md]]"

expected_outcome: "Facebook post published"
rollback_strategy: "Delete post manually from Facebook"

# Execution Result
facebook_post_url: "https://www.facebook.com/user/posts/123456"  # Added if retrievable
execution_log: "[[Logs/facebook/20260322-150000_publish.log]]"   # Added

tags: [facebook, post, published]
---
```

**State Transition**:
```
ApprovedFacebookPost (status: pending)
    ↓ [publish success]
PublishedFacebookPost (status: published)
    ↓ [file move]
/Approved/facebook/ → /Done/facebook/
```

---

## Entity 3: FailedFacebookPost

**Purpose**: Represents a Facebook post that failed to publish

**Location**: `/Approved/facebook/*.md` (same file, updated frontmatter)

**Frontmatter Schema** (extends ApprovedFacebookPost):

```yaml
---
type: approval_request
action_type: publish_facebook_post
status: failed                  # Changed from pending

created_at: "2026-03-22T14:30:00Z"
last_attempt_at: "2026-03-22T15:05:00Z"  # Added: last retry timestamp
created_by: orchestrator

target:
  platform: facebook
  post_type: text
  visibility: public

source:
  type: task
  path: "[[Needs_Action/tasks/task.md]]"

expected_outcome: "Facebook post published"
rollback_strategy: "Delete post manually from Facebook"

# Failure Details
retry_count: 3                  # Added: number of attempts
last_error: "Network timeout after 30 seconds"  # Added: error message

tags: [facebook, post, failed]
---
```

**State Transition**:
```
ApprovedFacebookPost (status: pending)
    ↓ [publish failure after 3 retries]
FailedFacebookPost (status: failed)
    [file remains in /Approved/facebook/ for retry or manual review]
```

---

## Entity 4: ExecutionLog

**Purpose**: Audit record for publish attempts

**Location**: `/Logs/facebook/facebook-YYYYMMDD.log`

**Format**: JSON Lines (one JSON object per line)

**Schema**:

```json
{
  "timestamp": "2026-03-22T15:00:00Z",
  "event": "published",
  "file_path": "Approved/facebook/20260322-143000_post.md",
  "details": {
    "post_url": "https://www.facebook.com/user/posts/123456",
    "content_preview": "First 100 characters of post...",
    "visibility": "public",
    "retry_count": 1,
    "publish_duration_ms": 5432
  }
}
```

**Event Types**:

| Event | Description | Required Details |
|-------|-------------|------------------|
| `detected` | File found in /Approved/facebook/ | file_path |
| `validated` | Frontmatter passed validation | file_path |
| `publishing` | Publish attempt started | file_path, attempt_number |
| `published` | Successfully published | file_path, post_url, duration_ms |
| `failed` | Publish failed | file_path, error, retry_count |
| `moved_to_done` | File moved to /Done/ | file_path, destination |
| `moved_to_needs_action` | File moved due to error | file_path, reason |
| `duplicate_skipped` | Content hash already processed | file_path, content_hash |

---

## Entity 5: PublisherState

**Purpose**: Tracks processed files and execution statistics

**Location**: `.watcher-state/facebook/publisher.json`

**Schema**:

```json
{
  "processed_hashes": [
    "abc123def456...",
    "789ghi012jkl..."
  ],
  "last_run": "2026-03-22T15:00:00Z",
  "stats": {
    "total_published": 42,
    "total_failed": 3,
    "total_skipped": 5
  }
}
```

**Hash Computation**:
```python
content_hash = sha256(
    action_type +
    content_body +
    source_path
).hexdigest()[:16]
```

---

## Entity 6: SessionState

**Purpose**: Playwright browser session for Facebook authentication

**Location**: `.watcher-state/facebook/storage_state.json`

**Schema**: Playwright storage_state format (managed by Playwright)

Contains:
- Cookies for facebook.com
- localStorage data
- Session tokens

**Security**:
- Excluded from git via `.gitignore`
- No credentials stored directly
- Re-auth via `--auth` flag when expired

---

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                       File System State                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /Approved/facebook/          /Done/facebook/                   │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │ ApprovedPost    │ ──────→  │ PublishedPost   │              │
│  │ (pending/failed)│  success │ (published)     │              │
│  └─────────────────┘          └─────────────────┘              │
│          │                                                      │
│          │ unrecoverable                                        │
│          ↓                                                      │
│  /Needs_Action/facebook/                                        │
│  ┌─────────────────┐                                           │
│  │ InvalidPost     │                                           │
│  │ (error state)   │                                           │
│  └─────────────────┘                                           │
│                                                                 │
│  /Logs/facebook/              .watcher-state/facebook/          │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │ ExecutionLog    │          │ PublisherState  │              │
│  │ (JSON Lines)    │          │ SessionState    │              │
│  └─────────────────┘          └─────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Summary

| Entity | Required Fields | Validation |
|--------|-----------------|------------|
| ApprovedFacebookPost | type, action_type, status, created_at, target.*, source.* | Schema + enum checks |
| PublishedFacebookPost | All above + published_at, executed_by | Status must be `published` |
| FailedFacebookPost | All above + retry_count, last_error | Status must be `failed` |
| ExecutionLog | timestamp, event, file_path | Event must be valid type |
| PublisherState | processed_hashes, last_run | Array and ISO date |
| SessionState | (Playwright managed) | Valid JSON |

---

**End of Data Model Document**
