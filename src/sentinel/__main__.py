"""CLI entry point for Vault Sentinel."""

import argparse
import sys

from sentinel import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="Vault Sentinel — Local-first file watcher for Obsidian vaults",
    )
    parser.add_argument(
        "--version", action="version", version=f"sentinel {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init subcommand
    init_parser = subparsers.add_parser("init", help="Initialize vault folder structure")
    init_parser.add_argument(
        "--vault-path",
        default=".",
        help="Path to vault root directory (default: current directory)",
    )

    # watch subcommand
    watch_parser = subparsers.add_parser("watch", help="Start Sentinel file watcher")
    watch_parser.add_argument(
        "--vault-path",
        default=".",
        help="Path to vault root directory (default: current directory)",
    )
    watch_parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between stability checks (default: 1.0)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        _run_init(args)
    elif args.command == "watch":
        _run_watch(args)


def _run_init(args):
    from sentinel.vault import init_vault

    try:
        result = init_vault(args.vault_path)
        print(f"Vault initialized at {result['vault_path']}")
        if result["created"]:
            print(f"  Created: {', '.join(result['created'])}")
        if result["existing"]:
            print(f"  Existing: {', '.join(result['existing'])}")
    except (ValueError, PermissionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _run_watch(args):
    from sentinel.watcher import start_watching

    try:
        start_watching(args.vault_path, args.poll_interval)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSentinel stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
