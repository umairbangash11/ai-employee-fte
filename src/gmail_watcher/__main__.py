"""CLI entry point for Gmail API watcher."""

import argparse
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError


# Global flag for graceful shutdown
_shutdown_requested = False

from gmail_watcher import __version__
from gmail_watcher.auth import get_credentials, save_token
from gmail_watcher.config import SentinelConfig
from gmail_watcher.state import load_state, save_state, is_captured, mark_captured
from gmail_watcher.watcher import build_service, fetch_unread_messages, parse_message
from gmail_watcher.writer import write_email_file


# Transient errors that can be retried
TRANSIENT_ERRORS = (TimeoutError, ConnectionError, HttpError)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="gmail-watcher",
        description="Gmail API watcher for Obsidian vault integration",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--auth",
        action="store_true",
        help="Run OAuth authentication flow and exit",
    )

    parser.add_argument(
        "--vault-path",
        type=Path,
        help="Path to Obsidian vault (default: VAULT_PATH env var or current dir)",
    )

    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("./secrets/gmail/credentials.json"),
        help="Path to OAuth credentials.json file",
    )

    parser.add_argument(
        "--token",
        type=Path,
        default=Path("./secrets/gmail/token.json"),
        help="Path to OAuth token.json file",
    )

    parser.add_argument(
        "--state",
        type=Path,
        default=Path("./.watcher-state/gmail-api.json"),
        help="Path to deduplication state file",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Poll interval in seconds (minimum: 60, default: 120)",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll once and exit (don't run continuous loop)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: show what would be captured without writing files",
    )

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> SentinelConfig:
    """Build SentinelConfig from CLI arguments."""
    config = SentinelConfig(
        credentials_path=args.credentials,
        token_path=args.token,
        state_path=args.state,
        poll_interval=args.interval,
        dry_run=args.dry_run,
        auth_mode=args.auth,
        once=args.once,
    )

    if args.vault_path:
        config.vault_path = args.vault_path

    return config


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and can be retried.

    Args:
        error: Exception to check

    Returns:
        True if the error is transient
    """
    if isinstance(error, HttpError):
        # Rate limit (429) or server errors (5xx) are transient
        status = error.resp.status
        return status == 429 or status >= 500
    return isinstance(error, TRANSIENT_ERRORS)


def get_actionable_message(error: Exception) -> str:
    """Get actionable error message for common failures.

    Args:
        error: Exception to describe

    Returns:
        Human-readable actionable message
    """
    if isinstance(error, RefreshError):
        return "Authentication token refresh failed. Run 'gmail-watcher --auth' to re-authenticate."
    if isinstance(error, FileNotFoundError):
        if "credentials.json" in str(error):
            return "OAuth credentials not found. Download credentials.json from Google Cloud Console."
        if "token.json" in str(error):
            return "Not authenticated. Run 'gmail-watcher --auth' first."
    if isinstance(error, HttpError):
        status = error.resp.status
        if status == 401:
            return "Authentication expired. Run 'gmail-watcher --auth' to re-authenticate."
        if status == 403:
            return "Permission denied. Check Gmail API is enabled and scopes are correct."
        if status == 429:
            return "Rate limited. Wait a few minutes before retrying."
    if isinstance(error, (TimeoutError, ConnectionError)):
        return "Network error. Check your internet connection."
    return str(error)


def poll_with_retry(config: SentinelConfig, max_retries: int = 3) -> int:
    """Run poll cycle with retry on transient errors.

    Implements Ralph Wiggum Loop: 3 retries with exponential backoff.

    Args:
        config: Sentinel configuration
        max_retries: Maximum number of retry attempts

    Returns:
        Exit code (0 for success)
    """
    for attempt in range(max_retries):
        try:
            return _do_poll(config)
        except TRANSIENT_ERRORS as e:
            if not is_transient_error(e):
                raise

            if attempt < max_retries - 1:
                backoff = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                print(f"Failed after {max_retries} attempts: {e}", file=sys.stderr)
                print(get_actionable_message(e), file=sys.stderr)
                return 1

    return 1  # Should not reach here


def _do_poll(config: SentinelConfig) -> int:
    """Internal poll implementation.

    Args:
        config: Sentinel configuration

    Returns:
        Exit code (0 for success)
    """
    # Get credentials
    creds = get_credentials(config.credentials_path, config.token_path)

    # Save token if it was refreshed
    save_token(creds, config.token_path)

    # Load deduplication state
    state = load_state(config.state_path)

    # Build service
    service = build_service(creds)

    # Fetch unread messages
    print(f"Polling Gmail for unread messages...")
    raw_messages = fetch_unread_messages(service, max_results=config.max_initial_fetch)

    if not raw_messages:
        print("No unread messages found.")
        return 0

    print(f"Found {len(raw_messages)} unread message(s)")

    # Process each message
    captured = 0
    skipped = 0
    for raw in raw_messages:
        message = parse_message(raw)

        # Skip already captured messages
        if is_captured(state, message.message_id):
            skipped += 1
            continue

        # Write to vault (or preview if dry-run)
        filepath = write_email_file(message, config.vault_path, dry_run=config.dry_run)

        if filepath:
            print(f"Captured: {message.subject}")
            print(f"  → {filepath}")
            captured += 1

            # Mark as captured (unless dry-run)
            if not config.dry_run:
                mark_captured(state, message.message_id)
        elif config.dry_run:
            # dry_run returns None but still counts as "would capture"
            captured += 1

    # Save state (unless dry-run)
    if not config.dry_run:
        save_state(state, config.state_path)

    # Report results
    if skipped > 0:
        print(f"Skipped {skipped} already captured message(s)")

    if config.dry_run:
        print(f"\nDry run complete. Would capture {captured} message(s).")
    else:
        print(f"\nCaptured {captured} message(s) to vault.")

    return 0


def run_once(config: SentinelConfig) -> int:
    """Run a single poll cycle with retry.

    Args:
        config: Sentinel configuration

    Returns:
        Exit code (0 for success)
    """
    return poll_with_retry(config)


def _handle_shutdown(signum, frame):
    """Handle shutdown signal (Ctrl+C)."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\nShutdown requested, finishing current poll...")


