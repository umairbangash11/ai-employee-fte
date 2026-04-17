"""CLI entry point for social_drafters.

Usage:
    python -m social_drafters <platform> "<content>" [--image-path PATH]

Example:
    python -m social_drafters facebook "Check out our latest update!"
    python -m social_drafters instagram "Caption here" --image-path /path/to/img.jpg
    python -m social_drafters x "Short tweet content"
"""

import os
import sys
from pathlib import Path

import click

from social_drafters.drafter import draft_post
from social_drafters.slugger import VALID_PLATFORMS


@click.command()
@click.argument("platform", type=click.Choice(sorted(VALID_PLATFORMS)))
@click.argument("content")
@click.option("--image-path", default=None, help="Local image file path (Instagram/X only)")
@click.option(
    "--vault-path",
    default=None,
    envvar="VAULT_PATH",
    type=click.Path(path_type=Path),
    help="Vault root directory (defaults to VAULT_PATH env var)",
)
@click.option("--source-path", default="", help="Caller-provided source reference")
def main(
    platform: str,
    content: str,
    image_path: str | None,
    vault_path: Path | None,
    source_path: str,
) -> None:
    """Write a social post proposal to vault/Pending_Approval/<platform>/."""
    if vault_path is None:
        vault_env = os.environ.get("VAULT_PATH")
        if not vault_env:
            click.echo("Error: VAULT_PATH environment variable is required", err=True)
            sys.exit(1)
        vault_path = Path(vault_env)

    try:
        dest = draft_post(
            platform=platform,
            content=content,
            vault_path=vault_path,
            source_path=source_path,
            image_path=image_path,
        )
        click.echo(f"Draft written: {dest}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
