"""
Failed item routing for resilience framework.

Implements FR-006 (Failed Item Recovery) from the 015-error-recovery-resilience
specification. Routes failed items to `Needs_Action/<source>/failed/` with
preserved content and recovery metadata.

Per Constitution Principle V: After 3 failures, items are routed here
for human review rather than silently dropped.
"""

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class FailedItemWrapper:
    """
    Wrapper for failed items with recovery metadata.

    Preserves the original content and frontmatter while adding
    failure context for operator analysis.

    Attributes:
        failed_at: ISO timestamp when the failure occurred
        failure_reason: Human-readable failure description
        original_path: Path where the item originally resided
        retry_attempts: Number of retries before failure
        recovery_action: Suggested recovery action for operator
        original_content: The original file content (body only)
        original_frontmatter: Original YAML frontmatter as dict
        subsystem: Subsystem that failed processing
        error_code: Error code from ResilienceError (if applicable)
    """
    failed_at: str
    failure_reason: str
    original_path: str
    retry_attempts: int
    recovery_action: str
    original_content: str
    original_frontmatter: dict = field(default_factory=dict)
    subsystem: Optional[str] = None
    error_code: Optional[str] = None

    def to_markdown(self) -> str:
        """
        Generate wrapped Markdown with YAML frontmatter.

        Returns:
            Markdown string with wrapper frontmatter containing
            original content preserved in body.
        """
        # Build wrapper frontmatter
        wrapper_frontmatter = {
            "wrapper_type": "failed_item",
            "failed_at": self.failed_at,
            "failure_reason": self.failure_reason,
            "original_path": self.original_path,
            "retry_attempts": self.retry_attempts,
            "recovery_action": self.recovery_action,
            "subsystem": self.subsystem or "unknown",
        }

        if self.error_code:
            wrapper_frontmatter["error_code"] = self.error_code

        # Preserve original frontmatter
        if self.original_frontmatter:
            wrapper_frontmatter["original_frontmatter"] = self.original_frontmatter

        # Build the markdown output
        yaml_str = yaml.dump(
            wrapper_frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Build output with wrapper frontmatter and preserved original content
        lines = [
            "---",
            yaml_str.rstrip(),
            "---",
            "",
            "## Original Content",
            "",
            self.original_content,
        ]

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, path: Path) -> "FailedItemWrapper":
        """
        Parse a wrapped failed item from a Markdown file.

        Args:
            path: Path to the failed item wrapper file

        Returns:
            FailedItemWrapper instance with parsed metadata

        Raises:
            ValueError: If file format is invalid or missing required fields
        """
        content = path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$",
            content,
            re.DOTALL,
        )

        if not frontmatter_match:
            raise ValueError(f"Invalid failed item wrapper format in {path}")

        frontmatter_str, body = frontmatter_match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {path}: {e}")

        if not isinstance(frontmatter, dict):
            raise ValueError(f"Frontmatter must be a dict in {path}")

        # Verify wrapper type
        if frontmatter.get("wrapper_type") != "failed_item":
            raise ValueError(f"Not a failed item wrapper: {path}")

        # Extract required fields
        required_fields = [
            "failed_at",
            "failure_reason",
            "original_path",
            "retry_attempts",
            "recovery_action",
        ]

        for field in required_fields:
            if field not in frontmatter:
                raise ValueError(f"Missing required field '{field}' in {path}")

        # Extract original content from body
        original_content = body
        # Remove "## Original Content" header if present
        if body.strip().startswith("## Original Content"):
            original_content = body.split("## Original Content", 1)[1].strip()

        return cls(
            failed_at=frontmatter["failed_at"],
            failure_reason=frontmatter["failure_reason"],
            original_path=frontmatter["original_path"],
            retry_attempts=frontmatter["retry_attempts"],
            recovery_action=frontmatter["recovery_action"],
            original_content=original_content,
            original_frontmatter=frontmatter.get("original_frontmatter", {}),
            subsystem=frontmatter.get("subsystem"),
            error_code=frontmatter.get("error_code"),
        )


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter and body from markdown content.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (frontmatter dict, body string)
    """
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        content,
        re.DOTALL,
    )

    if frontmatter_match:
        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            body = frontmatter_match.group(2)
            return frontmatter or {}, body
        except yaml.YAMLError:
            pass

    # No valid frontmatter, return content as body
    return {}, content


def route_to_failed_queue(
    source_item: Path,
    subsystem: str,
    failure_reason: str,
    retry_attempts: int = 3,
    recovery_action: str = "Review and manually process",
    vault_path: Optional[Path] = None,
    error_code: Optional[str] = None,
    move_original: bool = True,
) -> Path:
    """
    Route a failed item to the appropriate failed queue.

    Creates a wrapper file in `Needs_Action/<source>/failed/` containing
    failure metadata and the preserved original content.

    Args:
        source_item: Path to the failed item
        subsystem: Subsystem that failed processing (e.g., "gmail_watcher")
        failure_reason: Human-readable failure description
        retry_attempts: Number of retries before failure (default: 3)
        recovery_action: Suggested action for operator
        vault_path: Base vault path (default: source_item.parents to find vault)
        error_code: Error code from ResilienceError if applicable
        move_original: Whether to move (True) or copy (False) the original

    Returns:
        Path to the created wrapper file

    Raises:
        FileNotFoundError: If source_item doesn't exist
        ValueError: If vault_path cannot be determined
    """
    if not source_item.exists():
        raise FileNotFoundError(f"Source item not found: {source_item}")

    # Determine vault path if not provided
    if vault_path is None:
        # Look for common vault indicators in path
        for parent in source_item.parents:
            if (parent / "Inbox").exists() or (parent / "Needs_Action").exists():
                vault_path = parent
                break

        if vault_path is None:
            # Default to source item's grandparent
            vault_path = source_item.parent.parent

    # Determine source type from path or subsystem
    source_type = _determine_source_type(source_item, subsystem)

    # Create failed queue directory
    failed_dir = vault_path / "Needs_Action" / source_type / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)

    # Read original content
    original_content = source_item.read_text(encoding="utf-8")
    original_frontmatter, body = _parse_frontmatter(original_content)

    # Create wrapper
    wrapper = FailedItemWrapper(
        failed_at=datetime.utcnow().isoformat() + "Z",
        failure_reason=failure_reason,
        original_path=str(source_item),
        retry_attempts=retry_attempts,
        recovery_action=recovery_action,
        original_content=body,
        original_frontmatter=original_frontmatter,
        subsystem=subsystem,
        error_code=error_code,
    )

    # Generate output filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_name = f"{timestamp}_{source_item.stem}_failed.md"
    output_path = failed_dir / output_name

    # Write wrapper file
    output_path.write_text(wrapper.to_markdown(), encoding="utf-8")

    # Move or delete original
    if move_original and source_item.exists():
        source_item.unlink()

    return output_path


def _determine_source_type(source_item: Path, subsystem: str) -> str:
    """
    Determine source type from path or subsystem name.

    Args:
        source_item: Path to source item
        subsystem: Subsystem name

    Returns:
        Source type string (e.g., "email", "whatsapp")
    """
    # Map subsystems to source types
    subsystem_map = {
        "gmail_watcher": "email",
        "gmail_api": "email",
        "whatsapp_watcher": "whatsapp",
        "router": "router",
        "orchestrator": "triage",
        "briefing_generator": "briefing",
        "linkedin_publisher": "linkedin",
        "facebook_publisher": "facebook",
        "hitl_approval": "approvals",
    }

    if subsystem in subsystem_map:
        return subsystem_map[subsystem]

    # Try to infer from path
    path_str = str(source_item).lower()
    if "email" in path_str or "gmail" in path_str:
        return "email"
    if "whatsapp" in path_str:
        return "whatsapp"

    # Default to subsystem name
    return subsystem


def get_failed_items(
    vault_path: Path,
    subsystem: Optional[str] = None,
) -> list[FailedItemWrapper]:
    """
    List all failed items in the vault.

    Args:
        vault_path: Base vault path
        subsystem: Optional filter by subsystem name

    Returns:
        List of FailedItemWrapper instances
    """
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return []

    failed_items: list[FailedItemWrapper] = []

    # Find all failed directories
    for source_dir in needs_action.iterdir():
        if not source_dir.is_dir():
            continue

        failed_dir = source_dir / "failed"
        if not failed_dir.exists():
            continue

        # Parse each failed item
        for item_path in failed_dir.glob("*.md"):
            try:
                wrapper = FailedItemWrapper.from_markdown(item_path)

                # Filter by subsystem if specified
                if subsystem and wrapper.subsystem != subsystem:
                    continue

                # Store the file path for reference
                wrapper._file_path = item_path  # type: ignore

                failed_items.append(wrapper)
            except (ValueError, OSError):
                # Skip invalid files
                continue

    # Sort by failed_at (newest first)
    failed_items.sort(key=lambda x: x.failed_at, reverse=True)

    return failed_items


def recover_failed_item(
    wrapper_path: Path,
    destination: Optional[Path] = None,
) -> Path:
    """
    Recover a failed item by restoring it to its original location.

    Args:
        wrapper_path: Path to the failed item wrapper file
        destination: Optional custom destination (default: original_path)

    Returns:
        Path where the item was restored

    Raises:
        FileNotFoundError: If wrapper doesn't exist
        ValueError: If wrapper format is invalid
    """
    wrapper = FailedItemWrapper.from_markdown(wrapper_path)

    # Determine destination
    if destination is None:
        destination = Path(wrapper.original_path)

    # Ensure destination directory exists
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Rebuild original content
    if wrapper.original_frontmatter:
        yaml_str = yaml.dump(
            wrapper.original_frontmatter,
            default_flow_style=False,
            allow_unicode=True,
        )
        content = f"---\n{yaml_str.rstrip()}\n---\n\n{wrapper.original_content}"
    else:
        content = wrapper.original_content

    # Write restored file
    destination.write_text(content, encoding="utf-8")

    # Remove wrapper file
    wrapper_path.unlink()

    return destination
