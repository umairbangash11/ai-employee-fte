"""Logic Orchestrator — Watchdog-based Inbox monitor with AI triage.

Watches vault/Inbox/ for new Markdown files (e.g. captured emails from
Gmail Sentinel). Uses the OpenAI API (gpt-4o) with an 'Assistant'
persona to classify whether an email requires a reply. If so, moves
the email to Needs_Action/drafts/ and generates a draft reply alongside it.

Constitution compliance:
- Principle I:  External API (OpenAI) used for AI inference only.
- Principle II: Routes to canonical Needs_Action/drafts/ subdirectory.
- Principle IV: Writes execution plan to Approved/ before every file move.
- Principle V:  Ralph Wiggum retry loop (3 attempts) on failures.
- Principle VI: Draft replies are LOCAL only. No sending without
                Human-in-the-Loop via /Approved.

HITL Approval Integration (Phase 3):
------------------------------------
For LinkedIn posts and other external actions, use the HITL approval system
instead of direct execution. Example integration:

    from hitl_approval.writer import request_linkedin_post_approval

    # When orchestrator decides to publish a LinkedIn post:
    approval_path = request_linkedin_post_approval(
        post_content="Post content here...",
        source_task_path="Needs_Action/tasks/weekly-update.md",
        reasoning="Weekly engagement post based on task requirements",
        vault_path=vault_path,
    )
    # File created in /Pending_Approval/linkedin/
    # Human moves to /Approved/linkedin/ to authorize execution

See src/hitl_approval/writer.py for full API documentation.
"""

import os
import shutil
import sys
import time
import re
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from sentinel.logger import write_log_entry
from sentinel.mover import deduplicate_filename
from sentinel.planner import write_execution_plan

# Feature 015 — resilience integration (T083, T085, T086, T088, T089).
from resilience import (
    CircuitBreaker,
    CircuitOpenError,
    ExitCode,
    HealthManager,
    ResilienceError,
    ralph_wiggum_loop,
    route_to_failed_queue,
)
from resilience.exceptions import DataMalformedError, InternalError, TransientNetworkError

ORCHESTRATOR_SUBSYSTEM = "orchestrator"
OPENAI_CIRCUIT_NAME = "openai_api"
DEFAULT_STATE_DIR = Path(".watcher-state")


def create_orchestrator_health_manager(
    state_dir: Path = DEFAULT_STATE_DIR,
) -> HealthManager:
    """Factory for the orchestrator's HealthManager (T085)."""
    return HealthManager(subsystem=ORCHESTRATOR_SUBSYSTEM, state_dir=state_dir)


def create_openai_circuit_breaker(name: str = OPENAI_CIRCUIT_NAME) -> CircuitBreaker:
    """Factory for the OpenAI API CircuitBreaker (T086)."""
    return CircuitBreaker(name=name)


def _translate_orchestrator_error(error: Exception) -> ResilienceError:
    """Map brain.py exceptions to the resilience hierarchy."""
    if isinstance(error, ResilienceError):
        return error
    error_name = type(error).__name__
    if error_name in ("APIError", "APIConnectionError", "APITimeoutError", "RateLimitError"):
        return TransientNetworkError(
            f"OpenAI API error: {error}",
            context={"original_error": str(error), "error_type": error_name},
        )
    if isinstance(error, (ValueError, KeyError)):
        return DataMalformedError(
            f"Malformed classification response: {error}",
            context={"original_error": str(error)},
        )
    return InternalError(
        f"Unexpected orchestrator error: {error}",
        context={"original_error": str(error), "error_type": error_name},
    )


ASSISTANT_SYSTEM_PROMPT = """\
You are the Assistant persona for a Digital FTE (Full-Time Employee) system.
Your role is to triage incoming emails and determine whether they require
a reply from the user.

You will receive the full content of a captured email in Markdown format
(with YAML frontmatter). Analyze it and respond with EXACTLY this JSON
structure (no markdown fencing, no extra text):

{"needs_reply": true/false, "reason": "brief explanation", "draft": "draft reply text or null"}

Rules for classification:
- needs_reply: true if the email asks a question, requests action,
  expects a response, or is from a person (not automated/marketing).
- needs_reply: false for newsletters, automated notifications,
  marketing emails, receipts, shipping updates, or no-reply senders.
- When needs_reply is true, generate a concise, professional draft reply.
- When needs_reply is false, set draft to null.
- Keep draft replies brief (2-5 sentences), professional, and helpful.
- Never include sensitive information or commitments in drafts.
- The draft is a SUGGESTION for human review, not a final message.
"""


