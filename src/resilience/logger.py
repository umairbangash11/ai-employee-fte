"""
Structured failure logging for resilience framework.

Implements FR-005 (Structured Failure Logging) from the
015-error-recovery-resilience specification.

All failures produce structured log entries in `vault/Logs/` with
consistent schema for post-incident analysis.
"""

import re
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .exceptions import FailureCategory, ResilienceError


@dataclass
class FailureLogEntry:
    """
    Structured failure log entry per FR-005 schema.

    Attributes:
        log_id: Unique log identifier (UUID)
        timestamp: ISO 8601 timestamp when failure occurred
        action_type: What operation was being attempted
        subsystem: Which subsystem generated this log
        failure_category: FailureCategory enum value
        error_code: Structured error code (ERR_<SUBSYSTEM>_<CATEGORY>_<DETAIL>)
        retry_count: Number of retries attempted
        is_final_failure: Whether this was the final failure (after all retries)
        source_item: Path to the item being processed (if applicable)
        error_message: Human-readable error message
        stack_trace: Full stack trace (if applicable)
        context: Additional key-value pairs for debugging
        action_taken: What action was taken (e.g., "routed_to_failed_queue")
    """
    log_id: str
    timestamp: str
    action_type: str
    subsystem: str
    failure_category: str
    error_code: str
    retry_count: int
    is_final_failure: bool
    source_item: Optional[str] = None
    error_message: str = ""
    stack_trace: Optional[str] = None
    context: dict = field(default_factory=dict)
    action_taken: Optional[str] = None


def _slugify(text: str, max_length: int = 30) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: Text to slugify
        max_length: Maximum length of slug

    Returns:
        Slugified string
    """
    # Convert to lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate to max_length
    return slug[:max_length]


def _generate_filename(
    timestamp: datetime,
    subsystem: str,
    error_message: str,
) -> str:
    """
    Generate filename per FR-005 pattern.

    Pattern: YYYY-MM-DDTHH-MM-SS_failure_<subsystem>_<slug>.md

    Args:
        timestamp: Failure timestamp
        subsystem: Subsystem name
        error_message: Error message for slug generation

    Returns:
        Filename string
    """
    # Format timestamp (replace colons with hyphens for filesystem safety)
    ts_str = timestamp.strftime("%Y-%m-%dT%H-%M-%S")

    # Create slug from error message
    slug = _slugify(error_message)
    if not slug:
        slug = "unknown"

    return f"{ts_str}_failure_{subsystem}_{slug}.md"


def write_failure_log(
    error: Exception,
    subsystem: str,
    action_type: str,
    log_dir: Path,
    retry_count: int = 0,
    is_final_failure: bool = False,
    source_item: Optional[Path] = None,
    context: Optional[dict] = None,
    action_taken: Optional[str] = None,
    include_stack_trace: bool = True,
) -> Path:
    """
    Write a structured failure log entry.

    Creates a Markdown file in the specified log directory with YAML
    frontmatter and structured sections per FR-005.

    Args:
        error: The exception that caused the failure
        subsystem: Name of the subsystem (e.g., "gmail_watcher")
        action_type: What operation was being attempted
        log_dir: Directory to write logs (e.g., vault/Logs/)
        retry_count: Number of retries attempted
        is_final_failure: Whether this was the final failure
        source_item: Path to the item being processed
        context: Additional debugging context
        action_taken: What action was taken after failure
        include_stack_trace: Whether to include full stack trace

    Returns:
        Path to the created log file
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    now = datetime.utcnow()
    timestamp_iso = now.isoformat() + "Z"

    # Extract error details
    if isinstance(error, ResilienceError):
        failure_category = error.category.value
        error_code = error.error_code
        error_message = error.message
        error_context = {**error.context, **(context or {})}
    else:
        failure_category = FailureCategory.INTERNAL_ERROR.value
        error_code = f"ERR_{subsystem.upper()}_INTERNAL_UNHANDLED"
        error_message = str(error)
        error_context = context or {}

    # Generate stack trace if requested
    stack_trace = None
    if include_stack_trace:
        stack_trace = traceback.format_exc()
        if stack_trace == "NoneType: None\n":
            stack_trace = None

    # Create log entry
    log_entry = FailureLogEntry(
        log_id=str(uuid.uuid4()),
        timestamp=timestamp_iso,
        action_type=action_type,
        subsystem=subsystem,
        failure_category=failure_category,
        error_code=error_code,
        retry_count=retry_count,
        is_final_failure=is_final_failure,
        source_item=str(source_item) if source_item else None,
        error_message=error_message,
        stack_trace=stack_trace,
        context=error_context,
        action_taken=action_taken,
    )

    # Generate filename and content
    filename = _generate_filename(now, subsystem, error_message)
    content = _format_log_entry(log_entry)

    # Write file
    log_path = log_dir / filename
    log_path.write_text(content, encoding="utf-8")

    return log_path


