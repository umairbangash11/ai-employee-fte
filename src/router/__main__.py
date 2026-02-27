"""CLI entry point for Inbox → Needs_Action Router."""

import click

from router import route_inbox


@click.command()
@click.option(
    "--vault",
    "-v",
    default=".",
    help="Vault path (default: current directory)",
    type=click.Path(exists=True),
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be routed without moving files",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed output",
)
def main(vault: str, dry_run: bool, verbose: bool):
    """Route emails from Inbox to Needs_Action based on routing rules.

    Scans /Inbox/email/ for markdown files and routes matching files
    to /Needs_Action/email/ based on urgency flags, keywords, and SLA breach.
    """
    report = route_inbox(vault, dry_run=dry_run)

    if dry_run:
        click.echo("DRY RUN - No files were moved")
        click.echo()

    click.echo(f"Scanned: {report.total_scanned}")
    click.echo(f"Routed:  {report.routed_count}")
    click.echo(f"Skipped: {report.skipped_count}")
    click.echo(f"Errors:  {report.error_count}")
    click.echo(f"Time:    {report.duration_ms}ms")

    if verbose and report.routed_files:
        click.echo()
        click.echo("Routed files:")
        for rf in report.routed_files:
            click.echo(f"  {rf.source.name} → {rf.destination.name}")
            click.echo(f"    Rules: {', '.join(rf.matched_rules)}")

    if verbose and report.errors:
        click.echo()
        click.echo("Errors:")
        for err in report.errors:
            click.echo(f"  {err.path.name}: {err.error_type} - {err.message}")


if __name__ == "__main__":
    main()
