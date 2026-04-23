"""Resilience integration surface for whatsapp_watcher (Feature 015).

Provides the same factory + translator + routing helpers that
`gmail_watcher.watcher` exposes, so `__main__.py`'s async polling loop can
compose the shared resilience primitives (HealthManager, CircuitBreaker,
ralph_wiggum_loop, route_to_failed_queue) without duplicating logic.

This module is intentionally additive — it does not replace `scraper.py`,
`session.py`, or `writer.py`. Those remain the domain primitives.
"""

from pathlib import Path
from typing import Optional

from resilience import (
    CircuitBreaker,
    HealthManager,
    ResilienceError,
    route_to_failed_queue,
)
from resilience.exceptions import (
    DataMalformedError,
    InternalError,
    ResourceUnavailableError,
    SessionExpiredError as ResilienceSessionExpiredError,
    TransientNetworkError,
)

from whatsapp_watcher import __version__ as WHATSAPP_WATCHER_VERSION

SUBSYSTEM_NAME = "whatsapp_watcher"
WHATSAPP_CIRCUIT_NAME = "whatsapp_web"
DEFAULT_STATE_DIR = Path(".watcher-state")


def create_health_manager(state_dir: Path = DEFAULT_STATE_DIR) -> HealthManager:
    """Construct the HealthManager for the whatsapp_watcher subsystem (T070).

    Args:
        state_dir: Directory where the health file is persisted.

    Returns:
        HealthManager bound to `.watcher-state/whatsapp_watcher_health.json`.
    """
    return HealthManager(
        subsystem=SUBSYSTEM_NAME,
        state_dir=state_dir,
        version=WHATSAPP_WATCHER_VERSION,
    )


def create_whatsapp_circuit_breaker(
    name: str = WHATSAPP_CIRCUIT_NAME,
) -> CircuitBreaker:
    """Construct the CircuitBreaker protecting WhatsApp Web interactions.

    Uses `CircuitBreaker`'s defaults per spec FR-009 / tasks.md T035.

    Args:
        name: Circuit identifier.

    Returns:
        CircuitBreaker in CLOSED state.
    """
    return CircuitBreaker(name=name)


def route_message_to_failed(
    source_item: Path,
    vault_path: Path,
    failure_reason: str,
    retry_attempts: int = 3,
    error_code: Optional[str] = None,
) -> Path:
    """Move a captured WhatsApp message into `Needs_Action/whatsapp/failed/` (T074).

    Thin adapter over `resilience.route_to_failed_queue` that fixes
    `subsystem="whatsapp_watcher"` and attaches a WhatsApp-specific
    recovery hint.

    Args:
        source_item: Path to the captured message Markdown (must exist).
        vault_path: Vault root.
        failure_reason: Human-readable description of what went wrong.
        retry_attempts: Retries already exhausted.
        error_code: Optional ResilienceError.error_code for traceability.

    Returns:
        Path to the wrapper file in `Needs_Action/whatsapp/failed/`.
    """
    return route_to_failed_queue(
        source_item=source_item,
        subsystem=SUBSYSTEM_NAME,
        failure_reason=failure_reason,
        retry_attempts=retry_attempts,
        recovery_action=(
            "Inspect wrapped WhatsApp message. If the session is still alive, "
            "use `sentinel-recover retry` to re-queue. If the session expired, "
            "run `python -m whatsapp_watcher --auth` to re-authenticate, then "
            "retry."
        ),
        vault_path=vault_path,
        error_code=error_code,
    )


def translate_whatsapp_error(error: Exception) -> ResilienceError:
    """Translate WhatsApp / Playwright errors into ResilienceError (T075).

    Mapping:
      * whatsapp_watcher.session.SessionExpiredError → resilience SessionExpiredError
      * whatsapp_watcher.session.QRTimeoutError     → ResourceUnavailableError (manual re-auth)
      * Playwright TimeoutError (by name, to keep Playwright a soft dep)
                                                    → TransientNetworkError
      * Playwright Error / generic                  → TransientNetworkError
      * asyncio.TimeoutError / TimeoutError         → TransientNetworkError
      * ValueError / KeyError                       → DataMalformedError
      * Already a ResilienceError                   → returned as-is
      * Anything else                               → InternalError

    Args:
        error: Exception raised by the WhatsApp pipeline.

    Returns:
        ResilienceError subclass with category + retryable flag set.
    """
    if isinstance(error, ResilienceError):
        return error

    error_name = type(error).__name__
    module = type(error).__module__ or ""

    # Subsystem-specific auth / session errors
    if error_name == "SessionExpiredError":
        return ResilienceSessionExpiredError(
            "WhatsApp Web session expired — run `python -m whatsapp_watcher --auth`.",
            context={"original_error": str(error)},
        )
    if error_name == "QRTimeoutError":
        return ResourceUnavailableError(
            "QR authentication timed out — rerun `--auth` and scan the QR code within the window.",
            context={"original_error": str(error)},
        )

    # Playwright surface (duck-typed so we don't hard-require playwright here)
    if error_name in ("TimeoutError", "PlaywrightTimeoutError") or "playwright" in module.lower():
        return TransientNetworkError(
            f"WhatsApp Web interaction timed out: {error}",
            context={"original_error": str(error), "error_type": error_name},
        )

    if isinstance(error, (ConnectionError,)):
        return TransientNetworkError(
            f"Network error talking to WhatsApp Web: {error}",
            context={"original_error": str(error)},
        )

    if isinstance(error, (ValueError, KeyError)):
        return DataMalformedError(
            f"Malformed WhatsApp payload: {error}",
            context={"original_error": str(error), "error_type": error_name},
        )

    return InternalError(
        f"Unexpected error in whatsapp_watcher: {error}",
        context={"original_error": str(error), "error_type": error_name},
    )
