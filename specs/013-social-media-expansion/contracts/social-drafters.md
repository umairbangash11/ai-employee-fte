# Contract: social_drafters — Shared Social Post Draft Module

**Phase**: Gold Phase 3 | **Date**: 2026-04-17

---

## Module Location

`src/social_drafters/`

---

## Public API

### `draft_post(platform, content, vault_path, **kwargs) -> Path`

Write a social post proposal to `vault/Pending_Approval/<platform>/<slug>.md`.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `platform` | `str` | Yes | One of `"facebook"`, `"instagram"`, `"x"` |
| `content` | `str` | Yes | Full post text. Must not be empty. |
| `vault_path` | `Path` | Yes | Vault root (`VAULT_PATH` env var) |
| `image_path` | `str \| None` | No | Local image path (Instagram/X only) |
| `source_path` | `str` | No | Caller-provided source reference; defaults to `""` |

**Returns:** `Path` — absolute path to the written draft file.

**Raises:**
- `ValueError` — if `platform` is not one of the three accepted values
- `ValueError` — if `content` is empty or blank
- `OSError` — if vault directory creation or file write fails

**Behaviour:**
1. Ensures `vault/Pending_Approval/<platform>/` exists (creates if absent).
2. Constructs slug via `make_slug(platform, content)`.
3. Appends counter suffix on collision (`-2`, `-3`, ...).
4. Writes YAML frontmatter + `## Content` body.
5. Returns the written path.

**Idempotency:** Not idempotent. Each call produces a new file (slug suffix prevents silent overwrite).

---

### `make_slug(platform, content) -> str`

Construct a deterministic, filesystem-safe slug.

**Format:** `<platform>-<YYYYMMDD>-<first-5-content-words>`

**Rules:**
- Words derived from `content`: lowercase, strip punctuation, join with `-`
- Truncated at 5 words (shorter content uses all available words)
- Date is UTC today

**Example:** `instagram-20260417-quarterly-update-for-all` 

---

### `build_frontmatter(platform, content, dest_path, **kwargs) -> dict`

Build the canonical frontmatter dictionary. Does not write to disk.

**Returns dict with all required fields:**

```python
{
    "type": "pending_action",
    "platform": platform,
    "action_type": "publish_post",
    "status": "awaiting_approval",
    "source_path": kwargs.get("source_path", ""),
    "dest_path": str(dest_path),
    "captured_at": "<ISO 8601 UTC>",
    "content_preview": content[:100],
    # image_path: present for instagram/x when kwargs provides it
    # char_count: present for x (len(content))
    # warning: present for x when len(content) > 280
}
```

---

### `ensure_vault_dirs(vault_path, platform) -> None`

Create all canonical subdirectories for a platform if absent.

**Creates:** `Pending_Approval/<platform>/`, `Approved/<platform>/`, `Done/<platform>/`, `Needs_Action/<platform>/`

**Idempotent** — safe to call on every executor startup.

---

## Module File Inventory

```
src/social_drafters/
├── __init__.py          # exports: draft_post, make_slug, ensure_vault_dirs
├── drafter.py           # draft_post() implementation
├── frontmatter.py       # build_frontmatter()
├── slugger.py           # make_slug()
└── vault.py             # ensure_vault_dirs()
```

---

## Error Taxonomy

| Error | Condition | HTTP-equivalent |
|-------|-----------|-----------------|
| `ValueError("empty content")` | `content.strip() == ""` | 400 |
| `ValueError("invalid platform")` | platform not in allowed set | 400 |
| `OSError` | filesystem write failure | 500 |

---

## Integration Points

- Called by: Facebook drafter integration, Instagram executor drafter call, X executor drafter call
- Uses: `pathlib.Path`, `datetime.utcnow()`, `yaml` (stdlib `pyyaml`)
- Writes to: `vault/Pending_Approval/<platform>/`
- Reads from: nothing (pure write path)
- Does NOT import from: `facebook_publisher`, `instagram_publisher`, `x_publisher`, `linkedin_publisher`
