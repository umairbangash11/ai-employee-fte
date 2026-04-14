---
id: "0001"
title: "WhatsApp Watcher Specification Creation"
stage: spec
date: 2026-03-22
surface: agent
model: claude-opus-4-5-20251101
feature: 007-whatsapp-watcher
branch: 007-whatsapp-watcher
user: umair
command: /sp.specify
labels: ["whatsapp", "watcher", "silver-tier", "ingestion", "playwright"]
links:
  spec: specs/007-whatsapp-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/007-whatsapp-watcher/spec.md
  - specs/007-whatsapp-watcher/checklists/requirements.md
tests:
  - null
---

## Prompt

Create a phase specification for WhatsApp watcher integration in my Digital FTE project.

Constraints:
- Respect the existing constitution and vault-first architecture
- Do not modify SpecifyPlus internal folders
- Do not implement anything
- Limit this phase to WhatsApp message ingestion only
- Do not include external message sending in this phase
- Do not rebuild Gmail watcher, router, or HITL

Current confirmed baseline:
- Gmail watcher exists
- Inbox router exists
- Brain/orchestrator exists
- HITL approval workflow exists
- Vault is the system of record

Required scope:
- Add a WhatsApp watcher using a local session-based approach suitable for hackathon/demo use
- Monitor WhatsApp for new or unread messages
- Convert captured messages into markdown with YAML frontmatter
- Store messages in the vault under a clearly defined WhatsApp folder structure
- Define routing behavior for normal vs urgent/actionable messages
- Define deduplication behavior so the same WhatsApp message is not processed twice
- Define required metadata fields for captured WhatsApp messages
- Define logging requirements for watcher activity
- Define failure behavior for session loss, selector failure, and temporary page load issues
- Define non-goals:
  - no reply sending
  - no Facebook integration
  - no LinkedIn changes
  - no MCP server changes
- Define acceptance criteria and test scenarios

Output a strict phase specification only.

## Response snapshot

Created comprehensive WhatsApp Watcher specification (`007-whatsapp-watcher`) covering:

- **6 prioritized user stories**: Headless capture (P1), QR authentication (P1), urgent routing (P2), deduplication (P2), group chat support (P2), error logging (P3)
- **16 functional requirements**: Playwright-based automation, headless-by-default, configurable polling, YAML frontmatter, vault routing, deduplication via hash registry
- **Required metadata fields**: source, captured_at, sender, chat_name, chat_type, message_timestamp, urgency, status, has_media, media_type, tags, hash
- **Vault folder structure**: `/Inbox/whatsapp/`, `/Needs_Action/whatsapp/`, daily log files
- **Failure behavior table**: Session expiration, network timeout, selector failure, page load timeout, QR scan timeout, dedup state corruption
- **7 measurable success criteria**: Capture without manual copy-paste, 100% message capture, zero duplicates, actionable error logs, 4+ hour continuous operation
- **Explicit non-goals**: No reply sending, no Facebook, no LinkedIn changes, no MCP changes, no media downloads

Constitution compliance verified against Principle III (Silver Tier) and Principle VI (Silver Tier Autonomy).

## Outcome

- ✅ Impact: Feature specification created for WhatsApp message ingestion phase
- 🧪 Tests: Manual test scenarios defined for hackathon validation
- 📁 Files: 2 files created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: `/sp.plan` to generate implementation architecture
- 🧠 Reflection: Specification follows Gmail API OAuth spec pattern for consistency; hackathon focus reflected in 4+ hour runtime success criterion

## Evaluation notes (flywheel)

- Failure modes observed: None — specification created successfully
- Graders run and results (PASS/FAIL): Manual review PASS — all checklist items verified
- Prompt variant (if applicable): Standard /sp.specify with detailed constraints
- Next experiment (smallest change to try): None needed — proceed to planning phase
