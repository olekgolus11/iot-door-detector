from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from backend.common.config import YoloPublisherConfig
from backend.common.events import DoorEvent, topic_for_door, utc_now_iso

LOGGER = logging.getLogger("publisher-yolo")

Point = Tuple[float, float]


def parse_point(raw: str) -> Point:
    x, y = raw.split(",", maxsplit=1)
    return float(x.strip()), float(y.strip())


def signed_distance(point: Point, line_start: Point, line_end: Point) -> float:
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)


@dataclass
class CrossingDecision:
    track_id: int
    direction: str
    centroid: Point


class DoorCrossingTracker:
    def __init__(self, line_start: Point, line_end: Point, enter_when: str) -> None:
        self.line_start = line_start
        self.line_end = line_end
        self.enter_when = enter_when
        self.last_side: Dict[int, float] = {}
        self.cooldowns: Dict[int, int] = defaultdict(int)

    def update(self, track_id: int, centroid: Point) -> Optional[CrossingDecision]:
        current_side = math.copysign(1.0, signed_distance(centroid, self.line_start, self.line_end))
        previous_side = self.last_side.get(track_id)
        self.last_side[track_id] = current_side

        if self.cooldowns[track_id] > 0:
            self.cooldowns[track_id] -= 1
            return None

        if previous_side is None or previous_side == current_side:
            return None

        direction = (
            "enter"
            if (previous_side < current_side and self.enter_when == "negative_to_positive")
            or (previous_side > current_side and self.enter_when == "positive_to_negative")
            else "leave"
        )
        self.cooldowns[track_id] = 10
        return CrossingDecision(track_id=track_id, direction=direction, centroid=centroid)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = YoloPublisherConfig()
    if not config.stream_url:
        raise SystemExit("CAMERA_STREAM_URL is required for publisher-yolo")

    try:
        import cv2
        import paho.mqtt.client as mqtt
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "publisher-yolo requires opencv-python-headless, paho-mqtt, and ultralytics"
        ) from exc

    model = YOLO(config.model_name)
    line_start = parse_point(config.line_start)
    line_end = parse_point(config.line_end)
    tracker = DoorCrossingTracker(line_start=line_start, line_end=line_end, enter_when=config.enter_when)

    client = mqtt.Client(client_id=config.mqtt.client_id)
    client.connect(config.mqtt.host, config.mqtt.port, config.mqtt.keepalive)
    client.loop_start()

    capture = cv2.VideoCapture(config.stream_url)
    if not capture.isOpened():
        raise SystemExit(f"Unable to open camera stream: {config.stream_url}")

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                LOGGER.warning("Skipping frame because capture read failed")
                continue

            results = model.track(frame, persist=True, classes=[0], conf=config.confidence_threshold, verbose=False)
            if not results:
                continue

            boxes = results[0].boxes
            if boxes is None or boxes.id is None:
                continue

            ids = boxes.id.int().tolist()
            xyxy_list = boxes.xyxy.tolist()
            for track_id, xyxy in zip(ids, xyxy_list):
                x1, y1, x2, y2 = xyxy
                centroid = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                crossing = tracker.update(track_id=track_id, centroid=centroid)
                if crossing is None:
                    continue

                event = DoorEvent(
                    timestamp=utc_now_iso(),
                    door_id=config.door_id,
                    direction=crossing.direction,
                )
                client.publish(topic_for_door(config.door_id), event.to_json())
                LOGGER.info("Published %s for track=%s centroid=%s", event.to_json(), track_id, centroid)
    finally:
        capture.release()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run()

