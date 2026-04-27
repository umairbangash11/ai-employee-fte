# Research: Gold Phase 4 — CEO Briefing Generation

**Branch**: `014-ceo-briefing-generation`
**Date**: 2026-04-17
**Phase**: Phase 0 output of `/sp.plan`

---

## R-001: Vault Scanning Strategy

**Decision**: Use `pathlib.glob()` with a configurable lookback window. For files with YAML
frontmatter, prefer `captured_at` field for date comparison; fall back to `st_mtime` when
`captured_at` is absent.

**Rationale**: This pattern is already established across all Gold-tier vault modules
(instagram_publisher, x_publisher, sentinel watcher). Zero new dependencies. Handles both
well-formed frontmatter files and raw files equally. The lookback filter bounds the read
set to O(files_in_window) regardless of total vault size.

**Alternatives considered**:
- SQLite index of vault files: overkill for a weekly batch scanner; adds a dep and
  a schema-migration surface.
- watchdog event stream: wrong execution model — briefing is batch (triggered), not
  streaming (continuous).
- Walk all files then filter: correct but potentially slow on large vaults — the lookback
  pre-filter by mtime before opening files avoids unnecessary reads.

---

## R-002: LLM Synthesis Approach

**Decision**: Single structured GPT-4o call per run. Pass the `BriefingContext` as a JSON
blob in the user message. Use a system prompt that instructs the model to produce all six
briefing sections as a Markdown document. Parse the response directly into the renderer.

**Rationale**: `openai>=1.0` is already installed (Silver Tier email reasoning). A single
call is simpler to retry (Ralph Wiggum Loop wraps one call, not six) and produces more
coherent narrative than six independent calls that cannot reference each other. JSON
context gives the LLM structured, unambiguous data.

**Token budget**: `BriefingContext` JSON is capped at `BRIEFING_CONTEXT_MAX_TOKENS`
(default: 6000 tokens) before the call. Goals content is separately capped at
`BRIEFING_GOALS_MAX_CHARS` (default: 4000 chars). This keeps total prompt within GPT-4o's
128k context while avoiding unnecessary cost.

**Alternatives considered**:
- One LLM call per section: 6× the API calls, 6× the failure surface, no cross-section
  coherence (e.g., the Suggestions section cannot reference the Bottlenecks section).
- Streaming response: unnecessary complexity for a weekly batch job; adds retry
  complexity.
- Claude API: preference is OpenAI for this project (existing OPENAI_API_KEY
  infrastructure from Silver Tier email reasoning).

---

## R-003: Scheduling Strategy

**Decision**: Use the `schedule` Python library (v1.2+) in `watch` mode. The scheduler
runs in the main thread with a `time.sleep(60)` poll loop. SIGINT/SIGTERM handlers shut
it down cleanly.

**Rationale**: `schedule` is the simplest weekly-trigger solution in the Python
ecosystem — it adds one lightweight dependency, requires no daemon, and integrates
naturally with a `while True: schedule.run_pending(); sleep(60)` loop. The watch command
is intended for running as a background service (e.g., via systemd or `nohup`), not as a
long-lived interactive process.

**Alternatives considered**:
- APScheduler: much heavier (persistent job stores, multiple executor types). The briefing
  use case needs exactly one weekly job — APScheduler is over-engineered.
- cron: OS-level; not portable; cannot be configured from `.env`; no Python-land
  graceful shutdown.
- asyncio sleep loop: `asyncio.sleep(604800)` for one week is fragile and makes
  on-demand triggering harder to test.

**New dependency**: `schedule>=1.2` — add to `pyproject.toml` `[project.dependencies]`.

---

## R-004: Signal File Idempotency

**Decision**: Signal file slug is derived from the SHA-1 hash of the source file's
absolute path. On re-run, writing the same signal overwrites the previous file silently.
Filename format: `vault/Signals/<YYYY-MM-DD>-<signal_type>-<8-char-hash>.md`.

**Rationale**: Hash of source path guarantees the same source always maps to the same
signal filename — no duplicates on re-run, no state file needed. The date prefix keeps
signals chronologically ordered in directory listings. 8 hex chars (32-bit) is sufficient
for collision avoidance within a week's signal set (typically <100 files).

**Alternatives considered**:
- Timestamp-based slug: creates duplicate signals on re-run (defeats the purpose of
  idempotent re-run from FR-008).
- External state file (e.g., `.watcher-state/briefing.json`) tracking emitted signals:
  adds state management complexity; hash-based approach achieves the same without state.
- Full SHA-256: unnecessary length for a slug; 8 chars is sufficient.

---

## R-005: Template Fallback Format

**Decision**: When OpenAI is unavailable (any exception from the `openai` client),
synthesiser falls back to a pre-formatted Markdown template that populates each section
with structured lists drawn directly from `BriefingContext` (file names, counts, amounts).
No narrative prose — pure data. The briefing frontmatter records `synthesis:
template_fallback`.

