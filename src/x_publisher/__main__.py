"""CLI for X Publisher.

Commands:
    auth   - Headed auth flow to export storage_state.json
    run    - Process all currently approved posts (one-shot)
    watch  - Continuous monitoring mode
    list   - Show pending approved posts
    status - Show last run statistics
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import click

from x_publisher.config import XPublisherConfig
from x_publisher.detector import XApprovedDetector
from x_publisher.exceptions import FrontmatterValidationError, SessionExpiredError
from x_publisher.executor import XPublisher, run_auth_flow
from x_publisher.handlers import move_to_done, move_to_needs_action, update_frontmatter_failed, update_frontmatter_published
from x_publisher.logger import XLogger
from x_publisher.parser import parse_approved_post
from x_publisher.state import PublisherState
from x_publisher.utils import compute_content_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.option("--vault-path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--headless/--headed", default=True)
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx: click.Context, vault_path: Path | None, headless: bool, debug: bool) -> None:
    """X Publisher — publish approved posts from the vault."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    ctx.ensure_object(dict)
    try:
        config = XPublisherConfig.from_env()
    except ValueError:
        config = XPublisherConfig()
    if vault_path:
        config.vault_path = vault_path
    config.headless = headless
    ctx.obj["config"] = config


def process_file(
    file_path: Path,
    publisher: XPublisher,
    state: PublisherState,
    x_logger: XLogger,
    config: XPublisherConfig,
) -> bool:
    """Process a single approved X post file."""
    x_logger.log_detected(file_path)

    try:
        post = parse_approved_post(file_path)
        x_logger.log_validated(file_path, len(post.content))

        content_hash = compute_content_hash("publish_post", post.content, str(file_path))
        if state.is_duplicate(content_hash):
            x_logger.log_event("duplicate_skipped", file_path, {"hash": content_hash})
            state.update_stats("skipped")
            return False

        x_logger.log_publishing(file_path, post.char_count)
        result = asyncio.run(publisher.publish_with_retry(post))

        if result.success:
            update_frontmatter_published(file_path, result.post_url, result.duration_ms)
            dest_path = move_to_done(file_path, config.done_dir)
            x_logger.log_moved_to_done(file_path, dest_path)
            x_logger.write_vault_log_entry(
                action_type="publish_post",
                source_path=str(file_path),
                dest_path=str(dest_path),
                outcome="success",
                details=f"platform=x; post_url={result.post_url}",
            )
            state.add_hash(content_hash)
            state.update_stats("published")
            click.echo(f"Published: {file_path.name}")
            return True
        else:
            update_frontmatter_failed(file_path, result.error or "Unknown", result.error_type or "UnknownError", result.retry_count)
            dest_path = move_to_needs_action(file_path, config.needs_action_dir, result.error or "")
            x_logger.log_moved_to_needs_action(file_path, dest_path)
            x_logger.write_vault_log_entry(
                action_type="publish_post",
                source_path=str(file_path),
                dest_path=str(dest_path),
                outcome="failure",
                details=f"platform=x; error={result.error}; retry_count={result.retry_count}",
            )
            state.update_stats("failed")
            click.echo(f"Failed: {file_path.name} — {result.error}", err=True)
            return False

    except SessionExpiredError:
        x_logger.log_session_expired()
        click.echo("Session expired. Run 'x-executor auth' to re-authenticate.", err=True)
        raise
    except FrontmatterValidationError as e:
        x_logger.log_failed(file_path, str(e), "FrontmatterValidationError", 0)
        move_to_needs_action(file_path, config.needs_action_dir, str(e))
        state.update_stats("failed")
        return False
    except Exception as e:
        x_logger.log_failed(file_path, str(e), type(e).__name__, 0)
        state.update_stats("failed")
        logger.error(f"Error processing {file_path}: {e}")
        return False


def _try_process(file_path: Path, publisher: XPublisher, state: PublisherState, x_logger: XLogger, config: XPublisherConfig) -> bool:
    try:
        return process_file(file_path, publisher, state, x_logger, config)
    except SessionExpiredError:
        return False


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Process all approved X posts (one-shot mode)."""
    config: XPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()
    x_logger = XLogger(config)
    detector = XApprovedDetector(config)
    files = detector.scan_existing()

    if not files:
        click.echo("No approved X posts found.")
        return

    click.echo(f"Found {len(files)} approved post(s)")
    publisher = XPublisher(config)
    try:
        asyncio.run(publisher.initialize())
        success_count = sum(1 for f in files if _try_process(f, publisher, state, x_logger, config))
        click.echo(f"\nProcessed {success_count}/{len(files)} posts successfully")
    finally:
        asyncio.run(publisher.close())
        state.save()


@cli.command()
@click.pass_context
def watch(ctx: click.Context) -> None:
    """Continuous monitoring mode for approved X posts."""
    config: XPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()
    x_logger = XLogger(config)
    publisher = XPublisher(config)
    detector = XApprovedDetector(config)
    stop_event = asyncio.Event()

    def _signal_handler(sig, frame):
        click.echo("\nShutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    click.echo(f"Watching {config.approved_dir} for approved X posts...")

    try:
        asyncio.run(publisher.initialize())
        for f in detector.scan_existing():
            _try_process(f, publisher, state, x_logger, config)

        def on_new_file(file_path: Path) -> None:
            _try_process(file_path, publisher, state, x_logger, config)
            state.save()

        detector.start(on_new_file)
        while not stop_event.is_set() and detector.is_running:
            asyncio.run(asyncio.sleep(1))
    finally:
        detector.stop()
        asyncio.run(publisher.close())
        state.save()
        click.echo("Watch mode stopped")


@cli.command("list")
@click.pass_context
def list_posts(ctx: click.Context) -> None:
    """Show pending approved X posts."""
    config: XPublisherConfig = ctx.obj["config"]
    files = XApprovedDetector(config).scan_existing()
    if not files:
        click.echo("No approved X posts pending.")
        return
    for i, f in enumerate(files, 1):
        try:
            post = parse_approved_post(f)
            preview = post.content[:60] + "..." if len(post.content) > 60 else post.content
            char_info = f"chars={post.char_count}" if post.char_count else ""
            warning = " ⚠️ exceeds_char_limit" if post.exceeds_char_limit else ""
            click.echo(f"  {i}. {f.name}")
            click.echo(f"     {char_info}{warning}")
            click.echo(f"     {preview}\n")
        except Exception as e:
            click.echo(f"  {i}. {f.name} (error: {e})\n")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show last run statistics."""
    config: XPublisherConfig = ctx.obj["config"]
    state = PublisherState(config)
    state.load()
    stats = state.get_stats()
    click.echo("X Publisher Status")
    click.echo("=" * 40)
    click.echo(f"Last run: {stats['last_run'] or 'Never'}")
    click.echo(f"Processed hashes: {stats['processed_count']}")
    click.echo(f"  Published: {stats['stats']['published']}")
    click.echo(f"  Failed: {stats['stats']['failed']}")
    click.echo(f"  Skipped: {stats['stats']['skipped']}")


@cli.command()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Run headed auth flow for X login and export session."""
    config: XPublisherConfig = ctx.obj["config"]
    config = XPublisherConfig(vault_path=config.vault_path, headless=False)
    click.echo("Starting X authentication flow...")
    success = asyncio.run(run_auth_flow(config))
    if success:
        click.echo("\nAuthentication successful!")
    else:
        click.echo("\nAuthentication failed. Please try again.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
