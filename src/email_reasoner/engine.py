"""Reasoning engine for Email Reasoning Layer.

Orchestrates the full pipeline: scan → filter → classify → write.

SAFETY GUARANTEE (US4):
This engine performs READ-ONLY operations on source email files.
It does NOT modify, move, or delete any files in /Inbox/email/.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import ReasonerConfig
from .models import EmailFile, ClassificationResult
from .scanner import scan_and_parse_inbox
from .state import load_state, save_state, is_processed, mark_processed
from .classifier import classify_email
from .writer import write_task_file, write_plan_file

# HITL Approval imports (Phase 3)
try:
    from hitl_approval.models import ApprovalRequest
    from hitl_approval.writer import create_approval_request
    from hitl_approval.exceptions import DuplicateApprovalError
    HITL_AVAILABLE = True
except ImportError:
    HITL_AVAILABLE = False


logger = logging.getLogger(__name__)


# =============================================================================
# T049-T053: ReasonerEngine class
# =============================================================================


class ReasonerEngine:
    """Main orchestration engine for email reasoning.

    Coordinates scanning, classification, and task/plan generation.

    SAFETY GUARANTEE (Constitution Principle IV):
    - This engine is READ-ONLY on source files in /Inbox/email/
    - Original email files are NEVER modified, moved, or deleted
    - Only writes to /Needs_Action/tasks/, /Plans/, and /Logs/
    """

    def __init__(self, config: ReasonerConfig):
        """Initialize the engine with configuration.

        Args:
            config: ReasonerConfig with paths and options.
        """
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging based on verbose setting."""
        level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def run(self) -> dict:
        """Run the full reasoning pipeline.

        Pipeline:
        1. Load state (for deduplication)
        2. Scan inbox for email files
        3. Filter out already-processed emails
        4. Classify each email
        5. Write task/plan files for actionable emails
        6. Update state

        Returns:
            Summary dict with counts and results.
        """
        logger.info("Starting email reasoning pipeline")
        logger.info(f"Vault path: {self.config.vault_path}")
        logger.info(f"Dry run: {self.config.dry_run}")

        # Track results
        results = {
            "scanned": 0,
            "skipped_processed": 0,
            "classified": 0,
            "actionable": 0,
            "tasks_created": 0,
            "plans_created": 0,
            "errors": [],
        }

        # Step 1: Load state for deduplication (US5)
        state = load_state(self.config.state_path)
        logger.info(f"Loaded state with {len(state.processed)} processed emails")

        # Step 2: Scan inbox
        inbox_path = self.config.inbox_email_path
        if not inbox_path.exists():
            logger.warning(f"Inbox path does not exist: {inbox_path}")
            return results

        emails = scan_and_parse_inbox(inbox_path)
        results["scanned"] = len(emails)
        logger.info(f"Found {len(emails)} email files")

        # Apply limit if specified
        if self.config.limit and len(emails) > self.config.limit:
            emails = emails[: self.config.limit]
            logger.info(f"Limited to {self.config.limit} emails")

        # Step 3-5: Process each email
        for email in emails:
            try:
                self._process_email(email, state, results)
            except Exception as e:
                logger.error(f"Error processing {email.message_id}: {e}")
                results["errors"].append({
                    "message_id": email.message_id,
                    "error": str(e),
                })

        # Step 6: Save state (only if not dry-run)
        if not self.config.dry_run:
            save_state(state, self.config.state_path)
            logger.info("Saved updated state")

        # Summary
        logger.info(
            f"Pipeline complete: {results['scanned']} scanned, "
            f"{results['classified']} classified, "
            f"{results['actionable']} actionable, "
            f"{results['tasks_created']} tasks created, "
            f"{results['plans_created']} plans created"
        )

        return results

    def _process_email(
        self,
        email: EmailFile,
        state,
        results: dict,
    ) -> None:
        """Process a single email through the pipeline.

        Args:
            email: EmailFile to process.
            state: ReasonerState for deduplication.
            results: Results dict to update.
        """
        # Step 3: Check if already processed (US5)
        if is_processed(state, email.message_id):
            logger.debug(f"Skipping already processed: {email.message_id}")
            results["skipped_processed"] += 1
            return

        # Step 4: Classify
        logger.info(f"Classifying: {email.subject[:50]}...")
        result = classify_email(
            email,
            api_key=self.config.openai_api_key,
            confidence_threshold=self.config.confidence_threshold,
        )
        results["classified"] += 1

        # Log classification (T053)
        self._log_classification(email, result)

        # Step 5: Handle based on classification
        if result.creates_task:
            results["actionable"] += 1

            if self.config.dry_run:
                # T096-T097: Dry-run mode
                logger.info(
                    f"[DRY-RUN] Would create task for: {email.subject}"
                )
                if self._requires_approval(result):
                    logger.info(
                        f"[DRY-RUN] Would create approval request (HITL)"
                    )
                if result.creates_plan:
                    logger.info(
                        f"[DRY-RUN] Would create plan with {len(result.steps or [])} steps"
                    )
            else:
                # HITL Approval Check (Phase 3)
                # If action requires external execution, create approval request
                # instead of task file (Constitution Principle VI)
                if self._requires_approval(result):
                    approval_path = self._create_approval_request(email, result)
                    if approval_path:
                        results["tasks_created"] += 1  # Count as task for stats
                        # Track approval requests separately
                        if "approvals_created" not in results:
                            results["approvals_created"] = 0
                        results["approvals_created"] += 1
                        # Mark as processed
                        mark_processed(
                            state, email.message_id, result.classification,
                            str(approval_path.relative_to(self.config.vault_path))
                        )
                        save_state(state, self.config.state_path)
                        return  # Don't create task file, approval request is created

                # Write task file (non-approval actions)
                timestamp = datetime.utcnow()
                task_path = write_task_file(
                    email, result, self.config.vault_path, timestamp
                )
                results["tasks_created"] += 1

                # Get relative path for state and plan linking
                task_relative = str(task_path.relative_to(self.config.vault_path))

                # Write plan file if multi-step (US3)
                if result.creates_plan:
                    plan_path = write_plan_file(
                        email, result, task_relative, self.config.vault_path, timestamp
                    )
                    results["plans_created"] += 1
                    logger.info(f"Created plan with {len(result.steps or [])} steps")

                # Mark as processed (US5)
                mark_processed(state, email.message_id, result.classification, task_relative)
                # Save state after each email (T081)
                save_state(state, self.config.state_path)

        else:
            # T059-T060: Skip non-actionable, log reason
            logger.info(
                f"Skipped (not actionable): {email.subject[:30]}... "
                f"[{result.classification}]"
            )
            if not self.config.dry_run:
                # Still mark as processed to prevent reprocessing
                mark_processed(state, email.message_id, result.classification, None)
                save_state(state, self.config.state_path)

    def _requires_approval(self, result: ClassificationResult) -> bool:
        """Check if classification result requires HITL approval.

        Actions requiring approval (Constitution Principle VI):
        - reply, respond, send, forward in action text
        - Single external action (not multi-step internal tasks)
        - High or critical priority

        Args:
            result: Classification result to check

        Returns:
            True if approval required, False otherwise
        """
        if not HITL_AVAILABLE:
            return False

        if not result.action:
            return False

        # Check for external action keywords
        action_lower = result.action.lower()
        external_keywords = ["reply", "respond", "send", "forward", "email"]
        has_external_action = any(kw in action_lower for kw in external_keywords)

        # Multi-step tasks are internal planning, not direct execution
        is_single_action = not result.is_multi_step

        # Only route high priority external actions to approval
        is_high_priority = result.priority in ("high", "critical")

        return has_external_action and is_single_action and is_high_priority

    def _detect_action_type(self, result: ClassificationResult) -> str:
        """Detect action type from classification result.

        Args:
            result: Classification result

        Returns:
            Action type string: send_email_reply or send_email_followup
        """
        if not result.action:
            return "send_email_reply"

        action_lower = result.action.lower()

        if "follow" in action_lower or "followup" in action_lower:
            return "send_email_followup"
        else:
            return "send_email_reply"

    def _create_approval_request(
        self,
        email: EmailFile,
        result: ClassificationResult,
    ) -> Optional[Path]:
        """Create approval request file instead of executing action.

        Args:
            email: Source email
            result: Classification result

        Returns:
            Path to created approval file, or None if failed
        """
        if not HITL_AVAILABLE:
            logger.warning("HITL approval not available, skipping approval request")
            return None

        action_type = self._detect_action_type(result)

        try:
            approval = ApprovalRequest(
                action_type=action_type,
                target_recipient=email.sender,
                target_subject=f"Re: {email.subject}",
                content=result.action or "",
                source_path=str(email.file_path),
                source_type="email",
                reasoning=result.reasoning,
                expected_outcome=result.action or "Email reply sent",
                rollback_strategy="Email cannot be unsent once sent",
                created_by="email_reasoner",
                tags=["email", result.classification, result.priority or "medium"],
            )
            approval_path = create_approval_request(approval, self.config.vault_path)
            logger.info(f"Created approval request: {approval_path.name}")
            return approval_path
        except DuplicateApprovalError as e:
            logger.warning(f"Duplicate approval request: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            return None

    def _log_classification(
        self,
        email: EmailFile,
        result: ClassificationResult,
    ) -> None:
        """Log classification decision for auditability.

        Args:
            email: Classified email.
            result: Classification result.
        """
        if self.config.verbose:
            logger.info(
                f"Classification: {result.classification} "
                f"(confidence: {result.confidence:.2f})"
            )
            logger.info(f"Reasoning: {result.reasoning}")
            if result.action:
                logger.info(f"Action: {result.action}")
            if result.priority:
                logger.info(f"Priority: {result.priority}")
            if result.is_multi_step:
                logger.info(f"Steps: {result.steps}")


# =============================================================================
# T099-T102: Logging to /Logs/ (Phase 9)
# =============================================================================


def log_to_file(
    email: EmailFile,
    result: ClassificationResult,
    action_taken: str,
    logs_path: Path,
) -> None:
    """Log classification decision to /Logs/ directory.

    Uses JSON lines format for machine-readable logs.

    Args:
        email: Classified email.
        result: Classification result.
        action_taken: What action was taken (e.g., "task_created").
        logs_path: Path to /Logs/ directory.
    """
    # T101: Create directory if missing
    logs_path.mkdir(parents=True, exist_ok=True)

    # Generate log filename
    log_file = logs_path / f"reasoner-{datetime.utcnow().strftime('%Y%m%d')}.log"

    # Build log entry (T100, T102)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message_id": email.message_id,
        "subject": email.subject,
        "sender": email.sender,
        "classification": result.classification,
        "confidence": result.confidence,
        "action_taken": action_taken,
    }

    # Append to log file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
