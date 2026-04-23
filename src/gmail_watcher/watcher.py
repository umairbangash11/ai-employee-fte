"""Gmail API polling logic."""

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from resilience import (
    CircuitBreaker,
    CircuitOpenError,
    HealthManager,
    ResilienceError,
    RetryPolicy,
    ralph_wiggum_loop,
    route_to_failed_queue,
)
from resilience.exceptions import (
    CredentialsInvalidError,
    DataMalformedError,
    ExternalServiceDownError,
    InternalError,
    RateLimitedError,
    TransientNetworkError,
)

from gmail_watcher import __version__ as GMAIL_WATCHER_VERSION
from gmail_watcher.models import Attachment, EmailMessage

SUBSYSTEM_NAME = "gmail_watcher"
GMAIL_API_CIRCUIT_NAME = "gmail_api"
DEFAULT_STATE_DIR = Path(".watcher-state")


def create_health_manager(state_dir: Path = DEFAULT_STATE_DIR) -> HealthManager:
    """Construct the HealthManager for the gmail_watcher subsystem.

    Args:
        state_dir: Directory where the health file is persisted.

    Returns:
        HealthManager bound to `.watcher-state/gmail_watcher_health.json`.
    """
    return HealthManager(
        subsystem=SUBSYSTEM_NAME,
        state_dir=state_dir,
        version=GMAIL_WATCHER_VERSION,
    )


def create_gmail_circuit_breaker(
    name: str = GMAIL_API_CIRCUIT_NAME,
) -> CircuitBreaker:
    """Construct the CircuitBreaker that protects Gmail API calls.

    Uses `CircuitBreaker`'s defaults (failure_threshold=5,
    failure_rate_threshold=0.5, failure_window_seconds=60,
    recovery_timeout_seconds=30, success_threshold=3) per tasks.md T035 and
    spec FR-009. Integration into `poll_with_retry` is deferred to a
    subsequent step.

    Args:
        name: Circuit identifier.

    Returns:
        CircuitBreaker in CLOSED state.
    """
    return CircuitBreaker(name=name)


def poll_once(
    service: Resource,
    health: HealthManager,
    max_results: int = 50,
) -> list[dict]:
    """Execute one Gmail poll cycle, recording health and emitting a heartbeat.

    On success, returns the fetched messages and calls `health.record_success()`.
    On any exception from `fetch_unread_messages`, calls
    `health.record_failure(reason)` and re-raises so the caller can decide
    retry strategy (T061). `health.heartbeat()` always fires in the `finally`
    block so the watchdog observes liveness on every poll — success or failure.

    Args:
        service: Gmail API service.
        health: HealthManager for the gmail_watcher subsystem.
        max_results: Maximum number of unread messages to fetch.

    Returns:
        List of full message objects from the Gmail API (may be empty).
    """
    try:
        messages = fetch_unread_messages(service, max_results=max_results)
        health.record_success()
        return messages
    except Exception as exc:
        health.record_failure(str(exc) or exc.__class__.__name__)
        raise
    finally:
        health.heartbeat()


def poll_with_retry(
    service: Resource,
    health: HealthManager,
    max_results: int = 50,
    policy: Optional[RetryPolicy] = None,
    circuit: Optional[CircuitBreaker] = None,
) -> list[dict]:
    """Execute a Gmail poll under the Ralph Wiggum Loop (Constitution V).

    Wraps `poll_once` in `ralph_wiggum_loop` so transient failures retry with
    exponential backoff + jitter. `poll_once` remains the primitive — it still
    records success/failure and emits a heartbeat on every attempt, so the
    health file reflects each retry, not just the final outcome.

    When `circuit` is provided, `poll_once` runs under `circuit.execute()` so
    the breaker observes each attempt's success or failure and can trip OPEN
    when Gmail is sustainedly failing. A `CircuitOpenError` is forced to
    non-retryable locally before re-raising so `ralph_wiggum_loop` fast-fails
    instead of burning the retry budget against a circuit that is already
    short-circuiting calls.

    Args:
        service: Gmail API service.
        health: HealthManager for the gmail_watcher subsystem.
        max_results: Maximum unread messages to fetch per attempt.
        policy: Optional RetryPolicy override. Defaults to 3 attempts with
            exponential backoff.
        circuit: Optional CircuitBreaker guarding Gmail API calls. When
            omitted, `poll_once` runs unguarded exactly as before.

    Returns:
        List of full message objects from the first successful attempt.

    Raises:
        CircuitOpenError: If `circuit` is provided and its state is OPEN at
            the time of an attempt. Re-raised with `retryable=False` so the
            retry loop halts immediately rather than sleeping and re-trying
            under the same open circuit.
        Exception: The last exception raised by `poll_once` if all attempts
            fail or if a non-retryable exception is raised on an earlier
            attempt.
    """
    def _attempt() -> list[dict]:
        try:
            if circuit is None:
                return poll_once(service, health, max_results=max_results)
            try:
                return circuit.execute(
                    lambda: poll_once(service, health, max_results=max_results)
                )
            except CircuitOpenError as exc:
                # Module-wide CircuitOpenError.retryable is True so that
                # callers who schedule their own retries (e.g. a queue
                # scheduler with backoff aware of `remaining_seconds`) can
                # still do so. Inside `poll_with_retry`, however, retrying
                # immediately under an open circuit would waste the retry
                # budget — every attempt would fast-fail from the breaker
                # without ever reaching Gmail. Flip the flag so
                # `ralph_wiggum_loop`'s `is_retryable(e)` check fast-fails
                # on this attempt.
                exc.retryable = False
                raise
        except ResilienceError:
            # Already translated — pass through so ralph_wiggum_loop
            # consults its own `retryable` flag.
            raise
        except Exception as exc:
            # T066: translate raw Google / network errors at the Gmail API
            # boundary so `ralph_wiggum_loop.is_retryable(e)` resolves
            # against the resilience hierarchy (HttpError 429 -> retryable,
            # RefreshError -> non-retryable, etc.) rather than defaulting
            # non-ResilienceError exceptions to non-retryable.
            raise translate_gmail_error(exc) from exc

    return ralph_wiggum_loop(operation=_attempt, policy=policy)


