from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Set

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.common.config import SubscriberConfig
from backend.common.events import DoorEvent, EventValidationError, parse_event
from backend.subscriber_api.store import EventStore

LOGGER = logging.getLogger("subscriber-api")


class EventBroadcaster:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            await queue.put(payload)


class MqttIngestService:
    def __init__(self, store: EventStore, broadcaster: EventBroadcaster, config: SubscriberConfig) -> None:
        self.store = store
        self.broadcaster = broadcaster
        self.config = config
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            LOGGER.warning("paho-mqtt is not installed; MQTT ingest disabled")
            return

        client = mqtt.Client(client_id=self.config.mqtt.client_id)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.connect_async(self.config.mqtt.host, self.config.mqtt.port, self.config.mqtt.keepalive)
        client.loop_start()
        self._client = client

    def stop(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()

    def _on_connect(self, client, _userdata, _flags, rc, _properties=None) -> None:
        if rc == 0:
            client.subscribe("doors/+/events")
            LOGGER.info("Connected to MQTT broker and subscribed to doors/+/events")
        else:
            LOGGER.error("Failed to connect to MQTT broker: rc=%s", rc)

    def _on_message(self, _client, _userdata, msg) -> None:
        payload = msg.payload.decode("utf-8", errors="replace")
        try:
            event = parse_event(payload)
        except EventValidationError as exc:
            self.store.record_error(payload=payload, error_message=str(exc))
            LOGGER.warning("Rejected MQTT payload: %s", exc)
            return

        occupancy = self.store.add_event(event)
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(
                self.broadcaster.broadcast(
                    {
                        "type": "door_event",
                        "event": event.to_dict(),
                        "occupancy": occupancy,
                    }
                ),
                self._loop,
            )


def build_app(config: Optional[SubscriberConfig] = None) -> FastAPI:
    config = config or SubscriberConfig()
    store = EventStore(config.database_path)
    broadcaster = EventBroadcaster()
    ingest_service = MqttIngestService(store, broadcaster, config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        loop = asyncio.get_running_loop()
        ingest_service.start(loop)
        app.state.store = store
        app.state.broadcaster = broadcaster
        app.state.config = config
        try:
            yield
        finally:
            ingest_service.stop()

    app = FastAPI(title="IoT Room Occupancy Subscriber API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok", "mqtt_host": config.mqtt.host, "mqtt_port": config.mqtt.port}

    @app.get("/api/occupancy")
    async def occupancy() -> Dict[str, Any]:
        current = store.get_current_occupancy()
        return {"occupancy": current}

    @app.get("/api/events")
    async def events(
        limit: int = Query(default=50, ge=1, le=500),
        door_id: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        return {"events": store.list_events(limit=limit, door_id=door_id, since=since)}

    @app.get("/api/summary")
    async def summary() -> Dict[str, Any]:
        return store.get_summary()

    @app.get("/api/stream")
    async def stream() -> StreamingResponse:
        queue = broadcaster.subscribe()

        async def event_stream() -> AsyncIterator[str]:
            try:
                snapshot = json.dumps(
                    {
                        "type": "snapshot",
                        "occupancy": store.get_current_occupancy(),
                        "summary": store.get_summary(),
                    }
                )
                yield f"retry: {config.sse_retry_ms}\n"
                yield f"data: {snapshot}\n\n"
                while True:
                    item = await queue.get()
                    yield f"data: {json.dumps(item)}\n\n"
            finally:
                broadcaster.unsubscribe(queue)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app


app = build_app()
