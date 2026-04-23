"""Exceptions for HITL approval system.

Feature 015 / T101: the base class now inherits from `resilience.ResilienceError`
so the shared hierarchy (category + retryable + error_code + context) is
available on every HITL exception. Existing call sites that do
`raise HITLApprovalError("msg")` or `raise DuplicateApprovalError(...)` keep
working thanks to the forgiving `__init__` that accepts bare message strings.
"""

from resilience import ResilienceError
from resilience.exceptions import FailureCategory


class HITLApprovalError(ResilienceError):
    """Base exception for HITL approval system (now a ResilienceError)."""

    def __init__(
        self,
        message: str = "",
        error_code: str = "ERR_HITL_APPROVAL",
        category: FailureCategory = FailureCategory.INTERNAL_ERROR,
        retryable: bool = False,
        **kwargs,
    ):
        super().__init__(
            error_code=error_code,
            category=category,
            message=message,
            retryable=retryable,
            **kwargs,
        )


class DuplicateApprovalError(HITLApprovalError):
    """Raised when an identical approval request already exists."""

    def __init__(self, message: str = "Duplicate approval request", hash_value: str = ""):
        self.hash_value = hash_value
        composed = f"{message} (hash: {hash_value[:8]}...)" if hash_value else message
        super().__init__(
            composed,
            error_code="ERR_HITL_DUPLICATE_APPROVAL",
            category=FailureCategory.DATA_MALFORMED,
            retryable=False,
        )


class InvalidFrontmatterError(HITLApprovalError):
    """Raised when approval file has invalid or missing frontmatter."""

    def __init__(self, message: str = "Invalid frontmatter", file_path: str = ""):
        self.file_path = file_path
        composed = f"{message}: {file_path}" if file_path else message
        super().__init__(
            composed,
            error_code="ERR_HITL_INVALID_FRONTMATTER",
            category=FailureCategory.DATA_MALFORMED,
            retryable=False,
        )
