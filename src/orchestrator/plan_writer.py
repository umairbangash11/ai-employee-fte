"""Runtime Plan Writer — generates Needs_Action/plans/*.md files.

Called by brain.py's _route_reply_needed() immediately after
write_execution_plan() and before the email is moved. Produces
a human-readable, actionable triage plan in the vault.

Constitution compliance:
- Principle I:  Pure filesystem write — no external calls.
- Principle II: Writes to Needs_Action/plans/ (canonical location).
- Principle IV: Called AFTER write_execution_plan(), BEFORE shutil.move().
- Principle V:  OSError caught; returns None without halting triage flow.
- Principle VI: requires_approval is always true — no external action.
"""

import re
from datetime import datetime
from pathlib import Path


def _safe_slug(subject: str) -> str:
    """Sanitise an email subject into a filename-safe slug.

    Rules:
    - Lowercase
    - Replace non-alphanumeric/non-hyphen characters with hyphens
    - Collapse multiple consecutive hyphens into one
    - Strip leading/trailing hyphens
    - Truncate to 40 characters
    """
    slug = subject.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:40].rstrip("-")


def _deduplicate_path(plans_dir: Path, filename: str) -> Path:
    """Return a unique Path for filename inside plans_dir.

    If plans_dir/filename exists, appends _1, _2, etc. before the suffix
    until a free name is found.
    """
    candidate = plans_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        candidate = plans_dir / new_name
        if not candidate.exists():
            return candidate
        counter += 1


def write_runtime_plan(
    plans_dir: Path,
    source_filename: str,
    email_meta: dict,
    classification: dict,
) -> "Path | None":
    """Write a runtime triage plan to plans_dir.

    Parameters
    ----------
    plans_dir       : Absolute path to vault/Needs_Action/plans/
    source_filename : Original email filename (for slug and metadata)
    email_meta      : Keys: sender, subject, source, urgency
    classification  : Keys: needs_reply (bool), reason (str), draft (str|None)

    Returns the Path to the written file, or None if the write failed.
    The write failure is caught silently — the caller's triage flow must
    not be interrupted by a plan write error.
    """
    try:
        plans_dir = Path(plans_dir)
        plans_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
        filename_ts = now.strftime("%Y-%m-%dT%H-%M-%S")

        subject = email_meta.get("subject", "no-subject")
        sender = email_meta.get("sender", "")
        source = email_meta.get("source", "")
        urgency = email_meta.get("urgency", "normal")

        slug = _safe_slug(subject)
        raw_filename = f"{filename_ts}_plan_{slug}.md"
        plan_path = _deduplicate_path(plans_dir, raw_filename)

        needs_reply = classification.get("needs_reply", True)
        reason = classification.get("reason", "")

        # Determine status and action steps
        if needs_reply:
            status = "pending"
            action_steps = (
                "- [ ] Review the AI-generated draft reply in Needs_Action/drafts/\n"
                "- [ ] Edit the draft as needed\n"
                "- [ ] Approve by moving to Approved/email/ to authorise sending"
            )
        else:
            status = "error"
            action_steps = (
                "- [ ] Human review required \u2014 automated classification failed\n"
                "- [ ] Inspect the source email and determine required action manually"
            )

        content = (
            f"---\n"
            f"type: runtime_plan\n"
            f"status: {status}\n"
            f'created_at: "{timestamp}"\n'
            f'source_file: "{source_filename}"\n'
            f"requires_approval: true\n"
            f'email_sender: "{sender}"\n'
            f'email_subject: "{subject}"\n'
            f"---\n"
            f"\n"
            f"# Triage Plan: {subject}\n"
            f"\n"
            f"## Objective\n"
            f"\n"
            f"Review and action the incoming email from {sender or 'unknown sender'} "
            f"that requires a reply.\n"
            f"\n"
            f"## Source Context\n"
            f"\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| Sender | {sender} |\n"
            f"| Subject | {subject} |\n"
            f"| Source | {source} |\n"
            f"| Urgency | {urgency} |\n"
            f"| Classification reason | {reason} |\n"
            f"\n"
            f"## Action Steps\n"
            f"\n"
            f"{action_steps}\n"
            f"\n"
            f"## Approval Requirement\n"
            f"\n"
            f"> **Human approval required before any reply is sent.**\n"
            f"> This plan was generated automatically. No external action has been taken.\n"
            f"> Review the draft reply in `Needs_Action/drafts/` and move it to\n"
            f"> `Approved/email/` to authorise sending (Constitution Principle VI).\n"
            f"\n"
            f"## Status\n"
            f"\n"
            f"pending \u2014 Awaiting human review and approval.\n"
        )

        plan_path.write_text(content, encoding="utf-8")
        return plan_path

    except OSError:
        return None
