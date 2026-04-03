import io
import json
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from black_tape_web import create_app
from black_tape_engine.legacy_ingesters.zip_ingestor import ZipIngestor
from black_tape_engine.legacy_scanners.gps_scanner import GPSScanner


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.instance_path = Path(self.temp_dir.name) / "instance"
        self.instance_path.mkdir(parents=True, exist_ok=True)

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.app.instance_path = str(self.instance_path)

        vault_service = self.app.extensions["vault_service"]
        vault_service.upload_root = str(self.instance_path / "uploads")
        vault_service.cache.close()
        vault_service.cache = __import__("diskcache").Cache(str(self.instance_path / "vault_cache"))
        vault_service.engine = __import__("black_tape_engine").BlackTapeEngine(cache_dir=str(self.instance_path / "vault_cache"))

        Path(vault_service.upload_root).mkdir(parents=True, exist_ok=True)
        Path(self.instance_path / "vault_cache").mkdir(parents=True, exist_ok=True)

        self.client = self.app.test_client()
        self.sample_zip_bytes = self._build_sample_export_zip()

    def tearDown(self):
        self.app.extensions["vault_service"].cache.close()
        self.temp_dir.cleanup()

    def _build_sample_export_zip(self):
        payloads = {
            "snapchat/chat_history.json": {
                "casey_signal": [
                    {
                        "From": "casey_signal",
                        "Content": "Inbound message",
                        "Created": "2025-02-03 12:00:00 UTC",
                        "IsSender": False,
                    },
                    {
                        "From": "owner",
                        "Content": "Outbound reply",
                        "Created": "2025-02-03 12:02:00 UTC",
                        "IsSender": True,
                    },
                ],
                "river_echo": [
                    {
                        "From": "river_echo",
                        "Content": "Second thread",
                        "Created": "2025-02-04 08:15:00 UTC",
                        "IsSender": False,
                    }
                ],
            },
            "snapchat/location_history.json": {
                "Location History": [
                    ["2025-02-03 12:30:00 UTC", "28.061, -82.413"],
                    ["2025-02-03 13:45:00 UTC", "28.062, -82.414"],
                ]
            },
            "snapchat/memories_history.json": {
                "Memories History": [
                    {
                        "Date": "2025-02-03 14:00:00 UTC",
                        "Location": "28.070, -82.420",
                    }
                ]
            },
            "snapchat/friends.json": {
                "Friends": [
                    {
                        "Username": "casey_signal",
                        "Display Name": "Casey Signal",
                        "Creation Timestamp": "2024-10-10 11:00:00 UTC",
                    }
                ],
                "Deleted Friends": [
                    {
                        "Username": "archived_contact",
                        "Display Name": "Archived Contact",
                        "Creation Timestamp": "2024-01-05 09:30:00 UTC",
                    }
                ],
            },
            "snapchat/ranking.json": {
                "Statistics": {
                    "Snapscore": "101",
                    "Your Total Friends": "2",
                    "The Number of Accounts You Follow": "2",
                }
            },
            "google/location_history.json": {
                "Frequent Locations": [{"City": "Example City", "Country": "US", "Region": "FL"}],
                "Latest Location": [{"City": "Example City", "Country": "US", "Region": "FL"}],
                "Home & Work": {
                    "userProvidedHome": "lat 28.255 ± 0 meters, long -82.181 ± 0 meters",
                },
                "Location History": [
                    ["2025-02-05 09:00:00 UTC", "28.100, -82.500"],
                    ["2025-02-05 10:15:00 UTC", "28.101, -82.501"],
                ],
            },
            "google/Timeline Edits.json": {
                "timelineEdits": [
                    {
                        "deviceId": "device-1",
                        "rawSignal": {
                            "signal": {
                                "activityRecord": {
                                    "detectedActivities": [
                                        {"activityType": "IN_VEHICLE", "probability": 0.9},
                                        {"activityType": "STILL", "probability": 0.1},
                                    ],
                                    "timestamp": "2025-02-05T11:00:00.000Z",
                                }
                            },
                            "additionalTimestamp": "2025-02-05T11:00:10.000Z",
                            "metadata": {"platform": "ANDROID"},
                        },
                    },
                    {
                        "deviceId": "device-1",
                        "rawSignal": {
                            "signal": {
                                "wifiScan": {
                                    "deliveryTime": "2025-02-05T11:00:10.000Z",
                                    "devices": [{"mac": "1", "rawRssi": -40}, {"mac": "2", "rawRssi": -55}],
                                    "source": "ACTIVE_SCAN",
                                }
                            },
                            "additionalTimestamp": "2025-02-05T11:00:10.000Z",
                            "metadata": {"platform": "ANDROID"},
                        },
                    },
                    {
                        "deviceId": "device-1",
                        "rawSignal": {
                            "signal": {
                                "position": {
                                    "point": {"latE7": 281020000, "lngE7": -825020000},
                                    "accuracyMm": 12000,
                                    "altitudeMeters": 7.0,
                                    "source": "WIFI",
                                    "timestamp": "2025-02-05T11:00:05.000Z",
                                }
                            },
                            "additionalTimestamp": "2025-02-05T11:00:10.000Z",
                            "metadata": {"platform": "ANDROID"},
                        },
                    },
                ]
            },
        }

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for filename, payload in payloads.items():
                bundle.writestr(filename, json.dumps(payload))
        return archive.getvalue()

    def _build_extra_location_json(self):
        return json.dumps(
            {
                "Location History": [
                    ["2025-02-06 16:00:00 UTC", "28.222, -82.611"],
                    ["2025-02-06 17:00:00 UTC", "28.223, -82.612"],
                ]
            }
        ).encode("utf-8")

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ONLINE")

    def test_password_gate_redirects_and_allows_login(self):
        self.app.config["BLACKTAPE_PASSWORD"] = "deploy-pass"

        locked_response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(locked_response.status_code, 302)
        self.assertIn("/login", locked_response.headers["Location"])

        bad_login = self.client.post(
            "/login",
            data={"password": "wrong-pass", "next": "/dashboard"},
            follow_redirects=False,
        )
        self.assertEqual(bad_login.status_code, 401)

        good_login = self.client.post(
            "/login",
            data={"password": "deploy-pass", "next": "/dashboard"},
            follow_redirects=False,
        )
        self.assertEqual(good_login.status_code, 302)
        self.assertTrue(good_login.headers["Location"].endswith("/dashboard"))

        unlocked_response = self.client.get("/dashboard")
        self.assertEqual(unlocked_response.status_code, 200)

    def test_upload_rejects_unsupported_extension(self):
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"
        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(b"not-a-zip"), "payload.exe")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "ERROR")

    def test_upload_returns_json_when_request_exceeds_size_limit(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 32
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"

        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(b"x" * 256), "oversized.json")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["status"], "ERROR")
        self.assertIn("size limit", response.get_json()["message"].lower())

    def test_zip_ingestor_accepts_file_path_without_loading_archive_bytes_first(self):
        archive_path = Path(self.temp_dir.name) / "fixture.zip"
        archive_path.write_bytes(self.sample_zip_bytes)

        extracted = ZipIngestor().ingest_zip(archive_path)

        self.assertTrue(extracted)
        self.assertTrue(any(name.endswith("chat_history.json") for name, _data in extracted))

    def test_snapchat_location_history_keeps_snapchat_source_system(self):
        payload = {
            "Location History": [
                ["2025-02-03 12:30:00 UTC", "28.061, -82.413"],
            ]
        }

        points = GPSScanner().scan("snapchat/location_history.json", payload)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["source_system"], "snapchat")
        self.assertEqual(points[0]["layer"], "location_history")

    def test_mydata_archive_name_marks_location_history_as_snapchat(self):
        payload = {
            "Location History": [
                ["2025-02-03 12:30:00 UTC", "28.061, -82.413"],
            ]
        }

        points = GPSScanner().scan("MyData.zip::location_history.json", payload)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["source_system"], "snapchat")

    def test_takeout_archive_name_marks_location_history_as_google(self):
        payload = {
            "Location History": [
                ["2025-02-03 12:30:00 UTC", "28.061, -82.413"],
            ]
        }

        points = GPSScanner().scan("Takeout.zip::Location History.json", payload)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["source_system"], "google")

    def test_upload_archive_populates_conversations_and_gps(self):
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"
        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(self.sample_zip_bytes), "synthetic-export.zip")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )

        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ACCEPTED")
        job_id = payload["job_id"]

        status_payload = None
        for _ in range(40):
            status_response = self.client.get(f"/api/vault/status?job_id={job_id}")
            status_payload = status_response.get_json()
            if status_payload["status"] == "COMPLETE":
                break
            time.sleep(0.1)

        self.assertIsNotNone(status_payload)
        self.assertEqual(status_payload["status"], "COMPLETE")
        self.assertGreater(status_payload["messages_found"], 0)
        self.assertGreater(status_payload["gps_found"], 0)

        conversations = self.client.get(f"/api/conversations?job_id={job_id}").get_json()
        self.assertEqual(conversations["status"], "SUCCESS")
        self.assertGreater(len(conversations["payload"]), 0)
        first_conversation = conversations["payload"][0]
        self.assertIn("count", first_conversation)
        self.assertIn("last_message", first_conversation)

        convo_id = first_conversation["id"]
        conversation_detail = self.client.get(
            f"/api/conversations/{convo_id}?job_id={job_id}"
        ).get_json()
        self.assertEqual(conversation_detail["status"], "SUCCESS")
        self.assertGreater(len(conversation_detail["payload"]), 0)

        gps_payload = self.client.get(f"/api/gps?job_id={job_id}").get_json()
        self.assertEqual(gps_payload["status"], "SUCCESS")
        self.assertGreater(len(gps_payload["payload"]), 0)
        gps_layers = {point.get("layer") for point in gps_payload["payload"]}
        self.assertIn("location_history", gps_layers)
        self.assertIn("memories_history", gps_layers)
        self.assertIn("google_location_history", gps_layers)
        self.assertIn("google_timeline_edits", gps_layers)

        google_timeline_points = [
            point for point in gps_payload["payload"]
            if point.get("layer") == "google_timeline_edits"
        ]
        self.assertGreater(len(google_timeline_points), 0)
        self.assertEqual(google_timeline_points[0].get("source_system"), "google")
        self.assertEqual(google_timeline_points[0].get("activity_type"), "IN_VEHICLE")

        friends_payload = self.client.get(f"/api/friends?job_id={job_id}").get_json()
        self.assertEqual(friends_payload["status"], "SUCCESS")
        self.assertIn("summary", friends_payload["payload"])
        self.assertIn("categories", friends_payload["payload"])
        self.assertGreater(friends_payload["payload"]["summary"].get("unique_usernames", 0), 0)

        timeline_payload = self.client.get(f"/api/timeline?job_id={job_id}").get_json()
        self.assertEqual(timeline_payload["status"], "SUCCESS")
        self.assertGreater(len(timeline_payload["payload"]), 0)

        analytics_payload = self.client.get(f"/api/analytics?job_id={job_id}").get_json()
        self.assertEqual(analytics_payload["status"], "SUCCESS")
        self.assertGreater(analytics_payload["payload"]["overview"].get("messages", 0), 0)
        self.assertIn("top_conversations", analytics_payload["payload"]["chat"])

        explore_payload = self.client.get(f"/api/explore?job_id={job_id}").get_json()
        self.assertEqual(explore_payload["status"], "SUCCESS")
        self.assertGreater(len(explore_payload["payload"]["identity"]), 0)
        self.assertGreater(len(explore_payload["payload"]["google_signals"]), 0)

    def test_upload_multiple_files_merges_into_one_vault(self):
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"

        response = self.client.post(
            "/upload",
            data={
                "file": [
                    (io.BytesIO(self.sample_zip_bytes), "synthetic-export.zip"),
                    (io.BytesIO(self._build_extra_location_json()), "location_history.json"),
                ]
            },
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )

        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ACCEPTED")
        self.assertEqual(payload["file_count"], 2)
        job_id = payload["job_id"]

        status_payload = None
        for _ in range(50):
            status_response = self.client.get(f"/api/vault/status?job_id={job_id}")
            status_payload = status_response.get_json()
            if status_payload["status"] == "COMPLETE":
                break
            time.sleep(0.1)

        self.assertIsNotNone(status_payload)
        self.assertEqual(status_payload["status"], "COMPLETE")
        self.assertEqual(status_payload.get("file_count"), 2)
        self.assertEqual(status_payload.get("files_processed"), 2)

        gps_payload = self.client.get(f"/api/gps?job_id={job_id}").get_json()
        self.assertEqual(gps_payload["status"], "SUCCESS")
        timestamps = {point.get("timestamp") for point in gps_payload["payload"]}
        self.assertIn("2025-02-06 16:00:00 UTC", timestamps)
        self.assertIn("2025-02-06 17:00:00 UTC", timestamps)

    def test_uploaded_vault_expires_automatically(self):
        vault_service = self.app.extensions["vault_service"]
        vault_service.ttl_seconds = 1
        vault_service.engine._orchestrator.status_ttl = 1

        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"

        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(self.sample_zip_bytes), "synthetic-export.zip")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )

        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]

        for _ in range(40):
            status_payload = self.client.get(f"/api/vault/status?job_id={job_id}").get_json()
            if status_payload["status"] == "COMPLETE":
                break
            time.sleep(0.1)

        time.sleep(1.2)

        expired_status = self.client.get(f"/api/vault/status?job_id={job_id}").get_json()
        self.assertEqual(expired_status["status"], "IDLE")

        conversations = self.client.get(f"/api/conversations?job_id={job_id}").get_json()
        self.assertEqual(conversations["status"], "SUCCESS")
        self.assertEqual(conversations["payload"], [])

    def test_reset_vault_expiry_extends_active_vault(self):
        vault_service = self.app.extensions["vault_service"]
        vault_service.ttl_seconds = 2
        vault_service.engine._orchestrator.status_ttl = 2

        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf"

        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(self.sample_zip_bytes), "synthetic-export.zip")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "test-csrf"},
        )

        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]

        for _ in range(40):
            status_payload = self.client.get(f"/api/vault/status?job_id={job_id}").get_json()
            if status_payload["status"] == "COMPLETE":
                break
            time.sleep(0.1)

        initial_expires_at = status_payload.get("expires_at", 0)
        time.sleep(1.1)

        reset_response = self.client.post(
            f"/api/vault/reset-expiry?job_id={job_id}",
            headers={"X-CSRF-Token": "test-csrf"},
        )
        self.assertEqual(reset_response.status_code, 200)
        reset_payload = reset_response.get_json()
        self.assertEqual(reset_payload["status"], "SUCCESS")
        self.assertGreater(reset_payload["payload"].get("expires_at", 0), initial_expires_at)


if __name__ == "__main__":
    unittest.main()
