"""OAuth 2.0 authentication for Gmail API."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scope - read-only per Constitution Principle VIII
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def load_credentials(token_path: Path) -> Credentials | None:
    """Load OAuth credentials from token file.

    Args:
        token_path: Path to token.json file

    Returns:
        Credentials object if token exists and is valid, None otherwise
    """
    if not token_path.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return creds


def run_oauth_flow(credentials_path: Path, token_path: Path) -> Credentials:
    """Run browser-based OAuth consent flow.

    Args:
        credentials_path: Path to credentials.json (OAuth client config)
        token_path: Path to save the resulting token.json

    Returns:
        Credentials object after successful authentication

    Raises:
        FileNotFoundError: If credentials.json doesn't exist
    """
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {credentials_path}\n\n"
            "To set up Gmail API access:\n"
            "1. Go to https://console.cloud.google.com/apis/credentials\n"
            "2. Create OAuth 2.0 Client ID (Desktop application)\n"
            "3. Download the JSON file\n"
            "4. Save it as: {credentials_path}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)

    save_token(creds, token_path)
    return creds


def save_token(credentials: Credentials, token_path: Path) -> None:
    """Save OAuth token to file with secure permissions.

    Args:
        credentials: OAuth credentials to save
        token_path: Path to save token.json
    """
    # Ensure parent directory exists
    token_path.parent.mkdir(parents=True, exist_ok=True)

    # Write token file
    with open(token_path, "w") as f:
        f.write(credentials.to_json())

    # Set file permissions to 600 (owner read/write only)
    os.chmod(token_path, 0o600)


def refresh_if_expired(credentials: Credentials) -> Credentials:
    """Refresh access token if expired.

    Args:
        credentials: OAuth credentials to check/refresh

    Returns:
        Updated credentials (may be refreshed)

    Raises:
        google.auth.exceptions.RefreshError: If refresh fails
    """
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials


def get_credentials(credentials_path: Path, token_path: Path, force_auth: bool = False) -> Credentials:
    """Get valid OAuth credentials, running auth flow if needed.

    Args:
        credentials_path: Path to credentials.json
        token_path: Path to token.json
        force_auth: If True, always run OAuth flow even if token exists

    Returns:
        Valid OAuth credentials

    Raises:
        FileNotFoundError: If credentials.json doesn't exist
        google.auth.exceptions.RefreshError: If token refresh fails
    """
    creds = None

    if not force_auth:
        creds = load_credentials(token_path)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds = refresh_if_expired(creds)
            save_token(creds, token_path)
            return creds

    # Need to run OAuth flow
    return run_oauth_flow(credentials_path, token_path)
