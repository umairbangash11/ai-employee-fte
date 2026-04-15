"""Entry point for the vault MCP server: python3 -m vault_mcp"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from vault_mcp.server import create_server


def load_vault_root() -> Path:
    """Load and validate VAULT_PATH from environment / .env file."""
    load_dotenv()

    import os
    vault_path = os.getenv("VAULT_PATH", "").strip()

    if not vault_path:
        print("Error: VAULT_PATH not set or directory does not exist", file=sys.stderr)
        sys.exit(1)

    vault = Path(vault_path).resolve()

    if not vault.is_dir():
        print(
            f"Error: VAULT_PATH not set or directory does not exist: {vault_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    return vault


def main() -> None:
    vault_root = load_vault_root()
    mcp = create_server(vault_root)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
