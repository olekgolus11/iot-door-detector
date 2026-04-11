from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict

from backend.common.config import MockPublisherConfig
from backend.common.events import DoorEvent, topic_for_door, utc_now_iso
from backend.common.publisher_control import (
    MOCK_PUBLISHER_CONTROL_TOPIC,
    parse_mock_publisher_control_payload,
)

LOGGER = logging.getLogger("publisher-mock")


@dataclass
class MockDoorState:
    occupancy_by_door: Dict[str, int] = field(default_factory=dict)


@dataclass
class MockPublisherControl:
    enabled: bool = True

    def apply_payload(self, payload: bytes | str) -> bool:
        try:
            self.enabled = parse_mock_publisher_control_payload(payload)
        except ValueError as exc:
            LOGGER.warning("Ignored invalid mock publisher control payload: %s", exc)
            return False
        return True


def build_next_event(state: MockDoorState, door_id: str, rng: random.Random) -> DoorEvent:
    occupancy = state.occupancy_by_door.get(door_id, 0)
    if occupancy <= 0:
        direction = "enter"
    else:
        direction = rng.choices(["enter", "leave"], weights=(0.6, 0.4), k=1)[0]
    if direction == "enter":
        state.occupancy_by_door[door_id] = occupancy + 1
    else:
        state.occupancy_by_door[door_id] = max(0, occupancy - 1)
    return DoorEvent(timestamp=utc_now_iso(), door_id=door_id, direction=direction)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = MockPublisherConfig()
    rng = random.Random(config.seed)
    state = MockDoorState()
    control = MockPublisherControl()

    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install backend dependencies before running publisher-mock") from exc

    def on_connect(client, _userdata, _flags, rc, _properties=None) -> None:
        if rc == 0:
            client.subscribe(MOCK_PUBLISHER_CONTROL_TOPIC)
            LOGGER.info("Connected to MQTT broker and listening for mock publisher control")
        else:
            LOGGER.error("Failed to connect to MQTT broker: rc=%s", rc)

    def on_message(_client, _userdata, msg) -> None:
        was_enabled = control.enabled
        if control.apply_payload(msg.payload) and control.enabled != was_enabled:
            LOGGER.info("Mock publisher %s", "resumed" if control.enabled else "paused")

    client = mqtt.Client(client_id=config.mqtt.client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.mqtt.host, config.mqtt.port, config.mqtt.keepalive)
    client.loop_start()

    try:
        while True:
            if not control.enabled:
                time.sleep(0.25)
                continue
            door_id = rng.choice(config.door_ids)
            event = build_next_event(state, door_id, rng)
            event = DoorEvent(
                timestamp=event.timestamp,
                door_id=event.door_id,
                direction=event.direction,
                source_type="mock",
                publisher_id=config.publisher_id,
            )
            client.publish(topic_for_door(event.door_id), event.to_json())
            LOGGER.info("Published %s", event.to_json())
            time.sleep(rng.uniform(config.min_interval_seconds, config.max_interval_seconds))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run()
