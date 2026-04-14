"""Gmail API polling logic."""

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from gmail_watcher.models import Attachment, EmailMessage


def build_service(credentials: Credentials) -> Resource:
    """Create Gmail API service.

    Args:
        credentials: Valid OAuth credentials

    Returns:
        Gmail API service resource
    """
    return build("gmail", "v1", credentials=credentials)


def fetch_unread_messages(service: Resource, max_results: int = 50) -> list[dict]:
    """Fetch unread messages from Gmail.

    Args:
        service: Gmail API service
        max_results: Maximum number of messages to fetch

    Returns:
        List of full message objects from Gmail API
    """
    # List message IDs with UNREAD label
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["UNREAD"], maxResults=max_results)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        return []

    # Fetch full message details for each
    full_messages = []
    for msg in messages:
        full_msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="full")
            .execute()
        )
        full_messages.append(full_msg)

    return full_messages


def get_header(headers: list[dict], name: str) -> str:
    """Extract header value by name.

    Args:
        headers: List of header dicts from Gmail API
        name: Header name to find (case-insensitive)

    Returns:
        Header value or empty string if not found
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value", "")
    return ""


def get_message_body(payload: dict) -> str:
    """Extract message body from Gmail API payload.

    Handles multipart messages recursively, preferring plain text.

    Args:
        payload: Message payload from Gmail API

    Returns:
        Decoded message body as string
    """
    mime_type = payload.get("mimeType", "")

    # Simple text body
    if mime_type == "text/plain":
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        return ""

    # HTML body (fallback)
    if mime_type == "text/html":
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            # Return HTML as-is, let writer handle it
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        return ""

    # Multipart message - recurse through parts
    parts = payload.get("parts", [])
    if parts:
        # First try to find plain text
        for part in parts:
            if part.get("mimeType") == "text/plain":
                return get_message_body(part)

        # Fall back to HTML
        for part in parts:
            if part.get("mimeType") == "text/html":
                return get_message_body(part)

        # Recurse into nested multipart
        for part in parts:
            if part.get("mimeType", "").startswith("multipart/"):
                result = get_message_body(part)
                if result:
                    return result

    return ""


def get_attachments(payload: dict) -> list[Attachment]:
    """Extract attachment metadata from Gmail API payload.

    Args:
        payload: Message payload from Gmail API

    Returns:
        List of Attachment objects (content not downloaded)
    """
    attachments = []

    def _extract_attachments(part: dict) -> None:
        filename = part.get("filename", "")
        if filename:
            attachments.append(
                Attachment(
                    filename=filename,
                    mime_type=part.get("mimeType", "application/octet-stream"),
                    size=part.get("body", {}).get("size", 0),
                )
            )

        # Recurse into nested parts
        for nested_part in part.get("parts", []):
            _extract_attachments(nested_part)

    _extract_attachments(payload)
    return attachments


def parse_message(raw: dict) -> EmailMessage:
    """Convert Gmail API response to EmailMessage.

    Args:
        raw: Full message object from Gmail API

    Returns:
        EmailMessage dataclass with extracted fields
    """
    payload = raw.get("payload", {})
    headers = payload.get("headers", [])

    # Parse date header
    date_str = get_header(headers, "Date")
    try:
        date = parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        date = datetime.now()

    return EmailMessage(
        message_id=raw.get("id", ""),
        thread_id=raw.get("threadId", ""),
        sender=get_header(headers, "From"),
        subject=get_header(headers, "Subject") or "(no subject)",
        date=date,
        snippet=raw.get("snippet", ""),
        body=get_message_body(payload),
        label_ids=raw.get("labelIds", []),
        attachments=get_attachments(payload),
    )
