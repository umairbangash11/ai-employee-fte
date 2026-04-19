# Research: Gold Phase 3 — Social Media Expansion

**Branch**: `013-social-media-expansion` | **Date**: 2026-04-17

---

## R-001 — Platform Automation Approach

**Decision**: Playwright browser automation (async_api) for all three platforms  
**Rationale**: Instagram and X do not expose public posting APIs without approved developer accounts or expensive API tiers. Facebook's Graph API similarly requires app review. Playwright is already proven for LinkedIn and Facebook in this project (Silver Tier), uses persistent session state via `.watcher-state/`, and requires no external API credentials beyond user credentials.  
**Alternatives considered**:
- Meta Graph API (Facebook/Instagram): Requires app review, page tokens, and Business Manager setup — out of scope per spec.
- X API v2 (Basic/Pro tier): Requires OAuth 2.0 app credentials and paid access for write endpoints — out of scope per spec.
- Selenium: Playwright supersedes Selenium for async Python workflows; already installed.

---

## R-002 — Shared Drafter Module Design

**Decision**: New `src/social_drafters/` package with a `draft_post(platform, content, **kwargs) -> Path` function that handles all frontmatter generation, slug construction, and vault directory resolution for all three platforms.  
**Rationale**: FR-012 mandates zero duplication of frontmatter logic across platforms. The existing `facebook_publisher`, `linkedin_publisher` pattern keeps per-platform code in each package; the shared draft-writing layer prevents drift as a third and fourth platform are added.  
**Alternatives considered**:
- Duplicate draft logic in each publisher package: Rejected — violates FR-012, creates maintenance burden.
- Mixin class / base class in each publisher: Rejected — unnecessary inheritance hierarchy for a pure data-generation concern.

---

## R-003 — Facebook Frontmatter Schema Alignment

**Decision**: Update `facebook_publisher/parser.py` to accept the new canonical schema (`type: pending_action`, `action_type: publish_post`, `platform: facebook`) alongside the legacy schema (`type: approval_request`, `action_type: publish_facebook_post`), then migrate to the new schema in `social_drafters`.  
**Rationale**: The spec requires `type: pending_action` (FR-001) but the existing `facebook_publisher/parser.py` validates `type == "approval_request"`. Since the spec states the executor is "reused without modification" (assumptions), the safest path is a backward-compatible parser update (two accepted type values) rather than a hard break. Once the new drafter is live, new drafts use the canonical schema.  
**Alternatives considered**:
- Have `social_drafters` write the old format: Rejected — would make the drafter non-canonical and block Instagram/X from sharing the schema.
- Replace parser entirely: Rejected — larger change than needed; backward compat is cheaper.

---

## R-004 — Module Structure for New Publishers

**Decision**: `src/instagram_publisher/` and `src/x_publisher/` each replicate the `facebook_publisher` module inventory exactly: `config.py`, `models.py`, `executor.py`, `handlers.py`, `parser.py`, `selectors.py`, `detector.py`, `state.py`, `utils.py`, `exceptions.py`, `logger.py`, `__main__.py`.  
**Rationale**: FR-011 mandates this structure. Replicating the proven module layout means the same `sp.implement` task pattern applies to all three platforms, and future platforms can be added by cloning the template.  
**Alternatives considered**:
- Lighter package (executor + config only): Rejected — violates FR-011 and loses the proven parser/handler/detector separation.

---

## R-005 — Instagram Image Validation

**Decision**: Instagram executor validates image path existence before opening Playwright. If the image path in frontmatter is absent or the file does not exist, the executor moves the file to `Needs_Action/instagram/` without opening a browser session.  
**Rationale**: FR-013 mandates this. Opening a browser only to fail on a missing image wastes session time and masks the real error.  
**Alternatives considered**:
- Validate inside the browser flow: Rejected — too late; session already opened.

---

## R-006 — X Character Count Enforcement

**Decision**: The X drafter (in `social_drafters`) records `char_count: N` unconditionally. If `N > 280`, it also sets `warning: exceeds_char_limit`. The draft is always written — the human decides whether to edit before approving.  
**Rationale**: FR-014 mandates this. The draft stage is advisory; the operator sees the warning in the frontmatter and can truncate or split the text before moving to `Approved/x/`.  
**Alternatives considered**:
- Block drafts over 280 chars: Rejected — spec explicitly says the draft is still written.
- Auto-split into thread: Rejected — out of scope per spec Out of Scope section.

---

## R-007 — Vault Directory Bootstrapping

**Decision**: Each executor's `startup()` (or `__post_init__`) calls a shared `ensure_vault_dirs(vault_path, platform)` helper that creates `Pending_Approval/<platform>/`, `Approved/<platform>/`, `Done/<platform>/`, `Needs_Action/<platform>/` if absent.  
**Rationale**: FR-007 mandates no manual directory creation. Reusing the pattern already in `sentinel.vault.init` keeps the approach consistent.  
**Alternatives considered**:
- Create dirs lazily on first write: Rejected — creates timing issues when watching for files in a not-yet-created directory.

---

## R-008 — Session State Location

**Decision**: Playwright sessions stored in `.watcher-state/<platform>/storage_state.json`. Platform names: `facebook`, `instagram`, `x`.  
**Rationale**: Constitution Principle VII mandates `.watcher-state/` for Playwright sessions. FR-009 confirms platform-namespaced paths. Consistent with LinkedIn (`.watcher-state/linkedin/`) and Facebook (`.watcher-state/facebook/`).
