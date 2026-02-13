"""Gmail Sentinel — Playwright-based Gmail monitoring for Obsidian vaults.

Silver Tier watcher that polls Gmail Web for unread emails and converts
them to Obsidian-compatible Markdown files in the vault's Inbox/email/
or Needs_Action/email/ directories.

Constitution Principle VI: READ-ONLY monitoring. No sending, replying,
or modifying emails. External actions require Human-in-the-Loop via
/Approved.
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


WATCHER_STATE_DIR = ".watcher-state"
GMAIL_STATE_FILE = "gmail.json"
POLL_INTERVAL_DEFAULT = 300  # 5 minutes


def load_config() -> dict:
    """Load Gmail watcher configuration from .env file."""
    load_dotenv()
    return {
        "email": os.getenv("GMAIL_EMAIL", ""),
        "password": os.getenv("GMAIL_PASSWORD", ""),
        "vault_path": os.getenv("VAULT_PATH", "."),
        "poll_interval": int(
            os.getenv("GMAIL_POLL_INTERVAL", str(POLL_INTERVAL_DEFAULT))
        ),
        "headless": os.getenv("GMAIL_HEADLESS", "true").lower() == "true",
    }


def compute_email_hash(sender: str, timestamp: str, subject: str) -> str:
    """Compute deterministic hash for deduplication per WatcherInfrastructure skill.

    Hash = sha256(source + sender + timestamp + subject), truncated to 16 hex chars.
    """
    key = f"gmail|{sender}|{timestamp}|{subject}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def sanitize_filename(text: str, max_length: int = 60) -> str:
    """Sanitize a string for use as a filename component."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return safe[:max_length].strip().replace(" ", "-").lower() or "email"