def run_poll_loop(config: SentinelConfig) -> int:
    """Run continuous polling loop.

    Args:
        config: Sentinel configuration

    Returns:
        Exit code (0 for success)
    """
    global _shutdown_requested

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    print(f"Starting Gmail watcher (poll interval: {config.poll_interval}s)")
    print(f"Vault: {config.vault_path}")
    print("Press Ctrl+C to stop\n")

    poll_count = 0
    while not _shutdown_requested:
        poll_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Poll #{poll_count}")

        try:
            poll_with_retry(config)
        except Exception as e:
            print(f"Poll failed: {e}", file=sys.stderr)
            print(get_actionable_message(e), file=sys.stderr)

        if _shutdown_requested:
            break

        # Wait for next poll interval
        print(f"Next poll in {config.poll_interval} seconds...")
        for _ in range(config.poll_interval):
            if _shutdown_requested:
                break
            time.sleep(1)

    print("\nGmail watcher stopped.")
    return 0


def main() -> int:
    """Main entry point for gmail-watcher CLI."""
    args = parse_args()
    config = build_config(args)

    # Handle --auth flag
    if config.auth_mode:
        print("Starting OAuth authentication flow...")
        try:
            creds = get_credentials(
                config.credentials_path,
                config.token_path,
                force_auth=True,
            )
            print(f"Authentication successful!")
            print(f"Token saved to: {config.token_path}")
            return 0
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Authentication failed: {e}", file=sys.stderr)
            return 1

    # Validate interval
    if config.poll_interval < 60:
        print(f"Warning: Poll interval {config.poll_interval}s is below minimum (60s).", file=sys.stderr)
        print("Using minimum interval of 60 seconds.", file=sys.stderr)
        config.poll_interval = 60

    # Run watcher
    try:
        if config.once:
            return run_once(config)

        return run_poll_loop(config)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nRun 'gmail-watcher --auth' to authenticate first.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
