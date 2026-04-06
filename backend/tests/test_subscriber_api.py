import asyncio
import tempfile
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.common.config import MqttConfig, SubscriberConfig
from backend.common.events import DoorEvent
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
            app = build_app(config)

            with TestClient(app) as client:
                app.state.store.add_event(
                    DoorEvent(
                        timestamp="2026-04-06T18:00:00Z", door_id="door-a", direction="enter"
                    )
                )
                events = client.get("/api/events?limit=10").json()
                summary = client.get("/api/summary").json()

            self.assertEqual(len(events["events"]), 1)
            self.assertEqual(summary["occupancy"], 1)
            self.assertEqual(summary["total_enters"], 1)


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
                payload=b'{"timestamp":"2026-04-06T18:00:00Z","door_id":"door-a","direction":"enter"}'
            )
            service._on_message(None, None, message)

            payload = await asyncio.wait_for(queue.get(), timeout=1.0)
            self.assertEqual(payload["occupancy"], 1)
            self.assertEqual(store.get_current_occupancy(), 1)


if __name__ == "__main__":
    unittest.main()
