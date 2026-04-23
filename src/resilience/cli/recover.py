"""
sentinel-recover CLI command.

Implements failed item recovery management from the
015-error-recovery-resilience specification.

Usage:
    sentinel-recover list [--subsystem NAME] [--since DATE] [--json]
    sentinel-recover retry PATH [--force]
    sentinel-recover retry-all --subsystem NAME [--force] [--dry-run]
    sentinel-recover purge --older-than DAYS [--subsystem NAME] [--dry-run] [--yes]
"""

import argparse
import json
import shutil
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..failed_routing import (
    FailedItemWrapper,
    get_failed_items,
    recover_failed_item,
)


# Default paths
DEFAULT_VAULT_PATH = Path("vault")
DEFAULT_STATE_DIR = Path(".watcher-state")


def format_failed_items_table(items: list[FailedItemWrapper]) -> str:
    """
    Format failed items as a table.

    Columns: Path, Subsystem, Failed At, Reason

    Args:
        items: List of FailedItemWrapper to format

    Returns:
        Formatted table string
    """
    if not items:
        return "No failed items found."

    headers = ["Path", "Subsystem", "Failed At", "Reason"]

    rows = []
    for item in items:
        # Shorten path
        path = item.original_path
        if len(path) > 40:
            path = "..." + path[-37:]

        # Shorten timestamp
        failed_at = item.failed_at.split("T")[0] if "T" in item.failed_at else item.failed_at

        # Shorten reason
        reason = item.failure_reason
        if len(reason) > 30:
            reason = reason[:27] + "..."

        rows.append([
            path,
            item.subsystem or "unknown",
            failed_at,
            reason,
        ])

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table
    lines = []

    # Header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)

    # Separator
    separator = "-+-".join("-" * w for w in widths)
    lines.append(separator)

    # Rows
    for row in rows:
        row_line = " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
        lines.append(row_line)

    return "\n".join(lines)


def format_failed_items_json(items: list[FailedItemWrapper]) -> str:
    """
    Format failed items as JSON.

    Args:
        items: List of FailedItemWrapper

    Returns:
        JSON string
    """
    data = {
        "count": len(items),
        "items": [
            {
                "original_path": item.original_path,
                "subsystem": item.subsystem,
                "failed_at": item.failed_at,
                "failure_reason": item.failure_reason,
                "retry_attempts": item.retry_attempts,
                "recovery_action": item.recovery_action,
                "error_code": item.error_code,
            }
            for item in items
        ],
    }
    return json.dumps(data, indent=2)


def cmd_list(
    vault_path: Path,
    subsystem: Optional[str] = None,
    since: Optional[str] = None,
    output_json: bool = False,
) -> int:
    """
    List failed items.

    Args:
        vault_path: Base vault path
        subsystem: Optional filter by subsystem
        since: Optional date filter (YYYY-MM-DD)
        output_json: Whether to output JSON

    Returns:
        Exit code: 0=success, 1=error
    """
    try:
        items = get_failed_items(vault_path, subsystem)

        # Apply date filter
        if since:
            try:
                since_date = datetime.fromisoformat(since)
                items = [
                    item for item in items
                    if datetime.fromisoformat(item.failed_at.rstrip("Z")) >= since_date
                ]
            except ValueError:
                print(f"Error: Invalid date format: {since}", file=sys.stderr)
                return 1

        if output_json:
            print(format_failed_items_json(items))
        else:
            print(f"Failed Items: {len(items)}")
            print()
            print(format_failed_items_table(items))

        return 0

    except Exception as e:
        print(f"Error listing failed items: {e}", file=sys.stderr)
        return 1


def cmd_retry(
    wrapper_path: Path,
    force: bool = False,
) -> int:
    """
    Retry a single failed item.

    Args:
        wrapper_path: Path to the wrapper file
        force: Whether to retry non-retryable items

    Returns:
        Exit code: 0=success, 1=error
    """
    try:
        if not wrapper_path.exists():
            print(f"Error: File not found: {wrapper_path}", file=sys.stderr)
            return 1

        # Parse wrapper to check if retryable
        wrapper = FailedItemWrapper.from_markdown(wrapper_path)

        # Check if force is needed
        # For now, all items are retryable unless marked otherwise
        # Future: check wrapper.error_code for non-retryable categories

        # Recover the item
        restored_path = recover_failed_item(wrapper_path)
        print(f"✓ Recovered: {restored_path}")
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error recovering item: {e}", file=sys.stderr)
        return 1


