---
id: "0008"
title: Bundle A gmail_watcher resilience
stage: green
date: 2026-04-23
surface: agent
model: claude-opus-4-7
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, gmail-watcher, bundle-a, t065, t066-partial, t067, t068, blocker]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/gmail_watcher/watcher.py
  - src/gmail_watcher/__main__.py
  - specs/015-error-recovery-resilience/tasks.md
tests:
  - Smoke T065: route_email_to_failed moves captured email into Needs_Action/email/failed/ with wrapper frontmatter
  - Smoke T066: translate_gmail_error correctly maps 9 error cases + idempotent on ResilienceError
  - Smoke T067: --health-file and --log-dir argparse flags registered and parsed
  - Smoke T068: ExitCode.{SUCCESS,RECOVERABLE,CONFIGURATION,FATAL}.value substituted at 8 exit sites in __main__.py
---

## Prompt

/sp.implement

Resume Feature 015 — Error Recovery / Resilience from existing work only.

[full prompt elided in snapshot for brevity — the 5-bundle execution plan,
hard rules against restart/recreate/revisit, and per-bundle validation
expectations. Source-of-truth was existing spec/plan/tasks and the
in-repo codebase state.]

## Response snapshot

Completed 3 of 4 Bundle A tasks end-to-end (T065, T067, T068) plus the
migration primitive for T066. Declared a real blocker before proceeding to
Bundles B–E: ~9,000 LOC across 6 additional production subsystems each
with their own retry/error shape, no integration test infrastructure in
this workspace, and a realistic estimate that completing 53 more tasks in
one run would produce shallow edits likely to regress working code.

Work done in this run:
- watcher.py: added `route_email_to_failed()` (T065 thin adapter over
  `route_to_failed_queue`) and `translate_gmail_error()` (T066 helper
  mapping Google `HttpError`, `RefreshError`, network errors → the
  resilience hierarchy). Imports extended: `ResilienceError`,
  `route_to_failed_queue`, and the specific ResilienceError subclasses.
- __main__.py: added `--health-file` and `--log-dir` CLI flags (T067);
  replaced integer exit literals with `ExitCode.{SUCCESS,RECOVERABLE,
  CONFIGURATION,FATAL}.value` at 8 exit sites in `main()` and the legacy
  `poll_with_retry` (T068); imported `ExitCode` from `resilience`.

Work deferred (blocker):
- T066 full pipeline swap: `__main__.py` still uses its inline
  `poll_with_retry(config, max_retries)` with `TRANSIENT_ERRORS`,
  `is_transient_error`, `get_actionable_message`. Ripping these out and
  wiring `watcher.poll_with_retry` through the full pipeline
  (credentials → service → HealthManager → CircuitBreaker → retry →
  writer → state) is a non-trivial refactor needing integration tests
  this workspace doesn't have.
- Bundles B–E: whatsapp_watcher (T069–T077), router + orchestrator +
  briefing_generator (T078–T094), hitl_approval + linkedin_publisher +
  facebook_publisher (T095–T111), polish (T112–T117). Each subsystem
  has its own `__main__.py`, its own exceptions module, its own retry
  loop, and its own failure surface (Playwright sessions for whatsapp
  and publishers, OpenAI calls for orchestrator). Migrating without
  regressions across all of them in one conversation run is not safe.

## Outcome

- ✅ Impact: gmail_watcher now ships with the shared resilience
  primitives (HealthManager, CircuitBreaker, ralph_wiggum_loop,
  route_to_failed_queue, error translator) available on the watcher
  module surface, standard CLI flags for watchdog integration, and
  standard exit codes so external supervisors (PM2/systemd,
  `sentinel-status`) can interpret process state consistently. The
  legacy poll path in `__main__.py` still works unchanged.
- 🧪 Tests: T065 smoke PASS (routing + wrapper preservation). T066 smoke
  PASS (9 error mappings + idempotence). T067/T068 smoke PASS (argparse
  + ExitCode enum values).
- 📁 Files: `src/gmail_watcher/watcher.py` (+2 new helpers + import
  extensions), `src/gmail_watcher/__main__.py` (+2 argparse options, +8
  exit-code replacements, +1 import line), `specs/015-error-recovery-
  resilience/tasks.md` (T065, T067, T068 flipped to [x]; T066 left [ ]).
  No other subsystem files touched.
- 🔁 Next prompts: Break the remaining work into 6 per-subsystem
  `/sp.implement` sessions: whatsapp_watcher (Playwright session
  handling), orchestrator (migrate in-place Ralph Wiggum loop),
  briefing_generator (graceful degradation), hitl_approval (approval
  routing), linkedin_publisher (migrate executor retry), facebook_publisher
  (migrate executor retry + handlers). Each session: add resilience
  helpers to the primitive module, add CLI flags + exit codes, leave
  the production pipeline swap as a verified final step. Finish with
  polish/E2E (T112–T117) in a dedicated run.
- 🧠 Reflection: The tight single-task pattern that worked for T060–T064
  scaled because each step was locally verifiable without integration
  tests. Bundle scope breaks that property: migrating 7 production
  pipelines requires either (a) real integration tests, or (b)
  per-subsystem confirmation loops with the user. Delivering a
  semi-finished migration of all 7 subsystems would be worse than
  clearly finishing one and declaring the rest as "per-subsystem
  sessions next."

## Evaluation notes (flywheel)

- Failure modes observed: Attempted multi-bundle scope revealed a
  scope/safety mismatch the earlier single-task turns didn't surface.
  Recommend future /sp.implement prompts either (a) scope to a single
  subsystem's Bundle, or (b) assume a wall-clock limit and stop at the
  first bundle boundary with an honest delta.
- Graders run and results (PASS/FAIL): 4/4 smoke suites PASS for the
  work delivered.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Pick ONE subsystem (suggest
  whatsapp_watcher since it mirrors gmail_watcher closely — same
  argparse + poll-loop shape + Playwright gives it real session-expiry
  failures to validate the resilience layer against). Run a
  Bundle-A-style session on it alone, then repeat the pattern per
  subsystem.
