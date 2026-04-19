# Implementation Plan: Gold Phase 3 — Social Media Expansion

**Branch**: `013-social-media-expansion` | **Date**: 2026-04-17 | **Spec**: `specs/013-social-media-expansion/spec.md`
**Input**: Feature specification from `specs/013-social-media-expansion/spec.md`

---

## Summary

Extend the vault-based draft-and-approve publishing model to **Facebook** (drafter gap), **Instagram** (new full publisher), and **X** (new full publisher). A new shared `social_drafters` package centralises all frontmatter generation, slug construction, and vault directory resolution, eliminating per-platform duplication. Every post follows the same lifecycle: `Pending_Approval/<platform>/` → human approves → `Approved/<platform>/` → Playwright executor publishes → `Done/<platform>/` (or `Needs_Action/<platform/>` after Ralph Wiggum Loop exhaustion).

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: `playwright` (async_api), `watchdog>=6.0`, `python-dotenv`, `pyyaml`, `click`  
**Storage**: Local filesystem — vault directories under `VAULT_PATH` env var; Playwright session state in `.watcher-state/<platform>/storage_state.json`  
**Testing**: `pytest` + `pytest-asyncio` (`asyncio_mode = auto` — already added to pyproject.toml)  
**Target Platform**: Linux (WSL2 / Ubuntu); headless Chromium via Playwright  
**Project Type**: Single project (packages under `src/`)  
**Performance Goals**: No latency SLO; publish operations are human-triggered and expected to take 5–30 seconds per post  
**Constraints**: No credentials in vault or source code (Constitution VII); no self-approval (Constitution VI); Ralph Wiggum Loop on all publish failures (Constitution V)  
**Scale/Scope**: 3 platforms × ~10 posts/day at peak; single-operator workstation

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|---------|
| I. Local-First | ✅ PASS | All publishing via local Playwright; no cloud orchestration |
| II. Canonical Folder Structure | ✅ PASS | `Pending_Approval/<p>/`, `Approved/<p>/`, `Done/<p>/`, `Needs_Action/<p>/`, `Logs/` — all canonical |
| III. Tiered Scope | ✅ PASS | Gold Phase 3 — social media publishing is ratified Gold item #9 |
| IV. Safety-First Execution | ✅ PASS | Every post written to `Pending_Approval/` first; executor reads only `Approved/`; no self-approval |
| V. Ralph Wiggum Loop | ✅ PASS | FR-005 mandates 3-attempt retry with back-off before routing to `Needs_Action/` |
| VI. Human-in-the-Loop | ✅ PASS | FR-003 explicitly prohibits self-approval; human moves file from `Pending_Approval/` to `Approved/` |
| VII. Credential Isolation | ✅ PASS | Sessions in `.watcher-state/`; credentials in `.env`; both in `.gitignore`; no secrets in vault files |
| VIII. Agent Skills & MCP | ✅ PASS | Contract defined in `contracts/social-drafters.md`; social_drafters is the MCP-boundary-safe module |
| IX. Audit Logging | ✅ PASS | FR-006 mandates 6-field log entries; `sentinel.logger.write_log_entry()` reused |
| X. Graceful Degradation | ✅ PASS | FR-010 mandates per-platform credential failure is logged and skipped; orchestrator does not crash |
| XI. Gold-Tier Phased Development | ✅ PASS | Phase 2 confirmed complete 2026-04-15; Phase 3 spec approved; sequential workflow followed |
| XII. Gold Scope Boundary | ✅ PASS | Phase 4 (CEO briefing) and Phase 5 (reliability) explicitly excluded from spec |

**Post-design re-check**: PASS — data-model.md and contracts/social-drafters.md do not introduce any new principle violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-social-media-expansion/
├── plan.md                          # This file
├── research.md                      # Phase 0 — resolved unknowns
├── data-model.md                    # Phase 1 — entity schemas and state transitions
├── contracts/
│   └── social-drafters.md           # Phase 1 — shared drafter module API contract
└── tasks.md                         # Phase 2 output (/sp.tasks — NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── social_drafters/                 # NEW — shared draft-writing module (Phase I)
│   ├── __init__.py                  #   exports: draft_post, make_slug, ensure_vault_dirs
│   ├── drafter.py                   #   draft_post() — vault write + slug dedup
│   ├── frontmatter.py               #   build_frontmatter() — canonical schema builder
│   ├── slugger.py                   #   make_slug() — deterministic, collision-safe
│   └── vault.py                     #   ensure_vault_dirs() — idempotent dir bootstrapper
│
├── facebook_publisher/              # EXISTING — minor parser update only
│   ├── parser.py                    #   UPDATE: accept new schema (type: pending_action)
│   └── ...                          #   all other modules unchanged
│
├── instagram_publisher/             # NEW — full publisher package (Phase II)
│   ├── __init__.py
│   ├── __main__.py                  #   CLI entry point (auth / run / poll)
│   ├── config.py                    #   InstagramPublisherConfig (from_env)
│   ├── models.py                    #   ApprovedPost, PublishResult, ExecutionState
│   ├── executor.py                  #   InstagramPublisher (Playwright, Ralph Wiggum)
│   ├── handlers.py                  #   update_frontmatter_published/failed
│   ├── parser.py                    #   parse_approved_post, validate_frontmatter
│   ├── selectors.py                 #   SELECTORS, URLS, TIMEOUTS dicts
│   ├── detector.py                  #   watchdog handler + poll mode
│   ├── state.py                     #   ExecutionState load/save (processed hashes)
│   ├── utils.py                     #   ensure_directory, read/write_frontmatter, move_file
│   ├── exceptions.py                #   SessionExpiredError, PublishTimeoutError, etc.
│   └── logger.py                    #   write_log_entry wrapper (delegates to sentinel)
│
├── x_publisher/                     # NEW — full publisher package (Phase III)
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py                    #   XPublisherConfig (from_env)
│   ├── models.py                    #   ApprovedPost (+ char_count field), PublishResult
│   ├── executor.py                  #   XPublisher (Playwright, 280-char advisory)
│   ├── handlers.py
│   ├── parser.py                    #   validates char_count field presence
│   ├── selectors.py
│   ├── detector.py
│   ├── state.py
│   ├── utils.py
│   ├── exceptions.py
│   └── logger.py