def cmd_retry_all(
    vault_path: Path,
    subsystem: str,
    force: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Retry all failed items for a subsystem.

    Args:
        vault_path: Base vault path
        subsystem: Subsystem to retry
        force: Whether to retry non-retryable items
        dry_run: Whether to only show what would be done

    Returns:
        Exit code: 0=success, 1=error
    """
    try:
        items = get_failed_items(vault_path, subsystem)

        if not items:
            print(f"No failed items found for subsystem: {subsystem}")
            return 0

        print(f"Found {len(items)} failed items for {subsystem}")

        if dry_run:
            print("\n[DRY RUN] Would recover:")
            for item in items:
                print(f"  - {item.original_path}")
            return 0

        # Recover each item
        recovered = 0
        failed = 0

        for item in items:
            # Get the file path (stored during get_failed_items)
            file_path = getattr(item, "_file_path", None)
            if not file_path:
                print(f"  ✗ Cannot recover: missing file path for {item.original_path}")
                failed += 1
                continue

            try:
                restored_path = recover_failed_item(Path(file_path))
                print(f"  ✓ Recovered: {restored_path}")
                recovered += 1
            except Exception as e:
                print(f"  ✗ Failed to recover {item.original_path}: {e}")
                failed += 1

        print(f"\nRecovered: {recovered}, Failed: {failed}")
        return 0 if failed == 0 else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_purge(
    vault_path: Path,
    older_than_days: int,
    subsystem: Optional[str] = None,
    dry_run: bool = False,
    yes: bool = False,
    state_dir: Path = DEFAULT_STATE_DIR,
) -> int:
    """
    Purge old failed items.

    Args:
        vault_path: Base vault path
        older_than_days: Delete items older than this many days
        subsystem: Optional filter by subsystem
        dry_run: Whether to only show what would be done
        yes: Skip confirmation prompt
        state_dir: Directory for backup

    Returns:
        Exit code: 0=success, 1=error
    """
    try:
        items = get_failed_items(vault_path, subsystem)

        # Filter by age
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        old_items = [
            item for item in items
            if datetime.fromisoformat(item.failed_at.rstrip("Z")) < cutoff
        ]

        if not old_items:
            print(f"No failed items older than {older_than_days} days found.")
            return 0

        print(f"Found {len(old_items)} items older than {older_than_days} days")

        # Collect file paths
        file_paths = []
        for item in old_items:
            file_path = getattr(item, "_file_path", None)
            if file_path:
                file_paths.append(Path(file_path))

        if dry_run:
            print("\n[DRY RUN] Would delete:")
            for path in file_paths:
                print(f"  - {path}")
            return 0

        # Confirm
        if not yes:
            print(f"\nThis will permanently delete {len(file_paths)} files.")
            response = input("Continue? [y/N]: ")
            if response.lower() != "y":
                print("Aborted.")
                return 0

        # Create backup
        state_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"purge-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.tar.gz"
        backup_path = state_dir / backup_name

        with tarfile.open(backup_path, "w:gz") as tar:
            for path in file_paths:
                if path.exists():
                    tar.add(path, arcname=path.name)

        print(f"Created backup: {backup_path}")

        # Delete files
        deleted = 0
        for path in file_paths:
            if path.exists():
                path.unlink()
                deleted += 1

        print(f"Deleted {deleted} files.")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """CLI entry point for sentinel-recover."""
    parser = argparse.ArgumentParser(
        prog="sentinel-recover",
        description="Manage failed items in the recovery queue",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT_PATH,
        metavar="PATH",
        help=f"Vault path (default: {DEFAULT_VAULT_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list subcommand
    list_parser = subparsers.add_parser(
        "list",
        help="List failed items",
    )
    list_parser.add_argument(
        "--subsystem",
        type=str,
        metavar="NAME",
        help="Filter by subsystem",
    )
    list_parser.add_argument(
        "--since",
        type=str,
        metavar="DATE",
        help="Filter by date (YYYY-MM-DD)",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output in JSON format",
    )

    # retry subcommand
    retry_parser = subparsers.add_parser(
        "retry",
        help="Retry a single failed item",
    )
    retry_parser.add_argument(
        "path",
        type=Path,
        help="Path to the failed item wrapper file",
    )
    retry_parser.add_argument(
        "--force",
        action="store_true",
        help="Retry non-retryable items",
    )

    # retry-all subcommand
    retry_all_parser = subparsers.add_parser(
        "retry-all",
        help="Retry all failed items for a subsystem",
    )
    retry_all_parser.add_argument(
        "--subsystem",
        type=str,
        required=True,
        metavar="NAME",
        help="Subsystem to retry (required)",
    )
    retry_all_parser.add_argument(
        "--force",
        action="store_true",
        help="Retry non-retryable items",
    )
    retry_all_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )

    # purge subcommand
    purge_parser = subparsers.add_parser(
        "purge",
        help="Delete old failed items",
    )
    purge_parser.add_argument(
        "--older-than",
        type=int,
        required=True,
        metavar="DAYS",
        help="Delete items older than this many days (required)",
    )
    purge_parser.add_argument(
        "--subsystem",
        type=str,
        metavar="NAME",
        help="Filter by subsystem",
    )
    purge_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    purge_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Route to subcommand
    if args.command == "list":
        exit_code = cmd_list(
            vault_path=args.vault,
            subsystem=args.subsystem,
            since=args.since,
            output_json=args.output_json,
        )
    elif args.command == "retry":
        exit_code = cmd_retry(
            wrapper_path=args.path,
            force=args.force,
        )
    elif args.command == "retry-all":
        exit_code = cmd_retry_all(
            vault_path=args.vault,
            subsystem=args.subsystem,
            force=args.force,
            dry_run=args.dry_run,
        )
    elif args.command == "purge":
        exit_code = cmd_purge(
            vault_path=args.vault,
            older_than_days=args.older_than,
            subsystem=args.subsystem,
            dry_run=args.dry_run,
            yes=args.yes,
        )
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
