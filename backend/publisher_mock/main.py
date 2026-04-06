from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict

from backend.common.config import MockPublisherConfig
from backend.common.events import DoorEvent, topic_for_door, utc_now_iso

LOGGER = logging.getLogger("publisher-mock")


@dataclass
class MockDoorState:
    occupancy_by_door: Dict[str, int] = field(default_factory=dict)


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

    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install backend dependencies before running publisher-mock") from exc

    client = mqtt.Client(client_id=config.mqtt.client_id)
    client.connect(config.mqtt.host, config.mqtt.port, config.mqtt.keepalive)
    client.loop_start()

    try:
        while True:
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
