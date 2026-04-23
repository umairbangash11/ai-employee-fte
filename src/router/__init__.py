"""Inbox → Needs_Action Router.

Rule-based router that moves markdown files from /Inbox/email/ to
/Needs_Action/email/ based on urgency flags, keyword matching, and SLA breach.

Public API:
    - route_inbox: Scan and route all eligible files
    - evaluate_file: Evaluate a single file against routing rules
    - RouterConfig: Configuration dataclass
    - load_router_config: Load configuration from environment
    - parse_email_file: Parse markdown file with YAML frontmatter
    - move_file_to_needs_action: Atomic file move with claim-by-move
"""

# Resilience module integration (Feature 015, T078)
from resilience import (
    ExitCode,
    HealthManager,
    ResilienceError,
    exit_with_code,
    ralph_wiggum_loop,
    route_to_failed_queue,
)

from router.config import RouterConfig, load_router_config
from router.parser import (
    EmailFrontmatter,
    InboxFile,
    MalformedFrontmatterError,
    parse_email_file,
)
from router.router import (
    MoveResult,
    RoutedFile,
    RoutingError,
    RoutingReport,
    RouterError,
    RoutingFailedError,
    move_file_to_needs_action,
    route_inbox,
    evaluate_file,
)
from router.rules import (
    RoutingResult,
    RoutingRule,
    evaluate_rules,
    get_default_rules,
)

__all__ = [
    # Config
    "RouterConfig",
    "load_router_config",
    # Parser
    "EmailFrontmatter",
    "InboxFile",
    "MalformedFrontmatterError",
    "parse_email_file",
    # Router
    "MoveResult",
    "RoutedFile",
    "RoutingError",
    "RoutingReport",
    "RouterError",
    "RoutingFailedError",
    "move_file_to_needs_action",
    "route_inbox",
    "evaluate_file",
    # Rules
    "RoutingResult",
    "RoutingRule",
    "evaluate_rules",
    "get_default_rules",
]