def load_config() -> dict:
    """Load orchestrator configuration from .env."""
    load_dotenv()
    return {
        "vault_path": os.getenv("VAULT_PATH", "."),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-5o"),
        "poll_interval": float(os.getenv("BRAIN_POLL_INTERVAL", "1.0")),
    }


def parse_email_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields from a Markdown email file."""
    result = {
        "source": "",
        "sender": "",
        "subject": "",
        "urgency": "normal",
    }

    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return result

    fm_text = fm_match.group(1)
    for line in fm_text.splitlines():
        line = line.strip()
        if line.startswith("source:"):
            result["source"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("sender:"):
            result["sender"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("subject:"):
            result["subject"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("urgency:"):
            result["urgency"] = line.split(":", 1)[1].strip().strip('"')

    return result


def classify_email(
    client: OpenAI, model: str, email_content: str
) -> dict:
    """Call OpenAI API to classify an email and optionally generate a draft reply.

    Returns dict with keys: needs_reply (bool), reason (str), draft (str|None).
    """
    response = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze this captured email and classify it:\n\n"
                    f"{email_content}"
                ),
            },
        ],
    )

    response_text = response.choices[0].message.content.strip()

    import json

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response if wrapped in markdown
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            return {
                "needs_reply": False,
                "reason": f"Failed to parse LLM response: {response_text[:200]}",
                "draft": None,
            }

    return {
        "needs_reply": bool(result.get("needs_reply", False)),
        "reason": str(result.get("reason", "")),
        "draft": result.get("draft"),
    }


def write_draft_reply(
    drafts_dir: Path,
    original_filename: str,
    email_meta: dict,
    classification: dict,
) -> Path:
    """Write a draft reply as an Obsidian-compatible Markdown file.

    Placed in Needs_Action/drafts/ for human review and approval.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    filename_ts = now.strftime("%Y-%m-%dT%H-%M-%S")
    stem = Path(original_filename).stem
    draft_filename = f"{filename_ts}_draft-reply_{stem}.md"
    draft_filename = deduplicate_filename(drafts_dir, draft_filename)
    draft_path = drafts_dir / draft_filename

    content = (
        f"---\n"
        f"type: draft_reply\n"
        f'created_at: "{timestamp}"\n'
        f'in_reply_to: "{original_filename}"\n'
        f'sender: "{email_meta.get("sender", "Unknown")}"\n'
        f'subject: "Re: {email_meta.get("subject", "")}"\n'
        f"status: pending_review\n"
        f"tags: [draft, reply, needs-approval]\n"
        f"---\n"
        f"\n"
        f"# Draft Reply: Re: {email_meta.get('subject', '')}\n"
        f"\n"
        f"**To**: {email_meta.get('sender', 'Unknown')}\n"
        f"**In reply to**: [[{original_filename}]]\n"
        f"**Classification reason**: {classification.get('reason', '')}\n"
        f"\n"
        f"---\n"
        f"\n"
        f"{classification.get('draft', '(no draft generated)')}\n"
        f"\n"
        f"---\n"
        f"\n"
        f"> **This is an AI-generated draft. Review, edit, and approve "
        f"before sending.**\n"
        f"> To send, move the approved version to `/Approved/email/` "
        f"per Constitution Principle VI.\n"
    )

    draft_path.write_text(content, encoding="utf-8")
    return draft_path


