"""
odoo_mcp.__main__ — CLI entrypoint for the Odoo MCP server.

Usage:
    python -m odoo_mcp
    odoo-mcp           (after pip install)

Loads OdooConfig from .env, authenticates to Odoo, and starts the
FastMCP server over stdio. Handles startup failures gracefully.
"""

from __future__ import annotations

import sys
import logging

from odoo_accounting.config import OdooConfigError, load_odoo_config
from odoo_mcp.client import OdooConnectionError, connect
from odoo_mcp.server import create_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s odoo-mcp: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Load config, connect to Odoo, and run the MCP server."""
    try:
        config = load_odoo_config()
    except OdooConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    try:
        conn = connect(config.url, config.db, config.user, config.api_key)
        logger.info("Connected to Odoo at %s (uid=%s)", config.url, conn.uid)
    except OdooConnectionError as exc:
        logger.error("Odoo connection failed: %s", exc)
        sys.exit(1)

    mcp = create_server(conn, config)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