**Rationale**: The fallback must always produce a valid, complete briefing (SC-004). A
structured-list format is readable, honest about the absence of narrative synthesis, and
requires no additional dependencies. The `synthesis` field in frontmatter lets operators
identify template-mode briefings for follow-up.

**Alternatives considered**:
- Abort generation on API failure: violates SC-004 and FR-015 (graceful degradation).
- Partial generation (LLM for some sections, template for others): harder to implement,
  harder to audit, inconsistent output format.
- Cache last successful LLM output: stale data worse than honest template output.

---

## R-006: YAML Frontmatter Parsing

**Decision**: Use `pyyaml` + `re` split on `---` delimiters. Reuse the existing
`read_frontmatter()` / `write_frontmatter()` utility pattern from the social publisher
packages. Extract into `ceo_briefing/utils.py` with no duplication.

**Rationale**: `pyyaml` is already installed; the regex-split approach is already proven
across eight vault modules. No new dependency (`python-frontmatter` would add one without
benefit).

**Alternatives considered**:
- `python-frontmatter` library: clean API but new dep; the existing two-function pattern
  is already sufficient and well-understood.
- Manual string parsing: fragile; already had a bug with `## Content` vs
  `## Content Preview` in Phase 3.

---

## R-007: Briefing File Naming

**Decision**: `vault/Briefings/YYYY-MM-DD_Monday_Briefing.md` where `YYYY-MM-DD` is the
**actual run date** (not necessarily a Monday). The `_Monday_Briefing` suffix is a
semantic label, not a day guard. Running on a Tuesday still produces
`2026-04-21_Monday_Briefing.md`.

**Rationale**: The user spec explicitly names the file `YYYY-MM-DD_Monday_Briefing.md`.
The "Monday" is a branding label for the briefing type, not an enforcement gate. The
actual-date prefix allows multiple briefings per week if needed (e.g., a re-run after
corrections). Idempotency (FR-008) means same-day re-runs overwrite cleanly.

**Alternatives considered**:
- ISO week number prefix (`2026-W17_Monday_Briefing.md`): less readable; week-number
  collisions across years.
- Guard execution to Mondays only: over-constraining; the operator should be able to
  generate the briefing on demand any day.

---

## R-008: Package Dependencies

**Decision**: Add exactly one new dependency to `pyproject.toml`:

```toml
"schedule>=1.2",
```

All other required packages are already installed:
- `openai>=1.0` — LLM synthesis (Silver Tier email reasoning)
- `pyyaml` — frontmatter parsing (all vault modules)
- `python-dotenv` — `.env` loading (all vault modules)
- `click` — CLI (all Gold Tier publishers)
- `pathlib`, `datetime`, `re`, `json`, `hashlib`, `time`, `signal` — stdlib only

**Rationale**: Minimal dependency footprint per Constitution Principle I (local-first,
minimal external surface). `schedule` has no transitive dependencies.

**Alternatives considered**:
- APScheduler: 4 transitive deps; overkill for one weekly job.
- No new dep (manual sleep loop): `while True: check_if_monday(); sleep(3600)` — brittle
  DST handling, no holiday awareness, harder to test.

---

## R-009: Credential Redaction

**Decision**: Before writing any vault file (briefing, signal, or log), apply a simple
regex scrub for common credential patterns: API keys (`sk-...`, `Bearer ...`), email/
password pairs, and `.env`-style `KEY=value` lines. Replace matches with `[REDACTED]`.

**Rationale**: Constitution Principle VII mandates redaction of credentials in vault
content. The risk is low (briefing reads structured vault files, not raw emails) but
the mandate is unconditional. A 5-pattern regex is sufficient for the threat model.

**Alternatives considered**:
- Full PII detection (presidio, spaCy NER): massively over-engineered for a vault that
  already enforces credential isolation upstream.
- No redaction: violates Constitution Principle VII.

---

## Summary — Resolved Clarifications

| # | Item | Resolution |
|---|------|-----------|
| R-001 | Vault scanning | pathlib.glob + mtime/captured_at lookback |
| R-002 | LLM synthesis | Single GPT-4o call, JSON context, capped tokens |
| R-003 | Scheduling | `schedule` library, watch mode, 60s poll |
| R-004 | Signal idempotency | Hash-of-source-path slug, overwrite on re-run |
| R-005 | LLM fallback | Template mode with structured lists, `synthesis: template_fallback` |
| R-006 | Frontmatter parsing | pyyaml + re, reuse existing pattern |
| R-007 | Briefing filename | `YYYY-MM-DD_Monday_Briefing.md` (actual run date) |
| R-008 | New dependencies | `schedule>=1.2` only |
| R-009 | Credential redaction | 5-pattern regex scrub before any vault write |
