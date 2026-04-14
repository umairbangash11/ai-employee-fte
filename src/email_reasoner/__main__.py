"""CLI entry point for Email Reasoning Layer.

Usage:
    email-reasoner [OPTIONS]

Options:
    --vault-path PATH    Path to Obsidian vault (default: VAULT_PATH env)
    --dry-run            Preview classifications without creating files
    --limit N            Process at most N emails (default: all)
    --state PATH         Path to reasoner state file
    --verbose            Show detailed classification reasoning
    --version            Show version
    --help               Show help
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from . import __version__
from .config import ReasonerConfig
from .engine import ReasonerEngine


# =============================================================================
# T086-T095: CLI implementation
# =============================================================================


@click.command()
@click.option(
    "--vault-path",
    type=click.Path(exists=True, path_type=Path),
    envvar="VAULT_PATH",
    help="Path to Obsidian vault (default: VAULT_PATH env)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview classifications without creating files",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Process at most N emails (default: all)",
)
@click.option(
    "--state",
    "state_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to reasoner state file",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed classification reasoning",
)
@click.version_option(version=__version__, prog_name="email-reasoner")
def main(
    vault_path: Path | None,
    dry_run: bool,
    limit: int | None,
    state_path: Path | None,
    verbose: bool,
) -> None:
    """Email Reasoning Layer - classify emails and create tasks.

    Reads email markdown files from /Inbox/email/, classifies them using
    GPT-4o, and generates task files for actionable emails.

    Examples:

        # Process all emails in vault
        email-reasoner --vault-path /path/to/vault

        # Preview without creating files
        email-reasoner --vault-path /path/to/vault --dry-run

        # Process only 5 emails with detailed output
        email-reasoner --vault-path /path/to/vault --limit 5 --verbose
    """
    # T094: Load environment variables
    load_dotenv()

    # Build configuration
    config = ReasonerConfig.from_env()

    # Apply CLI overrides
    if vault_path:
        config.vault_path = vault_path
        # Reset state_path to use new vault_path default
        if state_path is None:
            config.state_path = vault_path / ".watcher-state" / "reasoner.json"

    if state_path:
        config.state_path = state_path

    config.dry_run = dry_run
    config.limit = limit
    config.verbose = verbose

    # T095: Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        sys.exit(1)

    # Display configuration
    click.echo(f"Email Reasoner v{__version__}")
    click.echo(f"Vault: {config.vault_path}")
    click.echo(f"Inbox: {config.inbox_email_path}")
    if dry_run:
        click.echo("Mode: DRY-RUN (no files will be created)")
    if limit:
        click.echo(f"Limit: {limit} emails")
    click.echo("")

    # Run the engine
    engine = ReasonerEngine(config)
    try:
        results = engine.run()

        # Display results
        click.echo("")
        click.echo("=" * 50)
        click.echo("Results:")
        click.echo(f"  Emails scanned: {results['scanned']}")
        click.echo(f"  Already processed: {results['skipped_processed']}")
        click.echo(f"  Classified: {results['classified']}")
        click.echo(f"  Actionable: {results['actionable']}")
        click.echo(f"  Tasks created: {results['tasks_created']}")
        click.echo(f"  Plans created: {results['plans_created']}")

        if results["errors"]:
            click.echo(f"  Errors: {len(results['errors'])}")
            for err in results["errors"]:
                click.echo(f"    - {err['message_id']}: {err['error']}", err=True)

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