class GmailWatcher:
    """Playwright-based Gmail inbox monitor.

    Polls Gmail Web for unread emails, extracts metadata and body,
    and writes Obsidian-compatible Markdown files to the vault.
    """

    def __init__(self, config: dict):
        self.config = config
        self.vault_path = Path(config["vault_path"]).resolve()
        self.inbox_dir = self.vault_path / "Inbox" / "email"
        self.needs_action_dir = self.vault_path / "Needs_Action" / "email"
        self.logs_dir = self.vault_path / "Logs"
        self.state_dir = Path(WATCHER_STATE_DIR)
        self.state_file = self.state_dir / GMAIL_STATE_FILE
        self.seen_hashes: set[str] = self._load_state()

    def _load_state(self) -> set[str]:
        """Load previously seen email hashes from .watcher-state/gmail.json."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return set(data)
            except (json.JSONDecodeError, TypeError):
                return set()
        return set()

    def _save_state(self) -> None:
        """Persist seen hashes to disk."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(sorted(self.seen_hashes), indent=2),
            encoding="utf-8",
        )

    def _ensure_dirs(self) -> None:
        """Ensure vault output directories exist."""
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _write_log(
        self, action_type: str, details: str, outcome: str = "success"
    ) -> None:
        """Write a log entry to Logs/ using the sentinel logger."""
        from sentinel.logger import write_log_entry

        write_log_entry(
            logs_dir=self.logs_dir,
            action_type=action_type,
            source_path=Path("gmail://inbox"),
            dest_path=self.inbox_dir,
            file_size=0,
            outcome=outcome,
            details=details,
        )

    def _login(self, page) -> None:
        """Authenticate with Gmail via Playwright.

        Uses email/password from .env. Persistent browser context
        stores cookies so subsequent runs skip login.
        """
        page.goto("https://mail.google.com/")

        # Enter email address
        page.wait_for_selector('input[type="email"]', timeout=30000)
        page.fill('input[type="email"]', self.config["email"])
        page.click("#identifierNext")

        # Enter password
        page.wait_for_selector(
            'input[type="password"]:visible', timeout=30000
        )
        page.fill('input[type="password"]', self.config["password"])
        page.click("#passwordNext")

        # Wait for inbox to load
        page.wait_for_url("**/mail/**", timeout=60000)
        page.wait_for_timeout(3000)

    def _scrape_unread(self, page) -> list[dict]:
        """Scrape unread emails from Gmail inbox.

        Returns a list of email data dicts. Only reads — never modifies
        email state (Constitution Principle VI).
        """
        page.goto("https://mail.google.com/mail/u/0/#inbox")
        page.wait_for_timeout(3000)

        emails = []
        unread_rows = page.query_selector_all("tr.zE")

        for row in unread_rows:
            try:
                email_data = self._extract_email_from_row(page, row)
                if email_data:
                    emails.append(email_data)
            except Exception as e:
                print(f"  Warning: Failed to extract email row: {e}")
                continue

        return emails

    def _extract_email_from_row(self, page, row) -> dict | None:
        """Extract email metadata from a Gmail inbox row element."""
        # Sender
        sender_el = row.query_selector(".yW .yP, .yW .zF")
        sender = "Unknown"
        if sender_el:
            sender = (
                sender_el.get_attribute("name")
                or sender_el.inner_text()
                or "Unknown"
            )

        # Subject
        subject_el = row.query_selector(".bog .bqe, .bog span:first-child")
        subject = (
            subject_el.inner_text().strip() if subject_el else "(no subject)"
        )

        # Snippet/preview
        snippet_el = row.query_selector(".y2")
        snippet = ""
        if snippet_el:
            snippet = snippet_el.inner_text().strip(" -\u2013\n")

        # Date
        date_el = row.query_selector(".xW span")
        date_text = ""
        if date_el:
            date_text = (
                date_el.get_attribute("title")
                or date_el.inner_text()
                or ""
            )

        # Priority indicators (read-only check)
        starred = (
            row.query_selector('.T-KT-Jp[aria-label*="Starred"]') is not None
        )
        important = (
            row.query_selector('.pG[aria-label*="Important"]') is not None
        )

        # Read full body by clicking into the email
        body = ""
        attachments = []
        try:
            row.click()
            page.wait_for_timeout(2000)

            body_el = page.query_selector(".a3s.aiL, .a3s")
            if body_el:
                body = body_el.inner_text().strip()

            attach_els = page.query_selector_all(".aZo .aV3")
            for att in attach_els:
                att_name = att.inner_text().strip()
                if att_name:
                    attachments.append(att_name)

            # Return to inbox list
            page.go_back()
            page.wait_for_timeout(1500)
        except Exception:
            pass

        return {
            "sender": sender,
            "subject": subject,
            "snippet": snippet,
            "date": date_text,
            "body": body,
            "starred": starred,
            "important": important,
            "attachments": attachments,
            "urgent": starred or important,
        }

    def _write_email_markdown(self, email_data: dict) -> Path | None:
        """Convert an email to an Obsidian-compatible Markdown file.

        Applies deduplication via hash. Routes urgent emails to
        Needs_Action/email/, normal emails to Inbox/email/.

        Returns the file path written, or None if skipped (duplicate).
        """
        email_hash = compute_email_hash(
            email_data["sender"],
            email_data["date"],
            email_data["subject"],
        )

        if email_hash in self.seen_hashes:
            return None

        now = datetime.now(timezone.utc)
        captured_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        urgency = "urgent" if email_data["urgent"] else "normal"

        # Route based on urgency per WatcherInfrastructure skill
        target_dir = (
            self.needs_action_dir if email_data["urgent"] else self.inbox_dir
        )

        # Generate safe filename
        slug = sanitize_filename(email_data["subject"])
        filename = f"{now.strftime('%Y%m%d-%H%M%S')}_{slug}.md"
        filepath = target_dir / filename

        # Build attachments section
        attachments_section = ""
        if email_data.get("attachments"):
            attachments_section = "\n## Attachments\n\n"
            for att in email_data["attachments"]:
                attachments_section += f"- [ ] attachment: {att}\n"

        # Escape quotes in frontmatter values
        sender_escaped = email_data["sender"].replace('"', '\\"')
        subject_escaped = email_data["subject"].replace('"', '\\"')

        content = (
            f"---\n"
            f"source: gmail\n"
            f"captured_at: {captured_at}\n"
            f'sender: "{sender_escaped}"\n'
            f'subject: "{subject_escaped}"\n'
            f"urgency: {urgency}\n"
            f"status: unread\n"
            f"tags: [inbox, gmail]\n"
            f"---\n"
            f"\n"
            f"# {email_data['subject']}\n"
            f"\n"
            f"**From**: {email_data['sender']}\n"
            f"**Date**: {email_data['date']}\n"
            f"\n"
            f"---\n"
            f"\n"
            f"{email_data['body'] or email_data['snippet']}\n"
            f"{attachments_section}"
        )

        filepath.write_text(content, encoding="utf-8")

        # Update dedup state
        self.seen_hashes.add(email_hash)
        self._save_state()

        return filepath

    def poll_once(self, page) -> tuple[int, int]:
        """Run a single poll cycle. Returns (written_count, skipped_count)."""
        emails = self._scrape_unread(page)
        written = 0
        skipped = 0

        for email_data in emails:
            result = self._write_email_markdown(email_data)
            if result:
                written += 1
                urgency = "URGENT" if email_data["urgent"] else "NORMAL"
                print(
                    f"  [{urgency}] {email_data['sender']}: "
                    f"{email_data['subject']} -> {result.name}"
                )
            else:
                skipped += 1

        return written, skipped

    def _handle_poll_error(self, page, error: Exception) -> None:
        """Handle poll errors with Ralph Wiggum retry loop (Principle V).

        Attempt 1: re-poll after brief wait.
        Attempt 2: refresh page, adjust context, retry.
        Attempt 3: simplify — navigate directly to inbox, retry.
        After 3 failures: log to /Logs and continue.
        """
        for attempt in range(1, 4):
            try:
                if attempt == 1:
                    print(f"  Retry {attempt}/3: re-polling after wait...")
                    time.sleep(2)
                elif attempt == 2:
                    print(f"  Retry {attempt}/3: refreshing page...")
                    page.reload()
                    page.wait_for_timeout(3000)
                else:
                    print(
                        f"  Retry {attempt}/3: "
                        f"navigating directly to inbox..."
                    )
                    page.goto("https://mail.google.com/mail/u/0/#inbox")
                    page.wait_for_timeout(5000)

                self.poll_once(page)
                return
            except Exception as retry_error:
                if attempt == 3:
                    self._write_log(
                        "error",
                        f"Gmail poll failed after 3 attempts: {retry_error}",
                        "failure",
                    )
                    print(
                        f"  Error: Poll failed after 3 attempts. "
                        f"See Logs/."
                    )

    def run(self) -> None:
        """Main run loop — poll Gmail at configured interval."""
        self._ensure_dirs()

        print("Gmail Sentinel starting...")
        print(f"  Account: {self.config['email']}")
        print(f"  Vault: {self.vault_path}")
        print(f"  Poll interval: {self.config['poll_interval']}s")
        print(f"  Headless: {self.config['headless']}")

        with sync_playwright() as pw:
            # Persistent context for cookie/session reuse
            user_data_dir = str(self.state_dir / "gmail-browser")
            self.state_dir.mkdir(parents=True, exist_ok=True)

            browser_context = pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=self.config["headless"],
            )
            page = browser_context.new_page()

            try:
                # Check if session is still valid or needs fresh login
                page.goto("https://mail.google.com/")
                page.wait_for_timeout(3000)

                if (
                    "accounts.google.com" in page.url
                    or "signin" in page.url
                ):
                    print("  Logging in to Gmail...")
                    self._login(page)
                    print("  Login successful.")
                else:
                    print("  Session restored from cookies.")
            except Exception as e:
                print(f"  Login failed: {e}", file=sys.stderr)
                self._write_log(
                    "error", f"Gmail login failed: {e}", "failure"
                )
                browser_context.close()
                raise SystemExit(1)

            self._write_log("gmail_start", "Gmail Sentinel started.")
            print("\n  Watching for unread emails... (Ctrl+C to stop)\n")

            try:
                while True:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{now_str}] Polling Gmail...")

                    try:
                        written, skipped = self.poll_once(page)
                        self._write_log(
                            "gmail_poll",
                            f"Poll complete: {written} new, "
                            f"{skipped} skipped",
                        )
                        print(
                            f"[{now_str}] Poll complete: "
                            f"{written} new, {skipped} already seen\n"
                        )
                    except Exception as e:
                        self._handle_poll_error(page, e)

                    time.sleep(self.config["poll_interval"])

            except KeyboardInterrupt:
                self._write_log("gmail_stop", "Gmail Sentinel stopped.")
                print("\nGmail Sentinel stopped.")
            finally:
                browser_context.close()


def main():
    """Entry point for gmail-sentinel command."""
    config = load_config()

    if not config["email"]:
        print("Error: GMAIL_EMAIL not set in .env", file=sys.stderr)
        raise SystemExit(1)
    if not config["password"]:
        print("Error: GMAIL_PASSWORD not set in .env", file=sys.stderr)
        raise SystemExit(1)

    watcher = GmailWatcher(config)
    watcher.run()


if __name__ == "__main__":
    main()
