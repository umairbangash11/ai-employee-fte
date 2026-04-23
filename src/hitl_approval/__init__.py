"""Human-in-the-Loop Approval System for vault-based action approval.

This package implements a file-based approval workflow for sensitive external
actions (email sends, LinkedIn posts). Instead of executing actions directly,
the system creates approval request files. Human operators approve by moving
files between directories.

Constitution Compliance:
- Principle II: Uses /Approved/, extends with /Pending_Approval/, /Rejected/
- Principle IV: No execution without /Approved/ file
- Principle VI: Enforces HITL for all external actions
"""

__version__ = "0.1.0"

# Resilience module integration (Feature 015, T095)
from pathlib import Path

from resilience import (
    ExitCode,
    HealthManager,
    ResilienceError,
    exit_with_code,
    ralph_wiggum_loop,
    route_to_failed_queue,
)


def create_hitl_health_manager(
    state_dir: Path = Path(".watcher-state"),
) -> HealthManager:
    """Factory for the hitl_approval subsystem's HealthManager (T096)."""
    return HealthManager(
        subsystem="hitl_approval",
        state_dir=state_dir,
        version=__version__,
    )


def route_invalid_approval_to_failed(
    source_item: Path,
    vault_path: Path,
    failure_reason: str,
    retry_attempts: int = 3,
    error_code: str = "ERR_HITL_APPROVAL_INVALID",
) -> Path:
    """Route an invalid approval to `Needs_Action/approvals/invalid/` (T097)."""
    return route_to_failed_queue(
        source_item=source_item,
        subsystem="hitl_approval",
        failure_reason=failure_reason,
        retry_attempts=retry_attempts,
        recovery_action=(
            "Inspect the approval frontmatter. Fix required fields (type, "
            "action_type, status, created_at, target, source, rollback_strategy) "
            "and re-submit, or delete the wrapper if obsolete."
        ),
        vault_path=vault_path,
        error_code=error_code,
    )
