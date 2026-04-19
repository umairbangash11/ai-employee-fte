"""Core router functionality for Inbox → Needs_Action routing.

Provides file moving with claim-by-move pattern and routing orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import os
import time

from router.config import RouterConfig, load_router_config
from router.parser import InboxFile, MalformedFrontmatterError, parse_email_file
from router.rules import RoutingResult, evaluate_rules, get_default_rules


class RouterError(Exception):
    """Base exception for router errors."""

    pass


class RoutingFailedError(RouterError):
    """Raised when file routing fails after claim attempt."""

    def __init__(self, source: Path, destination: Path, reason: str):
        self.source = source
        self.destination = destination
        self.reason = reason
        super().__init__(f"Failed to route {source} to {destination}: {reason}")


@dataclass
class MoveResult:
    """Result of a file move operation.

    Attributes:
        success: Whether the move completed successfully
        claimed: True if file was already moved by another process
        source: Original file path
        destination: New file path (None if claimed or failed)
    """

    success: bool
    claimed: bool
    source: Path
    destination: Path | None


@dataclass
class RoutedFile:
    """Information about a successfully routed file.

    Attributes:
        source: Original file path
        destination: New file path
        matched_rules: Names of rules that triggered routing
    """

    source: Path
    destination: Path
    matched_rules: list[str]


@dataclass
class RoutingError:
    """Information about a routing error.

    Attributes:
        path: File that caused the error
        error_type: Type of error
        message: Error description
    """

    path: Path
    error_type: str
    message: str


@dataclass
class RoutingReport:
    """Summary of a routing run.

    Attributes:
        total_scanned: Number of files scanned
        routed_count: Number of files routed
        skipped_count: Number of files skipped (no rules matched)
        error_count: Number of errors encountered
        routed_files: Details of routed files
        errors: Details of errors
        duration_ms: Time taken in milliseconds
    """

    total_scanned: int = 0
    routed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    routed_files: list[RoutedFile] = field(default_factory=list)
    errors: list[RoutingError] = field(default_factory=list)
    duration_ms: int = 0


def move_file_to_needs_action(
    source: Path,
    needs_action_dir: Path,
    logs_dir: Path,
    matched_rules: list[str] | None = None,
) -> MoveResult:
    """Move file from source to /Needs_Action/email/ with logging.

    Uses atomic rename (os.rename) for claim-by-move semantics.
    If source is already gone, returns MoveResult with claimed=True.

    Args:
        source: Path to source file
        needs_action_dir: Destination directory
        logs_dir: Directory for audit logs
        matched_rules: Rules that triggered this move (for logging)

    Returns:
        MoveResult with success status and destination path

    Raises:
        PermissionError: If destination is not writable
        OSError: If move fails for other reasons
    """
    # Create destination directory if needed (FR-011)
    needs_action_dir.mkdir(parents=True, exist_ok=True)

    destination = needs_action_dir / source.name

    # Handle duplicate filenames
    if destination.exists():
        stem = source.stem
        suffix = source.suffix
        counter = 1
        while destination.exists():
            destination = needs_action_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        # Atomic move using os.rename (claim-by-move pattern)
        os.rename(source, destination)
    except FileNotFoundError:
        # File already claimed by another process
        return MoveResult(
            success=False,
            claimed=True,
            source=source,
            destination=None,
        )
    except OSError as e:
        raise RoutingFailedError(source, destination, str(e))

    # Log the routing action
    _write_routing_log(logs_dir, source, destination, matched_rules or [])

    return MoveResult(
        success=True,
        claimed=False,
        source=source,
        destination=destination,
    )


def _write_routing_log(
    logs_dir: Path,
    source: Path,
    destination: Path,
    matched_rules: list[str],
) -> None:
    """Write a routing audit log entry.

    Args:
        logs_dir: Directory for log files
        source: Original file path
        destination: New file path
        matched_rules: Rules that triggered routing
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    log_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-routed-{source.stem}"

    rules_summary = ", ".join(matched_rules) if matched_rules else "none"
    log_content = f"""---
log_id: "{log_id}"
timestamp: "{timestamp}"
action_type: routed
source_path: "{source}"
dest_path: "{destination}"
matched_rules: {matched_rules}
outcome: success
details: "Routed by rules: {rules_summary}"
---
"""

    # Append to daily log file
    log_date = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"router-{log_date}.md"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_content)
        f.write("\n")


