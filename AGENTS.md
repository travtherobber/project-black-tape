# AGENTS.md — PROJECT BLACK-TAPE OVERHAUL

## System Role
You are operating on a structured codebase with supplemental context files.
Act as a senior full-stack engineer maintaining and extending this hosted-tool overhaul.

---

## Context Sources (READ FIRST)
1. PROJECT_CONTEXT.md → authoritative architecture + intent
2. actual repository files → source of truth for all edits

Priority:
- PROJECT_CONTEXT.md → understanding
- repo files → editing

---

## Context Maintenance
- Keep PROJECT_CONTEXT.md up to date when:
  - new features are added
  - architecture changes
  - new files/modules are introduced
  - data flow changes
- Updates must be minimal and precise
- Do NOT rewrite the entire file unless absolutely necessary

---

## Architecture
Hosted-tool split:
black_tape_engine → vault service → Flask API/UI → frontend console

---

## Core Files
- run.py (local entrypoint)
- src/black_tape_web/__init__.py (app factory)
- src/black_tape_web/blueprints/api.py
- src/black_tape_web/blueprints/ui.py
- src/black_tape_web/services/vault_service.py
- src/black_tape_engine/engine.py
- src/black_tape_engine/legacy_core/orchestrator.py

---

## Data Flow
Upload → /upload
→ VaultService.create_job()
→ background ingestion thread
→ BlackTapeEngine.process_file()
→ cache store
→ API endpoints
→ frontend render

---

## Planning Protocol
For any non-trivial task, you MUST create or update:
DEV_PLAN.md

### DEV_PLAN.md Format

# Goal
Clear description of the objective

# Current State
What exists now:
- bugs
- limitations
- relevant structure

# Planned Finished State
What the system should look like after completion

# Checklist
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

# Actual Result
(to be filled after completion)
- What worked
- What didn’t
- Side effects
- Follow-up work

---

## Execution Rules
- Do NOT begin implementation until DEV_PLAN.md exists or is updated
- Break work into small, atomic steps
- Check off checklist items as they are completed
- After finishing, complete the "Actual Result" section
- Log important assumptions inside DEV_PLAN.md during debugging

---

## When Planning is Required
Create/update DEV_PLAN.md when:
- modifying backend logic
- changing data flow
- touching multiple files
- debugging non-obvious issues
- adding features

Skip planning ONLY when:
- making small, isolated edits
- fixing obvious syntax errors
- adjusting UI text/styles without logic impact

---

## Debug Discipline
When something breaks:
1. Verify API response first
2. Check cache and job state
3. Trace VaultService
4. Trace BlackTapeEngine / orchestrator
5. Then inspect frontend rendering

Never start with frontend assumptions.

### Logging Requirement
- Be thorough about logging whenever a process can fail, crash, or be interrupted
- Logs must make it obvious:
  - what step started
  - what step completed
  - what input or job ID was being processed
  - what failed
  - where the process should resume or restart from
- Prefer structured, checkpoint-style logs over vague status messages
- Long-running or background work must emit enough state to reconstruct progress after interruption
- If a process is restartable, log the restart boundary explicitly
- If a process is not safely restartable, log the last durable checkpoint and the reason

---

## Frontend Notes
- Primary dashboard route: `/` and `/dashboard`
- UI files:
  - src/black_tape_web/templates/layout.html
  - src/black_tape_web/templates/pages/*.html
  - src/black_tape_web/static/css/style.css
  - src/black_tape_web/static/css/pages/home.css
  - src/black_tape_web/static/js/main.js
  - src/black_tape_web/static/js/dashboard.js

---

## Backend Notes
- Flask app factory + blueprints
- Background ingestion runs in a thread
- Data stored in diskcache
- Engine and web app are intentionally separated
- Background and hosted workflows should be instrumented so crashes and restarts are traceable

---

## Data Model
- chats = {conversation_id: [messages]}
- gps = [coordinates/events]

---

## Rules
- Always trace full data flow before modifying logic
- Prefer minimal, targeted fixes over large rewrites
- Preserve the engine/web separation
- Keep the hosted deployment shape intact
- When adding or changing process logic, include explicit logging for failure paths and restart checkpoints

---

## Constraints
- Do not introduce unnecessary dependencies
- Do not change data structures without updating all dependent layers
- Do not collapse the separated engine and web layers back together

---

## Priority Tasks
- Mature the hosted ingestion flow
- Rebuild conversation and map views on top of the new architecture
- Keep the atmospheric dashboard consistent with the new UI direction
- Maintain a clean boundary between engine processing and the web interface
