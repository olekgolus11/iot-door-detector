import asyncio
import tempfile
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.common.config import MqttConfig, SubscriberConfig
from backend.common.events import DoorEvent
from backend.common.publisher_control import MOCK_PUBLISHER_CONTROL_TOPIC
from backend.subscriber_api.app import EventBroadcaster, MqttIngestService, build_app
from backend.subscriber_api.store import EventStore


class SubscriberApiTests(unittest.TestCase):
    def test_rest_endpoints_return_persisted_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            app = build_app(config, enable_mqtt_ingest=False)

            with TestClient(app) as client:
                app.state.store.add_event(
                    DoorEvent(
                        timestamp="2026-04-06T18:00:00Z",
                        door_id="door-a",
                        direction="enter",
                        source_type="mock",
                    )
                )
                events = client.get("/api/events?limit=10").json()
                summary = client.get("/api/summary").json()
                control_state = client.get("/api/control-state").json()

            self.assertEqual(len(events["events"]), 1)
            self.assertEqual(summary["occupancy"], 1)
            self.assertEqual(summary["total_enters"], 1)
            self.assertEqual(control_state["active_source_mode"], "mock")

    def test_control_state_update_endpoint_changes_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            app = build_app(config, enable_mqtt_ingest=False)

            with TestClient(app) as client:
                payload = client.put(
                    "/api/control-state",
                    json={"collection_enabled": False, "active_source_mode": "camera", "baseline_occupancy": 5},
                ).json()
                occupancy = client.get("/api/occupancy").json()

            self.assertFalse(payload["collection_enabled"])
            self.assertEqual(payload["active_source_mode"], "camera")
            self.assertEqual(occupancy["occupancy"], 5)

    def test_active_source_update_publishes_mock_control_command(self) -> None:
        class FakeMqttClient:
            def __init__(self) -> None:
                self.published = []

            def publish(self, topic, payload, retain=False):
                self.published.append((topic, payload, retain))
                return SimpleNamespace(rc=0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            app = build_app(config, enable_mqtt_ingest=False)

            with TestClient(app) as client:
                fake_client = FakeMqttClient()
                app.state.ingest_service._client = fake_client
                client.put("/api/control-state", json={"active_source_mode": "camera"})
                client.put("/api/control-state", json={"active_source_mode": "mock"})

            self.assertEqual(
                fake_client.published,
                [
                    (MOCK_PUBLISHER_CONTROL_TOPIC, '{"enabled":false}', True),
                    (MOCK_PUBLISHER_CONTROL_TOPIC, '{"enabled":true}', True),
                ],
            )

    def test_mqtt_connect_syncs_mock_control_from_persisted_source_mode(self) -> None:
        class FakeMqttClient:
            def __init__(self) -> None:
                self.subscriptions = []
                self.published = []

            def subscribe(self, topic):
                self.subscriptions.append(topic)

            def publish(self, topic, payload, retain=False):
                self.published.append((topic, payload, retain))
                return SimpleNamespace(rc=0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            store = EventStore(config.database_path)
            store.update_control_state(active_source_mode="camera")
            service = MqttIngestService(
                store=store,
                broadcaster=EventBroadcaster(),
                config=config,
            )
            fake_client = FakeMqttClient()

            service._on_connect(fake_client, None, None, 0)

            self.assertEqual(fake_client.subscriptions, ["doors/+/events"])
            self.assertEqual(
                fake_client.published,
                [(MOCK_PUBLISHER_CONTROL_TOPIC, '{"enabled":false}', True)],
            )

    def test_rejected_events_endpoint_returns_reason_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            app = build_app(config, enable_mqtt_ingest=False)

            with TestClient(app) as client:
                client.put("/api/control-state", json={"collection_enabled": False})
                app.state.store.add_event(
                    DoorEvent(
                        timestamp="2026-04-06T18:00:00Z",
                        door_id="door-a",
                        direction="enter",
                        source_type="mock",
                    )
                )
                rejected = client.get("/api/rejected-events?limit=10").json()

            self.assertEqual(len(rejected["events"]), 1)
            self.assertEqual(rejected["events"][0]["reason_code"], "collection_paused")

    def test_clear_database_endpoint_returns_cleared_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-api", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            app = build_app(config, enable_mqtt_ingest=False)

            with TestClient(app) as client:
                client.put(
                    "/api/control-state",
                    json={"collection_enabled": True, "active_source_mode": "camera", "baseline_occupancy": 3},
                )
                app.state.store.add_event(
                    DoorEvent(
                        timestamp="2026-04-06T18:00:00Z",
                        door_id="door-a",
                        direction="enter",
                        source_type="camera",
                    )
                )
                client.put("/api/control-state", json={"collection_enabled": False})
                app.state.store.add_event(
                    DoorEvent(
                        timestamp="2026-04-06T18:01:00Z",
                        door_id="door-a",
                        direction="enter",
                        source_type="camera",
                    )
                )
                app.state.store.record_error(payload="{bad-json", error_message="invalid json")

                payload = client.post("/api/database/clear").json()
                events = client.get("/api/events?limit=10").json()
                rejected = client.get("/api/rejected-events?limit=10").json()

            self.assertEqual(payload["type"], "database_cleared")
            self.assertEqual(payload["summary"]["occupancy"], 0)
            self.assertEqual(payload["summary"]["system_status"]["accepted_events"], 0)
            self.assertEqual(payload["summary"]["system_status"]["rejected_events"], 0)
            self.assertFalse(payload["control_state"]["collection_enabled"])
            self.assertEqual(payload["control_state"]["active_source_mode"], "camera")
            self.assertEqual(payload["control_state"]["baseline_occupancy"], 3)
            self.assertEqual(events["events"], [])
            self.assertEqual(rejected["events"], [])


class SubscriberIngestTests(unittest.IsolatedAsyncioTestCase):
    async def test_mqtt_ingest_stores_and_broadcasts_valid_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = SubscriberConfig(
                mqtt=MqttConfig(host="localhost", port=1883, client_id="test-ingest", keepalive=60),
                database_path=f"{tmp_dir}/events.db",
                api_host="127.0.0.1",
                api_port=8000,
                sse_retry_ms=3000,
            )
            store = EventStore(config.database_path)
            broadcaster = EventBroadcaster()
            service = MqttIngestService(store=store, broadcaster=broadcaster, config=config)
            service._loop = asyncio.get_running_loop()
            queue = broadcaster.subscribe()

            message = SimpleNamespace(
                payload=b'{"timestamp":"2026-04-06T18:00:00Z","door_id":"door-a","direction":"enter","source_type":"mock"}'
            )
            service._on_message(None, None, message)

            payload = await asyncio.wait_for(queue.get(), timeout=1.0)
            self.assertEqual(payload["occupancy"], 1)
            self.assertEqual(store.get_current_occupancy(), 1)
            self.assertEqual(payload["summary"]["per_door"][0]["door_id"], "door-a")


if __name__ == "__main__":
    unittest.main()
