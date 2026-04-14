"""CLI for Facebook Publisher.

Commands:
- run: Process all approved posts (one-shot)
- watch: Continuous monitoring mode
- list: Show pending approved posts
- status: Show last run statistics
- auth: Run headed auth flow for Facebook login
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import click

from facebook_publisher.config import FacebookPublisherConfig
from facebook_publisher.detector import FacebookApprovedDetector
from facebook_publisher.exceptions import SessionExpiredError
from facebook_publisher.executor import FacebookPublisher, run_auth_flow
from facebook_publisher.exceptions import FrontmatterValidationError
from facebook_publisher.handlers import (
    handle_publish_failure,
    handle_publish_success,
    move_to_needs_action,
)
from facebook_publisher.logger import FacebookLogger
from facebook_publisher.parser import parse_approved_post
from facebook_publisher.state import PublisherState
from facebook_publisher.utils import compute_content_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--vault-path",
    type=click.Path(exists=True, path_type=Path),
    default=Path.home() / "vault",
    help="Path to the vault directory",
)
@click.option(
    "--headless/--headed",
    default=True,
    help="Run browser in headless mode (default) or headed mode",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug logging",
)
@click.pass_context
def cli(ctx: click.Context, vault_path: Path, headless: bool, debug: bool) -> None:
    """Facebook Publisher - Publish approved posts from the vault."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj["config"] = FacebookPublisherConfig(
        vault_path=vault_path,
        headless=headless,
    )


