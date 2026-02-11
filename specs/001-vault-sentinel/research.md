# Research: Vault Sentinel

**Feature**: 001-vault-sentinel
**Date**: 2026-02-11

## R1: Filesystem Watching Library

**Decision**: watchdog 6.0+

**Rationale**: Industry-standard Python filesystem monitoring
library. Uses inotify on Linux (including WSL2) for efficient
event-driven watching. Actively maintained, compatible with
Python 3.12, extensive documentation and community support.

**Alternatives considered**:

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| watchdog | Mature, inotify backend, broad docs | Slightly heavier than watchfiles | Selected |
| watchfiles | Rust backend, faster | Smaller ecosystem, less documentation | Rejected — overkill for single-folder watch |
| polling (os.listdir loop) | Zero dependencies | CPU-inefficient, no event granularity | Rejected |

## R2: File Stability Detection

**Decision**: Size-stability polling pattern — check file size
at intervals; consider file "ready" when size is unchanged for
0.5 seconds.

**Rationale**: Cross-platform, handles partial writes from any
source (browser downloads, `cp`, `scp`, etc.). On Linux/WSL2,
`IN_CLOSE_WRITE` is available via inotify but the polling
pattern is more portable and handles edge cases better.

**Parameters**:
- `check_interval`: 0.1 seconds
- `stable_duration`: 0.5 seconds
- `timeout`: 30 seconds

## R3: File Move Strategy

**Decision**: `shutil.move()` for file relocation.

**Rationale**: Handles cross-device moves (falls back to
copy+delete), returns the destination path for logging, and is
part of the Python standard library (no extra dependency).

## R4: WSL2 Considerations

**Key findings**:
- inotify events ONLY work reliably on WSL2-native filesystem
  (`~/...`), NOT on Windows-mounted drives (`/mnt/c/...`).
- Default inotify watch limit (8192) is sufficient for a
  single-folder watch.
- The vault MUST reside on the WSL2 filesystem for reliable
  operation.

## R5: CLI Framework

**Decision**: `argparse` (standard library).

**Rationale**: Two commands (`init` and `watch`) with minimal
options. No need for a third-party CLI framework at Bronze Tier.
`click` considered but adds a dependency for minimal benefit.

## R6: Log Format

**Decision**: One Markdown file per action in `Logs/`, named
with ISO timestamp and action slug
(e.g., `2026-02-11T14-30-00_moved_report.txt.md`).

**Rationale**: Obsidian-compatible (per constitution), one file
per event enables easy searching and linking. YAML frontmatter
for structured metadata, Markdown body for human readability.

## R7: Execution Plan Format (Constitution Principle IV)

**Decision**: One Markdown file per planned action in `Approved/`,
written atomically before the move executes. After successful
execution, the plan file remains as an audit record.

**Rationale**: Constitution Principle IV requires a plan in
`/Approved` before any system-modifying action. At Bronze Tier,
this is a lightweight structured log rather than a full
approval workflow.
