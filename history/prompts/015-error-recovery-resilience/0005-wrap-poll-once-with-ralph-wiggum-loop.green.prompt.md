---
id: "0005"
title: Wrap poll_once with Ralph Wiggum Loop
stage: green
date: 2026-04-23
surface: agent
model: claude-opus-4-7
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, gmail-watcher, ralph-wiggum, retry, t061]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/gmail_watcher/watcher.py
  - specs/015-error-recovery-resilience/tasks.md
tests:
  - Smoke: transient error on attempt 1 → success on attempt 2 (2 calls, no failures persisted)
  - Smoke: non-retryable CredentialsInvalidError → 1 call, no retry
  - Smoke: always-transient error → exhausts 3 attempts, consecutive_failures=3
  - Smoke: poll_once primitive still directly callable (unchanged)
---

## Prompt

/sp.implement

Resume Feature 015 — Error Recovery / Resilience from existing work only.

Source of truth:
- existing Phase 15 files
- current codebase
- completed work in gmail_watcher

Already complete:
- T059
- T060
- T062
- T063

Resume at:
- T061 only

Rules:
- Do NOT restart Feature 015
- Do NOT revisit earlier phases
- Do NOT recreate constitution
- Do NOT re-implement completed tasks
- Modify only the minimum required file(s) for T061
- Keep poll_once unchanged as the primitive
- Stop after completing T061

Output only:
1. what existing work was detected
2. exact code change for T061
3. files changed
4. next smallest task

## Response snapshot

Added `poll_with_retry(service, health, max_results=50, policy=None)` in `src/gmail_watcher/watcher.py`. It calls `ralph_wiggum_loop(operation=lambda: poll_once(...), policy=policy)` from `resilience`. `poll_once` is unchanged — success/failure recording and the finally-block heartbeat still fire on each attempt, so the health file reflects every retry, not just the final outcome.

Imports added: `typing.Optional`, plus `RetryPolicy` and `ralph_wiggum_loop` from `resilience` (already exported in `src/resilience/__init__.py`).

Smoke tests passed: transient-then-success takes 2 calls, non-retryable (`CredentialsInvalidError`) takes 1 call with no retry, always-transient exhausts 3 attempts and leaves `consecutive_failures=3`, and the primitive `poll_once` still returns correctly when called directly.

## Outcome

- ✅ Impact: gmail_watcher now satisfies Constitution Principle V at the poll-cycle boundary. A transient network blip retries up to 3 times with exponential backoff + jitter before the caller sees an exception. Non-retryable failures (bad credentials, malformed data) fast-fail on attempt 1 per `is_retryable()` in `src/resilience/exceptions.py`.
- 🧪 Tests: 4 smoke cases PASS (retryable success on 2nd, non-retryable fast-fail, retryable exhaustion, primitive unchanged).
- 📁 Files: `src/gmail_watcher/watcher.py` (+38 lines: one new function, two new imports); `specs/015-error-recovery-resilience/tasks.md` (T061 → [x]).
- 🔁 Next prompts: T064 — add `CircuitBreaker` for Gmail API calls around `poll_with_retry` so cascading failures open the circuit before exhausting the retry budget.
- 🧠 Reflection: Keeping `poll_once` as the primitive and adding `poll_with_retry` as a thin wrapper means T064 (circuit breaker) and T065 (failed-queue routing) compose cleanly as further wrapping layers rather than mutations to existing code. The lambda is the simplest bridge — no new callback shape needed.

## Evaluation notes (flywheel)

- Failure modes observed: None. The simplify_fn parameter of `ralph_wiggum_loop` is left `None` for now — attempt 3 just retries the primary operation. A Gmail-specific simplification (e.g., reduce `max_results`) can be added later if attempt-3 still fails often in practice, but there's no evidence yet.
- Graders run and results (PASS/FAIL): 4/4 smoke assertions PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): T064 — wire `CircuitBreaker(name="gmail_api", ...)` around the Gmail API calls. Smallest increment: construct the breaker once alongside `HealthManager` and expose `can_execute()` before `poll_with_retry` runs.
