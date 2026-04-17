"""Core draft_post() implementation — writes social post proposals to vault."""

from pathlib import Path

import yaml

from social_drafters.frontmatter import build_frontmatter
from social_drafters.slugger import make_slug, VALID_PLATFORMS
from social_drafters.vault import ensure_vault_dirs


def draft_post(
    platform: str,
    content: str,
    vault_path: Path,
    *,
    source_path: str = "",
    image_path: str | None = None,
) -> Path:
    """Write a social post proposal to vault/Pending_Approval/<platform>/<slug>.md.

    Args:
        platform: One of 'facebook', 'instagram', 'x'
        content: Full post text. Must not be empty or blank.
        vault_path: Vault root directory (VAULT_PATH env var)
        source_path: Caller-provided source reference (optional)
        image_path: Local image file path (Instagram/X only, optional)

    Returns:
        Absolute path to the written draft file.

    Raises:
        ValueError: If platform is unknown or content is empty/blank.
        OSError: If vault directory creation or file write fails.
    """
    if platform not in VALID_PLATFORMS:
        raise ValueError(f"Unknown platform '{platform}'. Must be one of: {sorted(VALID_PLATFORMS)}")

    if not content or not content.strip():
        raise ValueError("content must not be empty or blank")

    vault_path = Path(vault_path)

    # Ensure all lifecycle directories exist
    ensure_vault_dirs(vault_path, platform)

    pending_dir = vault_path / "Pending_Approval" / platform

    # Build slug and resolve collision-safe path
    slug = make_slug(platform, content)
    dest_path = _unique_path(pending_dir, slug)

    # Build frontmatter
    fm = build_frontmatter(
        platform=platform,
        content=content,
        dest_path=dest_path,
        source_path=source_path,
        image_path=image_path,
    )

    # Write file: YAML frontmatter + ## Content body
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    file_content = f"---\n{fm_str}---\n\n## Content\n\n{content}\n"
    dest_path.write_text(file_content, encoding="utf-8")

    return dest_path


def _unique_path(directory: Path, slug: str) -> Path:
    """Return a collision-safe path for a new draft file.

    Appends -2, -3, ... to the slug if the base name already exists.

    Args:
        directory: Target directory
        slug: Base slug string

    Returns:
        Path that does not yet exist
    """
    candidate = directory / f"{slug}.md"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = directory / f"{slug}-{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1
