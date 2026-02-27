# Data Model: Inbox → Needs_Action Router

**Feature**: 002-inbox-router
**Date**: 2026-02-27

## Overview

This document defines the data structures for the rule-based router. The router operates on Markdown files with YAML frontmatter, applying routing rules to determine if files should move from `/Inbox/email/` to `/Needs_Action/email/`.

---

## Entities

### 1. InboxFile

Represents a Markdown file in `/Inbox/email/` with parsed frontmatter.

```yaml
InboxFile:
  description: "Parsed representation of an email markdown file"
  fields:
    path:
      type: Path
      description: "Absolute path to the file"
      required: true

    frontmatter:
      type: EmailFrontmatter
      description: "Parsed YAML frontmatter metadata"
      required: true

    subject:
      type: string
      description: "Email subject extracted from frontmatter"
      required: false
      default: "(no subject)"

    body:
      type: string
      description: "Markdown body content (after frontmatter)"
      required: false
      default: ""

    file_size:
      type: integer
      description: "File size in bytes"
      required: true
```

### 2. EmailFrontmatter

The YAML metadata at the top of each email markdown file (as produced by Gmail sentinel).

```yaml
EmailFrontmatter:
  description: "YAML frontmatter structure for email files"
  fields:
    source:
      type: string
      description: "Origin of the email"
      enum: ["gmail", "whatsapp", "filesystem"]
      required: true

    captured_at:
      type: string
      format: "ISO 8601 datetime"
      description: "When the email was captured"
      example: "2026-02-27T14:30:00Z"
      required: true

    sender:
      type: string
      description: "Email sender name or address"
      required: true

    subject:
      type: string
      description: "Email subject line"
      required: false
      default: "(no subject)"

    urgency:
      type: string
      enum: ["normal", "urgent"]
      description: "Urgency level (set by Gmail sentinel)"
      default: "normal"

    starred:
      type: boolean
      description: "Whether email was starred in Gmail"
      default: false

    important:
      type: boolean
      description: "Whether email was marked important in Gmail"
      default: false

    status:
      type: string
      enum: ["unread", "read", "processed"]
      description: "Processing status"
      default: "unread"

    tags:
      type: array[string]
      description: "Tags for organization"
      default: ["inbox", "gmail"]
```

### 3. RoutingRule

A condition that triggers file routing to `/Needs_Action/`.

```yaml
RoutingRule:
  description: "A rule that determines if a file should be routed"
  fields:
    name:
      type: string
      description: "Human-readable rule identifier"
      required: true
      examples: ["flag:urgent", "flag:starred", "keyword:URGENT", "sla:24h"]

    type:
      type: string
      enum: ["flag", "keyword", "sla"]
      description: "Category of rule"
      required: true

    matcher:
      type: callable
      description: "Function (InboxFile) -> bool"
      required: true

    priority:
      type: integer
      description: "Rule evaluation order (lower = earlier)"
      default: 100
```

### 4. RoutingResult

The outcome of evaluating an InboxFile against all routing rules.

```yaml
RoutingResult:
  description: "Result of routing evaluation for a single file"
  fields:
    file:
      type: InboxFile
      description: "The evaluated file"
      required: true

    should_route:
      type: boolean
      description: "True if file matches any routing rule"
      required: true

    matched_rules:
      type: array[string]
      description: "Names of rules that matched"
      default: []
      examples: [["flag:urgent", "keyword:ASAP"]]

    destination:
      type: Path
      description: "Target path in /Needs_Action/email/"
      required: false  # Only set if should_route is true
```

### 5. RouterConfig

Runtime configuration for the router.

