"""Slug construction for social post draft filenames."""

import re
from datetime import datetime, timezone


VALID_PLATFORMS = {"facebook", "instagram", "x"}


def make_slug(platform: str, content: str) -> str:
    """Construct a deterministic, filesystem-safe slug.

    Format: <platform>-<YYYYMMDD>-<first-5-content-words>

    Args:
        platform: One of 'facebook', 'instagram', 'x'
        content: Full post text; first 5 words are used

    Returns:
        Slug string suitable for use as a filename stem

    Examples:
        make_slug("facebook", "Hello world from the team today")
        → "facebook-20260417-hello-world-from-the-team"
    """
    date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d")

    # Extract words: lowercase, strip non-alphanumeric, split
    words = re.sub(r"[^a-z0-9\s]", "", content.lower()).split()
    word_part = "-".join(words[:5]) if words else "draft"

    # Truncate to keep total slug under 80 chars (safe across all filesystems)
    slug = f"{platform}-{date_str}-{word_part}"
    return slug[:80]
