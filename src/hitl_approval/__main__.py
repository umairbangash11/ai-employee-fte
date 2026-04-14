"""CLI entry point for HITL approval system."""

import json
import os
import sys
from pathlib import Path

import click

from . import __version__
from .config import HITLConfig
from .validator import parse_approval_file, get_approval_summary, validate_frontmatter
from .utils import ensure_approval_dirs


@click.group()
@click.option(
    "--vault-path",
    envvar="VAULT_PATH",
    type=click.Path(exists=True),
    help="Path to Obsidian vault (default: VAULT_PATH env)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed output",
)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, vault_path, verbose):
    """Human-in-the-Loop Approval System.

    Manage approval requests for sensitive external actions.
    """
    ctx.ensure_object(dict)

    if vault_path:
        ctx.obj["vault_path"] = Path(vault_path)
    else:
        ctx.obj["vault_path"] = None

    ctx.obj["verbose"] = verbose


def _get_vault_path(ctx) -> Path:
    """Get vault path from context or environment."""
    vault_path = ctx.obj.get("vault_path")
    if vault_path:
        return vault_path

    env_path = os.environ.get("VAULT_PATH")
    if env_path:
        return Path(env_path)

    click.echo("Error: VAULT_PATH not set. Use --vault-path or set VAULT_PATH environment variable.", err=True)
    sys.exit(1)


def _get_pending_files(vault_path: Path) -> list[Path]:
    """Get all pending approval files."""
    files = []

    # Scan email and linkedin directories
    for action_dir in ["email", "linkedin"]:
        pending_dir = vault_path / "Pending_Approval" / action_dir
        if pending_dir.exists():
            files.extend(pending_dir.glob("*.md"))

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _get_approved_files(vault_path: Path) -> list[Path]:
    """Get all approved files."""
    files = []
    for action_dir in ["email", "linkedin"]:
        approved_dir = vault_path / "Approved" / action_dir
        if approved_dir.exists():
            files.extend(approved_dir.glob("*.md"))
    return files


def _get_rejected_files(vault_path: Path) -> list[Path]:
    """Get all rejected files."""
    files = []
    for action_dir in ["email", "linkedin"]:
        rejected_dir = vault_path / "Rejected" / action_dir
        if rejected_dir.exists():
            files.extend(rejected_dir.glob("*.md"))
    return files


@cli.command()
@click.pass_context
def list(ctx):
    """List all pending approval requests."""
    vault_path = _get_vault_path(ctx)

    # Ensure directories exist
    ensure_approval_dirs(vault_path)

    pending_files = _get_pending_files(vault_path)

    if not pending_files:
        click.echo("No pending approvals")
        return

    click.echo(f"Pending approvals ({len(pending_files)}):\n")

    for file_path in pending_files:
        parsed = parse_approval_file(file_path)
        if parsed:
            summary = get_approval_summary(parsed)
            click.echo(f"  {summary['filename']}")
            click.echo(f"    Action: {summary['action_type']}")
            click.echo(f"    Target: {summary['target']}")
            click.echo(f"    Created: {summary['created_at']}")
            click.echo()
        else:
            click.echo(f"  {file_path.name} (parse error)")
            click.echo()


@cli.command()
@click.argument("approval_id")
@click.pass_context
def show(ctx, approval_id):
    """Show details of specific approval request.

    APPROVAL_ID can be a filename or partial filename.
    """
    vault_path = _get_vault_path(ctx)

    # Find matching file
    all_files = (
        _get_pending_files(vault_path) +
        _get_approved_files(vault_path) +
        _get_rejected_files(vault_path)
    )

    matches = [f for f in all_files if approval_id in f.name]

    if not matches:
        click.echo(f"No approval found matching: {approval_id}", err=True)
        sys.exit(1)

    if len(matches) > 1:
        click.echo(f"Multiple matches found for '{approval_id}':")
        for m in matches:
            click.echo(f"  {m.name}")
        sys.exit(1)

    file_path = matches[0]
    parsed = parse_approval_file(file_path)

    if not parsed:
        click.echo(f"Failed to parse: {file_path}", err=True)
        sys.exit(1)

    # Determine status from location
    if "Pending_Approval" in str(file_path):
        status = "pending"
    elif "Approved" in str(file_path):
        status = "approved"
    elif "Rejected" in str(file_path):
        status = "rejected"
    else:
        status = "unknown"

    fm = parsed["frontmatter"]

    click.echo(f"Approval: {file_path.name}")
    click.echo(f"Status: {status}")
    click.echo(f"Location: {file_path.parent}")
    click.echo()
    click.echo("Frontmatter:")
    click.echo(f"  Type: {fm.get('type')}")
    click.echo(f"  Action: {fm.get('action_type')}")
    click.echo(f"  Created: {fm.get('created_at')}")
    click.echo(f"  Created by: {fm.get('created_by')}")
    click.echo(f"  Target: {fm.get('target')}")
    click.echo(f"  Rollback: {fm.get('rollback_strategy')}")
    click.echo()

    if ctx.obj.get("verbose"):
        click.echo("Body:")
        click.echo(parsed["body"][:500])
        if len(parsed["body"]) > 500:
            click.echo("... (truncated)")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show approval statistics."""
    vault_path = _get_vault_path(ctx)

    # Ensure directories exist
    ensure_approval_dirs(vault_path)

    pending = _get_pending_files(vault_path)
    approved = _get_approved_files(vault_path)
    rejected = _get_rejected_files(vault_path)

    # Count by type
    pending_email = len([f for f in pending if "email" in str(f.parent)])
    pending_linkedin = len([f for f in pending if "linkedin" in str(f.parent)])
    approved_email = len([f for f in approved if "email" in str(f.parent)])
    approved_linkedin = len([f for f in approved if "linkedin" in str(f.parent)])
    rejected_email = len([f for f in rejected if "email" in str(f.parent)])
    rejected_linkedin = len([f for f in rejected if "linkedin" in str(f.parent)])

    click.echo("Approval Statistics")
    click.echo("=" * 40)
    click.echo()
    click.echo("By Status:")
    click.echo(f"  Pending:   {len(pending)}")
    click.echo(f"  Approved:  {len(approved)}")
    click.echo(f"  Rejected:  {len(rejected)}")
    click.echo(f"  Total:     {len(pending) + len(approved) + len(rejected)}")
    click.echo()
    click.echo("By Type:")
    click.echo(f"  Email:     {pending_email + approved_email + rejected_email}")
    click.echo(f"  LinkedIn:  {pending_linkedin + approved_linkedin + rejected_linkedin}")
    click.echo()
    click.echo("Pending by Type:")
    click.echo(f"  Email:     {pending_email}")
    click.echo(f"  LinkedIn:  {pending_linkedin}")


if __name__ == "__main__":
    cli()
