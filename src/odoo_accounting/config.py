"""
odoo_accounting.config — OdooConfig loading from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class OdooConfigError(Exception):
    """Raised when required Odoo env vars are missing or invalid."""


@dataclass
class OdooConfig:
    """Runtime configuration for the Odoo accounting integration."""

    url: str
    db: str
    user: str
    api_key: str
    vault_path: Path
    reconcile_batch_limit: int = 20

    def __post_init__(self) -> None:
        if not self.url:
            raise OdooConfigError("ODOO_URL must not be empty")
        if not self.db:
            raise OdooConfigError("ODOO_DB must not be empty")
        if not self.user:
            raise OdooConfigError("ODOO_USER must not be empty")
        if not self.api_key:
            raise OdooConfigError("ODOO_API_KEY must not be empty")
        if not self.vault_path:
            raise OdooConfigError("VAULT_PATH must not be empty")


def load_odoo_config() -> OdooConfig:
    """Load OdooConfig from environment variables (reads .env if present).

    Raises:
        OdooConfigError: if any required variable is missing or empty.
    """
    load_dotenv()

    missing: list[str] = []

    url = os.getenv("ODOO_URL", "").strip()
    db = os.getenv("ODOO_DB", "").strip()
    user = os.getenv("ODOO_USER", "").strip()
    api_key = os.getenv("ODOO_API_KEY", "").strip()
    vault_path_str = os.getenv("VAULT_PATH", "").strip()

    if not url:
        missing.append("ODOO_URL")
    if not db:
        missing.append("ODOO_DB")
    if not user:
        missing.append("ODOO_USER")
    if not api_key:
        missing.append("ODOO_API_KEY")
    if not vault_path_str:
        missing.append("VAULT_PATH")

    if missing:
        raise OdooConfigError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    batch_raw = os.getenv("ODOO_RECONCILE_BATCH", "20").strip()
    try:
        reconcile_batch_limit = int(batch_raw)
    except ValueError:
        reconcile_batch_limit = 20

    return OdooConfig(
        url=url,
        db=db,
        user=user,
        api_key=api_key,
        vault_path=Path(vault_path_str),
        reconcile_batch_limit=reconcile_batch_limit,
    )
