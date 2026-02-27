# Router API Contract

**Feature**: 002-inbox-router
**Date**: 2026-02-27
**Type**: Internal Python API (no HTTP endpoints)

## Overview

The Inbox Router is a Python module exposing functions for routing email markdown files from `/Inbox/email/` to `/Needs_Action/email/`. This document defines the public API contract.

---

## Module: `src/router/router.py`

### Function: `route_inbox`

Main entry point for routing all eligible files in the inbox.

```python
def route_inbox(
    vault_path: str | Path = ".",
    config: RouterConfig | None = None,
    dry_run: bool = False
) -> RoutingReport:
    """
    Scan /Inbox/email/ and route matching files to /Needs_Action/email/.

    Args:
        vault_path: Root path of the vault (default: current directory)
        config: Optional RouterConfig override (default: load from .env)
        dry_run: If True, report what would be routed without moving files

    Returns:
        RoutingReport with counts and details of routed/skipped/error files

    Raises:
        ValueError: If vault_path does not exist
        PermissionError: If inbox/needs_action directories are not accessible
    """
```

**Return Type:**

```python
@dataclass
class RoutingReport:
    total_scanned: int
    routed_count: int
    skipped_count: int
    error_count: int
    routed_files: list[RoutedFile]
    errors: list[RoutingError]
    duration_ms: int

@dataclass
class RoutedFile:
    source: Path
    destination: Path
    matched_rules: list[str]

@dataclass
class RoutingError:
    path: Path
    error_type: str
    message: str
```

---

### Function: `evaluate_file`

Evaluate a single file against routing rules (used internally and for testing).

```python
def evaluate_file(
    file_path: str | Path,
    config: RouterConfig | None = None
) -> RoutingResult:
    """
    Parse file and evaluate against all routing rules.

    Args:
        file_path: Path to the markdown file
        config: Optional RouterConfig (default: load from .env)

    Returns:
        RoutingResult indicating whether file should be routed

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not a .md file
    """
```

---

### Function: `parse_email_file`

Parse a markdown file into an InboxFile structure.

```python
def parse_email_file(file_path: str | Path) -> InboxFile:
    """
    Read and parse a markdown file with YAML frontmatter.

    Args:
        file_path: Path to the markdown file

    Returns:
        InboxFile with parsed frontmatter and body

    Raises:
        FileNotFoundError: If file does not exist
        MalformedFrontmatterError: If YAML parsing fails
    """
```

---

### Function: `move_file_to_needs_action`

Atomically move a file using claim-by-move pattern.

```python
def move_file_to_needs_action(
    source: Path,
    needs_action_dir: Path,
    logs_dir: Path
) -> MoveResult:
    """
    Move file from source to /Needs_Action/email/ with logging.

    Uses atomic rename (os.rename) for claim-by-move semantics.
    If source is already gone, returns MoveResult with claimed=True.

    Args:
        source: Path to source file
        needs_action_dir: Destination directory
        logs_dir: Directory for audit logs

    Returns:
        MoveResult with success status and destination path

    Raises:
        PermissionError: If destination is not writable
        OSError: If move fails for other reasons
    """
```

**Return Type:**

```python
@dataclass
class MoveResult:
    success: bool
    claimed: bool  # True if file was already moved by another process
    source: Path
    destination: Path | None
```

---

## Module: `src/router/rules.py`

### Function: `get_default_rules`

Returns the default set of routing rules.

```python
def get_default_rules(config: RouterConfig) -> list[RoutingRule]:
    """
    Build the default routing rule set.

    Rules (in evaluation order):
    1. Flag rules (urgency=urgent, starred=true, important=true)
    2. Keyword rules (configurable keyword list)
    3. SLA rule (captured_at exceeds threshold)

    Args:
        config: RouterConfig with keywords and SLA threshold

    Returns:
        List of RoutingRule objects
    """
```

---

### Rule Specifications

