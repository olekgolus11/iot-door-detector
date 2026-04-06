from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Set

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.common.config import SubscriberConfig
from backend.common.events import EventValidationError, parse_event
from backend.subscriber_api.schemas import ControlStateUpdate
from backend.subscriber_api.store import EventStore

LOGGER = logging.getLogger("subscriber-api")


class EventBroadcaster:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
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

        result = self.store.add_event(event)
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(
                self.broadcaster.broadcast(
                    build_stream_payload(
                        store=self.store,
                        event=result.get("event"),
                        rejected_event=result.get("rejected_event"),
                        event_type="door_event" if result["accepted"] else "rejected_event",
                    )
                ),
                self._loop,
            )


def build_stream_payload(
    store: EventStore,
    event_type: str,
    event: Optional[Dict[str, Any]] = None,
    rejected_event: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = store.get_summary()
    return {
        "type": event_type,
        "event": event,
        "rejected_event": rejected_event,
        "occupancy": summary["occupancy"],
        "summary": summary,
        "control_state": summary["control_state"],
    }


def build_app(config: Optional[SubscriberConfig] = None, enable_mqtt_ingest: bool = True) -> FastAPI:
    config = config or SubscriberConfig()
    store = EventStore(config.database_path)
    broadcaster = EventBroadcaster()
    ingest_service = MqttIngestService(store, broadcaster, config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        loop = asyncio.get_running_loop()
        if enable_mqtt_ingest:
            ingest_service.start(loop)
        app.state.store = store
        app.state.broadcaster = broadcaster
        app.state.config = config
        try:
            yield
        finally:
            if enable_mqtt_ingest:
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
        summary = store.get_summary()
        return {
            "status": "ok",
            "mqtt_host": config.mqtt.host,
            "mqtt_port": config.mqtt.port,
            "system_status": summary["system_status"],
        }

    @app.get("/api/occupancy")
    async def occupancy() -> Dict[str, Any]:
        current = store.get_current_occupancy()
        return {"occupancy": current, "control_state": store.get_control_state()}

    @app.get("/api/control-state")
    async def control_state() -> Dict[str, Any]:
        return store.get_control_state()

    @app.put("/api/control-state")
    async def update_control_state(payload: ControlStateUpdate) -> Dict[str, Any]:
        updated = store.update_control_state(
            collection_enabled=payload.collection_enabled,
            active_source_mode=payload.active_source_mode,
            baseline_occupancy=payload.baseline_occupancy,
        )
        await broadcaster.broadcast(
            build_stream_payload(store=store, event_type="control_state_updated")
        )
        return updated

    @app.get("/api/events")
    async def events(
        limit: int = Query(default=50, ge=1, le=500),
        door_id: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None),
        until: Optional[str] = Query(default=None),
        direction: Optional[str] = Query(default=None),
        source_type: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        if direction and direction not in ("enter", "leave"):
            raise HTTPException(status_code=400, detail="direction must be 'enter' or 'leave'")
        return {
            "events": store.list_events(
                limit=limit,
                door_id=door_id,
                since=since,
                until=until,
                direction=direction,
                source_type=source_type,
            )
        }

    @app.get("/api/rejected-events")
    async def rejected_events(
        limit: int = Query(default=50, ge=1, le=500),
        door_id: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None),
        until: Optional[str] = Query(default=None),
        direction: Optional[str] = Query(default=None),
        source_type: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        if direction and direction not in ("enter", "leave"):
            raise HTTPException(status_code=400, detail="direction must be 'enter' or 'leave'")
        return {
            "events": store.list_rejected_events(
                limit=limit,
                door_id=door_id,
                since=since,
                until=until,
                direction=direction,
                source_type=source_type,
            )
        }

    @app.get("/api/summary")
    async def summary() -> Dict[str, Any]:
        return store.get_summary()

    @app.get("/api/stream")
    async def stream() -> StreamingResponse:
        queue = broadcaster.subscribe()

        async def event_stream() -> AsyncIterator[str]:
            try:
                snapshot = json.dumps(build_stream_payload(store=store, event_type="snapshot"))
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
