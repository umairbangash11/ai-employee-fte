"""
sentinel-status CLI command.

Implements US1 (Operator Diagnoses Failure) from the
015-error-recovery-resilience specification.

Usage:
    sentinel-status [--json] [--subsystem NAME]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ..health import (
    HealthState,
    HealthStatus,
    read_all_health_files,
    compute_aggregate_status,
)


# Default state directory
DEFAULT_STATE_DIR = Path(".watcher-state")


def format_table(statuses: list[HealthStatus]) -> str:
    """
    Format health statuses as a table.

    Columns: Subsystem, Status, Last Success, Failures, Circuit

    Args:
        statuses: List of HealthStatus to format

    Returns:
        Formatted table string
    """
    if not statuses:
        return "No subsystems found."

    # Define columns
    headers = ["Subsystem", "Status", "Last Success", "Failures", "Circuit"]

    # Build rows
    rows = []
    for status in statuses:
        # Format last success
        last_success = status.last_success or "Never"
        if status.last_success:
            # Shorten ISO timestamp to just time
            last_success = status.last_success.split("T")[1][:8] if "T" in status.last_success else status.last_success

        # Status with indicator
        status_str = status.status.value.upper()
        if status.status == HealthState.HEALTHY:
            status_indicator = "✓"
        elif status.status == HealthState.DEGRADED:
            status_indicator = "⚠"
        else:
            status_indicator = "✗"

        rows.append([
            status.subsystem,
            f"{status_indicator} {status_str}",
            last_success,
            str(status.consecutive_failures),
            status.circuit_state.value.upper(),
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


def format_json_output(
    statuses: list[HealthStatus],
    aggregate: HealthState,
) -> str:
    """
    Format health statuses as JSON.

    Args:
        statuses: List of HealthStatus
        aggregate: Aggregate health state

    Returns:
        JSON string
    """
    data = {
        "aggregate_status": aggregate.value,
        "subsystems": [
            {
                "subsystem": s.subsystem,
                "status": s.status.value,
                "last_heartbeat": s.last_heartbeat,
                "last_success": s.last_success,
                "consecutive_failures": s.consecutive_failures,
                "degradation_reason": s.degradation_reason,
                "circuit_state": s.circuit_state.value,
                "version": s.version,
            }
            for s in statuses
        ],
    }
    return json.dumps(data, indent=2)


def run_status(
    state_dir: Path = DEFAULT_STATE_DIR,
    output_json: bool = False,
    subsystem_filter: Optional[str] = None,
) -> int:
    """
    Run the sentinel-status command.

    Args:
        state_dir: Directory containing health files
        output_json: Whether to output JSON format
        subsystem_filter: Optional filter by subsystem name

    Returns:
        Exit code: 0=all healthy, 1=some degraded, 2=some unhealthy
    """
    # Read all health files
    statuses = read_all_health_files(state_dir)

    # Apply filter
    if subsystem_filter:
        statuses = [s for s in statuses if s.subsystem == subsystem_filter]

    # Sort by subsystem name
    statuses.sort(key=lambda s: s.subsystem)

    # Compute aggregate status
    aggregate = compute_aggregate_status(statuses)

    # Output
    if output_json:
        print(format_json_output(statuses, aggregate))
    else:
        # Header
        if aggregate == HealthState.HEALTHY:
            print("System Status: ✓ HEALTHY")
        elif aggregate == HealthState.DEGRADED:
            print("System Status: ⚠ DEGRADED")
        else:
            print("System Status: ✗ UNHEALTHY")
        print()

        # Table
        print(format_table(statuses))

        # Show degradation reasons
        degraded = [s for s in statuses if s.degradation_reason]
        if degraded:
            print()
            print("Degradation Reasons:")
            for s in degraded:
                print(f"  - {s.subsystem}: {s.degradation_reason}")

    # Return exit code based on aggregate status
    if aggregate == HealthState.HEALTHY:
        return 0
    elif aggregate == HealthState.DEGRADED:
        return 1
    else:
        return 2


def main() -> None:
    """CLI entry point for sentinel-status."""
    parser = argparse.ArgumentParser(
        prog="sentinel-status",
        description="View health status of all subsystems",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output in JSON format",
    )

    parser.add_argument(
        "--subsystem",
        type=str,
        metavar="NAME",
        help="Filter by subsystem name",
    )

    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        metavar="PATH",
        help=f"State directory (default: {DEFAULT_STATE_DIR})",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    exit_code = run_status(
        state_dir=args.state_dir,
        output_json=args.output_json,
        subsystem_filter=args.subsystem,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
