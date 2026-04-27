"""CLI entry point for CEO Briefing Generator.

Usage:
    sentinel-briefing generate [--vault-path PATH] [--force-adhoc] [--dry-run] [--verbose]
    sentinel-briefing status [--vault-path PATH]
"""

import click

from briefing_generator.config import get_vault_path


@click.group()
def cli() -> None:
    """CEO Briefing Generator — Generate executive briefings from vault data."""
    pass


@cli.command()
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to vault directory. Defaults to VAULT_PATH env var.",
)
@click.option(
    "--force-adhoc",
    is_flag=True,
    default=False,
    help="Generate Adhoc briefing even on Monday.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print briefing to stdout without writing.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Print debug information during generation.",
)
def generate(
    vault_path: str | None,
    force_adhoc: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Generate a CEO briefing from vault data."""
    from pathlib import Path

    from briefing_generator import generate_briefing

    # Resolve vault path
    if vault_path:
        vp = Path(vault_path)
    else:
        try:
            vp = get_vault_path()
        except ValueError as e:
            raise click.ClickException(str(e))

    if verbose:
        click.echo(f"Vault path: {vp}")
        click.echo(f"Force adhoc: {force_adhoc}")
        click.echo(f"Dry run: {dry_run}")

    try:
        result = generate_briefing(
            vault_path=vp,
            force_adhoc=force_adhoc,
            dry_run=dry_run,
        )
        if dry_run:
            click.echo(result)  # Print the markdown content
            click.echo("\n---\nDry run complete. No file written.", err=True)
        else:
            click.echo(f"Briefing generated: {result}")
    except Exception as e:
        raise click.ClickException(f"Briefing generation failed: {e}")


@cli.command()
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to vault directory. Defaults to VAULT_PATH env var.",
)
def status(vault_path: str | None) -> None:
    """Show current vault statistics relevant to briefing generation."""
    from pathlib import Path

    from briefing_generator.config import VAULT_DIRS

    # Resolve vault path
    if vault_path:
        vp = Path(vault_path)
    else:
        try:
            vp = get_vault_path()
        except ValueError as e:
            raise click.ClickException(str(e))

    click.echo(f"Vault Status: {vp}")
    click.echo("=" * 40)

    # Check directories
    for name, dirname in VAULT_DIRS.items():
        if name == "goals_file":
            path = vp / dirname
            exists = path.exists()
            click.echo(f"Business Goals: {'Found' if exists else 'Not found'}")
        else:
            path = vp / dirname
            if path.is_dir():
                count = len(list(path.rglob("*.md")))
                click.echo(f"{dirname}: {count} files")
            else:
                click.echo(f"{dirname}: Not found")


if __name__ == "__main__":
    cli()