def route_email_to_failed(
    source_item: Path,
    vault_path: Path,
    failure_reason: str,
    retry_attempts: int = 3,
    error_code: Optional[str] = None,
) -> Path:
    """Move a captured email into `Needs_Action/email/failed/` (T065, FR-006).

    Thin adapter over `resilience.route_to_failed_queue` that fixes
    `subsystem="gmail_watcher"` and attaches a Gmail-specific recovery hint,
    so `__main__.py`'s per-message processing loop can route a single failed
    email in one call.

    Args:
        source_item: Path to the captured email Markdown file (must exist).
        vault_path: Vault root (used to resolve the failed-queue directory).
        failure_reason: Human-readable description of what went wrong.
        retry_attempts: Retries already exhausted. Default 3 matches the
            Ralph Wiggum Loop policy from `poll_with_retry`.
        error_code: Optional ResilienceError.error_code for traceability.

    Returns:
        Path to the wrapper file in `Needs_Action/email/failed/`.
    """
    return route_to_failed_queue(
        source_item=source_item,
        subsystem=SUBSYSTEM_NAME,
        failure_reason=failure_reason,
        retry_attempts=retry_attempts,
        recovery_action=(
            "Inspect wrapped email. If the original content is recoverable, "
            "use `sentinel-recover retry` to re-queue. Otherwise fix the root "
            "cause (credentials, parser, write target) and delete this wrapper."
        ),
        vault_path=vault_path,
        error_code=error_code,
    )


def translate_gmail_error(error: Exception) -> ResilienceError:
    """Translate Google API / network errors into ResilienceError (T066).

    Provides the mapping `__main__.py` needs to migrate its legacy
    `TRANSIENT_ERRORS`/`is_transient_error`/`get_actionable_message` trio to
    the shared exception hierarchy without duplicating classification logic
    across subsystems. Uses duck-typing for HttpError so `googleapiclient`
    remains a soft dependency of this helper.

    Mapping:
      * HttpError 401 / RefreshError → CredentialsInvalidError
      * HttpError 403                → CredentialsInvalidError (scope/denied)
      * HttpError 429                → RateLimitedError
      * HttpError 5xx                → ExternalServiceDownError
      * HttpError 4xx (other)        → DataMalformedError
      * TimeoutError / ConnectionError → TransientNetworkError
      * Already a ResilienceError    → returned as-is (idempotent)
      * Anything else                → InternalError

    Args:
        error: Exception raised by the Gmail API path.

    Returns:
        ResilienceError subclass with category, error_code, and retryable
        flag set so `ralph_wiggum_loop` and `sentinel-status` interpret it
        consistently.
    """
    if isinstance(error, ResilienceError):
        return error

    error_name = type(error).__name__
    if error_name == "RefreshError":
        return CredentialsInvalidError(
            "Gmail OAuth token refresh failed — run `gmail-watcher --auth`.",
            context={"original_error": str(error)},
        )

    if error_name == "HttpError":
        status = getattr(getattr(error, "resp", None), "status", None)
        context = {"http_status": status, "original_error": str(error)}
        if status in (401, 403):
            return CredentialsInvalidError(
                f"Gmail API rejected credentials (HTTP {status}).",
                context=context,
            )
        if status == 429:
            return RateLimitedError(
                "Gmail API rate limit exceeded (HTTP 429).",
                context=context,
            )
        if status is not None and status >= 500:
            return ExternalServiceDownError(
                f"Gmail API unavailable (HTTP {status}).",
                context=context,
            )
        return DataMalformedError(
            f"Gmail API rejected request (HTTP {status}).",
            context=context,
        )

    if isinstance(error, (TimeoutError, ConnectionError)):
        return TransientNetworkError(
            f"Network error contacting Gmail: {error}",
            context={"original_error": str(error)},
        )

    return InternalError(
        f"Unexpected error in gmail_watcher: {error}",
        context={"original_error": str(error), "error_type": error_name},
    )


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
