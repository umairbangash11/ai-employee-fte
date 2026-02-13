---
id: 009
title: Swap Anthropic to OpenAI SDK
stage: refactor
date: 2026-02-12
surface: agent
model: claude-opus-4-6
feature: vault-sentinel
branch: 001-vault-sentinel
user: umair
command: /sp.implement
labels: ["openai", "gpt-4o", "refactor", "sdk-swap", "orchestrator"]
links:
  spec: specs/001-vault-sentinel/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/orchestrator/brain.py
  - pyproject.toml
  - .env.example
  - CLAUDE.md
  - specs/001-vault-sentinel/tasks.md
tests:
  - Syntax validation (ast.parse) — PASS
  - load_config reads OPENAI_API_KEY and OPENAI_MODEL — PASS
  - parse_email_frontmatter unchanged behavior — PASS
  - InboxTriageHandler accepts OpenAI client, model=gpt-4o — PASS
  - classify_email type hint is OpenAI (not anthropic.Anthropic) — PASS
  - Zero 'anthropic' or 'ANTHROPIC' references in source — PASS
  - IDE diagnostics — 0 errors
---

## Prompt

Update logic_orchestrator.md to use the OpenAI Python SDK instead of Anthropic. Ensure it uses the 'gpt-4o' model for email classification and draft generation while maintaining the same vault routing logic.

## Response snapshot

Refactored src/orchestrator/brain.py from Anthropic SDK to OpenAI SDK. Changes: replaced `import anthropic` with `from openai import OpenAI`, rewrote `classify_email()` to use `client.chat.completions.create()` with system/user message format (OpenAI chat completions API), updated `load_config()` to read `OPENAI_API_KEY`/`OPENAI_MODEL` (default: gpt-4o), updated type hints on `InboxTriageHandler.__init__` and `start_brain()` from `anthropic.Anthropic` to `OpenAI`, changed default model from `claude-sonnet-4-5-20250929` to `gpt-4o`, updated error message for missing API key. Also swapped `anthropic>=0.40` to `openai>=1.0` in pyproject.toml, updated .env.example, and updated CLAUDE.md Active Technologies. All vault routing logic (Needs_Action/drafts/, Approved/ execution plans, Logs/, Ralph Wiggum retry) unchanged.

## Outcome

- ✅ Impact: LLM provider swapped from Anthropic to OpenAI with zero behavior change in vault routing
- 🧪 Tests: 7 automated checks passed (syntax, config, frontmatter, handler, type hints, no-remnants, diagnostics)
- 📁 Files: 5 files modified
- 🔁 Next prompts: Set OPENAI_API_KEY in .env for end-to-end test; consider making LLM provider configurable
- 🧠 Reflection: Clean SDK swap — OpenAI chat completions API maps closely to Anthropic messages API. Response extraction changed from `message.content[0].text` to `response.choices[0].message.content`. System prompt moved from kwarg to message array.

## Evaluation notes (flywheel)

- Failure modes observed: none — straightforward 1:1 API mapping
- Graders run and results (PASS/FAIL): 7/7 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add response_format={"type":"json_object"} to OpenAI call for guaranteed JSON output
