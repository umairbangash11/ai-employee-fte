"""Router configuration management.

Loads routing configuration from environment variables with sensible defaults.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class RouterConfig:
    """Configuration settings for the router.

    Attributes:
        vault_path: Root path of the vault
        sla_threshold_hours: Hours before SLA breach triggers routing
        urgency_keywords: Keywords that trigger urgency routing
        verbose_logging: Log skipped (no-match) files
    """

    vault_path: Path = field(default_factory=lambda: Path("."))
    sla_threshold_hours: int = 24
    urgency_keywords: list[str] = field(
        default_factory=lambda: [
            "urgent",
            "asap",
            "deadline",
            "critical",
            "time-sensitive",
            "immediate",
            "priority",
            "emergency",
            "action required",
        ]
    )
    verbose_logging: bool = False


def load_router_config() -> RouterConfig:
    """Load RouterConfig from environment variables.

    Environment Variables:
        VAULT_PATH: Vault root (default: ".")
        ROUTER_SLA_HOURS: SLA threshold (default: 24)
        ROUTER_URGENCY_KEYWORDS: Comma-separated keywords
        ROUTER_VERBOSE_LOG: Enable verbose logging (default: false)

    Returns:
        RouterConfig with loaded or default values
    """
    vault_path = Path(os.getenv("VAULT_PATH", "."))

    sla_hours_str = os.getenv("ROUTER_SLA_HOURS", "24")
    try:
        sla_threshold_hours = max(1, int(sla_hours_str))
    except ValueError:
        sla_threshold_hours = 24

    keywords_str = os.getenv("ROUTER_URGENCY_KEYWORDS", "")
    if keywords_str.strip():
        urgency_keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
    else:
        urgency_keywords = [
            "urgent",
            "asap",
            "deadline",
            "critical",
            "time-sensitive",
            "immediate",
            "priority",
            "emergency",
            "action required",
        ]

    verbose_str = os.getenv("ROUTER_VERBOSE_LOG", "false").lower()
    verbose_logging = verbose_str in ("true", "1", "yes")

    return RouterConfig(
        vault_path=vault_path,
        sla_threshold_hours=sla_threshold_hours,
        urgency_keywords=urgency_keywords,
        verbose_logging=verbose_logging,
    )
