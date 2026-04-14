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
    return parser.parse_args()


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

        return 0

    except session.QRTimeoutError as e:
        print(f"ERROR: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}", file=sys.stderr)
        return 1


async def run_poll_cycle(page, config: cfg.WatcherConfig, dedup_state: state.DeduplicationState) -> dict:
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
        # Scrape messages
        all_messages = await scraper.scrape_unread_messages(page, config)
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
        print(f"Poll cycle error: {e}", file=sys.stderr)
        stats["errors"] += 1

    return stats


async def run_polling_mode(config: cfg.WatcherConfig, run_once: bool = False) -> int:
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

                # Run poll cycle with retry
                stats = None
                for attempt in range(3):
                    try:
                        stats = await run_poll_cycle(page, config, dedup_state)
                        break
                    except Exception as e:
                        if attempt < 2:
                            delay = 2 ** attempt  # 1s, 2s
                            print(f"Poll cycle attempt {attempt+1}/3 failed: {e}. Retrying in {delay}s...", file=sys.stderr)
                            await asyncio.sleep(delay)
                        else:
                            print(f"Poll cycle failed after 3 attempts: {e}", file=sys.stderr)
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

        return 0

    except session.SessionExpiredError as e:
        print(f"ERROR: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nShutting down gracefully...", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"ERROR: Polling failed: {e}", file=sys.stderr)
        return 1


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

    # Branch based on mode
    if args.auth:
        return asyncio.run(run_auth_mode(config))
    elif args.once or args.dry_run:
        return asyncio.run(run_polling_mode(config, run_once=True))
    else:
        return asyncio.run(run_polling_mode(config, run_once=False))


if __name__ == "__main__":
    sys.exit(main())
