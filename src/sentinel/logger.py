"""Log entry writer for Sentinel actions."""

from datetime import datetime
from pathlib import Path


def write_log_entry(
    logs_dir: Path,
    action_type: str,
    source_path: Path,
    dest_path: Path,
    file_size: int,
    outcome: str,
    details: str = "",
) -> Path:
    """Write a Markdown log entry to the Logs/ folder.

    Returns the path to the created log file.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    filename_ts = now.strftime("%Y-%m-%dT%H-%M-%S")
    source_name = Path(source_path).name
    slug = source_name.replace(" ", "-")
    log_filename = f"{filename_ts}_{action_type}_{slug}.md"
    log_path = Path(logs_dir) / log_filename

    details_line = f"- **Details**: {details}\n" if details else ""

    content = (
        f"---\n"
        f'log_id: "{filename_ts}-{action_type}-{slug}"\n'
        f'timestamp: "{timestamp}"\n'
        f"action_type: {action_type}\n"
        f'source_path: "{source_path}"\n'
        f'dest_path: "{dest_path}"\n'
        f"outcome: {outcome}\n"
        f'details: "{details}"\n'
        f"---\n"
        f"\n"
        f"## {action_type.replace('_', ' ').title()}\n"
        f"\n"
        f"- **File**: {source_name}\n"
        f"- **From**: {source_path}\n"
        f"- **To**: {dest_path}\n"
        f"- **Size**: {file_size:,} bytes\n"
        f"- **Processed**: {timestamp}\n"
        f"{details_line}"
    )

    log_path.write_text(content, encoding="utf-8")
    return log_path