```yaml
RouterConfig:
  description: "Configuration settings for the router"
  fields:
    vault_path:
      type: Path
      description: "Root path of the vault"
      required: true
      env: "VAULT_PATH"
      default: "."

    sla_threshold_hours:
      type: integer
      description: "Hours before SLA breach triggers routing"
      env: "ROUTER_SLA_HOURS"
      default: 24
      validation: ">= 1"

    urgency_keywords:
      type: array[string]
      description: "Keywords that trigger urgency routing"
      env: "ROUTER_URGENCY_KEYWORDS"
      default:
        - "urgent"
        - "asap"
        - "deadline"
        - "critical"
        - "time-sensitive"
        - "immediate"
        - "priority"
        - "emergency"
        - "action required"

    verbose_logging:
      type: boolean
      description: "Log skipped (no-match) files"
      env: "ROUTER_VERBOSE_LOG"
      default: false
```

### 6. RoutingLog

Audit log entry for a routing action (extends existing log format).

```yaml
RoutingLog:
  description: "Log entry for a routing action"
  fields:
    log_id:
      type: string
      format: "{timestamp}-{action_type}-{filename_slug}"
      required: true

    timestamp:
      type: string
      format: "ISO 8601 datetime"
      required: true

    action_type:
      type: string
      enum: ["routed", "skipped", "error"]
      required: true

    source_path:
      type: Path
      description: "Original path in /Inbox/email/"
      required: true

    dest_path:
      type: Path
      description: "Target path in /Needs_Action/email/"
      required: false  # Only for action_type=routed

    matched_rules:
      type: array[string]
      description: "Rules that triggered routing"
      required: false

    outcome:
      type: string
      enum: ["success", "failure", "skipped"]
      required: true

    details:
      type: string
      description: "Additional context (error message, etc.)"
      required: false
```

---

## Relationships

```
┌─────────────────┐
│  RouterConfig   │
└────────┬────────┘
         │ configures
         ▼
┌─────────────────┐       evaluates       ┌─────────────────┐
│  RoutingRule[]  │ ◄────────────────────► │    InboxFile    │
└────────┬────────┘                        └────────┬────────┘
         │                                          │
         │ produces                                 │ contains
         ▼                                          ▼
┌─────────────────┐                        ┌─────────────────┐
│  RoutingResult  │                        │ EmailFrontmatter│
└────────┬────────┘                        └─────────────────┘
         │
         │ logged as
         ▼
┌─────────────────┐
│   RoutingLog    │
└─────────────────┘
```

---

## State Transitions

### InboxFile Lifecycle

```
[Created by Gmail Sentinel]
         │
         ▼
┌─────────────────┐
│   /Inbox/email/ │  ◄─── status: unread
└────────┬────────┘
         │
         │ Router evaluates
         ▼
   ┌─────┴─────┐
   │           │
   ▼           ▼
[Matches]   [No Match]
   │           │
   ▼           │
┌─────────────────┐
│/Needs_Action/   │  ◄─── status: unread (preserved)
│     email/      │
└─────────────────┘
         │           │
         │           │ (remains in Inbox until
         │           │  human/AI processes)
         ▼           ▼
   [Processed by human or AI]
         │
         ▼
┌─────────────────┐
│     /Done/      │  ◄─── status: processed
└─────────────────┘
```

---

## Validation Rules

1. **InboxFile.path**: Must be a valid `.md` file in `/Inbox/email/`
2. **EmailFrontmatter.captured_at**: Must be valid ISO 8601 datetime
3. **RouterConfig.sla_threshold_hours**: Must be >= 1
4. **RouterConfig.urgency_keywords**: Must be non-empty list
5. **RoutingResult.destination**: If `should_route=true`, must be valid path in `/Needs_Action/email/`

---

## File Format Example

```markdown
---
source: gmail
captured_at: 2026-02-27T14:30:00Z
sender: "John Doe"
subject: "URGENT: Project deadline extended"
urgency: normal
starred: false
important: false
status: unread
tags: [inbox, gmail]
---

# URGENT: Project deadline extended

**From**: John Doe
**Date**: Feb 27, 2026, 2:30 PM

---

Hi team,

Just wanted to let you know the deadline has been moved to Friday.

Best,
John
```

This file would be routed due to `keyword:URGENT` match in subject.
