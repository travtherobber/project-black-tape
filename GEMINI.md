# Project Black-Tape: System Context

Welcome to **Project Black-Tape**, a specialized chat analysis and visualization platform designed with a high-performance "Redline Protocol" for signal exploration and tactical search.

## Project Overview

- **Mission:** Ingest, normalize, and visualize disparate chat logs (Snapchat, Instagram, etc.) into a unified, chronological stream.
- **Geospatial Intelligence:** Extract and map GPS signal packets from location and memories history.
- **Chrono-Alignment:** Global timezone management for normalized cross-platform forensic analysis.
- **Backend:** Python/Flask application following a modular pipeline architecture (Ingest -> Scan -> Align -> Search).
- **Frontend:** A modern "Holographic" UI built with Vanilla JavaScript, CSS, and Leaflet.js.

## Key Features

### 1. Tactical Search & Analysis
- **Advanced Search:** Supports exact matches (`"word"`), exclusions (`-[term]`), and logical grouping (`(a, b)`).
- **On-Demand Loading:** Optimized for performance; fetches detailed conversation data only when required.
- **Signal Metadata:** Direct access to raw forensic metadata for every signal packet.

### 2. Geospatial Mapping
- **GPS Extraction:** Automatically identifies coordinate pairs in `location_history.json` and `memories_history.json`.
- **Interactive Intel:** Real-time map population with tactical markers and movement bounds.

### 3. Global Chrono-Zone
- **Dynamic Conversion:** Sidebar selector for real-time conversion of all UTC signals to local timezones (EST, PST, JST, etc.).
- **Persistence:** User timezone preference is maintained across sessions via `localStorage`.

## System Architecture

### 1. Data Pipeline (`core/`)
- **`orchestrator.py`:** Pipeline coordinator. Routes data to `ChatScanner` and `GPSScanner`.
- **`scanners/`**: Specialized heuristic extractors for various JSON structures.
- **`data_aligner.py`:** Platform normalization logic.

### 2. API & Vault Management (`app.py`)
- **`VaultManager`:** In-memory signal cache with TTL support.
- **`/api/conversations`**: Metadata list for sidebar navigation.
- **`/api/gps`**: Payload for geospatial intelligence mapping.

## Building and Running

### Local Setup
```bash
pip install -r requirements.txt
python app.py
```

### Deployment (Render)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

---
*System initialization complete. Redline Protocol active.*
