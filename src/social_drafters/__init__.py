"""social_drafters — shared social post draft-writing module.

Provides a platform-agnostic API for writing social post proposals to
vault/Pending_Approval/<platform>/ with canonical YAML frontmatter.

Public API:
    draft_post(platform, content, vault_path, **kwargs) -> Path
    make_slug(platform, content) -> str
    ensure_vault_dirs(vault_path, platform) -> None
"""

from social_drafters.drafter import draft_post
from social_drafters.slugger import make_slug
from social_drafters.vault import ensure_vault_dirs

__all__ = ["draft_post", "make_slug", "ensure_vault_dirs"]
