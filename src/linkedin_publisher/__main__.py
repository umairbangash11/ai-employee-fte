"""CLI for LinkedIn publisher."""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from .config import LinkedInPublisherConfig
from .detector import LinkedInApprovedDetector
from .exceptions import (
    InvalidFrontmatterError,
    DuplicatePostError,
    AuthenticationError,
    is_retryable_error,
)
from .executor import LinkedInPublisher
from .logger import LinkedInLogger
from .models import ApprovedPost
from .parser import parse_approved_file
from .state import (
    load_execution_state,
    save_execution_state,
    compute_content_hash,
    is_duplicate,
    add_processed_hash,
)
from .utils import (
    ensure_directories,
    handle_publish_success,
    update_file_with_failure,
    move_file_to_needs_action,
)


async def process_approved_file(
    file_path: Path,
    config: LinkedInPublisherConfig,
    logger: LinkedInLogger,
    publisher: Optional[LinkedInPublisher] = None,
    verbose: bool = False,
) -> bool:
    """Process a single approved LinkedIn post file.

    Orchestrates: parse -> validate -> check duplicate -> publish -> handle result -> log

    Args:
        file_path: Path to approval file
        config: Publisher configuration
        logger: LinkedIn logger
        publisher: Optional existing publisher (created if not provided)
        verbose: Enable verbose output

    Returns:
        True if published successfully, False otherwise
    """
    file_path = Path(file_path)
    own_publisher = publisher is None

    try:
        # Log detection
        logger.log_detected(str(file_path))

        if verbose:
            click.echo(f"Processing: {file_path.name}")

        # Parse file
        try:
            approved_post = parse_approved_file(file_path)
        except InvalidFrontmatterError as e:
            logger.log_failed(str(file_path), str(e), "InvalidFrontmatterError", retryable=False)
            new_path = move_file_to_needs_action(file_path, config.needs_action_path)
            logger.log_moved_to_needs_action(str(file_path), str(new_path), str(e))
            click.echo(f"  Invalid frontmatter: {e}", err=True)
            return False

        # Load state and check for duplicate
        state = load_execution_state(config.state_path)
        content_hash = compute_content_hash(
            approved_post.frontmatter.get("action_type", "publish_linkedin_post"),
            approved_post.content,
            approved_post.source_path or str(file_path),
        )

        if is_duplicate(state, content_hash):
            logger.log_duplicate_skipped(str(file_path), content_hash)
            if verbose:
                click.echo(f"  Skipped (duplicate content)")
            # Move to done since it was already published
            new_path = handle_publish_success(
                file_path,
                config.done_path,
                log_path=logger.get_log_path_for_today(),
            )
            logger.log_moved_to_done(str(file_path), str(new_path))
            return True

        # Initialize publisher if needed
        if own_publisher:
            publisher = LinkedInPublisher(
                config.session_path,
                config.headless,
                storage_state_path=config.storage_state_path,
            )
            await publisher.initialize()

        # Log publishing attempt
        logger.log_publishing(str(file_path), approved_post.content[:100])

        if verbose:
            click.echo(f"  Publishing to LinkedIn...")

        # Publish with retry
        result = await publisher.publish_with_retry(approved_post.content)

        if result.success:
            # Success: update frontmatter, move to done, add hash
            logger.log_published(
                str(file_path),
                result.post_url,
                result.retry_count,
                result.publish_duration_ms,
            )

            new_path = handle_publish_success(
                file_path,
                config.done_path,
                result.post_url,
                logger.get_log_path_for_today(),
            )

            logger.log_moved_to_done(str(file_path), str(new_path))

            add_processed_hash(state, content_hash, success=True)
            save_execution_state(state, config.state_path)

            if verbose:
                click.echo(f"  Published successfully!")
                if result.post_url:
                    click.echo(f"  URL: {result.post_url}")

            return True

        else:
            # Failure
            logger.log_failed(
                str(file_path),
                result.error or "Unknown error",
                result.error_type,
                result.retry_count,
                retryable=result.error_type != "AuthenticationError",
            )

            if result.error_type == "AuthenticationError":
                # Auth failure: move to needs_action
                new_path = move_file_to_needs_action(file_path, config.needs_action_path)
                logger.log_moved_to_needs_action(str(file_path), str(new_path), result.error or "Auth required")
                click.echo(f"  Auth failed. Run 'linkedin-publish auth' to re-authenticate.", err=True)
            else:
                # Other failure: update frontmatter, keep in approved
                update_file_with_failure(file_path, result.error or "Unknown error", result.retry_count)
                click.echo(f"  Failed: {result.error}", err=True)

            add_processed_hash(state, content_hash, success=False)
            save_execution_state(state, config.state_path)

            return False

    except Exception as e:
        logger.log_failed(str(file_path), str(e), type(e).__name__, retryable=is_retryable_error(e))
        click.echo(f"  Error: {e}", err=True)
        return False

    finally:
        if own_publisher and publisher:
            await publisher.close()


