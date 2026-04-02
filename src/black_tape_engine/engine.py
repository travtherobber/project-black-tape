from __future__ import annotations

from black_tape_engine.legacy_core.orchestrator import Orchestrator
from black_tape_engine.legacy_core.search_engine import SignalSearch


class BlackTapeEngine:
    """Thin boundary around the legacy processing engine."""

    def __init__(self, cache_dir: str, status_ttl: int = 3600):
        self._orchestrator = Orchestrator(cache_dir=cache_dir, status_ttl=status_ttl)

    def process_file(self, job_id: str, filename: str, file_path: str) -> dict:
        return self._orchestrator.process_file(job_id, filename, file_path)


class EngineSearch:
    """Search boundary so the web layer does not import legacy modules directly."""

    @staticmethod
    def execute(chat_data: dict, query: str) -> list[dict]:
        engine = SignalSearch(chat_data)
        return engine.execute(query)
