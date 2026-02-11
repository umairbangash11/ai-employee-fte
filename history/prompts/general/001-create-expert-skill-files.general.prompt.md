---
id: 001
title: Create Expert Skill Files
stage: general
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: umair
command: none
labels: ["skills", "setup", "project-config"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .claude/skills/infra_watcher_manager.md
  - .claude/skills/data_vault_manager.md
  - .claude/skills/action_mcp_integrator.md
  - .claude/skills/logic_orchestrator.md
  - .claude/skills/biz_ops_specialist.md
  - .claude/skills/security_qa_engineer.md
tests:
  - none
---

## Prompt

i need to establish my expert skills. please create a folder named .claude/skills and then create these 6 markdown files inside it with following content: 1. create .claude/skills/infra_watcher_manager.md: 'Expert in python sentinel scripts for Gmail and whatsapp monitoring.' 2. Create .claude/skills/data_vault_manager.md: 'expert in obsidian structure and file lifecycle management.' 3. create .claude/skills/action_mcp_integrator.md 'expert in mcp servers and hitl safety protocols.' 4. Create .claude/skills/logic_orchestrator.md: 'Expert in Ralph Wiggum persistence loops and autonomous task completion.' 5. Create .claude/skills/biz_ops_specialist.md: 'Expert in auditing, Odoo ERP integration, and business metrics.' 6. Create .claude/skills/security_qa_engineer.md: 'Expert in audit logs, system recovery, and error handling.' Once created, list the files to confirm.

## Response snapshot

Created .claude/skills/ directory and all 6 skill markdown files successfully. Each file contains the expert capability description. Files confirmed via ls command showing all 6 files present in the directory.

## Outcome

- ✅ Impact: Established expert skill definitions for project; enabled capability-driven agent specialization
- 🧪 Tests: File existence verification via ls; directory structure confirmed
- 📁 Files: 6 skill definition files created in .claude/skills/
- 🔁 Next prompts: Configure skill routing in agent system; define skill selection criteria
- 🧠 Reflection: Successfully created skill foundation for multi-agent system; clear descriptions enable proper role assignment

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): PASS - all files created and verified
- Prompt variant (if applicable): null
- Next experiment: Integrate skills with agent selection logic
