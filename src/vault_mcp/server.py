"""Vault MCP Server — exposes list_files, read_file, write_file over stdio."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _safe_resolve(vault_root: Path, relative_path: str) -> Path:
    """Resolve relative_path against vault_root and verify it stays inside.

    Raises ValueError on path-traversal attempts or empty path where forbidden.
    """
    resolved = (vault_root / relative_path).resolve()
    if not resolved.is_relative_to(vault_root):
        raise ValueError(f"Path escapes vault root: {relative_path}")
    return resolved


def _list_files_impl(vault_root: Path, path: str) -> str:
    try:
        target = _safe_resolve(vault_root, path)
    except ValueError as e:
        return f"Error: {e}"

    if not target.exists():
        return ""

    entries = sorted(entry.name for entry in target.iterdir())
    return "\n".join(entries)


def _read_file_impl(vault_root: Path, path: str) -> str:
    if not path:
        return "Error: Path must not be empty"

    try:
        target = _safe_resolve(vault_root, path)
    except ValueError as e:
        return f"Error: {e}"

    if not target.exists():
        return f"Error: File not found: {path}"

    if target.is_dir():
        return f"Error: Path is a directory, not a file: {path}"

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: Cannot decode file as UTF-8: {path}"


def _write_file_impl(vault_root: Path, path: str, content: str) -> str:
    if not path:
        return "Error: Path must not be empty"

    try:
        target = _safe_resolve(vault_root, path)
    except ValueError as e:
        return f"Error: {e}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"Error: Write failed: {e}"

    return f"Written: {path}"


def create_server(vault_root: Path) -> FastMCP:
    """Instantiate and return the vault MCP server with all three tools registered."""
    mcp = FastMCP(
        "vault",
        instructions=(
            "Vault file server. Use list_files to explore, "
            "read_file to read, write_file to create or update files."
        ),
    )

    @mcp.tool(description="List files and directories at a path relative to the vault root.")
    def list_files(path: str = "") -> str:
        return _list_files_impl(vault_root, path)

    @mcp.tool(description="Read the full UTF-8 content of a file inside the vault.")
    def read_file(path: str) -> str:
        return _read_file_impl(vault_root, path)

    @mcp.tool(description="Write (create or overwrite) a file inside the vault.")
    def write_file(path: str, content: str) -> str:
        return _write_file_impl(vault_root, path, content)

    return mcp
