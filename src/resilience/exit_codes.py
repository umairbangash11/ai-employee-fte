"""
Standard exit codes for all subsystems.

Implements FR-007 exit code standardization for watchdog integration.
These codes enable PM2, systemd, and other process managers to make
correct restart decisions.
"""

import sys
from enum import IntEnum


class ExitCode(IntEnum):
    """
    Standard exit codes for all subsystems.

    Usage:
        - SUCCESS (0): Clean shutdown, no restart needed
        - RECOVERABLE (1): Transient error, restart with backoff
        - CONFIGURATION (2): Config error, no restart (manual fix needed)
        - FATAL (3): Fatal error, no restart (investigation needed)
    """
    SUCCESS = 0           # Clean shutdown (SIGINT, graceful stop)
    RECOVERABLE = 1       # Recoverable error (restart with backoff)
    CONFIGURATION = 2     # Configuration error (no restart, manual fix)
    FATAL = 3             # Fatal error (no restart, investigation needed)


def exit_with_code(code: ExitCode, message: str = "") -> None:
    """
    Exit process with standard code and optional message.

    Args:
        code: Exit code from ExitCode enum
        message: Optional message to print before exit

    Note:
        - SUCCESS messages go to stdout
        - Error messages go to stderr
    """
    if message:
        if code == ExitCode.SUCCESS:
            print(message)
        else:
            print(f"Error: {message}", file=sys.stderr)

    sys.exit(code)