def route_inbox(
    vault_path: str | Path = ".",
    config: RouterConfig | None = None,
    dry_run: bool = False,
) -> RoutingReport:
    """Scan /Inbox/email/ and route matching files to /Needs_Action/email/.

    Args:
        vault_path: Root path of the vault (default: current directory)
        config: Optional RouterConfig override (default: load from .env)
        dry_run: If True, report what would be routed without moving files

    Returns:
        RoutingReport with counts and details of routed/skipped/error files

    Raises:
        ValueError: If vault_path does not exist
        PermissionError: If inbox/needs_action directories are not accessible
    """
    start_time = time.time()

    vault = Path(vault_path)
    if not vault.exists():
        raise ValueError(f"Vault path does not exist: {vault}")

    if config is None:
        config = load_router_config()
        config.vault_path = vault

    inbox_dir = vault / "Inbox" / "email"
    needs_action_dir = vault / "Needs_Action" / "email"
    logs_dir = vault / "Logs"

    report = RoutingReport()
    rules = get_default_rules(config)

    # Scan inbox for markdown files
    if not inbox_dir.exists():
        # No inbox directory means nothing to route
        return report

    md_files = list(inbox_dir.glob("*.md"))
    report.total_scanned = len(md_files)

    for file_path in md_files:
        try:
            # Parse the file
            inbox_file = parse_email_file(file_path)

            # Evaluate against rules
            result = evaluate_rules(inbox_file, rules)

            if result.should_route:
                if dry_run:
                    # In dry run, just record what would happen
                    report.routed_files.append(
                        RoutedFile(
                            source=file_path,
                            destination=needs_action_dir / file_path.name,
                            matched_rules=result.matched_rules,
                        )
                    )
                    report.routed_count += 1
                else:
                    # Actually move the file
                    move_result = move_file_to_needs_action(
                        source=file_path,
                        needs_action_dir=needs_action_dir,
                        logs_dir=logs_dir,
                        matched_rules=result.matched_rules,
                    )

                    if move_result.success:
                        report.routed_files.append(
                            RoutedFile(
                                source=file_path,
                                destination=move_result.destination,
                                matched_rules=result.matched_rules,
                            )
                        )
                        report.routed_count += 1
                    elif move_result.claimed:
                        # Already claimed by another process - treat as skipped
                        report.skipped_count += 1
            else:
                report.skipped_count += 1

        except MalformedFrontmatterError as e:
            # Log but don't fail the whole run (FR-012)
            report.errors.append(
                RoutingError(
                    path=file_path,
                    error_type="MalformedFrontmatter",
                    message=str(e),
                )
            )
            report.error_count += 1
            report.skipped_count += 1

        except Exception as e:
            report.errors.append(
                RoutingError(
                    path=file_path,
                    error_type=type(e).__name__,
                    message=str(e),
                )
            )
            report.error_count += 1

    report.duration_ms = int((time.time() - start_time) * 1000)
    return report


def evaluate_file(
    file_path: str | Path,
    config: RouterConfig | None = None,
) -> RoutingResult:
    """Parse file and evaluate against all routing rules.

    Args:
        file_path: Path to the markdown file
        config: Optional RouterConfig (default: load from .env)

    Returns:
        RoutingResult indicating whether file should be routed

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not a .md file
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".md":
        raise ValueError(f"File is not a markdown file: {path}")

    if config is None:
        config = load_router_config()

    inbox_file = parse_email_file(path)
    rules = get_default_rules(config)

    return evaluate_rules(inbox_file, rules)
