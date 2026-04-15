"""
odoo_mcp — Odoo MCP server package.

Exposes six FastMCP tools for Odoo Community: three read-only tools
(no approval gate) and three write tools (executor-only, post-approval).
Connection is via stdlib xmlrpc.client — no new dependencies required.
"""
