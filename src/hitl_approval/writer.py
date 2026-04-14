"""Approval request file writer for HITL system."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import HITLConfig
from .exceptions import DuplicateApprovalError
from .logger import ApprovalLogger
from .models import ApprovalRequest, ApprovalState
from .state import add_hash, is_duplicate, load_approval_state, save_approval_state
from .utils import (
    ensure_approval_dirs,
    generate_approval_filename,
    generate_slug,
    get_action_type_dir,
)


def compute_approval_hash(request: ApprovalRequest) -> str:
    """Compute SHA256 hash for approval request deduplication.

    Hash is computed from: action_type + target_recipient + subject + source_path

    Args:
        request: ApprovalRequest to hash

    Returns:
        SHA256 hex digest
    """
    data = f"{request.action_type}|{request.target_recipient}|{request.target_subject}|{request.source_path}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_frontmatter(request: ApprovalRequest, timestamp: datetime) -> str:
    """Generate YAML frontmatter for approval request.

    Args:
        request: ApprovalRequest to serialize
        timestamp: Creation timestamp

    Returns:
        YAML frontmatter string (including --- delimiters)
    """
    expires_at = ""
    if request.expires_at:
        expires_at = f'\nexpires_at: "{request.expires_at.isoformat()}Z"'

    tags_str = ", ".join(request.tags) if request.tags else "approval"

    # Determine target structure based on action type
    if request.action_type == "publish_linkedin_post":
        target_block = f"""target:
  platform: linkedin
  post_type: text"""
    else:
        target_block = f"""target:
  recipient: "{request.target_recipient}"
  subject: "{request.target_subject}\""""

    frontmatter = f"""---
type: approval_request
action_type: {request.action_type}
status: pending
created_at: "{timestamp.isoformat()}Z"
created_by: {request.created_by}

{target_block}

source:
  type: {request.source_type}
  path: "[[{request.source_path}]]"

expected_outcome: "{request.expected_outcome}"
rollback_strategy: "{request.rollback_strategy}"

tags: [{tags_str}]{expires_at}
---"""
    return frontmatter


def generate_body(request: ApprovalRequest) -> str:
    """Generate markdown body for approval request.

    Args:
        request: ApprovalRequest to serialize

    Returns:
        Markdown body string
    """
    # Determine content preview format
    if request.action_type == "publish_linkedin_post":
        content_preview = f"""**Post Type**: text
**Content**:

{request.content}"""
        action_dir = "linkedin"
    else:
        content_preview = f"""**To**: {request.target_recipient}
**Subject**: {request.target_subject}

---

{request.content}"""
        action_dir = "email"

    # Determine impact level
    impact = "medium"
    if "urgent" in request.tags or "high" in request.tags:
        impact = "high"
    elif "low" in request.tags:
        impact = "low"

    # Determine reversibility
    reversible = "no"
    if "delete" in request.rollback_strategy.lower():
        reversible = "yes (manual)"

    body = f"""# Action: {request.target_subject}

## Summary

{request.reasoning}

## Content Preview

{content_preview}

---

## Context

- Source: [[{request.source_path}]]
- Reasoning: {request.reasoning}

## Risk Assessment

- Impact: {impact}
- Reversible: {reversible}
- Rollback: {request.rollback_strategy}

## Approval Instructions

To approve: Move this file to `/Approved/{action_dir}/`
To reject: Move this file to `/Rejected/{action_dir}/`
"""
    return body


def create_approval_request(
    request: ApprovalRequest,
    vault_path: Path,
    state_path: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
) -> Path:
    """Create approval request file in /Pending_Approval/<type>/.

    This is the main entry point for creating approval requests.
    It handles:
    1. Deduplication check
    2. Directory creation
    3. File writing
    4. State update

    Args:
        request: ApprovalRequest to create
        vault_path: Path to Obsidian vault
        state_path: Optional path to state file (for deduplication)
        timestamp: Optional timestamp (defaults to now)

    Returns:
        Path to created approval file

    Raises:
        DuplicateApprovalError: If identical request already exists
    """
    vault_path = Path(vault_path)
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Set up state path
    if state_path is None:
        state_path = vault_path.parent / ".watcher-state" / "approvals.json"

    # Load state and check for duplicates
    state = load_approval_state(state_path)
    hash_value = compute_approval_hash(request)

    if is_duplicate(state, hash_value):
        raise DuplicateApprovalError(
            f"Approval request already exists for {request.action_type}",
            hash_value=hash_value,
        )

    # Ensure directories exist
    ensure_approval_dirs(vault_path)

    # Generate filename
    slug = generate_slug(request.target_subject)
    filename = generate_approval_filename(request.action_type, slug, timestamp)

    # Determine target directory
    action_dir = get_action_type_dir(request.action_type)
    target_dir = vault_path / "Pending_Approval" / action_dir
    file_path = target_dir / filename

    # Generate content
    frontmatter = generate_frontmatter(request, timestamp)
    body = generate_body(request)
    content = f"{frontmatter}\n\n{body}"

    # Write file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Update state
    add_hash(state, hash_value)
    save_approval_state(state, state_path)

    # Log creation event (T062)
    logs_path = vault_path / "Logs"
    approval_logger = ApprovalLogger(logs_path)
    approval_logger.log_created(
        file_path=str(file_path.relative_to(vault_path)),
        action_type=request.action_type,
        actor=request.created_by,
        target=request.target_recipient,
        subject=request.target_subject,
    )

    return file_path


def request_linkedin_post_approval(
    post_content: str,
    source_task_path: str,
    reasoning: str,
    vault_path: Path,
    state_path: Optional[Path] = None,
) -> Path:
    """Create approval request for LinkedIn post.

    Convenience function for orchestrator integration.

    Args:
        post_content: Content of the LinkedIn post
        source_task_path: Path to task that triggered this post
        reasoning: Why this post is recommended
        vault_path: Path to Obsidian vault
        state_path: Optional path to state file

    Returns:
        Path to created approval file
    """
    request = ApprovalRequest(
        action_type="publish_linkedin_post",
        target_recipient="linkedin",
        target_subject="LinkedIn Post",
        content=post_content,
        source_path=source_task_path,
        source_type="task",
        reasoning=reasoning,
        expected_outcome="LinkedIn post published",
        rollback_strategy="Delete post manually from LinkedIn",
        created_by="orchestrator",
        tags=["linkedin", "post"],
    )
    return create_approval_request(request, vault_path, state_path)
