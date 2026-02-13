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
        """Triage a single email file with Ralph Wiggum retry."""
        filename = filepath.name
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{now_str}] Processing: {filename}")

        last_error = None
        for attempt in range(1, 4):
            try:
                content = filepath.read_text(encoding="utf-8")
                email_meta = parse_email_frontmatter(content)

                if attempt == 1:
                    # Attempt 1: classify as planned
                    classification = classify_email(
                        self.client, self.model, content
                    )
                elif attempt == 2:
                    # Attempt 2: re-read content, retry
                    content = filepath.read_text(encoding="utf-8")
                    classification = classify_email(
                        self.client, self.model, content
                    )
                else:
                    # Attempt 3: simplify — assume needs reply
                    classification = {
                        "needs_reply": True,
                        "reason": "Fallback: classification failed, "
                        "routing for human review.",
                        "draft": None,
                    }

                if classification["needs_reply"]:
                    self._route_reply_needed(
                        filepath, filename, email_meta, classification
                    )
                else:
                    print(
                        f"  No reply needed: {classification['reason']}"
                    )
                    write_log_entry(
                        logs_dir=self.logs_dir,
                        action_type="email_triaged",
                        source_path=filepath,
                        dest_path=filepath,
                        file_size=filepath.stat().st_size,
                        outcome="success",
                        details=(
                            f"No reply needed. "
                            f"Reason: {classification['reason']}"
                        ),
                    )

                return

            except Exception as e:
                last_error = e
                if attempt < 3:
                    print(
                        f"  Retry {attempt}/3 failed: {e}"
                    )
                    time.sleep(1.0 * attempt)
                    continue

                # All attempts exhausted
                write_log_entry(
                    logs_dir=self.logs_dir,
                    action_type="error",
                    source_path=filepath,
                    dest_path=self.drafts_dir,
                    file_size=(
                        filepath.stat().st_size if filepath.exists() else 0
                    ),
                    outcome="failure",
                    details=(
                        f"Triage failed after 3 attempts: {last_error}"
                    ),
                )
                print(
                    f"  Error: Triage failed after 3 attempts. "
                    f"See Logs/."
                )

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
                raise SystemExit(2)
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
        raise SystemExit(1)

    start_brain(
        vault_path=config["vault_path"],
        api_key=config["api_key"],
        model=config["model"],
        poll_interval=config["poll_interval"],
    )


if __name__ == "__main__":
    main()
