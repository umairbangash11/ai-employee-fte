"""CLI entry point for Gmail API watcher."""

import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path


# Global flag for graceful shutdown
_shutdown_requested = False

from gmail_watcher import __version__
from gmail_watcher.auth import get_credentials, save_token
from gmail_watcher.config import SentinelConfig
from gmail_watcher.state import load_state, save_state, is_captured, mark_captured
from gmail_watcher.watcher import (
    build_service,
    create_gmail_circuit_breaker,
    create_health_manager,
    parse_message,
    poll_with_retry as _watcher_poll_with_retry,
    route_email_to_failed,
    translate_gmail_error,
)
from gmail_watcher.writer import write_email_file
from resilience import (
    CircuitBreaker,
    ExitCode,
    FailureCategory,
    HealthManager,
    ResilienceError,
)


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

    # Resilience integration (Feature 015, T067)
    parser.add_argument(
        "--health-file",
        type=Path,
        default=Path("./.watcher-state/gmail_watcher_health.json"),
        help="Path to health status JSON (read by sentinel-status)",
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("./vault/Logs"),
        help="Directory for structured failure logs (FR-005)",
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


def _exit_code_for(error: ResilienceError) -> int:
    """Map a ResilienceError's category to an ExitCode integer (T066/T068).

    Args:
        error: Translated resilience error.

    Returns:
        Int exit code: CONFIGURATION for credentials/missing-resource,
        RECOVERABLE for transient/rate-limit/service-down, FATAL otherwise.
    """
    if error.category in (
        FailureCategory.CREDENTIALS_INVALID,
        FailureCategory.RESOURCE_UNAVAILABLE,
    ):
        return ExitCode.CONFIGURATION.value
    if error.category in (
        FailureCategory.TRANSIENT_NETWORK,
        FailureCategory.RATE_LIMITED,
        FailureCategory.EXTERNAL_SERVICE_DOWN,
        FailureCategory.SESSION_EXPIRED,
    ):
        return ExitCode.RECOVERABLE.value
    return ExitCode.FATAL.value


def _build_health_and_circuit(
    config: SentinelConfig,
    args: argparse.Namespace,
) -> tuple[HealthManager, CircuitBreaker]:
    """Construct the HealthManager and CircuitBreaker for this process (T066).

    The health file path honours --health-file (default
    `./.watcher-state/gmail_watcher_health.json`). The breaker uses
    resilience defaults per spec FR-009 and persists across poll cycles
    within this process so its rolling failure window spans real time.

    Args:
        config: Built SentinelConfig (already reconciled with args).
        args: Parsed argparse namespace.

    Returns:
        Tuple of (HealthManager, CircuitBreaker).
    """
    health_path: Path = args.health_file
    health = create_health_manager(state_dir=health_path.parent)
    # The factory uses the default filename; if the caller supplied a custom
    # --health-file basename, override the health manager's health_file
    # accessor by pointing state_dir at its parent (already done above).
    circuit = create_gmail_circuit_breaker()
    health.set_circuit_state(circuit.state)
    return health, circuit


def _do_poll(
    config: SentinelConfig,
    health: HealthManager,
    circuit: CircuitBreaker,
) -> int:
    """Run one resilience-integrated Gmail poll cycle (T066 pipeline swap).

    Uses `watcher.poll_with_retry` for the fetch step (ralph_wiggum_loop +
    circuit breaker + translated error hierarchy). Per-message processing
    failures route each offending email to `Needs_Action/email/failed/`
    via `route_email_to_failed`. Returns a standardized ExitCode integer.
    """
    # Authentication (outside retry — non-retryable per FR-002).
    try:
        creds = get_credentials(config.credentials_path, config.token_path)
        save_token(creds, config.token_path)
    except Exception as exc:
        translated = translate_gmail_error(exc)
        print(f"Error: {translated.message}", file=sys.stderr)
        health.record_failure(translated.message)
        health.heartbeat()
        return _exit_code_for(translated)

    # Load deduplication state (outside retry — disk errors are config/fatal).
    state = load_state(config.state_path)
    service = build_service(creds)

    # Poll with resilience (retry + circuit + health updates already inside).
    print(f"Polling Gmail for unread messages...")
    try:
        raw_messages = _watcher_poll_with_retry(
            service,
            health,
            max_results=config.max_initial_fetch,
            circuit=circuit,
        )
    except ResilienceError as exc:
        print(f"Poll failed: {exc.message}", file=sys.stderr)
        # `poll_with_retry` already called health.record_failure per attempt;
        # keep the breaker reflection on the health file current.
        health.set_circuit_state(circuit.state)
        health.heartbeat()
        return _exit_code_for(exc)
    except Exception as exc:
        translated = translate_gmail_error(exc)
        print(f"Poll failed: {translated.message}", file=sys.stderr)
        health.set_circuit_state(circuit.state)
        health.heartbeat()
        return _exit_code_for(translated)

    if not raw_messages:
        print("No unread messages found.")
        health.set_circuit_state(circuit.state)
        return ExitCode.SUCCESS.value

    print(f"Found {len(raw_messages)} unread message(s)")

    # Per-message processing — each failure routes to Needs_Action/email/failed/.
    captured = 0
    skipped = 0
    per_message_failures = 0
    for raw in raw_messages:
        filepath: Path | None = None
        try:
            message = parse_message(raw)

            if is_captured(state, message.message_id):
                skipped += 1
                continue

            filepath = write_email_file(message, config.vault_path, dry_run=config.dry_run)

            if filepath:
                print(f"Captured: {message.subject}")
                print(f"  → {filepath}")
                captured += 1
                if not config.dry_run:
                    mark_captured(state, message.message_id)
            elif config.dry_run:
                captured += 1
        except Exception as exc:
            per_message_failures += 1
            translated = (
                exc if isinstance(exc, ResilienceError) else translate_gmail_error(exc)
            )
            print(
                f"Message processing failed: {translated.message}",
                file=sys.stderr,
            )
            if filepath is not None and filepath.exists() and not config.dry_run:
                try:
                    routed = route_email_to_failed(
                        source_item=filepath,
                        vault_path=config.vault_path,
                        failure_reason=translated.message,
                        error_code=translated.error_code,
                    )
                    print(f"  Routed to failed queue: {routed}", file=sys.stderr)
                except Exception as route_exc:
                    print(
                        f"  Routing to failed queue also failed: {route_exc}",
                        file=sys.stderr,
                    )

    if not config.dry_run:
        save_state(state, config.state_path)

    if skipped > 0:
        print(f"Skipped {skipped} already captured message(s)")

    if config.dry_run:
        print(f"\nDry run complete. Would capture {captured} message(s).")
    else:
        print(f"\nCaptured {captured} message(s) to vault.")

    health.set_circuit_state(circuit.state)

    if per_message_failures > 0:
        return ExitCode.RECOVERABLE.value
    return ExitCode.SUCCESS.value


def run_once(
    config: SentinelConfig,
    health: HealthManager,
    circuit: CircuitBreaker,
) -> int:
    """Run a single resilience-integrated poll cycle.

    Retry is now inside `_watcher_poll_with_retry` (ralph_wiggum_loop), so
    `run_once` performs exactly one pass through `_do_poll`.
    """
    return _do_poll(config, health, circuit)


def _handle_shutdown(signum, frame):
    """Handle shutdown signal (Ctrl+C)."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\nShutdown requested, finishing current poll...")


def run_poll_loop(
    config: SentinelConfig,
    health: HealthManager,
    circuit: CircuitBreaker,
) -> int:
    """Run continuous polling loop with resilience integration (T066)."""
    import time as _time  # local alias — the legacy top-level import was removed

    global _shutdown_requested

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
            _do_poll(config, health, circuit)
        except ResilienceError as exc:
            print(f"Poll failed: {exc.message}", file=sys.stderr)
        except Exception as exc:
            translated = translate_gmail_error(exc)
            print(f"Poll failed: {translated.message}", file=sys.stderr)

        if _shutdown_requested:
            break

        print(f"Next poll in {config.poll_interval} seconds...")
        for _ in range(config.poll_interval):
            if _shutdown_requested:
                break
            _time.sleep(1)

    print("\nGmail watcher stopped.")
    return ExitCode.SUCCESS.value


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
            return ExitCode.SUCCESS.value
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return ExitCode.CONFIGURATION.value
        except Exception as e:
            print(f"Authentication failed: {e}", file=sys.stderr)
            return ExitCode.FATAL.value

    # Validate interval
    if config.poll_interval < 60:
        print(f"Warning: Poll interval {config.poll_interval}s is below minimum (60s).", file=sys.stderr)
        print("Using minimum interval of 60 seconds.", file=sys.stderr)
        config.poll_interval = 60

    # Build resilience context (HealthManager + CircuitBreaker) — T066.
    health, circuit = _build_health_and_circuit(config, args)

    # Run watcher
    try:
        if config.once:
            return run_once(config, health, circuit)

        return run_poll_loop(config, health, circuit)

    except FileNotFoundError as e:
        translated = translate_gmail_error(e)
        print(f"Error: {translated.message}", file=sys.stderr)
        print("\nRun 'gmail-watcher --auth' to authenticate first.", file=sys.stderr)
        return ExitCode.CONFIGURATION.value
    except ResilienceError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return _exit_code_for(e)
    except Exception as e:
        translated = translate_gmail_error(e)
        print(f"Error: {translated.message}", file=sys.stderr)
        return _exit_code_for(translated)


if __name__ == "__main__":
    sys.exit(main())
