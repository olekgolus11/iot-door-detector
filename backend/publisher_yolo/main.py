from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from backend.common.config import YoloPublisherConfig
from backend.common.events import DoorEvent, topic_for_door, utc_now_iso

LOGGER = logging.getLogger("publisher-yolo")
HEARTBEAT_EVERY_FRAMES = 150
DETECTION_LOG_EVERY_FRAMES = 30
PREVIEW_WINDOW_NAME = "YOLO Doorway Debug"

Point = Tuple[float, float]


def parse_point(raw: str) -> Point:
    x, y = raw.split(",", maxsplit=1)
    return float(x.strip()), float(y.strip())


def signed_distance(point: Point, line_start: Point, line_end: Point) -> float:
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    line_length = math.hypot(x2 - x1, y2 - y1)
    if line_length == 0:
        return 0.0
    return ((x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)) / line_length


@dataclass
class CrossingDecision:
    track_id: int
    direction: str
    point: Point


def representative_point(xyxy: list[float], mode: str) -> Point:
    x1, y1, x2, y2 = xyxy
    if mode == "centroid":
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    return ((x1 + x2) / 2.0, y2)


class DoorCrossingTracker:
    def __init__(
        self,
        line_start: Point,
        line_end: Point,
        enter_when: str,
        *,
        line_band_pixels: int,
        cooldown_frames: int,
    ) -> None:
        self.line_start = line_start
        self.line_end = line_end
        self.enter_when = enter_when
        self.line_band_pixels = max(0, line_band_pixels)
        self.cooldown_frames = max(0, cooldown_frames)
        self.last_side: Dict[int, int] = {}
        self.cooldowns: Dict[int, int] = defaultdict(int)

    def classify_side(self, point: Point) -> int:
        distance = signed_distance(point, self.line_start, self.line_end)
        if distance > self.line_band_pixels:
            return 1
        if distance < -self.line_band_pixels:
            return -1
        return 0

    def update(self, track_id: int, point: Point) -> Optional[CrossingDecision]:
        current_side = self.classify_side(point)
        previous_side = self.last_side.get(track_id)

        if self.cooldowns[track_id] > 0:
            self.cooldowns[track_id] -= 1
            if current_side != 0:
                self.last_side[track_id] = current_side
            return None

        if current_side == 0:
            return None

        self.last_side[track_id] = current_side
        if previous_side is None or previous_side == current_side:
            return None

        direction = "leave"
        if (
            previous_side < current_side and self.enter_when == "negative_to_positive"
        ) or (
            previous_side > current_side and self.enter_when == "positive_to_negative"
        ):
            direction = "enter"

        self.cooldowns[track_id] = self.cooldown_frames
        return CrossingDecision(track_id=track_id, direction=direction, point=point)


