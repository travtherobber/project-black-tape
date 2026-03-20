import os
import time
import logging
import diskcache
from datetime import datetime
from ingesters.json_ingestor import JSONIngestor
from ingesters.zip_ingestor import ZipIngestor
from scanners.chat_scanner import ChatScanner
from scanners.gps_scanner import GPSScanner
from scanners.scanner import GenericScanner

# Initialize Logging
logger = logging.getLogger("BLACK-TAPE.ORCHESTRATOR")

class Orchestrator:
    def __init__(self):
        self.json_ingestor = JSONIngestor()
        self.zip_ingestor = ZipIngestor()
        self.chat_scanner = ChatScanner()
        self.gps_scanner = GPSScanner()
        self.generic_scanner = GenericScanner()

        # Force absolute path to ensure both app.py and worker use the same folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, '.vault_cache')

        self.cache = diskcache.Cache(cache_dir)
        logger.info(f"Worker connected to Vault: {cache_dir}")

    def _update_job_progress(self, job_id, message_count, gps_count):
        """Drips partial counts into the cache for live UI updates."""
        status = {
            "status": "PROCESSING",
            "messages_found": message_count,
            "gps_found": gps_count,
            "last_update": time.time()
        }
        self.cache.set(f"{job_id}_status", status, expire=3600)

    def process_file(self, job_id, filename, file_path):
        """
        The Background Worker Engine.
        Processes data and populates the vault_structure.
        """
        vault_structure = {"chats": {}, "gps": [], "identity": {}}
        msg_total = 0
        gps_total = 0

        try:
            # 1. Branch: ZIP Archive or Single File
            if filename.endswith('.zip'):
                logger.info(f"[Job {job_id}] Siphoning ZIP Archive: {filename}")

                for sub_name, data in self.zip_ingestor.ingest_zip(file_path):
                    # Chat Siphon
                    signals = self._extract_messages(sub_name, data)
                    for cid, msgs in signals.items():
                        if cid not in vault_structure["chats"]:
                            vault_structure["chats"][cid] = []
                        vault_structure["chats"][cid].extend(msgs)
                        msg_total += len(msgs)

                    # GPS Siphon
                    gps_points = self.gps_scanner.scan(sub_name, data)
                    if gps_points:
                        vault_structure["gps"].extend(gps_points)
                        gps_total += len(gps_points)

                    self._update_job_progress(job_id, msg_total, gps_total)
                    time.sleep(0.01)

            else:
                # SINGLE JSON INGESTION
                logger.info(f"[Job {job_id}] Siphoning JSON: {filename}")
                with open(file_path, 'rb') as f:
                    raw_data = self.json_ingestor.ingest_file(f)

                    # Chat Extraction
                    signals = self._extract_messages(filename, raw_data)
                    for cid, msgs in signals.items():
                        vault_structure["chats"][cid] = msgs
                        msg_total += len(msgs)

                    # GPS Extraction
                    gps_points = self.gps_scanner.scan(filename, raw_data)
                    if gps_points:
                        vault_structure["gps"] = gps_points
                        gps_total = len(gps_points)

                    # Identity/Generic Siphon
                    vault_structure["identity"] = self.generic_scanner.scan(filename, raw_data)

                    self._update_job_progress(job_id, msg_total, gps_total)

            # 2. Final Alignment & Sorting
            for cid in vault_structure["chats"]:
                vault_structure["chats"][cid] = sorted(
                    vault_structure["chats"][cid],
                    key=lambda x: x["Created"]
                )

            if vault_structure["gps"]:
                vault_structure["gps"] = sorted(
                    vault_structure["gps"],
                    key=lambda x: x.get("timestamp", 0)
                )

            return vault_structure

        except Exception as e:
            logger.error(f"[Job {job_id}] Pipeline failure: {str(e)}", exc_info=True)
            return None

    def _extract_messages(self, filename, raw_data):
        """Helper to process raw scanner results into structured chat blocks."""
        extracted = self.chat_scanner.scan(filename, raw_data)
        if not extracted:
            return {}

        conversations = {}
        for msg in extracted:
            convo_id = msg.get("conversation") or "GENERAL_SIGNAL"
            if convo_id not in conversations:
                conversations[convo_id] = []

            is_sender = msg.get("is_sender_flag")
            if is_sender is None:
                is_sender = self._is_outbound(msg.get("sender"))

            conversations[convo_id].append({
                "Content": msg.get("text") or "[NO_CONTENT]",
                "Created": self._safe_timestamp(msg.get("timestamp")),
                "IsSender": is_sender,
                "SenderName": msg.get("sender") or "Unknown",
                "Metadata": msg.get("metadata", {})
            })
        return conversations

    def _is_outbound(self, sender):
        """
        Generic Outbound Detection.
        Determines if a signal originated from the local account holder.
        """
        if not sender:
            return False

        system_self_markers = ["you", "me", "self", "owner", "user", "primary_account"]
        return str(sender).lower() in system_self_markers

    def _safe_timestamp(self, ts):
        """
        Normalizes heterogeneous temporal signals into a standard ISO-style string.
        """
        if not ts:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        try:
            if isinstance(ts, (int, float)):
                if ts > 1e11:
                    ts /= 1000
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

            if isinstance(ts, str):
                ts_clean = ts.replace(" UTC", "").replace("Z", "").replace("T", " ").strip()
                try:
                    dt = datetime.fromisoformat(ts_clean)
                    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except ValueError:
                    return ts if "UTC" in ts else f"{ts} UTC"
        except Exception:
            pass

        return f"{ts} UTC"
