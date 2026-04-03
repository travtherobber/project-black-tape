import os
import time
import logging
import diskcache
from datetime import datetime
from black_tape_engine.legacy_ingesters.json_ingestor import JSONIngestor
from black_tape_engine.legacy_ingesters.zip_ingestor import ZipIngestor
from black_tape_engine.legacy_scanners.chat_scanner import ChatScanner
from black_tape_engine.legacy_scanners.friends_scanner import FriendsScanner
from black_tape_engine.legacy_scanners.google_signal_scanner import GoogleSignalScanner
from black_tape_engine.legacy_scanners.gps_scanner import GPSScanner
from black_tape_engine.legacy_scanners.scanner import GenericScanner

# Initialize Logging
logger = logging.getLogger("BLACK-TAPE.ORCHESTRATOR")

class Orchestrator:
    def __init__(
        self,
        cache_dir=None,
        status_ttl=3600,
        max_files=256,
        max_json_bytes=32 * 1024 * 1024,
        max_total_bytes=80 * 1024 * 1024,
    ):
        self.json_ingestor = JSONIngestor()
        self.zip_ingestor = ZipIngestor(
            max_files=max_files,
            max_json_bytes=max_json_bytes,
            max_total_bytes=max_total_bytes,
        )
        self.chat_scanner = ChatScanner()
        self.friends_scanner = FriendsScanner()
        self.google_signal_scanner = GoogleSignalScanner()
        self.gps_scanner = GPSScanner()
        self.generic_scanner = GenericScanner()
        self.status_ttl = status_ttl

        # Use an injected cache directory so the web host controls storage location.
        if cache_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, ".vault_cache")

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
        self.cache.set(f"{job_id}_status", status, expire=self.status_ttl)

    def process_file(self, job_id, filename, file_path):
        """
        The Background Worker Engine.
        Processes data and populates the vault_structure.
        """
        vault_structure = {
            "chats": {},
            "gps": [],
            "google_signals": [],
            "identity": {},
            "friends": {"categories": {}, "ranking": {}},
        }
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

                    google_signals = self.google_signal_scanner.scan(sub_name, data)
                    if google_signals:
                        vault_structure["google_signals"].extend(google_signals)

                    generic_payload = self.generic_scanner.scan(sub_name, data)
                    self._merge_identity(vault_structure["identity"], generic_payload)

                    self._merge_friends(vault_structure["friends"], self.friends_scanner.scan(sub_name, data))

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

                    google_signals = self.google_signal_scanner.scan(filename, raw_data)
                    if google_signals:
                        vault_structure["google_signals"] = google_signals

                    # Identity/Generic Siphon
                    self._merge_identity(vault_structure["identity"], self.generic_scanner.scan(filename, raw_data))
                    self._merge_friends(vault_structure["friends"], self.friends_scanner.scan(filename, raw_data))

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

            if vault_structure["google_signals"]:
                vault_structure["google_signals"] = sorted(
                    vault_structure["google_signals"],
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

    def _merge_friends(self, target, payload):
        if not payload:
            return

        categories = payload.get("categories", {})
        for category, entries in categories.items():
            if category not in target["categories"]:
                target["categories"][category] = []
            target["categories"][category].extend(entries)

        if payload.get("ranking"):
            target["ranking"] = payload["ranking"]

    def _merge_identity(self, target, payload):
        if not payload:
            return
        if not target:
            target.update({
                "source_files": [],
                "identity_markers": {},
                "raw_metadata_count": 0,
            })

        source_file = payload.get("source_file")
        if source_file and source_file not in target["source_files"]:
            target["source_files"].append(source_file)
        target["identity_markers"].update(payload.get("identity_markers") or {})
        target["raw_metadata_count"] += int(payload.get("raw_metadata_count") or 0)

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