class InboxTriageHandler(FileSystemEventHandler):
    """Watchdog handler that triages new Markdown files in Inbox/.

    Monitors all subdirectories of Inbox/ (e.g. Inbox/email/).
    When a .md file appears, reads it, calls OpenAI for classification,
    and if reply-needed, moves it to Needs_Action/drafts/ with a
    draft reply file.
    """

    def __init__(
        self,
        vault_path: Path,
        client: OpenAI,
        model: str,
        health: HealthManager = None,
        circuit: CircuitBreaker = None,
    ):
        super().__init__()
        self.vault_path = Path(vault_path).resolve()
        self.inbox_dir = self.vault_path / "Inbox"
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.drafts_dir = self.needs_action_dir / "drafts"
        self.approved_dir = self.vault_path / "Approved"
        self.logs_dir = self.vault_path / "Logs"
        self.client = client
        self.model = model
        # T085/T086 — resilience context constructed at startup, persisted across events.
        self.health = health or create_orchestrator_health_manager()
        self.circuit = circuit or create_openai_circuit_breaker()

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        if filepath.suffix.lower() != ".md":
            return

        # Wait for file to be fully written
        from sentinel.watcher import wait_for_stability

        if not wait_for_stability(filepath):
            return

        if not filepath.exists():
            return

        self._process_email(filepath)

    def _process_email(self, filepath: Path) -> None:
        """Triage a single email file using the shared Ralph Wiggum Loop (T084)."""
        filename = filepath.name
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{now_str}] Processing: {filename}")

        try:
            content = filepath.read_text(encoding="utf-8")
            email_meta = parse_email_frontmatter(content)
        except Exception as e:
            # Non-retryable read/parse failure — log and skip.
            translated = _translate_orchestrator_error(e)
            self.health.record_failure(translated.message)
            self.health.heartbeat()
            write_log_entry(
                logs_dir=self.logs_dir, action_type="error",
                source_path=filepath, dest_path=self.drafts_dir,
                file_size=(filepath.stat().st_size if filepath.exists() else 0),
                outcome="failure",
                details=f"Pre-classification read failed: {translated.message}",
            )
            print(f"  Error: {translated.message}")
            return

        def primary():
            # Re-read inside the operation so attempt 2 picks up any
            # mid-flight edits (matches the legacy attempt-2 semantics).
            fresh_content = filepath.read_text(encoding="utf-8")
            return self.circuit.execute(
                lambda: classify_email(self.client, self.model, fresh_content)
            )

        def simplified_fallback():
            # Attempt 3: skip OpenAI entirely, route for human review (legacy semantics).
            return {
                "needs_reply": True,
                "reason": (
                    "Fallback: classification failed after retries, "
                    "routing for human review."
                ),
                "draft": None,
            }

        try:
            classification = ralph_wiggum_loop(
                operation=primary,
                simplify_fn=simplified_fallback,
            )
        except CircuitOpenError as exc:
            # Circuit is open — fast-fail and route the email so a human can
            # retry once OpenAI recovers (T088).
            self.health.record_failure(exc.message)
            self.health.set_circuit_state(self.circuit.state)
            self.health.heartbeat()
            try:
                route_to_failed_queue(
                    source_item=filepath, subsystem=ORCHESTRATOR_SUBSYSTEM,
                    failure_reason=exc.message, retry_attempts=3,
                    recovery_action=(
                        "OpenAI API circuit is open. Wait for recovery then "
                        "use `sentinel-recover retry` to re-queue."
                    ),
                    vault_path=self.vault_path, error_code=exc.error_code,
                )
            except Exception as re:
                print(f"  Routing to failed queue failed: {re}")
            print(f"  Error: {exc.message}")
            return
        except Exception as e:
            translated = _translate_orchestrator_error(e)
            self.health.record_failure(translated.message)
            self.health.set_circuit_state(self.circuit.state)
            self.health.heartbeat()
            write_log_entry(
                logs_dir=self.logs_dir, action_type="error",
                source_path=filepath, dest_path=self.drafts_dir,
                file_size=(filepath.stat().st_size if filepath.exists() else 0),
                outcome="failure",
                details=f"Triage failed after 3 attempts: {translated.message}",
            )
            # T088: route failed emails to Needs_Action/email/failed/ for recovery.
            try:
                if filepath.exists():
                    route_to_failed_queue(
                        source_item=filepath, subsystem=ORCHESTRATOR_SUBSYSTEM,
                        failure_reason=translated.message, retry_attempts=3,
                        recovery_action=(
                            "Inspect email, fix classification issue or retry "
                            "with `sentinel-recover retry`."
                        ),
                        vault_path=self.vault_path, error_code=translated.error_code,
                    )
            except Exception as re:
                print(f"  Routing to failed queue failed: {re}")
            print(f"  Error: Triage failed after 3 attempts. See Logs/.")
            return

        # Classification succeeded (possibly via fallback).
        self.health.record_success()
        self.health.set_circuit_state(self.circuit.state)
        self.health.heartbeat()

        if classification["needs_reply"]:
            self._route_reply_needed(filepath, filename, email_meta, classification)
        else:
            print(f"  No reply needed: {classification['reason']}")
            write_log_entry(
                logs_dir=self.logs_dir, action_type="email_triaged",
                source_path=filepath, dest_path=filepath,
                file_size=filepath.stat().st_size, outcome="success",
                details=f"No reply needed. Reason: {classification['reason']}",
            )
        return

    def _route_reply_needed(
        self,
        filepath: Path,
        filename: str,
        email_meta: dict,
        classification: dict,
    ) -> None:
        """Move email to Needs_Action/drafts/ and write draft reply."""
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        file_size = filepath.stat().st_size

        # Resolve destination filename
        resolved_name = deduplicate_filename(self.drafts_dir, filename)
        dest_path = self.drafts_dir / resolved_name

        # Constitution Principle IV: write plan before action
        write_execution_plan(
            approved_dir=self.approved_dir,
            action="triage_move",
            source=filepath,
            destination=dest_path,
            rollback=f"Move `{dest_path}` back to `{filepath}`.",
            expected_outcome=(
                f"Email moved to Needs_Action/drafts/ as '{resolved_name}'; "
                f"draft reply generated alongside it."
            ),
        )

        # Move the email
        shutil.move(str(filepath), str(dest_path))

        # Generate draft reply
        draft_path = write_draft_reply(
            drafts_dir=self.drafts_dir,
            original_filename=resolved_name,
            email_meta=email_meta,
            classification=classification,
        )

        # Log the action
        write_log_entry(
            logs_dir=self.logs_dir,
            action_type="email_triaged",
            source_path=filepath,
            dest_path=dest_path,
            file_size=file_size,
            outcome="success",
            details=(
                f"Reply needed. Reason: {classification['reason']}. "
                f"Draft: {draft_path.name}"
            ),
        )

        print(
            f"  Reply needed: {classification['reason']}\n"
            f"  Moved to: {dest_path.relative_to(self.vault_path)}\n"
            f"  Draft: {draft_path.relative_to(self.vault_path)}"
        )


