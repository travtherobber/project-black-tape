# Project Black-Tape

A modern, futuristic chat analysis and visualization platform designed for high-performance signal exploration. Project Black-Tape provides a sophisticated interface for ingesting disparate chat logs, normalizing them into a unified chronological stream, and performing advanced tactical searches.

## Core Features

- **Device-Agnostic Ingestion:** Support for multiple chat export formats (Snapchat, Instagram, etc.) with heuristic-based field mapping.
- **Advanced Tactical Search:** Global message search supporting exact word matches (`"word"`), phrase grouping (`(exact phrase)`), unordered requirements (`(term1, term2)`), and exclusions (`-[term]`).
- **Dynamic Chronological Sorting:** Instantly toggle between newest-first and oldest-first perspectives.
- **Holographic UI:** A modern sci-fi aesthetic featuring glowing gradients, scanline textures, and a responsive, device-agnostic layout.
- **Session Persistence:** Local vault synchronization ensures your analyzed data persists across browser refreshes while remaining entirely under your control.

## System Architecture

### Backend (Python/Flask)
- `app.py`: Core application entry point and API route management.
- `core/orchestrator.py`: Pipeline coordinator for data ingestion and normalization.
- `core/data_aligner.py`: Schema normalization logic for heterogeneous data sources.
- `scanners/chat_scanner.py`: Heuristic extraction of chat signals from raw JSON.

### Frontend (JavaScript/CSS)
- `static/js/chat.js`: Interactive chat explorer and search engine.
- `static/js/main.js`: Global system logic and data ingestion handling.
- `static/css/style.css`: Global sci-fi UI framework and tactical textures.
- `static/css/pages/chat.css`: Specialized styling for holographic message blocks and FAB controls.

## Getting Started

1. **Environment Setup:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch System:**
   ```bash
   python app.py
   ```
   The interface will be accessible at `http://localhost:5000`.

3. **Analyze Data:**
   Navigate to the Dashboard, upload a supported JSON chat history, and hand off the signal to the Analysis Viewer.

## Engineering Standards

Project Black-Tape is built with a focus on:
- **Performance:** Optimized search and rendering logic for large datasets.
- **Clarity:** Professional, well-documented code designed for maintainability and extension.
- **Security:** In-memory caching with TTL-enabled purging and local-only persistence.

---
*Initializing Redline Protocol...*
