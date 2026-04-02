# Project Black-Tape Overhaul

This repo is the overhaul workspace for the next version of Black-Tape.

It is intentionally separate from `Project-Blacktape-Main`. The goal here is to split the system into two clearer parts:

- `black_tape_engine`: the Python ingestion/search tool
- `black_tape_web`: the hosted web application that calls into the engine

## Why this structure

The current `Main` repo mixes ingestion logic, cache handling, routes, templates, and UI concerns in one place. This overhaul creates a boundary so the Python tool can run as a web-hosted service instead of the web app and engine being tightly interwoven.

## Layout

```text
src/
  black_tape_engine/
    engine.py
    legacy_core/
    legacy_ingesters/
    legacy_scanners/
    legacy_processors/
    legacy_exporters/
    legacy_display/
  black_tape_web/
    __init__.py
    blueprints/
    services/
    templates/
    static/
run.py
pyproject.toml
```

## Current state

- The legacy processing code has been copied in as a migration base.
- The new Flask app uses an app factory plus blueprints.
- The web layer talks to the engine through a `VaultService`.
- Existing frontend routes were preserved where practical so the current UI can keep functioning while the overhaul proceeds.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app will start on `http://127.0.0.1:5000`.

## Deploy on Render

This repo is ready for Render with the included [`render.yaml`](./render.yaml).

Minimum environment variables:

```env
SECRET_KEY=<long-random-secret>
SESSION_COOKIE_SECURE=1
```

Optional:

```env
BLACKTAPE_PASSWORD=<deployment-password>
```

Leave `BLACKTAPE_PASSWORD` unset if you want the app to be openly accessible without a login wall.

Recommended privacy setting:

```env
BLACKTAPE_CACHE_TTL=900
```

That keeps uploaded vault data for 15 minutes before it is expired and actively cleaned from the server cache.

Render will run the app with:

```bash
gunicorn -c gunicorn.conf.py run:app
```

Runtime notes:

- uploads and cache data are written to `/tmp/black-tape-instance` by default on Render
- the filesystem is ephemeral, so uploaded vault data will not persist across redeploys or restarts
- uploaded files are deleted immediately after ingestion, and parsed vault data expires automatically after `BLACKTAPE_CACHE_TTL` seconds
- if you need persistence later, move cache/upload storage to a persistent disk or external store

## Privacy

- this repo should not contain real account exports, screenshots, or raw archive files
- tests use synthetic in-memory fixtures rather than committed personal datasets
- local secrets and raw exports are excluded with `.gitignore`