| Rule Name | Type | Trigger Condition |
|-----------|------|-------------------|
| `flag:urgent` | flag | `frontmatter.urgency == "urgent"` |
| `flag:starred` | flag | `frontmatter.starred == True` |
| `flag:important` | flag | `frontmatter.important == True` |
| `keyword:{kw}` | keyword | `kw.lower() in (subject + body).lower()` |
| `sla:{hours}h` | sla | `now - captured_at > threshold_hours` |

---

## Module: `src/router/config.py`

### Function: `load_router_config`

Load configuration from environment.

```python
def load_router_config() -> RouterConfig:
    """
    Load RouterConfig from .env file.

    Environment Variables:
        VAULT_PATH: Vault root (default: ".")
        ROUTER_SLA_HOURS: SLA threshold (default: 24)
        ROUTER_URGENCY_KEYWORDS: Comma-separated keywords
        ROUTER_VERBOSE_LOG: Enable verbose logging (default: false)

    Returns:
        RouterConfig with loaded or default values
    """
```

---

## Error Handling

### Custom Exceptions

```python
class RouterError(Exception):
    """Base exception for router errors."""
    pass

class MalformedFrontmatterError(RouterError):
    """Raised when YAML frontmatter cannot be parsed."""
    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Malformed frontmatter in {path}: {reason}")

class RoutingFailedError(RouterError):
    """Raised when file routing fails after claim attempt."""
    def __init__(self, source: Path, destination: Path, reason: str):
        self.source = source
        self.destination = destination
        self.reason = reason
        super().__init__(f"Failed to route {source} to {destination}: {reason}")
```

---

## Usage Examples

### Basic Usage

```python
from router import route_inbox

# Route all eligible files
report = route_inbox("/path/to/vault")
print(f"Routed {report.routed_count} files")
for rf in report.routed_files:
    print(f"  {rf.source.name} -> {rf.destination.name}")
    print(f"    Rules: {', '.join(rf.matched_rules)}")
```

### Dry Run

```python
from router import route_inbox

# Preview what would be routed
report = route_inbox("/path/to/vault", dry_run=True)
print(f"Would route {report.routed_count} files")
```

### Custom Configuration

```python
from router import route_inbox, RouterConfig

config = RouterConfig(
    vault_path="/custom/vault",
    sla_threshold_hours=4,
    urgency_keywords=["urgent", "critical", "p0"],
    verbose_logging=True
)

report = route_inbox(config.vault_path, config=config)
```

### Single File Evaluation

```python
from router import evaluate_file

result = evaluate_file("/vault/Inbox/email/urgent-email.md")
if result.should_route:
    print(f"Would route due to: {result.matched_rules}")
else:
    print("No matching rules")
```

---

## Integration with Existing Components

### Watcher Integration

```python
# In src/sentinel/watcher.py
from router import route_inbox

class VaultWatcher:
    def on_file_created(self, event):
        if "/Inbox/email/" in str(event.src_path):
            # Trigger routing after new email arrives
            route_inbox(self.vault_path)
```

### CLI Integration

```python
# In src/router/__main__.py
import click
from router import route_inbox

@click.command()
@click.option("--vault", default=".", help="Vault path")
@click.option("--dry-run", is_flag=True, help="Preview only")
def main(vault: str, dry_run: bool):
    """Route emails from Inbox to Needs_Action."""
    report = route_inbox(vault, dry_run=dry_run)
    click.echo(f"Scanned: {report.total_scanned}")
    click.echo(f"Routed: {report.routed_count}")
    click.echo(f"Skipped: {report.skipped_count}")
    click.echo(f"Errors: {report.error_count}")

if __name__ == "__main__":
    main()
```

---

## Idempotency Guarantee

The router is idempotent:
- Files already in `/Needs_Action/email/` are not re-processed
- Running router multiple times on the same inbox state produces the same result
- Claim-by-move ensures no duplicate moves on concurrent runs
