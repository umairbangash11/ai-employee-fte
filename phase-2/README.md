# Phase 2: Email Reasoning Layer

**Status**: In Progress (Tasks Generated)
**Constitution**: v2.0.0 (Principles II, IV, VI, VII)

## Goal

Build a reasoning layer that reads captured email markdown files and generates actionable task files for emails requiring follow-up.

## Scope

- Read email files from `/Inbox/email/` (created by Phase 1)
- Classify emails: actionable, informational, promotional, ignore
- Create task files in `/Needs_Action/tasks/` for actionable emails
- Create plan files in `/Plans/` for multi-step actionable emails
- NO email sending, NO Gmail state changes, NO file deletion

## Feature Artifacts

```
phase-2/
  spec.md          # Feature specification (complete)
  README.md        # This file

specs/004-email-reasoning/
  research.md      # Technical research and decisions (complete)
  data-model.md    # Entity definitions and schemas (complete)
  plan.md          # Implementation architecture (complete)
  tasks.md         # Dependency-ordered tasks (complete)
```

## Workflow Progress

| Step | Command | Status |
|------|---------|--------|
| Specify | `/sp.specify` | Complete |
| Plan | `/sp.plan` | Complete |
| Tasks | `/sp.tasks` | Complete |
| Implement | `/sp.implement` | Pending |

## Constitution Compliance

This phase follows:

- **Principle II (Canonical Folders)**: Outputs to /Needs_Action, /Plans, /Logs
- **Principle IV (Safety-First)**: Read-only on source files, no auto-execution
- **Principle VI (Silver Tier Autonomy)**: Human-in-the-loop for all actions
- **Principle VII (Phased Development)**: Scoped to Phase 2 only
