---
id: "0004"
title: Heartbeat in Gmail poll cycle
stage: green
date: 2026-04-22
surface: agent
model: claude-opus-4-7
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, gmail-watcher, heartbeat, health, t063]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/gmail_watcher/watcher.py
  - specs/015-error-recovery-resilience/tasks.md
tests:
  - Smoke: poll_once success path — heartbeat timestamp set
  - Smoke: poll_once failure path — heartbeat timestamp updates AFTER exception raised
  - Smoke: on-disk gmail_watcher_health.json reflects latest heartbeat + consecutive_failures
---

## Prompt

/sp.implement

Continue Gold Phase 5 (Feature 015) from current state.

Context:
- T062 completed (success/failure logging integrated in watcher)
- Resume at T063

Task:
- Add health.heartbeat() inside a finally block in poll loop
- Ensure it runs on EVERY iteration (success or failure)
- Do NOT modify other subsystems yet
- Do NOT re-implement previous tasks
- Keep scope limited to gmail_watcher only

Output:
- exact code change
- where it is placed
- why it guarantees watchdog visibility

## Response snapshot

Restructured `poll_once(service, health, max_results)` in `src/gmail_watcher/watcher.py` to use a `try/except/finally` shape:

```python
try:
    messages = fetch_unread_messages(service, max_results=max_results)
    health.record_success()
    return messages
except Exception as exc:
    health.record_failure(str(exc) or exc.__class__.__name__)
    raise
finally:
    health.heartbeat()
```

The `finally` block fires on success (after the return value is evaluated, before it is returned), on handled failure (after `record_failure`, around the re-raise), and on any uncaught path — so `last_heartbeat` in `.watcher-state/gmail_watcher_health.json` updates every iteration.

Scope respected:
- Only `src/gmail_watcher/watcher.py` touched (plus `tasks.md` checkbox flip for T059, T060, T062, T063 — previously completed-in-code but unchecked).
- No other subsystems modified.
- Previous tasks not re-implemented.

## Outcome

- ✅ Impact: External watchdogs (PM2/systemd/`sentinel-status`) now see a fresh `last_heartbeat` after every Gmail poll, regardless of whether the poll succeeded, raised a transient network error, or raised an unhandled exception. `HealthStatus.is_stale()` becomes a reliable liveness signal for gmail_watcher.
- 🧪 Tests: Smoke test with a FakeService confirmed heartbeat updates on success path, updates again on failure path after `record_failure`, and the on-disk JSON reflects the latest value.
- 📁 Files: `src/gmail_watcher/watcher.py` (+1 finally block, +2 lines moved inside try); `specs/015-error-recovery-resilience/tasks.md` (checkboxes T059, T060, T062, T063 → [x]).
- 🔁 Next prompts: T061 — wrap the `poll_once` call with `ralph_wiggum_loop()` so transient failures retry before the caller sees an exception. Then T064 (CircuitBreaker for Gmail API), T065 (route failed emails to `Needs_Action/email/failed/`), T066–T068 (exception migration + CLI flags + exit codes).
- 🧠 Reflection: `finally` is the correct placement because both `return messages` and `raise` transfer control out of the try/except — only a `finally` guarantees heartbeat fires on both. Placing heartbeat after `record_success`/`record_failure` but outside a finally would miss unhandled paths (e.g., KeyboardInterrupt, bugs in `record_failure` itself).

## Evaluation notes (flywheel)

- Failure modes observed: None. Previous iteration recorded failure reason but the next `_update_state` call inside HealthManager cleared it — a quirk of HealthManager itself, out of scope for this task.
- Graders run and results (PASS/FAIL): Manual smoke PASS (3 assertions).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): T061 — introduce `ralph_wiggum_loop()` wrapper function `poll_with_retry(service, health, policy)` that calls `poll_once` under retry. Keep `poll_once` as the primitive.