@click.group()
@click.option(
    "--vault-path",
    envvar="VAULT_PATH",
    type=click.Path(exists=True, path_type=Path),
    help="Path to Obsidian vault",
)
@click.option(
    "--headless/--headed",
    default=True,
    help="Browser mode (default: headless)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Verbose output",
)
@click.pass_context
def cli(ctx, vault_path: Optional[Path], headless: bool, verbose: bool):
    """LinkedIn publisher for approved posts.

    Publishes approved LinkedIn posts from /Approved/linkedin/ to LinkedIn
    via browser automation.
    """
    ctx.ensure_object(dict)

    if vault_path:
        config = LinkedInPublisherConfig(
            vault_path=vault_path,
            headless=headless,
            verbose=verbose,
        )
    else:
        try:
            config = LinkedInPublisherConfig.from_env()
            config.headless = headless
            config.verbose = verbose
        except ValueError:
            # Don't exit here — subcommands check `if not config` themselves.
            # Exiting in the group callback prevents --help from working on
            # subcommands when VAULT_PATH is unset.
            config = None

    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose


@cli.command()
@click.pass_context
def run(ctx):
    """Process all approved posts (one-shot).

    Scans /Approved/linkedin/, processes each file, and exits.
    """
    config: LinkedInPublisherConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    if not config:
        ctx.exit(1)

    # Ensure directories exist
    ensure_directories(config.vault_path)

    # Initialize logger
    logger = LinkedInLogger(config.logs_path)

    # Scan for approved files
    detector = LinkedInApprovedDetector(config.vault_path)
    files = detector.scan_existing()

    if not files:
        click.echo("No approved LinkedIn posts found.")
        return

    click.echo(f"Found {len(files)} approved post(s)")

    # Process each file
    success_count = 0
    fail_count = 0

    async def process_all():
        nonlocal success_count, fail_count

        click.echo(f"[debug] Session file: {config.storage_state_path}")
        click.echo(f"[debug] Session exists: {config.storage_state_path.exists()}")

        publisher = LinkedInPublisher(
            config.session_path,
            config.headless,
            storage_state_path=config.storage_state_path,
        )
        await publisher.initialize()

        try:
            for file_path in files:
                result = await process_approved_file(
                    file_path,
                    config,
                    logger,
                    publisher,
                    verbose,
                )
                if result:
                    success_count += 1
                else:
                    fail_count += 1
        finally:
            await publisher.close()

    asyncio.run(process_all())

    # Summary
    click.echo(f"\nCompleted: {success_count} published, {fail_count} failed")


