---
id: "0007"
title: Wire CircuitBreaker into poll_with_retry
stage: green
date: 2026-04-23
surface: agent
model: claude-opus-4-7
feature: 015-error-recovery-resilience
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: [resilience, gmail-watcher, circuit-breaker, t064, integration]
links:
  spec: specs/015-error-recovery-resilience/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/gmail_watcher/watcher.py
  - specs/015-error-recovery-resilience/tasks.md
tests:
  - Smoke A: no-circuit success path unchanged (1 call)
  - Smoke B: circuit CLOSED + success → state remains CLOSED, 1 call
  - Smoke C: circuit CLOSED + 3 transient errors → 3 calls, breaker still CLOSED (3 < threshold 5)
  - Smoke D: pre-tripped circuit (5 manual failures) → CircuitOpenError, ZERO fetch calls
  - Smoke E: pre-tripped circuit + 3-attempt retry policy → retry budget NOT consumed (still 0 fetches)
---

## Prompt

/sp.implement

Continue Feature 015 — Error Recovery / Resilience.

Modify ONLY:
src/gmail_watcher/watcher.py

Task:
- Complete T064 (integration step)
- Add optional circuit: CircuitBreaker | None = None parameter to poll_with_retry
- If circuit is provided:
  - wrap poll_once call with circuit.execute(...)
  - ensure CircuitOpenError stops retries immediately
- Do NOT modify poll_once
- Do NOT modify other files
- Stop after this one step

Output:
1. exact code change
2. how circuit integrates with retry loop
3. how CircuitOpenError behaves
4. next smallest task

## Response snapshot

Added `circuit: Optional[CircuitBreaker] = None` to `poll_with_retry`. When
the caller supplies a breaker, a local `_attempt()` helper replaces the
previous direct lambda: it calls `circuit.execute(lambda: poll_once(...))` so
each attempt flows through the breaker's success/failure accounting. A
caught `CircuitOpenError` has its `retryable` flag flipped to `False` before
being re-raised so `ralph_wiggum_loop` fast-fails on that attempt rather
than sleeping and retrying under an already-open circuit. `poll_once` is
untouched.

Imports expanded from `resilience`: `CircuitOpenError` added.

Critical finding: `CircuitOpenError` in `src/resilience/circuit_breaker.py:54`
is constructed with `retryable=True` (intentional — external schedulers may
want to retry using `remaining_seconds` from context). Since the user
constrained the change to watcher.py only, the fix is a local attribute flip
on the caught instance — it doesn't modify the resilience module and
preserves the module-wide semantics for other callers.

## Outcome

- ✅ Impact: T064 fully complete. `poll_with_retry` now composes circuit breaker + retry loop cleanly. Under sustained Gmail failures, the breaker trips OPEN (5 failures in 60s) and subsequent `poll_with_retry` calls fast-fail with `CircuitOpenError` in O(1) — no wasted retries, no wasted HTTP calls, no wasted `fetch_unread_messages` invocations. `poll_once` remains the single point of success/failure recording.
- 🧪 Tests: 5 smoke cases PASS. Crucial invariants verified: (a) behaviour identical when `circuit=None`, (b) breaker state accounting works across attempts, (c) pre-OPEN circuit consumes ZERO of the retry budget.
- 📁 Files: `src/gmail_watcher/watcher.py` — one new parameter, one inner helper function, +1 import symbol. `specs/015-error-recovery-resilience/tasks.md` — T064 → [x]. No other files touched.
- 🔁 Next prompts: T065 — on final failure inside `poll_with_retry`, call `route_to_failed_queue()` to move the failed email (or failure record) into `Needs_Action/email/failed/` with recovery wrapper frontmatter. This will need the original email content, so the shape is: wrap one more level outward, catch the final exception, route, re-raise (or return a sentinel).
- 🧠 Reflection: Composing wrappers outward from `poll_once` (primitive → retry → circuit) instead of mutating the primitive keeps each feature addition reversible and independently testable. The one wart — needing to flip `retryable=False` on `CircuitOpenError` — is a seam worth remembering for whatsapp_watcher integration (T071): it'll need the same pattern, or the resilience module could be amended to expose a `retryable_in_outer_retry_loop` convention.

## Evaluation notes (flywheel)

- Failure modes observed: Discovered mid-implementation that `CircuitOpenError(retryable=True)` would cause `ralph_wiggum_loop` to retry under an open circuit — opposite of intent. Handled locally via attribute flip. Logged this as a future amendment candidate for the resilience module (maybe a `retryable=False` override at construction, or a convention that outer retry loops treat CircuitOpenError as terminal).
- Graders run and results (PASS/FAIL): 5/5 smoke assertions PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): T065 — route failed items to `Needs_Action/email/failed/`. Smallest increment: add `poll_with_recovery(service, health, vault_path, circuit=None, policy=None)` as one more outward wrap that catches the final exception from `poll_with_retry`, calls `route_to_failed_queue(...)` with the email path, then re-raises. Keeps `poll_with_retry` primitive-stable.