pyproject.toml                       # UPDATE: add instagram-executor, x-executor entry points
```

---

## Architecture Decisions

### AD-001 — social_drafters as Zero-Dependency Shared Module

`social_drafters` MUST NOT import from any publisher package. It depends only on `pathlib`, `datetime`, `yaml`, and `re`. This keeps it usable from any context (orchestrator, Claude Code, MCP tool) without pulling in Playwright or platform-specific code.

### AD-002 — Facebook Parser Backward-Compatible Update

`facebook_publisher/parser.py` will accept both `type: approval_request` (legacy) and `type: pending_action` (new canonical). New drafts from `social_drafters` write the canonical schema. Existing approved files in `Approved/facebook/` written with the legacy schema continue to work. This is the smallest viable change.

### AD-003 — Instagram Image Validation at Parser Layer

The Instagram `parser.py` validates `image_path` file existence before the executor initialises a browser. Validation failure raises `ImageNotFoundError`, caught by the executor, which routes the file to `Needs_Action/instagram/` without any Playwright session.

### AD-004 — Session State Pattern

All three new publishers use the same `storage_state.json` approach proven by the updated `linkedin_publisher` (see uncommitted changes on this branch): auth exports cookies to `.watcher-state/<platform>/storage_state.json`; the executor loads from that JSON, avoiding headed-vs-headless Chrome profile incompatibility.

### AD-005 — pyproject.toml Entry Points

Two new entry points added:
- `instagram-executor = "instagram_publisher.__main__:main"`  
- `x-executor = "x_publisher.__main__:main"`

---

## Implementation Phases

### Phase I — Shared Foundation (Prerequisite for everything)

| Step | Action | Files |
|------|--------|-------|
| I-1 | Create `src/social_drafters/` package | 5 new files |
| I-2 | Update `facebook_publisher/parser.py` to accept canonical schema | 1 file updated |
| I-3 | Commit Facebook drafter integration test (write draft → verify Pending_Approval) | test or manual verify |

**Gate**: `social_drafters.draft_post("facebook", ...)` writes a valid file to `vault/Pending_Approval/facebook/` and `facebook_publisher` executor can pick it up from `vault/Approved/facebook/`.

### Phase II — Instagram Publisher

| Step | Action | Files |
|------|--------|-------|
| II-1 | Scaffold `src/instagram_publisher/` package (config, models, exceptions, utils) | 4 new files |
| II-2 | Implement Instagram executor (Playwright, image validation, Ralph Wiggum Loop) | executor.py |
| II-3 | Implement handlers, parser, selectors, detector, state, logger, __main__ | 7 new files |
| II-4 | Register entry point in pyproject.toml | pyproject.toml |

**Gate**: Full lifecycle — `draft_post("instagram", ...)` → human moves to Approved → executor publishes → file in `Done/instagram/` with `status: published` and log entry in `Logs/`.

### Phase III — X Publisher

| Step | Action | Files |
|------|--------|-------|
| III-1 | Scaffold `src/x_publisher/` package (config, models, exceptions, utils) | 4 new files |
| III-2 | Implement X executor (Playwright, char_count advisory, Ralph Wiggum Loop) | executor.py |
| III-3 | Implement handlers, parser, selectors, detector, state, logger, __main__ | 7 new files |
| III-4 | Register entry point in pyproject.toml | pyproject.toml |

**Gate**: Full lifecycle — `draft_post("x", content_over_280_chars)` includes `char_count` + `warning` in frontmatter → human edits + approves → executor publishes → `Done/x/` + log.

### Phase IV — Vault Lifecycle Verification

| Step | Action |
|------|--------|
| IV-1 | Verify `vault_audit.py` reports zero boundary violations across all three `Pending_Approval/<platform>/` directories |
| IV-2 | Verify graceful failure handling: missing `.env` credentials → log entry + no crash |
| IV-3 | Verify Ralph Wiggum Loop: simulated failure after 3 retries → file in `Needs_Action/<platform>/` |

---

## Complexity Tracking

No constitution violations identified. No complexity justification required.

---

## Risks and Mitigations

1. **Instagram/X selectors brittle** — Playwright automation relies on DOM selectors that may change without notice. Mitigated by maintaining a `selectors.py` with fallback selectors (pattern from `linkedin_publisher`) and routing auth failures to `Needs_Action/` for manual retry.

2. **Facebook schema migration** — Existing `Approved/facebook/` files written with `type: approval_request` will coexist with new `type: pending_action` drafts during transition. Mitigated by backward-compatible parser update (AD-002); no existing approved files are modified.

3. **Image path drift for Instagram/X** — Image files referenced in proposals may be moved or deleted between drafting and execution. Mitigated by FR-013 image existence check in parser before any browser action.