@cli.command("list")
@click.pass_context
def list_pending(ctx):
    """List pending approved posts.

    Shows files in /Approved/linkedin/ with creation dates.
    """
    config: LinkedInPublisherConfig = ctx.obj["config"]

    if not config:
        ctx.exit(1)

    detector = LinkedInApprovedDetector(config.vault_path)
    files = detector.scan_existing()

    if not files:
        click.echo("No approved LinkedIn posts found.")
        return

    click.echo(f"Pending approved posts ({len(files)}):\n")

    for file_path in files:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        click.echo(f"  {file_path.name}")
        click.echo(f"    Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show last run statistics.

    Reads .watcher-state/linkedin/publisher.json and displays stats.
    """
    config: LinkedInPublisherConfig = ctx.obj["config"]

    if not config:
        ctx.exit(1)

    state = load_execution_state(config.state_path)

    click.echo("LinkedIn Publisher Status\n")
    click.echo(f"  Last run: {state.last_run.strftime('%Y-%m-%d %H:%M:%S') if state.last_run else 'Never'}")
    click.echo(f"  Total published: {state.total_published}")
    click.echo(f"  Total failed: {state.total_failed}")
    click.echo(f"  Processed hashes: {len(state.processed_hashes)}")

    # Count pending
    detector = LinkedInApprovedDetector(config.vault_path)
    pending = len(detector.scan_existing())
    click.echo(f"  Pending in queue: {pending}")


@cli.command()
@click.option(
    "--timeout",
    default=300,
    type=int,
    help="Seconds to wait for login (default: 300)",
)
@click.pass_context
def auth(ctx, timeout: int):
    """Authenticate with LinkedIn.

    Opens a headed browser, navigates to the LinkedIn login page once,
    and waits — without refreshing — for you to log in manually.
    When your feed appears, the session is saved automatically.
    """
    config: LinkedInPublisherConfig = ctx.obj["config"]

    if not config:
        ctx.exit(1)

    click.echo("─" * 55)
    click.echo("  LinkedIn Authentication")
    click.echo("─" * 55)
    click.echo("1. A browser window will open at the LinkedIn login page.")
    click.echo("2. Enter your credentials (and complete 2FA if prompted).")
    click.echo("3. Do NOT close the browser — this script detects login")
    click.echo("   automatically when your feed loads.")
    click.echo(f"4. Timeout: {timeout} seconds.")
    click.echo("─" * 55 + "\n")

    success = False

    async def do_auth():
        nonlocal success
        # Always force headed mode for auth regardless of config/env.
        publisher = LinkedInPublisher(config.session_path, headless=False)
        await publisher.initialize()

        try:
            click.echo("Browser opened. Navigating to LinkedIn login page...")
            success = await publisher.wait_for_login(
                timeout_ms=timeout * 1000,
                storage_state_path=config.storage_state_path,
            )
        finally:
            await publisher.close()

    try:
        asyncio.run(do_auth())
    except KeyboardInterrupt:
        click.echo("\nAuthentication cancelled by user.")
        return

    if success:
        click.echo("\nLogin detected — session saved successfully.")
        click.echo(f"Session file : {config.storage_state_path}")
        click.echo("\nYou can now run headless publishing:")
        click.echo("  linkedin-publish --vault-path vault/ run")
    else:
        click.echo(
            f"\nTimeout: login was not detected within {timeout} seconds.",
            err=True,
        )
        click.echo("Run the command again and complete login before the timeout.", err=True)


@cli.command()
@click.option(
    "--poll-interval",
    default=30,
    type=int,
    help="Seconds between poll scans (default: 30)",
)
@click.pass_context
def watch(ctx, poll_interval: int):
    """Watch and process approved posts continuously.

    Monitors /Approved/linkedin/ for new files and processes them
    as they appear. Runs until interrupted (Ctrl+C).
    """
    config: LinkedInPublisherConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    if not config:
        ctx.exit(1)

    # Ensure directories exist
    ensure_directories(config.vault_path)

    # Initialize components
    logger = LinkedInLogger(config.logs_path)
    detector = LinkedInApprovedDetector(
        config.vault_path,
        mode=config.detection_mode,
        poll_interval=poll_interval,
    )

    click.echo(f"Watching /Approved/linkedin/ (mode: {config.detection_mode})")
    click.echo("Press Ctrl+C to stop.\n")

    # Process queue for async handling
    file_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    def on_file_detected(file_path: Path):
        """Callback when file detected."""
        click.echo(f"Detected: {file_path.name}")
        # Put in queue for async processing
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                file_queue.put_nowait, file_path
            )
        except RuntimeError:
            # Event loop not running yet, use sync approach
            pass

    async def process_queue():
        """Process files from queue."""
        publisher = LinkedInPublisher(
            config.session_path,
            config.headless,
            storage_state_path=config.storage_state_path,
        )
        await publisher.initialize()

        try:
            # First, process existing files
            existing = detector.scan_existing()
            for file_path in existing:
                await process_approved_file(file_path, config, logger, publisher, verbose)

            # Then process new files as they arrive
            while not stop_event.is_set():
                try:
                    file_path = await asyncio.wait_for(file_queue.get(), timeout=1.0)
                    await process_approved_file(file_path, config, logger, publisher, verbose)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

        finally:
            await publisher.close()

    async def main_watch():
        """Main watch loop."""
        # Start detector in background
        detector.start(on_file_detected)

        try:
            await process_queue()
        finally:
            detector.stop()

    def handle_sigint(signum, frame):
        """Handle Ctrl+C."""
        click.echo("\nStopping...")
        stop_event.set()
        detector.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        asyncio.run(main_watch())
    except KeyboardInterrupt:
        click.echo("\nStopped.")


if __name__ == "__main__":
    cli()
