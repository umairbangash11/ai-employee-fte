"""
odoo_accounting — Odoo accounting action modules.

Contains config, vault_writer, invoice_drafter, payment_drafter,
reconciliation, and executor. All Odoo writes are proposal-gated:
vault/Pending_Approval/odoo/ → (human approval) → vault/Approved/odoo/.
The executor watches Approved/odoo/ via watchdog and calls the
odoo_mcp write tools after detecting a human-authorized file.
"""
