"""Execution plan writer for Safety-First operations (Constitution Principle IV)."""

from datetime import datetime
from pathlib import Path


def write_execution_plan(
    approved_dir: Path,
    action: str,
    source: Path,
    destination: Path,
    rollback: str,
    expected_outcome: str,
) -> Path:
    """Write an execution plan to Approved/ before performing an action.

    Returns the path to the created plan file.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    filename_ts = now.strftime("%Y-%m-%dT%H-%M-%S")
    source_name = Path(source).name
    slug = source_name.replace(" ", "-")
    plan_filename = f"{filename_ts}_plan_{action}_{slug}.md"
    plan_path = Path(approved_dir) / plan_filename

    content = (
        f"---\n"
        f'plan_id: "{filename_ts}-{action}-{slug}"\n'
        f"action: {action}\n"
        f'source: "{source}"\n'
        f'destination: "{destination}"\n'
        f'created_at: "{timestamp}"\n'
        f"---\n"
        f"\n"
        f"## Action\n"
        f"\n"
        f"Move `{source_name}` from `{Path(source).parent}` to "
        f"`{Path(destination).parent}`.\n"
        f"\n"
        f"## Rollback\n"
        f"\n"
        f"{rollback}\n"
        f"\n"
        f"## Expected Outcome\n"
        f"\n"
        f"{expected_outcome}\n"
    )

    plan_path.write_text(content, encoding="utf-8")
    return plan_path