def draw_debug_overlay(
    cv2,
    frame,
    *,
    line_start: Point,
    line_end: Point,
    line_band_pixels: int,
    ids: list[int],
    xyxy_list: list[list[float]],
    tracker: DoorCrossingTracker,
    crossing_point_mode: str,
    frame_count: int,
    event_count: int,
    last_crossing: Optional[CrossingDecision],
) -> None:
    line_color = (64, 102, 255)
    text_color = (32, 32, 32)
    panel_color = (245, 247, 250)
    centroid_color = (36, 160, 237)

    cv2.line(
        frame,
        (int(line_start[0]), int(line_start[1])),
        (int(line_end[0]), int(line_end[1])),
        line_color,
        3,
    )
    cv2.putText(
        frame,
        "doorway crossing line",
        (int(line_start[0]), max(30, int(line_start[1]) - 12)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        line_color,
        2,
        cv2.LINE_AA,
    )

    for track_id, xyxy in zip(ids, xyxy_list):
        x1, y1, x2, y2 = (int(value) for value in xyxy)
        point = representative_point(xyxy, crossing_point_mode)
        current_side = tracker.last_side.get(track_id, 0.0)
        side_label = "positive" if current_side > 0 else "negative" if current_side < 0 else "band"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (51, 153, 102), 2)
        cv2.circle(frame, (int(point[0]), int(point[1])), 5, centroid_color, -1)
        cv2.putText(
            frame,
            f"id={track_id} side={side_label}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (51, 153, 102),
            2,
            cv2.LINE_AA,
        )

    cv2.rectangle(frame, (16, 16), (430, 150), panel_color, -1)
    cv2.rectangle(frame, (16, 16), (430, 150), (210, 214, 220), 1)
    status_lines = [
        f"frames: {frame_count}",
        f"tracked people: {len(ids)}",
        f"published events: {event_count}",
        f"point mode: {crossing_point_mode}",
        f"line band: +/- {line_band_pixels}px",
        "press q to quit preview",
    ]
    if last_crossing is not None:
        status_lines.append(f"last crossing: id={last_crossing.track_id} {last_crossing.direction}")

    for index, text in enumerate(status_lines):
        cv2.putText(
            frame,
            text,
            (28, 44 + index * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            text_color,
            2,
            cv2.LINE_AA,
        )


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = YoloPublisherConfig()
    if not config.stream_url:
        raise SystemExit("CAMERA_STREAM_URL is required for publisher-yolo")

    LOGGER.info("Starting YOLO doorway publisher")
    LOGGER.info(
        "Configuration: door_id=%s publisher_id=%s mqtt=%s:%s model=%s confidence=%.2f enter_when=%s preview=%s",
        config.door_id,
        config.publisher_id,
        config.mqtt.host,
        config.mqtt.port,
        config.model_name,
        config.confidence_threshold,
        config.enter_when,
        config.debug_preview,
    )
    LOGGER.info(
        "Crossing line: start=%s end=%s band=%spx point_mode=%s cooldown_frames=%s",
        config.line_start,
        config.line_end,
        config.line_band_pixels,
        config.crossing_point,
        config.track_cooldown_frames,
    )
    LOGGER.info("Opening camera stream: %s", config.stream_url)

    try:
        import cv2
        import paho.mqtt.client as mqtt
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "publisher-yolo requires opencv-python-headless, paho-mqtt, and ultralytics"
        ) from exc

    LOGGER.info("Dependencies imported successfully")
    LOGGER.info("Loading YOLO model: %s", config.model_name)
    model = YOLO(config.model_name)
    LOGGER.info("YOLO model loaded")
    line_start = parse_point(config.line_start)
    line_end = parse_point(config.line_end)
    tracker = DoorCrossingTracker(
        line_start=line_start,
        line_end=line_end,
        enter_when=config.enter_when,
        line_band_pixels=config.line_band_pixels,
        cooldown_frames=config.track_cooldown_frames,
    )

    client = mqtt.Client(client_id=config.mqtt.client_id)
    LOGGER.info("Connecting to MQTT broker at %s:%s", config.mqtt.host, config.mqtt.port)
    client.connect(config.mqtt.host, config.mqtt.port, config.mqtt.keepalive)
    client.loop_start()
    LOGGER.info("Connected to MQTT broker")

    capture = cv2.VideoCapture(config.stream_url)
    if not capture.isOpened():
        raise SystemExit(f"Unable to open camera stream: {config.stream_url}")
    LOGGER.info("Camera stream opened successfully")
    if config.debug_preview:
        LOGGER.info("Debug preview enabled; a local window will open. Press q in that window to quit.")

    frame_count = 0
    event_count = 0
    first_frame_logged = False
    last_crossing: Optional[CrossingDecision] = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                LOGGER.warning("Skipping frame because capture read failed")
                continue
            frame_count += 1

            if not first_frame_logged:
                LOGGER.info("Receiving frames: resolution=%sx%s", frame.shape[1], frame.shape[0])
                LOGGER.info("Publisher is live and waiting for tracked doorway crossings")
                first_frame_logged = True

            results = model.track(frame, persist=True, classes=[0], conf=config.confidence_threshold, verbose=False)
            if not results:
                if config.debug_preview:
                    draw_debug_overlay(
                        cv2,
                        frame,
                        line_start=line_start,
                        line_end=line_end,
                        line_band_pixels=config.line_band_pixels,
                        ids=[],
                        xyxy_list=[],
                        tracker=tracker,
                        crossing_point_mode=config.crossing_point,
                        frame_count=frame_count,
                        event_count=event_count,
                        last_crossing=last_crossing,
                    )
                    cv2.imshow(PREVIEW_WINDOW_NAME, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        LOGGER.info("Debug preview requested shutdown")
                        break
                if frame_count % HEARTBEAT_EVERY_FRAMES == 0:
                    LOGGER.info("Heartbeat: processed %s frames, published %s events", frame_count, event_count)
                continue

            boxes = results[0].boxes
            if boxes is None or boxes.id is None:
                if config.debug_preview:
                    draw_debug_overlay(
                        cv2,
                        frame,
                        line_start=line_start,
                        line_end=line_end,
                        line_band_pixels=config.line_band_pixels,
                        ids=[],
                        xyxy_list=[],
                        tracker=tracker,
                        crossing_point_mode=config.crossing_point,
                        frame_count=frame_count,
                        event_count=event_count,
                        last_crossing=last_crossing,
                    )
                    cv2.imshow(PREVIEW_WINDOW_NAME, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        LOGGER.info("Debug preview requested shutdown")
                        break
                if frame_count % HEARTBEAT_EVERY_FRAMES == 0:
                    LOGGER.info("Heartbeat: processed %s frames, published %s events", frame_count, event_count)
                continue

            ids = boxes.id.int().tolist()
            xyxy_list = boxes.xyxy.tolist()
            if ids and config.debug_log_detections and frame_count % DETECTION_LOG_EVERY_FRAMES == 0:
                LOGGER.info("YOLO currently sees %s tracked person(s): ids=%s", len(ids), ids)
            if frame_count % HEARTBEAT_EVERY_FRAMES == 0:
                LOGGER.info(
                    "Heartbeat: processed %s frames, active_tracks=%s, published %s events",
                    frame_count,
                    len(ids),
                    event_count,
                )
            for track_id, xyxy in zip(ids, xyxy_list):
                point = representative_point(xyxy, config.crossing_point)
                crossing = tracker.update(track_id=track_id, point=point)
                if crossing is None:
                    continue

                last_crossing = crossing
                event = DoorEvent(
                    timestamp=utc_now_iso(),
                    door_id=config.door_id,
                    direction=crossing.direction,
                    source_type="camera",
                    publisher_id=config.publisher_id,
                )
                client.publish(topic_for_door(config.door_id), event.to_json())
                event_count += 1
                LOGGER.info("Published %s for track=%s point=%s", event.to_json(), track_id, point)

            if config.debug_preview:
                draw_debug_overlay(
                    cv2,
                    frame,
                    line_start=line_start,
                    line_end=line_end,
                    line_band_pixels=config.line_band_pixels,
                    ids=ids,
                    xyxy_list=xyxy_list,
                    tracker=tracker,
                    crossing_point_mode=config.crossing_point,
                    frame_count=frame_count,
                    event_count=event_count,
                    last_crossing=last_crossing,
                )
                cv2.imshow(PREVIEW_WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    LOGGER.info("Debug preview requested shutdown")
                    break
    finally:
        LOGGER.info("Shutting down YOLO publisher")
        capture.release()
        if config.debug_preview:
            cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()
        LOGGER.info("MQTT disconnected and camera released")


if __name__ == "__main__":
    run()
