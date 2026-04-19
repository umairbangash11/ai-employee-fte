# Setup Guide

## Prerequisites
- Python 3.12+
- Gmail account with OAuth credentials

## Steps

1. **Create and activate virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure environment**
   ```bash
   cp .env_example .env
   ```
   Edit `.env` and fill in:
   - `VAULT_PATH` — absolute path to your vault directory (e.g. `/home/user/vault`)
   - `OPENAI_API_KEY` — required for the brain/orchestrator
   - `OPENAI_MODEL` — e.g. `gpt-4o`
   - `GMAIL_POLL_INTERVAL` — seconds between polls (default: 300)

4. **Add Gmail OAuth credentials**
   ```bash
   mkdir -p secrets/gmail
   # Place your downloaded credentials.json from Google Cloud Console here:
   # secrets/gmail/credentials.json
   ```

5. **Authenticate Gmail (first run only)**
   ```bash
   gmail-watcher --auth
   ```
   A browser will open for OAuth. Token saved to `secrets/gmail/token.json`.

6. **Initialize vault structure**
   ```bash
   sentinel init --vault-path "$VAULT_PATH"
   ```

7. **Run Gmail watcher**
   ```bash
   gmail-watcher
   ```
   Polls Gmail at the configured interval and writes emails to `$VAULT_PATH/Inbox/email/`.

8. **Run the orchestrator (brain)**
   ```bash
   PYTHONPATH=src python3 -m orchestrator.brain
   ```
   Watches `Inbox/` for new emails, classifies them, and generates plan files.

9. **Run the vault MCP server** (for Claude Code integration)
   ```bash
   # Registered automatically via .mcp.json — no manual start needed in Claude Code
   # To test manually:
   PYTHONPATH=src python3 -m vault_mcp
   ```

10. **Verify setup**
    ```bash
    PYTHONPATH=src pytest tests/unit/ -q --tb=short
    # Expected: 121 passed, 3 failed (pre-existing facebook_publisher failures only)
    ```

## Security

> **Never commit `.env` or `secrets/` to version control.**
> Both are listed in `.gitignore`. Double-check before any `git push`.
