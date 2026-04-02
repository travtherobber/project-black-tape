# PROJECT BLACK-TAPE OVERHAUL

## Purpose
Hosted web tool that ingests exported data, processes it through a separated Python engine layer, and presents results through a dedicated forensic-interface web application.

## Core Architecture
1. Engine Layer
   - `src/black_tape_engine/engine.py`
   - legacy processing modules copied under:
     - `legacy_core/`
     - `legacy_ingesters/`
     - `legacy_scanners/`
     - `legacy_processors/`
     - `legacy_exporters/`

2. Web Layer
   - `src/black_tape_web/__init__.py` → Flask app factory
   - `src/black_tape_web/blueprints/api.py`
   - `src/black_tape_web/blueprints/ui.py`
   - `src/black_tape_web/services/vault_service.py`

3. Frontend
   - Templates:
     - `src/black_tape_web/templates/layout.html`
     - `src/black_tape_web/templates/pages/*.html`
   - JS:
     - `src/black_tape_web/static/js/main.js`
     - `src/black_tape_web/static/js/dashboard.js`
   - CSS:
     - `src/black_tape_web/static/css/style.css`
     - `src/black_tape_web/static/css/pages/home.css`

## API Flow
Upload → `/upload`
→ `VaultService.create_job()`
→ background ingestion thread
→ `BlackTapeEngine.process_file()`
→ cache results
→ UI/API reads:
  - `/api/vault/status`
  - `/api/conversations`
  - `/api/conversations/<id>`
  - `/api/gps`
  - `/api/search`

## Backend Notes
- Uses Flask + diskcache
- `run.py` is the local entrypoint
- The web layer owns request/session/cache orchestration
- The engine layer owns processing/search behavior
- Long-running and background flows should log durable checkpoints so restart points are visible after crashes or interruptions

## Frontend Direction
- The dashboard is a submerged forensic intelligence console
- The primary route is a three-column operational surface
- Panels are transparent wireframe containment volumes, not standard cards
- Motion is slow and restrained: abyss particles, sonar sweep, target pulses

## Data Model
- chats = {conversation_id: [messages]}
- gps = [coordinates/events]

## Important Files
- `run.py`
- `src/black_tape_web/__init__.py`
- `src/black_tape_web/services/vault_service.py`
- `src/black_tape_engine/engine.py`
- `src/black_tape_engine/legacy_core/orchestrator.py`
- `src/black_tape_web/templates/pages/home.html`
- `src/black_tape_web/static/js/dashboard.js`

## Current Focus
- Finalize hosted-tool UX and route rebuilds
- Keep architecture documentation synchronized with real code changes
- Preserve the engine/web separation while replacing legacy UI flows
- Improve operational logging so interrupted processing can resume from known checkpoints
