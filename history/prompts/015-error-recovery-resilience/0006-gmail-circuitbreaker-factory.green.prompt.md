---
id: "0006"
title: Gmail CircuitBreaker factory
stage: green
date: 2026-04-23
surface: agent
model: claude-opus-4-7
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, gmail-watcher, circuit-breaker, t064, factory-only]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/gmail_watcher/watcher.py
tests:
  - Smoke: create_gmail_circuit_breaker() returns CircuitBreaker in CLOSED state with defaults
  - Smoke: name override (name="gmail_api_test") respected
  - Smoke: GMAIL_API_CIRCUIT_NAME constant equals "gmail_api"
  - Smoke: poll_once, poll_with_retry, create_health_manager unchanged and importable
---

## Prompt

/sp.implement

Continue Feature 015 — Error Recovery / Resilience.

Modify ONLY:
src/gmail_watcher/watcher.py

Task:
- Implement T064
- Add a create_gmail_circuit_breaker(name="gmail_api") factory
- Place it next to create_health_manager
- Do NOT integrate it into poll_with_retry yet
- Do NOT modify other files
- Stop after this one step

Output:
1. exact code change
2. where the factory is placed
3. what CircuitBreaker configuration is used
4. next smallest task

## Response snapshot

Added `GMAIL_API_CIRCUIT_NAME = "gmail_api"` module constant and
`create_gmail_circuit_breaker(name=GMAIL_API_CIRCUIT_NAME) -> CircuitBreaker`
factory in `src/gmail_watcher/watcher.py`. The factory returns a fresh
`CircuitBreaker` in CLOSED state using all library defaults (failure_threshold=5,
failure_rate_threshold=0.5, failure_window_seconds=60, recovery_timeout_seconds=30,
success_threshold=3). `CircuitBreaker` was added to the existing `from resilience`
import. No wiring into `poll_with_retry` — integration is a separate follow-up
step as instructed.

## Outcome

- ✅ Impact: T064 part 1 (factory) complete. A Gmail-specific CircuitBreaker can now be constructed symmetrically with HealthManager — same factory shape (`create_*`), same placement (top of file before polling functions), same override-via-argument pattern. Sets up integration into `poll_with_retry` as a pure composition step next.
- 🧪 Tests: 4 smoke assertions PASS (default config, name override, constant, siblings intact).
- 📁 Files: `src/gmail_watcher/watcher.py` — +21 lines, +1 import symbol (`CircuitBreaker`). No other files touched. tasks.md deliberately NOT flipped to [x] for T064 since integration is still pending.
- 🔁 Next prompts: Integrate the factory into `poll_with_retry` — check `breaker.can_execute()` before calling `poll_once`, record success/failure on the breaker after each attempt, raise `CircuitOpenError` fast when the circuit is open. This completes T064.
- 🧠 Reflection: Splitting T064 into (a) construct the tool, (b) wire the tool mirrors the T060/T062/T063 cadence that's been working. Each sub-step is one commit, one smoke test, one reviewable delta.

## Evaluation notes (flywheel)

- Failure modes observed: None. Library defaults match spec FR-009 exactly, so no per-subsystem tuning is required at this stage.
- Graders run and results (PASS/FAIL): 4/4 smoke assertions PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Integration — modify `poll_with_retry` to accept an optional `circuit: CircuitBreaker` argument and call `circuit.execute(lambda: poll_once(...))` under the retry loop. Keep `poll_once` primitive intact.
