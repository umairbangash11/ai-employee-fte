# AI Employee FTE

A **local-first autonomous AI system** for managing business operations. This project acts as a digital full-time employee (FTE) that monitors your communications, triages tasks, and helps execute actions with human-in-the-loop approval.

## Overview

AI Employee FTE is built around an **Obsidian vault** as its central workspace. It monitors multiple input sources (Gmail, WhatsApp, local files), uses AI to classify and triage items, and routes them through a structured approval workflow.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Gmail     │     │  WhatsApp   │     │ Local Files │
│   Watcher   │     │  Watcher    │     │  Sentinel   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                    ┌─────────────┐
                    │   /Inbox    │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ Orchestrator│  ◄── OpenAI (gpt-4o)
                    │   (Brain)   │
                    └──────┬──────┘
                           ▼
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │/Needs_Action│          │    /Done    │
       └──────┬──────┘          └─────────────┘
              ▼
       ┌─────────────┐
       │  /Approved  │  ◄── Human Review
       └──────┬──────┘
              ▼
       ┌─────────────┐
       │  Execution  │  (LinkedIn, Facebook, Email Replies)
       └─────────────┘
```

## Features

### Watchers (Input Sources)
- **Gmail Watcher** - Monitors Gmail via OAuth API, captures unread emails as Markdown
- **WhatsApp Watcher** - Browser automation (Playwright) to capture messages
- **Filesystem Sentinel** - Watches local directories for new files

### AI-Powered Orchestration
- **Email Triage** - Classifies emails using OpenAI to determine if reply is needed
- **Draft Generation** - Automatically generates draft replies for human review
- **Smart Routing** - Routes items to appropriate folders based on urgency and type

### Human-in-the-Loop (HITL) Approval
- **Pending Approval Queue** - Actions wait for human approval before execution
- **Audit Trail** - Every action is logged with full context
- **Safety-First** - No external actions without explicit human consent

### Publishers (Output Actions)
- **LinkedIn Publisher** - Publishes approved posts via Playwright
- **Facebook Publisher** - Publishes approved posts via Playwright
- **Email Drafts** - Prepares draft replies for human review and sending

### Resilience Layer (Feature 015)
Every subsystem is wrapped by a shared resilience module that handles transient failures uniformly and surfaces health state to external watchdogs.

- **Retry with exponential backoff** — `ralph_wiggum_loop()` implements Constitution Principle V (3 attempts + simplified fallback + jitter).
- **Circuit breaker** — external APIs (Gmail, OpenAI, LinkedIn, Facebook) are protected by a `CircuitBreaker` that fast-fails after 5 failures in 60s, auto-retries after 30s (`HALF_OPEN` probe).
- **Structured failure logs** — every failure writes a Markdown file to `vault/Logs/` with YAML frontmatter matching FR-005 schema (log_id, timestamp, subsystem, failure_category, error_code, retry_count, is_final_failure).
- **Failed-item routing** — items whose processing exhausts retries are moved to `Needs_Action/<source>/failed/` with a recovery wrapper preserving the original content.
- **Health files** — each subsystem writes `.watcher-state/<subsystem>_health.json` per poll; `sentinel-status` aggregates across all 7 subsystems.
- **Standardized exit codes** — 0=success, 1=recoverable, 2=configuration, 3=fatal. PM2/systemd can key restart policy on the exit code.

See [`specs/015-error-recovery-resilience/quickstart.md`](specs/015-error-recovery-resilience/quickstart.md) for the full operator guide.

## Vault Structure

The system uses a canonical folder structure:

```
vault/
├── Inbox/              # Incoming items awaiting triage
│   ├── email/          # Captured emails
│   └── whatsapp/       # Captured messages
├── Needs_Action/       # Items requiring human or AI decision
│   └── drafts/         # AI-generated draft replies
├── Pending_Approval/   # Actions awaiting human approval
│   ├── linkedin/       # LinkedIn posts pending approval
│   └── facebook/       # Facebook posts pending approval
├── Approved/           # Plans and scripts cleared for execution
├── Done/               # Completed artifacts and archives
└── Logs/               # Execution logs and audit trails
```

## Installation

### Prerequisites
- Python 3.12+
- An Obsidian vault (or any folder to use as your workspace)
- OpenAI API key
- Gmail OAuth credentials (for email monitoring)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/umairbangash11/ai-employee-fte.git
   cd ai-employee-fte
   ```

2. **Create and activate virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Install Playwright browsers** (for WhatsApp/LinkedIn/Facebook)
   ```bash
   playwright install chromium
   ```

5. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   # Required
   VAULT_PATH=/path/to/your/obsidian/vault
   OPENAI_API_KEY=sk-your-openai-api-key

   # Optional
   OPENAI_MODEL=gpt-4o
   BRAIN_POLL_INTERVAL=1.0
   ```

6. **Set up Gmail OAuth** (for email monitoring)

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable the Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials and save as `secrets/credentials.json`
   - Run the Gmail watcher once to complete OAuth flow

## Usage

### Initialize the Vault

First, initialize your vault with the required folder structure:

```bash
sentinel init
```

### Start the Watchers

**Gmail Watcher** - Monitor emails:
```bash
gmail-watcher
```

**WhatsApp Watcher** - Monitor WhatsApp (requires initial QR scan):
```bash
whatsapp-watcher
```

**Filesystem Sentinel** - Monitor local files:
```bash
sentinel watch
```

### Start the Orchestrator

The orchestrator (Brain) triages incoming items:

```bash
python -m src.orchestrator.brain
```

### HITL Approval Workflow

Check pending approvals:
```bash
hitl-approval list
```

Watch for approved items and execute:
```bash
hitl-approval watch
```

### Social Media Publishing

Publish to LinkedIn (from approved posts):
```bash
linkedin-publish watch
```

Publish to Facebook (from approved posts):
```bash
facebook-publish watch
```

## CLI Commands

### Core pipeline

| Command | Description |
|---------|-------------|
| `sentinel init` | Initialize vault folder structure |
| `sentinel watch` | Start filesystem watcher |
| `gmail-watcher` | Start Gmail monitoring |
| `whatsapp-watcher` | Start WhatsApp monitoring |
| `email-reasoner` | Run email classification |
| `hitl-approval` | Manage approval workflow |
| `linkedin-publish` | LinkedIn publishing automation |
| `facebook-publish` | Facebook publishing automation |

### Resilience / operator CLIs (Feature 015)

| Command | Description |
|---------|-------------|
| `sentinel-status` | Aggregate health across all subsystems (reads `.watcher-state/*_health.json`). `--json` for machine-readable output, `--subsystem NAME` to filter, `--state-dir PATH` to point at an alternate state dir. Exit: 0=healthy, 1=degraded, 2=unhealthy. |
| `sentinel-recover list` | List all items in `Needs_Action/*/failed/`. Supports `--subsystem`, `--since`, `--json`. |
| `sentinel-recover retry PATH` | Re-queue a single failed item; `--force` allows re-queuing non-retryable items. |
| `sentinel-recover retry-all --subsystem NAME` | Re-queue every failed item for a subsystem. `--dry-run` to preview. |
| `sentinel-recover purge --older-than N` | Delete wrappers older than N days (integer). `--dry-run`, `--yes`, `--subsystem` available. Always creates a backup tarball under `.watcher-state/`. |

Each watcher `__main__` also exposes `--health-file` and `--log-dir` flags for external watchdog integration (PM2/systemd).

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_PATH` | Path to your Obsidian vault | `.` |
| `OPENAI_API_KEY` | OpenAI API key for AI features | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |
| `BRAIN_POLL_INTERVAL` | Orchestrator polling interval (seconds) | `1.0` |

### Gmail OAuth Setup

1. Create credentials at [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API for your project
3. Create OAuth 2.0 credentials (Desktop app type)
4. Save credentials to `secrets/credentials.json`
5. Run `gmail-watcher` - it will open a browser for OAuth consent
6. Tokens are stored in `.watcher-state/` (gitignored)

## Project Structure

```
ai-employee-fte/
├── src/
│   ├── sentinel/           # Core filesystem watcher
│   ├── gmail_watcher/      # Gmail API integration
│   ├── whatsapp_watcher/   # WhatsApp Playwright automation
│   ├── orchestrator/       # AI orchestration (Brain)
│   ├── router/             # Email routing rules
│   ├── email_reasoner/     # Email classification
│   ├── hitl_approval/      # Human-in-the-loop system
│   ├── linkedin_publisher/ # LinkedIn automation
│   ├── facebook_publisher/ # Facebook automation
│   └── resilience/         # Shared resilience layer (retry, circuit, health, CLIs)
├── tests/                  # Test suite
├── docs/                   # Operator guides (demo script, troubleshooting)
├── specs/                  # Feature specifications
├── .specify/               # SpecifyPlus framework
├── pyproject.toml          # Python project config
└── .env                    # Environment variables (create this)
```

## Safety & Security

This project follows strict safety principles:

1. **No Secrets in Code** - All credentials stored in `.env` (gitignored)
2. **Human-in-the-Loop** - No external actions without human approval
3. **Audit Trail** - Every action logged to `/Logs`
4. **Local-First** - All processing happens locally; cloud APIs for AI inference only
5. **Execution Plans** - System writes plans to `/Approved` before any action

## Development

### Running Tests

```bash
pytest
```

### Development Workflow

This project uses [SpecifyPlus](https://github.com/specify-dev/specifyplus) for spec-driven development:

```bash
source venv/bin/activate
sp --help  # SpecifyPlus CLI
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the spec-driven workflow (see `.specify/memory/constitution.md`)
4. Submit a pull request

## Documentation

- **[Quickstart (Resilience)](specs/015-error-recovery-resilience/quickstart.md)** — operator guide for `sentinel-status`, `sentinel-recover`, health files, exit codes, PM2/systemd integration.
- **[Demo Script](docs/demo-script.md)** — 10-minute end-to-end walkthrough: capture → triage → failure cascade → recovery.
- **[Troubleshooting](docs/troubleshooting.md)** — symptom-to-fix field guide for Gmail auth, WhatsApp sessions, circuit breaker stuck open, failed queue handling, missing subsystems.
- **[Gmail API Setup](docs/gmail-api-setup.md)** — step-by-step OAuth setup.

## Acknowledgments

- Built with [OpenAI](https://openai.com/) for AI capabilities
- Uses [Playwright](https://playwright.dev/) for browser automation
- Integrates with [Obsidian](https://obsidian.md/) for note management
- Developed using [SpecifyPlus](https://github.com/specify-dev/specifyplus) framework
