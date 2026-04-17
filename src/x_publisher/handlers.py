"""Post-publish handlers for X posts."""

from pathlib import Path

from x_publisher.utils import format_timestamp, move_file, read_frontmatter, write_frontmatter


def update_frontmatter_published(file_path: Path, post_url: str | None, duration_ms: int | None = None) -> None:
    frontmatter, body = read_frontmatter(file_path)
    frontmatter["status"] = "published"
    frontmatter["published_at"] = format_timestamp()
    frontmatter["executed_by"] = "x_publisher"
    if post_url:
        frontmatter["post_url"] = post_url
    if duration_ms is not None:
        frontmatter["publish_duration_ms"] = duration_ms
    for field in ["last_error", "last_error_type", "last_attempt_at"]:
        frontmatter.pop(field, None)
    write_frontmatter(file_path, frontmatter, body)


def update_frontmatter_failed(file_path: Path, error: str, error_type: str, retry_count: int) -> None:
    frontmatter, body = read_frontmatter(file_path)
    frontmatter["status"] = "failed"
    frontmatter["last_error"] = error
    frontmatter["last_error_type"] = error_type
    frontmatter["last_attempt_at"] = format_timestamp()
    frontmatter["retry_count"] = retry_count
    write_frontmatter(file_path, frontmatter, body)


def move_to_done(file_path: Path, done_dir: Path) -> Path:
    return move_file(file_path, done_dir)


def move_to_needs_action(file_path: Path, needs_action_dir: Path, reason: str = "") -> Path:
    if reason:
        try:
            frontmatter, body = read_frontmatter(file_path)
            frontmatter["failure_reason"] = reason
            write_frontmatter(file_path, frontmatter, body)
        except Exception:
            pass
    return move_file(file_path, needs_action_dir)
