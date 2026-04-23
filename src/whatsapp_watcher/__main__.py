"""CLI entrypoint for WhatsApp watcher.

Usage:
    python -m whatsapp_watcher           # Normal polling mode (headless)
    python -m whatsapp_watcher --auth    # One-time QR code authentication
    python -m whatsapp_watcher --dry-run # Preview without writing files
    python -m whatsapp_watcher --once    # Single poll cycle then exit
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from . import config as cfg
from . import scraper, session, state, writer
from .watcher import (
    create_health_manager,
    create_whatsapp_circuit_breaker,
    translate_whatsapp_error,
)
from resilience import (
    ExitCode,
    FailureCategory,
    ResilienceError,
    async_ralph_wiggum_loop,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="whatsapp-watcher",
        description="Monitor WhatsApp Web for unread messages and save to vault",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Open headed browser for QR code authentication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which messages would be captured without writing files",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single poll cycle then exit",
    )
    # Resilience integration (Feature 015, T076)
    parser.add_argument(
        "--health-file",
        type=Path,
        default=Path("./.watcher-state/whatsapp_watcher_health.json"),
        help="Path to health status JSON (read by sentinel-status)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("./vault/Logs"),
        help="Directory for structured failure logs (FR-005)",
    )
    return parser.parse_args()


def _exit_code_for(error: ResilienceError) -> int:
    """Map a ResilienceError category to a standardized ExitCode integer (T077)."""
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


async def run_auth_mode(config: cfg.WatcherConfig) -> int:
    """Run one-time QR code authentication flow.

    Algorithm:
        1. Launch Playwright with headless=False
        2. Create browser context (triggers QR flow)
        3. Wait for authentication
        4. Save session
        5. Exit

    Args:
        config: WatcherConfig with headless=False

    Returns:
        Exit code (0 success, 1 failure)
    """
    try:
        async with async_playwright() as p:
            print("Starting authentication mode...", file=sys.stderr)
            context = await session.create_browser_context(config, p)

            # Session is saved automatically in create_browser_context
            # Close browser
            await context.close()

        return ExitCode.SUCCESS.value

    except session.QRTimeoutError as e:
        print(f"ERROR: {e.message}", file=sys.stderr)
        return ExitCode.CONFIGURATION.value
    except Exception as e:
        translated = translate_whatsapp_error(e)
        print(f"ERROR: {translated.message}", file=sys.stderr)
        return _exit_code_for(translated)


async def run_poll_cycle(
    page,
    config: cfg.WatcherConfig,
    dedup_state: state.DeduplicationState,
    health=None,
) -> dict:
    """Execute single poll cycle.

    Algorithm:
        1. Scrape unread messages from WhatsApp Web
        2. Filter out already-processed messages
        3. Write new messages to vault
        4. Update dedup state
        5. Save state
        6. Return stats

    Args:
        page: Playwright page with WhatsApp Web loaded
        config: WatcherConfig with settings
        dedup_state: Current deduplication state

    Returns:
        Stats dict: {scraped, new, written, duplicates, errors}
    """
    stats = {
        "scraped": 0,
        "new": 0,
        "written": 0,
        "duplicates": 0,
        "errors": 0
    }

    captured_at = datetime.now()

    try:
        # Scrape messages (T071/T072 — health accounting per attempt)
        all_messages = await scraper.scrape_unread_messages(page, config)
        if health is not None:
            health.record_success()
        stats["scraped"] = len(all_messages)

        if not all_messages:
            print("No messages scraped.", file=sys.stderr)
            return stats

        # Filter duplicates
        new_messages = []
        for message in all_messages:
            if state.is_message_processed(message, dedup_state):
                stats["duplicates"] += 1
            else:
                new_messages.append(message)

        stats["new"] = len(new_messages)
        print(f"Found {stats['new']} new messages ({stats['duplicates']} duplicates skipped)", file=sys.stderr)

        # Write new messages
        for message in new_messages:
            try:
                filepath = writer.write_message_file(message, config, captured_at)
                if filepath:  # None if dry-run
                    stats["written"] += 1
                state.mark_message_processed(message, dedup_state, captured_at)
            except Exception as e:
                print(f"Error writing message: {e}", file=sys.stderr)
                stats["errors"] += 1

        # Save state
        if not config.dry_run:
            state.save_dedup_state(dedup_state, config)

    except Exception as e:
        translated = translate_whatsapp_error(e)
        print(f"Poll cycle error: {translated.message}", file=sys.stderr)
        if health is not None:
            health.record_failure(translated.message)
        stats["errors"] += 1
        # Re-raise as a ResilienceError so the outer async_ralph_wiggum_loop
        # can consult its retryable flag (T071 + T075).
        raise translated from e
    finally:
        # T073: heartbeat every poll cycle, success or failure.
        if health is not None:
            health.heartbeat()

    return stats


async def run_polling_mode(
    config: cfg.WatcherConfig,
    run_once: bool = False,
    health=None,
    circuit=None,
) -> int:
    """Run continuous polling mode.

    Algorithm:
        1. Load config
        2. Load dedup state
        3. Initialize Playwright
        4. Create browser context (reuse session)
        5. Loop:
            a. Run poll cycle
            b. Log stats
            c. Sleep for poll_interval
            d. Break if run_once=True
        6. Clean shutdown

    Args:
        config: WatcherConfig with settings
        run_once: If True, exit after one cycle

    Returns:
        Exit code (0 success, 1 failure)
    """
    try:
        # Load dedup state
        dedup_state = state.load_dedup_state(config)

        async with async_playwright() as p:
            # Create browser context (reuse session)
            print("Initializing browser session...", file=sys.stderr)
            context = await session.create_browser_context(config, p)
            page = await context.new_page()

            # Navigate to WhatsApp Web
            await page.goto("https://web.whatsapp.com", timeout=config.page_timeout)
            await session.wait_for_whatsapp_ready(page, timeout=config.page_timeout)

            # Polling loop
            cycle_count = 0
            while True:
                cycle_count += 1
                print(f"\n--- Poll Cycle {cycle_count} Start ---", file=sys.stderr)

                # Run poll cycle with resilience (T071 — shared ralph_wiggum_loop
                # replaces the inline 3-attempt retry).
                stats = None
                try:
                    stats = await async_ralph_wiggum_loop(
                        operation=lambda: run_poll_cycle(page, config, dedup_state, health=health),
                    )
                    if circuit is not None:
                        circuit.record_success()
                except ResilienceError as exc:
                    if circuit is not None:
                        circuit.record_failure()
                        if health is not None:
                            health.set_circuit_state(circuit.state)
                    print(f"Poll cycle failed after retries: {exc.message}", file=sys.stderr)
                    stats = {"scraped": 0, "new": 0, "written": 0, "duplicates": 0, "errors": 1}
                except Exception as exc:
                    translated = translate_whatsapp_error(exc)
                    if circuit is not None:
                        circuit.record_failure()
                        if health is not None:
                            health.set_circuit_state(circuit.state)
                    print(f"Poll cycle failed: {translated.message}", file=sys.stderr)
                    stats = {"scraped": 0, "new": 0, "written": 0, "duplicates": 0, "errors": 1}

                # Log stats
                if stats:
                    print(f"Stats: Scraped={stats['scraped']}, New={stats['new']}, Written={stats['written']}, Duplicates={stats['duplicates']}, Errors={stats['errors']}", file=sys.stderr)

                print(f"--- Poll Cycle {cycle_count} End ---\n", file=sys.stderr)

                # Exit if run_once
                if run_once:
                    print("Single poll complete, exiting.", file=sys.stderr)
                    break

                # Sleep for poll interval
                print(f"Sleeping for {config.poll_interval}s...", file=sys.stderr)
                await asyncio.sleep(config.poll_interval)

            # Clean shutdown
            await context.close()

        return ExitCode.SUCCESS.value

    except session.SessionExpiredError as e:
        print(f"ERROR: {e.message}", file=sys.stderr)
        return ExitCode.RECOVERABLE.value
    except KeyboardInterrupt:
        print("\nShutting down gracefully...", file=sys.stderr)
        return ExitCode.SUCCESS.value
    except ResilienceError as e:
        print(f"ERROR: {e.message}", file=sys.stderr)
        return _exit_code_for(e)
    except Exception as e:
        translated = translate_whatsapp_error(e)
        print(f"ERROR: Polling failed: {translated.message}", file=sys.stderr)
        return _exit_code_for(translated)


def main() -> int:
    """Main CLI entry point.

    Branches based on CLI args:
        --auth → run_auth_mode()
        --once → run_polling_mode(run_once=True)
        default → run_polling_mode(run_once=False)
    """
    args = parse_args()

    # Load config
    config = cfg.load_config(
        dry_run=args.dry_run,
        headless=not args.auth  # headless=False for --auth
    )

    # Build resilience context (T070, T076 — honours --health-file).
    health = create_health_manager(state_dir=args.health_file.parent)
    circuit = create_whatsapp_circuit_breaker()
    health.set_circuit_state(circuit.state)

    # Branch based on mode
    if args.auth:
        return asyncio.run(run_auth_mode(config))
    elif args.once or args.dry_run:
        return asyncio.run(run_polling_mode(config, run_once=True, health=health, circuit=circuit))
    else:
        return asyncio.run(run_polling_mode(config, run_once=False, health=health, circuit=circuit))


if __name__ == "__main__":
    sys.exit(main())