def _format_log_entry(entry: FailureLogEntry) -> str:
    """
    Format a log entry as Markdown with YAML frontmatter.

    Args:
        entry: FailureLogEntry to format

    Returns:
        Formatted Markdown string
    """
    # Build frontmatter
    frontmatter = {
        "log_type": "failure",
        "log_id": entry.log_id,
        "timestamp": entry.timestamp,
        "action_type": entry.action_type,
        "subsystem": entry.subsystem,
        "failure_category": entry.failure_category,
        "error_code": entry.error_code,
        "retry_count": entry.retry_count,
        "is_final_failure": entry.is_final_failure,
    }

    if entry.source_item:
        frontmatter["source_item"] = entry.source_item

    if entry.action_taken:
        frontmatter["action_taken"] = entry.action_taken

    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Build body sections
    sections = [
        "---",
        yaml_str.rstrip(),
        "---",
        "",
        "## Failure Details",
        "",
        f"**Error Code:** `{entry.error_code}`",
        "",
        f"**Category:** {entry.failure_category}",
        "",
        f"**Message:** {entry.error_message}",
        "",
        f"**Final Failure:** {'Yes' if entry.is_final_failure else 'No'}",
        "",
        f"**Retry Count:** {entry.retry_count}",
        "",
    ]

    if entry.source_item:
        sections.extend([
            f"**Source Item:** `{entry.source_item}`",
            "",
        ])

    if entry.action_taken:
        sections.extend([
            f"**Action Taken:** {entry.action_taken}",
            "",
        ])

    # Stack trace section
    if entry.stack_trace:
        sections.extend([
            "## Stack Trace",
            "",
            "```python",
            entry.stack_trace.rstrip(),
            "```",
            "",
        ])

    # Context section
    if entry.context:
        sections.extend([
            "## Context",
            "",
        ])
        for key, value in entry.context.items():
            sections.append(f"- **{key}:** {value}")
        sections.append("")

    return "\n".join(sections)


def get_failure_logs(
    log_dir: Path,
    subsystem: Optional[str] = None,
    since: Optional[datetime] = None,
    is_final_only: bool = False,
) -> list[dict]:
    """
    Retrieve failure logs with optional filtering.

    Args:
        log_dir: Directory containing logs
        subsystem: Filter by subsystem name
        since: Only return logs after this timestamp
        is_final_only: Only return final failures

    Returns:
        List of parsed log entries as dicts
    """
    if not log_dir.exists():
        return []

    logs = []

    for log_path in log_dir.glob("*_failure_*.md"):
        try:
            content = log_path.read_text(encoding="utf-8")

            # Parse frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---",
                content,
                re.DOTALL,
            )

            if not frontmatter_match:
                continue

            frontmatter = yaml.safe_load(frontmatter_match.group(1))

            if not isinstance(frontmatter, dict):
                continue

            # Apply filters
            if subsystem and frontmatter.get("subsystem") != subsystem:
                continue

            if since:
                log_timestamp = datetime.fromisoformat(
                    frontmatter.get("timestamp", "").rstrip("Z")
                )
                if log_timestamp < since:
                    continue

            if is_final_only and not frontmatter.get("is_final_failure"):
                continue

            # Add file path to entry
            frontmatter["_file_path"] = str(log_path)
            logs.append(frontmatter)

        except (yaml.YAMLError, OSError, ValueError):
            continue

    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return logs
