"""File mover with retry logic (Ralph Wiggum Loop)."""

import shutil
import time
from datetime import datetime
from pathlib import Path

from sentinel.logger import write_log_entry
from sentinel.planner import write_execution_plan


def deduplicate_filename(dest_dir: Path, filename: str) -> str:
    """Resolve naming conflicts by appending _1, _2, etc.

    Returns the resolved filename (may be unchanged if no conflict).
    """
    dest = Path(dest_dir) / filename
    if not dest.exists():
        return filename

    stem = Path(filename).stem
    suffix = Path(filename).suffix

    for i in range(1, 1000):
        candidate = f"{stem}_{i}{suffix}"
        if not (Path(dest_dir) / candidate).exists():
            return candidate

    # Fallback: use timestamp
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{stem}_{ts}{suffix}"


def move_file(
    source_path: Path,
    needs_action_dir: Path,
    approved_dir: Path,
    logs_dir: Path,
) -> bool:
    """Move a file from Inbox to Needs_Action with plan and log.

    Implements the Ralph Wiggum retry loop (3 attempts).
    Returns True on success, False on final failure.
    """
    source = Path(source_path)
    needs_action = Path(needs_action_dir)
    approved = Path(approved_dir)
    logs = Path(logs_dir)

    filename = source.name
    file_size = source.stat().st_size if source.exists() else 0

    last_error = None

    for attempt in range(1, 4):
        try:
            if attempt == 1:
                # Attempt 1: execute as planned
                resolved_name = deduplicate_filename(needs_action, filename)
            elif attempt == 2:
                # Attempt 2: re-read file metadata, recompute destination
                file_size = source.stat().st_size if source.exists() else 0
                resolved_name = deduplicate_filename(needs_action, filename)
            else:
                # Attempt 3: simplify — skip dedup, use timestamp suffix
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                resolved_name = f"{stem}_{ts}{suffix}"

            dest_path = needs_action / resolved_name
            renamed = resolved_name != filename

            details = ""
            if renamed:
                details = (
                    f"Renamed from '{filename}' to '{resolved_name}' "
                    f"(naming conflict)"
                )

            # Constitution Principle IV: write plan before action
            rollback = (
                f"Move `{dest_path}` back to `{source}`."
            )
            write_execution_plan(
                approved_dir=approved,
                action="move_file",
                source=source,
                destination=dest_path,
                rollback=rollback,
                expected_outcome=(
                    f"File appears in Needs_Action/ as '{resolved_name}'; "
                    f"removed from Inbox/."
                ),
            )

            # Perform the move
            shutil.move(str(source), str(dest_path))

            # Log success
            write_log_entry(
                logs_dir=logs,
                action_type="file_moved",
                source_path=source,
                dest_path=dest_path,
                file_size=file_size,
                outcome="success",
                details=details,
            )

            action_desc = f"Moved: {filename}"
            if renamed:
                action_desc += f" → {needs_action.name}/{resolved_name} (conflict)"
            else:
                action_desc += f" → {needs_action.name}/{filename}"
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action_desc}"
            )
            return True

        except Exception as e:
            last_error = e
            if attempt < 3:
                time.sleep(0.5 * attempt)
                continue

            # All 3 attempts failed — log and escalate to Needs_Action
            write_log_entry(
                logs_dir=logs,
                action_type="error",
                source_path=source,
                dest_path=needs_action / filename,
                file_size=file_size,
                outcome="failure",
                details=(
                    f"Failed after 3 attempts: {last_error}. "
                    f"File left in Inbox for human review."
                ),
            )

            # Constitution Principle V: write failure to Needs_Action
            # for human review
            _write_failure_to_needs_action(
                needs_action, filename, source, last_error
            )

            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Error: Failed to move '{filename}' after 3 attempts. "
                f"See Logs/.",
                flush=True,
            )
            return False

    return False


def _write_failure_to_needs_action(
    needs_action_dir: Path,
    filename: str,
    source: Path,
    error: Exception,
) -> None:
    """Write a failure summary file to Needs_Action/ for human review."""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%dT%H-%M-%S")
    failure_filename = f"{ts}_FAILED_{filename}.md"
    failure_path = Path(needs_action_dir) / failure_filename

    content = (
        f"---\n"
        f"type: failure_report\n"
        f'timestamp: "{now.strftime("%Y-%m-%dT%H:%M:%S")}"\n'
        f'file: "{filename}"\n'
        f'source: "{source}"\n'
        f"---\n"
        f"\n"
        f"## Failed File Move — Human Review Required\n"
        f"\n"
        f"- **File**: {filename}\n"
        f"- **Source**: {source}\n"
        f"- **Attempts**: 3 (exhausted)\n"
        f"- **Error**: {error}\n"
        f"\n"
        f"### Action Required\n"
        f"\n"
        f"Please manually move or inspect `{source}` and resolve "
        f"the issue described above.\n"
    )

    try:
        failure_path.write_text(content, encoding="utf-8")
    except OSError:
        pass  # Best-effort; already logged to /Logs
