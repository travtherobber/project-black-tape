from __future__ import annotations

from collections import Counter, defaultdict
import os
import threading
import time
import uuid

import diskcache
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from black_tape_engine import BlackTapeEngine, EngineSearch


class VaultService:
    def __init__(self, upload_root: str, cache_root: str, ttl_seconds: int):
        self.upload_root = upload_root
        self.cache = diskcache.Cache(cache_root)
        self.ttl_seconds = ttl_seconds
        self.engine = BlackTapeEngine(cache_dir=cache_root, status_ttl=ttl_seconds)

    def _purge_expired(self) -> None:
        self.cache.expire()
        self.cache.cull()

    def create_job(self, uploaded_files: list[FileStorage]) -> str:
        self._purge_expired()
        job_id = uuid.uuid4().hex
        os.makedirs(self.upload_root, exist_ok=True)
        saved_files: list[dict] = []
        original_names: list[str] = []
        for index, uploaded_file in enumerate(uploaded_files):
            filename = secure_filename(uploaded_file.filename) or f"{job_id}-{index}.bin"
            file_path = os.path.join(self.upload_root, f"{job_id}-{index}-{filename}")
            uploaded_file.save(file_path)
            saved_files.append({"filename": filename, "path": file_path})
            original_names.append(filename)

        self.cache.set(
            f"{job_id}_status",
            {
                "status": "PROCESSING",
                "messages_found": 0,
                "gps_found": 0,
                "source_files": original_names,
                "file_count": len(saved_files),
                "expires_at": int(time.time()) + self.ttl_seconds,
            },
            expire=self.ttl_seconds,
        )

        thread = threading.Thread(
            target=self._background_ingestion,
            args=(job_id, saved_files),
            daemon=True,
        )
        thread.start()
        return job_id

    def reset_expiry(self, job_id: str) -> bool:
        self._purge_expired()
        status_key = f"{job_id}_status"
        data_key = f"{job_id}_data"
        status = self.cache.get(status_key)
        if not status:
            return False

        expires_at = int(time.time()) + self.ttl_seconds
        next_status = dict(status)
        next_status["expires_at"] = expires_at
        self.cache.set(status_key, next_status, expire=self.ttl_seconds)

        data = self.cache.get(data_key)
        if data is not None:
            self.cache.set(data_key, data, expire=self.ttl_seconds)

        return True

    def _merge_results(self, target: dict, incoming: dict) -> None:
        for convo_id, messages in (incoming.get("chats") or {}).items():
            target["chats"].setdefault(convo_id, []).extend(messages)

        if incoming.get("gps"):
            target["gps"].extend(incoming["gps"])

        if incoming.get("google_signals"):
            target["google_signals"].extend(incoming["google_signals"])

        identity = incoming.get("identity") or {}
        target_identity = target["identity"]
        if identity:
            target_identity.setdefault("source_files", [])
            target_identity.setdefault("identity_markers", {})
            target_identity.setdefault("raw_metadata_count", 0)
            for source_file in identity.get("source_files") or []:
                if source_file not in target_identity["source_files"]:
                    target_identity["source_files"].append(source_file)
            target_identity["identity_markers"].update(identity.get("identity_markers") or {})
            target_identity["raw_metadata_count"] += int(identity.get("raw_metadata_count") or 0)

        friends = incoming.get("friends") or {}
        target_friends = target["friends"]
        for category, entries in (friends.get("categories") or {}).items():
            target_friends["categories"].setdefault(category, []).extend(entries)
        if friends.get("ranking"):
            target_friends["ranking"] = friends["ranking"]

    def _finalize_results(self, results: dict) -> dict:
        for convo_id in results["chats"]:
            results["chats"][convo_id] = sorted(
                results["chats"][convo_id],
                key=lambda item: item["Created"],
            )
        if results["gps"]:
            results["gps"] = sorted(results["gps"], key=lambda item: item.get("timestamp", 0))
        if results["google_signals"]:
            results["google_signals"] = sorted(results["google_signals"], key=lambda item: item.get("timestamp", 0))
        return results

    def _background_ingestion(self, job_id: str, saved_files: list[dict]) -> None:
        try:
            merged_results = {
                "chats": {},
                "gps": [],
                "google_signals": [],
                "identity": {"source_files": [], "identity_markers": {}, "raw_metadata_count": 0},
                "friends": {"categories": {}, "ranking": {}},
            }

            for index, file_info in enumerate(saved_files, start=1):
                results = self.engine.process_file(job_id, file_info["filename"], file_info["path"])
                if not results:
                    raise RuntimeError(f"Ingestion returned no results for {file_info['filename']}")
                self._merge_results(merged_results, results)
                self.cache.set(
                    f"{job_id}_status",
                    {
                        "status": "PROCESSING",
                        "messages_found": sum(len(messages) for messages in merged_results.get("chats", {}).values()),
                        "gps_found": len(merged_results.get("gps", [])),
                        "source_files": [item["filename"] for item in saved_files],
                        "file_count": len(saved_files),
                        "active_file": file_info["filename"],
                        "files_processed": index,
                        "expires_at": int(time.time()) + self.ttl_seconds,
                    },
                    expire=self.ttl_seconds,
                )

            merged_results = self._finalize_results(merged_results)
            chat_count = sum(len(messages) for messages in merged_results.get("chats", {}).values())
            gps_count = len(merged_results.get("gps", []))
            self.cache.set(f"{job_id}_data", merged_results, expire=self.ttl_seconds)
            self.cache.set(
                f"{job_id}_status",
                {
                    "status": "COMPLETE",
                    "messages_found": chat_count,
                    "gps_found": gps_count,
                    "source_files": [item["filename"] for item in saved_files],
                    "file_count": len(saved_files),
                    "files_processed": len(saved_files),
                    "expires_at": int(time.time()) + self.ttl_seconds,
                },
                expire=self.ttl_seconds,
            )
        except Exception as exc:
            self.cache.set(
                f"{job_id}_status",
                {
                    "status": "FAILED",
                    "message": str(exc),
                    "source_files": [item["filename"] for item in saved_files],
                    "file_count": len(saved_files),
                    "expires_at": int(time.time()) + self.ttl_seconds,
                },
                expire=self.ttl_seconds,
            )
        finally:
            for file_info in saved_files:
                if os.path.exists(file_info["path"]):
                    os.remove(file_info["path"])

    def get_status(self, job_id: str) -> dict:
        self._purge_expired()
        return self.cache.get(f"{job_id}_status") or {"status": "IDLE"}

    def get_data(self, job_id: str) -> dict | None:
        self._purge_expired()
        return self.cache.get(f"{job_id}_data")

    def list_conversations(self, job_id: str) -> list[dict]:
        data = self.get_data(job_id)
        if not data or "chats" not in data:
            return []
        payload = []
        for convo_id, messages in data["chats"].items():
            if not messages:
                continue
            payload.append(
                {
                    "id": convo_id,
                    "count": len(messages),
                    "messageCount": len(messages),
                    "lastMessage": messages[-1]["Content"],
                    "last_message": messages[-1]["Created"],
                }
            )
        return payload

    def get_conversation(self, job_id: str, convo_id: str) -> list[dict] | None:
        data = self.get_data(job_id)
        if not data or "chats" not in data:
            return None
        return data["chats"].get(convo_id)

    def get_gps(self, job_id: str) -> list[dict]:
        data = self.get_data(job_id)
        if not data:
            return []
        return data.get("gps", [])

    def get_friends(self, job_id: str) -> dict:
        data = self.get_data(job_id)
        if not data:
            return {"categories": {}, "summary": {}, "ranking": {}}

        friends = data.get("friends") or {}
        categories = friends.get("categories") or {}
        ranking = friends.get("ranking") or {}

        summary = {
            category: len(entries)
            for category, entries in categories.items()
        }
        summary["total_records"] = sum(summary.values())
        summary["unique_usernames"] = len(
            {
                entry.get("username")
                for entries in categories.values()
                for entry in entries
                if entry.get("username")
            }
        )

        return {
            "categories": categories,
            "summary": summary,
            "ranking": ranking,
        }

    def get_timeline(self, job_id: str) -> list[dict]:
        data = self.get_data(job_id)
        if not data:
            return []

        timeline: list[dict] = []

        for convo_id, messages in (data.get("chats") or {}).items():
            for index, message in enumerate(messages):
                timestamp = message.get("Created")
                if not timestamp:
                    continue
                timeline.append(
                    {
                        "id": f"chat:{convo_id}:{index}",
                        "timestamp": timestamp,
                        "kind": "chat",
                        "label": convo_id,
                        "summary": message.get("Content") or "[NO CONTENT]",
                        "details": {
                            "conversation": convo_id,
                            "sender": message.get("SenderName") or "Unknown",
                            "direction": "outbound" if message.get("IsSender") else "inbound",
                        },
                    }
                )

        for index, point in enumerate(data.get("gps") or []):
            timestamp = point.get("timestamp")
            if not timestamp:
                continue
            timeline.append(
                {
                    "id": f"gps:{index}",
                    "timestamp": timestamp,
                    "kind": "gps",
                    "label": point.get("layer") or "gps",
                    "summary": point.get("source") or "GPS point",
                    "details": {
                        "layer": point.get("layer") or "unknown",
                        "source": point.get("source") or "unknown",
                        "coordinates": f"{point.get('lat')}, {point.get('lon')}",
                    },
                }
            )

        for index, signal in enumerate(data.get("google_signals") or []):
            timestamp = signal.get("timestamp")
            if not timestamp:
                continue
            timeline.append(
                {
                    "id": signal.get("id") or f"google:{index}",
                    "timestamp": timestamp,
                    "kind": "google",
                    "label": signal.get("subkind") or "google_signal",
                    "summary": signal.get("summary") or "Google signal",
                    "details": {
                        "source": signal.get("source") or "unknown",
                        **(signal.get("details") or {}),
                    },
                }
            )

        friends = data.get("friends") or {}
        for category, entries in (friends.get("categories") or {}).items():
            for index, entry in enumerate(entries):
                created = entry.get("created")
                modified = entry.get("modified")
                display_name = entry.get("display_name") or entry.get("username") or "Unknown profile"
                if created:
                    timeline.append(
                        {
                            "id": f"friend-created:{category}:{index}",
                            "timestamp": created,
                            "kind": "friend",
                            "label": category,
                            "summary": f"{display_name} added to {category}",
                            "details": {
                                "username": entry.get("username") or "unknown",
                                "display_name": display_name,
                                "bucket": category,
                                "source": entry.get("source") or "unknown",
                                "event": "created",
                            },
                        }
                    )
                if modified and modified != created:
                    timeline.append(
                        {
                            "id": f"friend-modified:{category}:{index}",
                            "timestamp": modified,
                            "kind": "friend",
                            "label": category,
                            "summary": f"{display_name} updated in {category}",
                            "details": {
                                "username": entry.get("username") or "unknown",
                                "display_name": display_name,
                                "bucket": category,
                                "source": entry.get("source") or "unknown",
                                "event": "modified",
                            },
                        }
                    )

        return sorted(timeline, key=lambda item: item["timestamp"])

    def get_analytics(self, job_id: str) -> dict:
        data = self.get_data(job_id)
        if not data:
            return {
                "overview": {},
                "chat": {},
                "gps": {},
                "friends": {},
                "google": {},
            }

        chats = data.get("chats") or {}
        gps_points = data.get("gps") or []
        friends = self.get_friends(job_id)
        google_signals = data.get("google_signals") or []

        total_messages = sum(len(messages) for messages in chats.values())
        top_conversations = sorted(
            (
                {
                    "conversation": convo_id,
                    "messages": len(messages),
                    "last_timestamp": messages[-1].get("Created") if messages else "",
                }
                for convo_id, messages in chats.items()
                if messages
            ),
            key=lambda item: item["messages"],
            reverse=True,
        )[:8]

        gps_layers = Counter(point.get("layer") or "unknown" for point in gps_points)
        day_buckets = Counter((point.get("timestamp") or "").split(" ")[0] for point in gps_points if point.get("timestamp"))
        busiest_days = [
            {"day": day, "points": count}
            for day, count in day_buckets.most_common(8)
            if day
        ]

        google_activity = Counter()
        google_platform = Counter()
        google_signal_types = Counter()
        for signal in google_signals:
            details = signal.get("details") or {}
            if details.get("activity_type"):
                google_activity[str(details["activity_type"])] += 1
            if details.get("platform"):
                google_platform[str(details["platform"])] += 1
            if signal.get("subkind"):
                google_signal_types[str(signal["subkind"])] += 1

        return {
            "overview": {
                "messages": total_messages,
                "conversations": len(chats),
                "gps_points": len(gps_points),
                "friend_records": friends.get("summary", {}).get("total_records", 0),
                "google_signals": len(google_signals),
            },
            "chat": {
                "top_conversations": top_conversations,
            },
            "gps": {
                "layers": dict(gps_layers),
                "busiest_days": busiest_days,
            },
            "friends": {
                "summary": friends.get("summary", {}),
                "ranking": friends.get("ranking", {}),
            },
            "google": {
                "signal_types": dict(google_signal_types),
                "top_activities": [
                    {"activity": name, "count": count}
                    for name, count in google_activity.most_common(6)
                ],
                "platforms": dict(google_platform),
            },
        }

    def get_explore(self, job_id: str) -> dict:
        data = self.get_data(job_id)
        if not data:
            return {"sources": [], "identity": [], "google_signals": [], "other": []}

        identity_payload = data.get("identity") or {}
        sources = []
        identity_markers = identity_payload.get("identity_markers") or {}
        for source_file in identity_payload.get("source_files") or ([identity_payload.get("source_file")] if identity_payload.get("source_file") else []):
            sources.append(
                {
                    "source": source_file,
                    "type": "identity_scan",
                    "metadata_count": identity_payload.get("raw_metadata_count", 0),
                }
            )

        google_signals = []
        for signal in data.get("google_signals") or []:
            details = signal.get("details") or {}
            google_signals.append(
                {
                    "timestamp": signal.get("timestamp") or "",
                    "kind": signal.get("subkind") or "google_signal",
                    "summary": signal.get("summary") or "Google signal",
                    "details": details,
                    "source": signal.get("source") or "",
                }
            )

        other_records = []
        for point in data.get("gps") or []:
            if point.get("layer") == "other":
                other_records.append(
                    {
                        "timestamp": point.get("timestamp") or "",
                        "type": "map_other",
                        "summary": point.get("source") or "Unclassified map point",
                        "details": {
                            "coordinates": f"{point.get('lat')}, {point.get('lon')}",
                            "source_system": point.get("source_system") or "unknown",
                        },
                    }
                )

        return {
            "sources": sources,
            "identity": [{"key": key, "value": value} for key, value in identity_markers.items()],
            "google_signals": google_signals[:80],
            "other": other_records[:80],
        }

    def search(self, job_id: str, query: str) -> list[dict]:
        data = self.get_data(job_id)
        if not data or "chats" not in data:
            return []
        return EngineSearch.execute(data["chats"], query)

    def clear(self, job_id: str) -> None:
        self.cache.delete(f"{job_id}_data")
        self.cache.delete(f"{job_id}_status")
        self._purge_expired()