def start_brain(
    vault_path: str = ".",
    api_key: str = "",
    model: str = "gpt-4o",
    poll_interval: float = 1.0,
) -> None:
    """Start the Logic Orchestrator watching Inbox/ for new Markdown files."""
    vault = Path(vault_path).resolve()

    # Validate vault structure
    from sentinel.vault import validate_vault

    if not validate_vault(str(vault)):
        raise ValueError(
            f"Vault not initialized at '{vault}'. "
            f"Run 'python -m sentinel init' first."
        )

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Ensure drafts directory exists
    drafts_dir = vault / "Needs_Action" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    inbox_dir = vault / "Inbox"
    handler = InboxTriageHandler(vault, client, model)
    observer = Observer()
    observer.schedule(handler, str(inbox_dir), recursive=True)
    observer.start()

    print("Logic Orchestrator (Brain) starting...")
    print(f"  Vault: {vault}")
    print(f"  Watching: {inbox_dir} (recursive)")
    print(f"  Model: {model}")
    print(f"  Drafts: {drafts_dir}")
    print(f"  Press Ctrl+C to stop.\n")

    write_log_entry(
        logs_dir=vault / "Logs",
        action_type="brain_start",
        source_path=inbox_dir,
        dest_path=drafts_dir,
        file_size=0,
        outcome="success",
        details="Logic Orchestrator started.",
    )

    try:
        while True:
            if not inbox_dir.is_dir():
                print(
                    f"\nError: Inbox directory '{inbox_dir}' no longer exists.",
                    flush=True,
                )
                write_log_entry(
                    logs_dir=vault / "Logs",
                    action_type="error",
                    source_path=inbox_dir,
                    dest_path=inbox_dir,
                    file_size=0,
                    outcome="failure",
                    details="Inbox directory deleted while Brain was running.",
                )
                observer.stop()
                observer.join()
                raise SystemExit(ExitCode.CONFIGURATION.value)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        observer.stop()
        write_log_entry(
            logs_dir=vault / "Logs",
            action_type="brain_stop",
            source_path=inbox_dir,
            dest_path=drafts_dir,
            file_size=0,
            outcome="success",
            details="Logic Orchestrator stopped.",
        )
        print("\nLogic Orchestrator stopped.")
    observer.join()


def main():
    """Entry point for brain command."""
    config = load_config()

    if not config["api_key"]:
        print(
            "Error: OPENAI_API_KEY not set in .env",
            file=sys.stderr,
        )
        raise SystemExit(ExitCode.CONFIGURATION.value)

    start_brain(
        vault_path=config["vault_path"],
        api_key=config["api_key"],
        model=config["model"],
        poll_interval=config["poll_interval"],
    )


if __name__ == "__main__":
    main()
