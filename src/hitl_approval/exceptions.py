"""Exceptions for HITL approval system."""


class HITLApprovalError(Exception):
    """Base exception for HITL approval system."""

    pass


class DuplicateApprovalError(HITLApprovalError):
    """Raised when an identical approval request already exists.

    This prevents creating duplicate approval requests for the same action.
    The hash is computed from: action_type + target_recipient + subject + source_path
    """

    def __init__(self, message: str = "Duplicate approval request", hash_value: str = ""):
        self.hash_value = hash_value
        super().__init__(f"{message} (hash: {hash_value[:8]}...)" if hash_value else message)


class InvalidFrontmatterError(HITLApprovalError):
    """Raised when approval file has invalid or missing frontmatter.

    Required frontmatter fields:
    - type: approval_request
    - action_type: send_email_reply | send_email_followup | publish_linkedin_post
    - status: pending | approved | rejected
    - created_at: ISO timestamp
    - target: dict with recipient info
    - source: dict with source reference
    - rollback_strategy: string describing rollback
    """

    def __init__(self, message: str = "Invalid frontmatter", file_path: str = ""):
        self.file_path = file_path
        super().__init__(f"{message}: {file_path}" if file_path else message)
