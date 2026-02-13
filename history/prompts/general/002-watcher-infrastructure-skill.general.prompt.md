---
id: 002
title: WatcherInfrastructure Skill in CLAUDE.md
stage: general
date: 2026-02-12
surface: agent
model: claude-opus-4-6
feature: none
branch: 001-vault-sentinel
user: umair
command: /sp.skill (custom request)
labels: ["skill", "watcher", "claude-md", "silver-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - CLAUDE.md
tests:
  - none
---

## Prompt

/sp.skill Create a skill named 'WatcherInfrastructure' specialized in Python-based sentinel scripts using Watchdog and Playwright. The skill must be capable of implementing robust, local-first monitoring for Gmail, WhatsApp, and filesystem events, ensuring unread or urgent items are converted into standardized Markdown files in the /Inbox or /Needs_Action folders.

## Response snapshot

Added a comprehensive "Skill: WatcherInfrastructure" section to CLAUDE.md covering: technology stack (Python 3.12, watchdog, Playwright, python-dotenv), three watcher types (Filesystem/Gmail/WhatsApp), standardized Markdown output format with YAML frontmatter, implementation patterns (sentinel script structure, dedup via hash registry, error handling), security constraints, and non-goals. The section is gated as Silver Tier, requiring a constitution amendment before implementation can proceed. Gmail and WhatsApp watchers are marked as blocked; filesystem watcher is active under Bronze Tier.

## Outcome

- ✅ Impact: Persistent skill guidance added to CLAUDE.md for all future sessions
- 🧪 Tests: none (documentation-only change)
- 📁 Files: CLAUDE.md modified (added ~80 lines)
- 🔁 Next prompts: Amend constitution to Silver Tier via `/sp.constitution`, then spec Gmail/WhatsApp watchers
- 🧠 Reflection: Detected constitution conflict (Principle III) proactively; user chose Silver Tier gating over ignoring the constraint

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
