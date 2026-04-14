"""Post-publish handlers for Facebook posts.

Handles frontmatter updates and file movements after publish success/failure.
"""

from datetime import datetime
from pathlib import Path

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.models import ApprovedPost, PublishResult
from facebook_publisher.utils import (
    ensure_directory,
    format_timestamp,
    move_file,
    read_frontmatter,
    write_frontmatter,
)


def update_frontmatter_failed(
    file_path: Path,
    error: str,
    error_type: str,
    retry_count: int,
) -> None:
    """Update frontmatter with failure information.

    After 3 failed publish attempts, the file remains in /Approved/facebook/
    with error metadata for debugging and potential manual intervention.

    Args:
        file_path: Path to the approved post file
        error: Error message
        error_type: Type of error (exception class name)
        retry_count: Number of attempts made
    """
    frontmatter, body = read_frontmatter(file_path)

    # Update status and error fields
    frontmatter["status"] = "failed"
    frontmatter["last_error"] = error
    frontmatter["last_error_type"] = error_type
    frontmatter["last_attempt_at"] = format_timestamp()
    frontmatter["retry_count"] = retry_count

    write_frontmatter(file_path, frontmatter, body)


def update_frontmatter_published(
    file_path: Path,
    post_url: str | None,
    duration_ms: int | None = None,
) -> None:
    """Update frontmatter with publication success information.

    Args:
        file_path: Path to the approved post file
        post_url: URL of the published Facebook post (if available)
        duration_ms: Time taken to publish in milliseconds
    """
    frontmatter, body = read_frontmatter(file_path)

    # Update status and publication fields
    frontmatter["status"] = "published"
    frontmatter["published_at"] = format_timestamp()
    frontmatter["executed_by"] = "facebook_publisher"

    if post_url:
        frontmatter["facebook_post_url"] = post_url

    if duration_ms is not None:
        frontmatter["publish_duration_ms"] = duration_ms

    # Clear any previous error fields if present
    for field in ["last_error", "last_error_type", "last_attempt_at"]:
        frontmatter.pop(field, None)

    write_frontmatter(file_path, frontmatter, body)


def move_to_done(file_path: Path, config: FacebookPublisherConfig) -> Path:
    """Move a successfully published file to /Done/facebook/.

    Args:
        file_path: Path to the published post file
        config: Publisher configuration

    Returns:
        Path to the file in its new location
    """
    # Ensure /Done/facebook/ directory exists
    ensure_directory(config.done_dir)

    # Move file preserving original name
    return move_file(file_path, config.done_dir, preserve_name=True)


def handle_publish_success(
    post: ApprovedPost,
    result: PublishResult,
    config: FacebookPublisherConfig,
) -> Path:
    """Handle successful publication: update frontmatter and move to Done.

    Args:
        post: The approved post that was published
        result: The publish result with post URL and duration
        config: Publisher configuration

    Returns:
        Path to the file in /Done/facebook/
    """
    # Update frontmatter with success info
    update_frontmatter_published(
        post.file_path,
        post_url=result.post_url,
        duration_ms=result.duration_ms,
    )

    # Move to Done folder
    return move_to_done(post.file_path, config)


def handle_publish_failure(
    post: ApprovedPost,
    result: PublishResult,
) -> None:
    """Handle failed publication: update frontmatter with error info.

    The file remains in /Approved/facebook/ for potential retry or manual intervention.

    Args:
        post: The approved post that failed to publish
        result: The publish result with error details
    """
    update_frontmatter_failed(
        post.file_path,
        error=result.error or "Unknown error",
        error_type=result.error_type or "UnknownError",
        retry_count=result.retry_count or 0,
    )


def move_to_needs_action(
    file_path: Path,
    config: FacebookPublisherConfig,
    error: str,
) -> Path:
    """Move a file with invalid frontmatter to /Needs_Action/facebook/.

    Args:
        file_path: Path to the file with validation errors
        config: Publisher configuration
        error: Error message describing the issue

    Returns:
        Path to the file in its new location
    """
    # Ensure /Needs_Action/facebook/ directory exists
    ensure_directory(config.needs_action_dir)

    # Try to add error info to frontmatter if possible
    try:
        frontmatter, body = read_frontmatter(file_path)
        frontmatter["status"] = "needs_action"
        frontmatter["validation_error"] = error
        frontmatter["moved_at"] = format_timestamp()
        write_frontmatter(file_path, frontmatter, body)
    except Exception:
        # If frontmatter is completely invalid, just move the file as-is
        pass

    # Move file to Needs_Action
    return move_file(file_path, config.needs_action_dir, preserve_name=True)
