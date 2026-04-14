"""Human-in-the-Loop Approval System for vault-based action approval.

This package implements a file-based approval workflow for sensitive external
actions (email sends, LinkedIn posts). Instead of executing actions directly,
the system creates approval request files. Human operators approve by moving
files between directories.

Constitution Compliance:
- Principle II: Uses /Approved/, extends with /Pending_Approval/, /Rejected/
- Principle IV: No execution without /Approved/ file
- Principle VI: Enforces HITL for all external actions
"""

__version__ = "0.1.0"