def process_file(
    file_path: Path,
    publisher: FacebookPublisher,
    state: PublisherState,
    fb_logger: FacebookLogger,
    config: FacebookPublisherConfig,
) -> bool:
    """Process a single approved post file.

    Orchestrates: detect → parse → validate → publish → move → log

    Args:
        file_path: Path to the approved post file
        publisher: Facebook publisher instance
        state: Publisher state for deduplication
        fb_logger: Facebook audit logger
        config: Publisher configuration

    Returns:
        True if published successfully, False otherwise
    """
    fb_logger.log_detected(file_path)

    try:
        # Parse and validate
        post = parse_approved_post(file_path)
        fb_logger.log_validated(file_path, len(post.content))

        # Check for duplicate
        content_hash = compute_content_hash(
            "publish_facebook_post",
            post.content,
            str(file_path),
        )
        if state.is_duplicate(content_hash):
            fb_logger.log_duplicate_skipped(file_path, content_hash)
            state.update_stats("skipped")
            logger.info(f"Skipped duplicate: {file_path}")
            return False

        # Publish with retry
        fb_logger.log_publishing(file_path, post.visibility)
        result = asyncio.run(publisher.publish_with_retry(post.content, post.visibility))

        if result.success:
            # Handle success
            fb_logger.log_published(
                file_path,
                result.post_url,
                result.duration_ms,
                result.retry_count or 1,
            )
            dest_path = handle_publish_success(post, result, config)
            fb_logger.log_moved_to_done(file_path, dest_path)
            state.add_hash(content_hash)
            state.update_stats("published")
            logger.info(f"Published: {file_path} → {dest_path}")
            return True
        else:
            # Handle failure
            fb_logger.log_failed(
                file_path,
                result.error or "Unknown error",
                result.error_type or "UnknownError",
                result.retry_count or 0,
            )
            handle_publish_failure(post, result)
            state.update_stats("failed")
            logger.error(f"Failed: {file_path} - {result.error}")
            return False

    except SessionExpiredError:
        fb_logger.log_session_expired()
        logger.error("Session expired - run 'facebook-publish auth' to re-authenticate")
        raise
    except FrontmatterValidationError as e:
        # Invalid frontmatter - move to Needs_Action
        fb_logger.log_failed(file_path, str(e), "FrontmatterValidationError", 0)
        dest_path = move_to_needs_action(file_path, config, str(e))
        fb_logger.log_moved_to_needs_action(file_path, dest_path)
        state.update_stats("failed")
        logger.error(f"Invalid frontmatter: {file_path} → {dest_path}")
        return False
    except Exception as e:
        fb_logger.log_failed(file_path, str(e), type(e).__name__, 0)
        state.update_stats("failed")
        logger.error(f"Error processing {file_path}: {e}")
        return False


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Process all approved posts (one-shot mode)."""
    config: FacebookPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()
    fb_logger = FacebookLogger(config)

    detector = FacebookApprovedDetector(config)
    files = detector.scan_existing()

    if not files:
        click.echo("No approved posts found.")
        return

    click.echo(f"Found {len(files)} approved post(s)")

    publisher = FacebookPublisher(config)
    try:
        asyncio.run(publisher.initialize())

        success_count = 0
        for file_path in files:
            try:
                if process_file(file_path, publisher, state, fb_logger, config):
                    success_count += 1
            except SessionExpiredError:
                click.echo("\nSession expired. Run 'facebook-publish auth' to re-authenticate.")
                break

        click.echo(f"\nProcessed {success_count}/{len(files)} posts successfully")

    finally:
        asyncio.run(publisher.close())
        state.save()


@cli.command()
@click.pass_context
def watch(ctx: click.Context) -> None:
    """Continuous monitoring mode for approved posts."""
    config: FacebookPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()
    fb_logger = FacebookLogger(config)

    publisher = FacebookPublisher(config)
    detector = FacebookApprovedDetector(config)

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        click.echo("\nShutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    click.echo(f"Watching {config.approved_dir} for approved posts...")
    click.echo("Press Ctrl+C to stop")

    try:
        asyncio.run(publisher.initialize())

        # Process existing files first
        for file_path in detector.scan_existing():
            try:
                process_file(file_path, publisher, state, fb_logger, config)
            except SessionExpiredError:
                click.echo("Session expired. Run 'facebook-publish auth' to re-authenticate.")
                return

        # Start watching for new files
        def on_new_file(file_path: Path) -> None:
            try:
                process_file(file_path, publisher, state, fb_logger, config)
                state.save()
            except SessionExpiredError:
                click.echo("Session expired. Stopping watch mode.")
                detector.stop()

        detector.start(on_new_file)

        # Wait for shutdown signal
        while not shutdown_event.is_set() and detector.is_running:
            asyncio.run(asyncio.sleep(1))

    finally:
        detector.stop()
        asyncio.run(publisher.close())
        state.save()
        click.echo("Watch mode stopped")


@cli.command("list")
@click.pass_context
def list_posts(ctx: click.Context) -> None:
    """Show pending approved posts."""
    config: FacebookPublisherConfig = ctx.obj["config"]
    detector = FacebookApprovedDetector(config)
    files = detector.scan_existing()

    if not files:
        click.echo("No approved posts pending.")
        return

    click.echo(f"Pending approved posts ({len(files)}):\n")
    for i, file_path in enumerate(files, 1):
        try:
            post = parse_approved_post(file_path)
            preview = post.content[:50] + "..." if len(post.content) > 50 else post.content
            click.echo(f"  {i}. {file_path.name}")
            click.echo(f"     Visibility: {post.visibility}")
            click.echo(f"     Preview: {preview}")
            click.echo()
        except Exception as e:
            click.echo(f"  {i}. {file_path.name} (error: {e})")
            click.echo()


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show last run statistics from state file."""
    config: FacebookPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()

    stats = state.get_stats()

    click.echo("Facebook Publisher Status")
    click.echo("=" * 40)
    click.echo(f"Last run: {stats['last_run'] or 'Never'}")
    click.echo(f"Processed hashes: {stats['processed_count']}")
    click.echo()
    click.echo("Statistics:")
    click.echo(f"  Published: {stats['stats']['published']}")
    click.echo(f"  Failed: {stats['stats']['failed']}")
    click.echo(f"  Skipped (duplicates): {stats['stats']['skipped']}")


@cli.command()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Run headed auth flow for Facebook login."""
    config: FacebookPublisherConfig = ctx.obj["config"]

    # Force headed mode for auth
    config = FacebookPublisherConfig(
        vault_path=config.vault_path,
        headless=False,
    )

    click.echo("Starting Facebook authentication flow...")
    success = asyncio.run(run_auth_flow(config))

    if success:
        click.echo("\nAuthentication successful! You can now run headless commands.")
    else:
        click.echo("\nAuthentication failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    cli()
