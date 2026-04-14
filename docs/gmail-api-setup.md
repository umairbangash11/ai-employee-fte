# Gmail API Setup Guide

This guide explains how to set up Gmail API access for the gmail-watcher tool.

## Prerequisites

- Google account with Gmail
- Python 3.12+ with gmail-watcher installed

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "Gmail Watcher")
4. Click "Create"

## Step 2: Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click on "Gmail API" and then "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select "External" user type (or "Internal" if using Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - App name: "Gmail Watcher"
   - User support email: your email
   - Developer contact: your email
5. Click "Save and Continue"
6. On Scopes page, click "Add or Remove Scopes"
7. Add: `https://www.googleapis.com/auth/gmail.readonly`
8. Click "Save and Continue"
9. Add your email as a test user
10. Click "Save and Continue"

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Desktop app" as application type
4. Name it "Gmail Watcher Desktop"
5. Click "Create"
6. Click "Download JSON" to download credentials

## Step 5: Install Credentials

1. Create the secrets directory:
   ```bash
   mkdir -p secrets/gmail
   ```

2. Move the downloaded JSON file:
   ```bash
   mv ~/Downloads/client_secret_*.json secrets/gmail/credentials.json
   ```

3. Ensure the directory is in .gitignore (it should be by default)

## Step 6: Authenticate

Run the authentication command:

```bash
gmail-watcher --auth
```

This will:
1. Open your browser for OAuth consent
2. Ask you to grant read-only access to Gmail
3. Save the token to `secrets/gmail/token.json`

## Step 7: Verify Setup

Test the watcher with a single poll:

```bash
gmail-watcher --once --vault-path /path/to/vault
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_PATH` | Path to Obsidian vault | Current directory |

## CLI Options

| Flag | Description |
|------|-------------|
| `--auth` | Run OAuth flow and exit |
| `--once` | Poll once and exit |
| `--dry-run` | Preview without writing files |
| `--vault-path PATH` | Path to vault |
| `--credentials PATH` | Path to credentials.json |
| `--token PATH` | Path to token.json |
| `--state PATH` | Path to state file |
| `--interval SECONDS` | Poll interval (min: 60, default: 120) |
| `--version` | Show version |

## Troubleshooting

### "OAuth credentials not found"

Ensure `credentials.json` exists at `secrets/gmail/credentials.json`.

### "Authentication token refresh failed"

Your token may have been revoked. Run:
```bash
gmail-watcher --auth
```

### "Permission denied" (403)

1. Verify Gmail API is enabled in Google Cloud Console
2. Check that `gmail.readonly` scope was granted
3. Ensure your email is in the test users list

### "Rate limited" (429)

Gmail API has quota limits. Wait a few minutes and try again.
The watcher uses a minimum 60-second poll interval to avoid rate limits.

### Network errors

Check your internet connection. The watcher will retry up to 3 times
with exponential backoff on transient network errors.

## Security Notes

- `credentials.json` contains your OAuth client secret - never commit this
- `token.json` contains your access token - never commit this
- Both are stored in `secrets/` which is gitignored
- Token file has chmod 600 (owner read/write only)
- The watcher uses read-only Gmail scope - it cannot modify or send emails
