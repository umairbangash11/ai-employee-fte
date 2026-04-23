"""CLI entry point for Inbox → Needs_Action Router."""

import sys
from pathlib import Path

import click

from resilience import ExitCode, HealthManager, ResilienceError
from router import route_inbox

SUBSYSTEM_NAME = "router"


def _router_health_manager(health_file: Path) -> HealthManager:
    """Factory for the router subsystem's HealthManager (T079)."""
    return HealthManager(subsystem=SUBSYSTEM_NAME, state_dir=health_file.parent)


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
@click.option(
    "--health-file",
    type=click.Path(),
    default="./.watcher-state/router_health.json",
    help="Path to health status JSON (read by sentinel-status, T081)",
)
@click.option(
    "--log-dir",
    type=click.Path(),
    default="./vault/Logs",
    help="Directory for structured failure logs (FR-005)",
)
def main(vault: str, dry_run: bool, verbose: bool, health_file: str, log_dir: str):
    """Route emails from Inbox to Needs_Action based on routing rules.

    Scans /Inbox/email/ for markdown files and routes matching files
    to /Needs_Action/email/ based on urgency flags, keywords, and SLA breach.
    """
    # T079 + T081: Initialize HealthManager, record each router invocation.
    health = _router_health_manager(Path(health_file))

    try:
        report = route_inbox(vault, dry_run=dry_run)
    except ResilienceError as exc:
        health.record_failure(exc.message)
        health.heartbeat()
        click.echo(f"Router failed: {exc.message}", err=True)
        sys.exit(ExitCode.RECOVERABLE.value if exc.retryable else ExitCode.FATAL.value)
    except Exception as exc:
        health.record_failure(str(exc))
        health.heartbeat()
        click.echo(f"Router failed: {exc}", err=True)
        sys.exit(ExitCode.FATAL.value)

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

    # T081: health accounting + heartbeat.
    if report.error_count == 0:
        health.record_success()
    else:
        health.record_failure(f"{report.error_count} file(s) failed during routing")
    health.heartbeat()

    # T082: standard exit codes.
    if report.error_count > 0:
        sys.exit(ExitCode.RECOVERABLE.value)
    sys.exit(ExitCode.SUCCESS.value)


if __name__ == "__main__":
    main()
