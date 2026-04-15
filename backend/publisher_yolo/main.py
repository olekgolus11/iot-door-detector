from __future__ import annotations

import logging
import math
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
    source: str = "same-id"
    recovered_from_track_id: Optional[int] = None


@dataclass
class TrackState:
    track_id: int
    point: Point
    side: int
    distance: float
    last_nonzero_side: Optional[int]
    last_seen_frame: int
    cooldown_until_frame: int = 0


@dataclass
class LostTrackState:
    track_id: int
    point: Point
    side: int
    distance: float
    last_nonzero_side: Optional[int]
    last_seen_frame: int
    cooldown_until_frame: int = 0


def representative_point(xyxy: list[float], mode: str) -> Point:
    x1, y1, x2, y2 = xyxy
    normalized_mode = mode.strip().lower().replace("-", "_")
    if normalized_mode in {"center", "centre", "centroid"}:
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    if normalized_mode != "bottom_center":
        LOGGER.warning("Unknown YOLO_CROSSING_POINT=%r; using bottom_center", mode)
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
        lost_grace_frames: int = 20,
        match_max_distance_pixels: int = 160,
        event_suppression_frames: int = 30,
    ) -> None:
        self.line_start = line_start
        self.line_end = line_end
        self.enter_when = enter_when
        self.line_band_pixels = max(0, line_band_pixels)
        self.cooldown_frames = max(0, cooldown_frames)
        self.lost_grace_frames = max(0, lost_grace_frames)
        self.match_max_distance_pixels = max(0, match_max_distance_pixels)
        self.event_suppression_frames = max(0, event_suppression_frames)
        self.active_tracks: Dict[int, TrackState] = {}
        self.lost_tracks: Dict[int, LostTrackState] = {}
        self.event_suppression_until_frame = 0

    def classify_side(self, point: Point) -> int:
        distance = signed_distance(point, self.line_start, self.line_end)
        if distance > self.line_band_pixels:
            return 1
        if distance < -self.line_band_pixels:
            return -1
        return 0

    def last_side_for(self, track_id: int) -> int:
        state = self.active_tracks.get(track_id)
        if state is None:
            return 0
        return state.last_nonzero_side or 0

    def prune_lost_tracks(self, frame_number: int) -> None:
        stale_track_ids = [
            track_id
            for track_id, state in self.lost_tracks.items()
            if frame_number - state.last_seen_frame > self.lost_grace_frames
        ]
        for track_id in stale_track_ids:
            del self.lost_tracks[track_id]

    def mark_missing_tracks(self, visible_track_ids: set[int], frame_number: int) -> None:
        self.prune_lost_tracks(frame_number)
        missing_track_ids = [
            track_id for track_id in self.active_tracks if track_id not in visible_track_ids
        ]
        for track_id in missing_track_ids:
            state = self.active_tracks.pop(track_id)
            if state.side == 0 or state.last_nonzero_side is not None:
                self.lost_tracks[track_id] = LostTrackState(
                    track_id=state.track_id,
                    point=state.point,
                    side=state.side,
                    distance=state.distance,
                    last_nonzero_side=state.last_nonzero_side,
                    last_seen_frame=state.last_seen_frame,
                    cooldown_until_frame=state.cooldown_until_frame,
                )

    def recently_lost_count(self, frame_number: int) -> int:
        self.prune_lost_tracks(frame_number)
        return len(self.lost_tracks)

    def _direction_for(self, previous_side: int, current_side: int) -> str:
        if (
            previous_side < current_side and self.enter_when == "negative_to_positive"
        ) or (
            previous_side > current_side and self.enter_when == "positive_to_negative"
        ):
            return "enter"
        return "leave"

    def _point_distance(self, first: Point, second: Point) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def _prior_side_for_lost_track(self, lost: LostTrackState) -> Optional[int]:
        if lost.last_nonzero_side is not None:
            return lost.last_nonzero_side
        if lost.distance > 0:
            return 1
        if lost.distance < 0:
            return -1
        return None

    def _is_suppressed(self, frame_number: int) -> bool:
        return frame_number <= self.event_suppression_until_frame

    def _suppress_after_event(self, frame_number: int) -> None:
        self.event_suppression_until_frame = max(
            self.event_suppression_until_frame,
            frame_number + self.event_suppression_frames,
        )

    def _build_state(self, track_id: int, point: Point, side: int, distance: float, frame_number: int) -> TrackState:
        return TrackState(
            track_id=track_id,
            point=point,
            side=side,
            distance=distance,
            last_nonzero_side=side if side != 0 else None,
            last_seen_frame=frame_number,
        )

    def _recover_lost_track(
        self,
        track_id: int,
        point: Point,
        current_side: int,
        current_distance: float,
        frame_number: int,
    ) -> Optional[CrossingDecision]:
        best_track_id: Optional[int] = None
        best_distance: Optional[float] = None
        for lost_track_id, lost in self.lost_tracks.items():
            age = frame_number - lost.last_seen_frame
            if age < 0 or age > self.lost_grace_frames:
                continue
            pixel_distance = self._point_distance(lost.point, point)
            if pixel_distance > self.match_max_distance_pixels:
                continue
            if best_distance is None or pixel_distance < best_distance:
                best_track_id = lost_track_id
                best_distance = pixel_distance

        if best_track_id is None:
            return None

        lost = self.lost_tracks.pop(best_track_id)
        previous_side = self._prior_side_for_lost_track(lost)
        self.active_tracks[track_id] = TrackState(
            track_id=track_id,
            point=point,
            side=current_side,
            distance=current_distance,
            last_nonzero_side=current_side if current_side != 0 else previous_side,
            last_seen_frame=frame_number,
            cooldown_until_frame=lost.cooldown_until_frame,
        )
        if (
            previous_side is None
            or current_side == 0
            or previous_side == current_side
            or frame_number <= lost.cooldown_until_frame
            or self._is_suppressed(frame_number)
        ):
            return None

        direction = self._direction_for(previous_side, current_side)
        self.active_tracks[track_id].cooldown_until_frame = frame_number + self.cooldown_frames
        self._suppress_after_event(frame_number)
        return CrossingDecision(
            track_id=track_id,
            direction=direction,
            point=point,
            source="recovered-id",
            recovered_from_track_id=lost.track_id,
        )

    def update(self, track_id: int, point: Point, frame_number: int) -> Optional[CrossingDecision]:
        self.prune_lost_tracks(frame_number)
        current_side = self.classify_side(point)
        current_distance = signed_distance(point, self.line_start, self.line_end)
        state = self.active_tracks.get(track_id)

        if state is None:
            recovered_crossing = self._recover_lost_track(
                track_id=track_id,
                point=point,
                current_side=current_side,
                current_distance=current_distance,
                frame_number=frame_number,
            )
            if recovered_crossing is not None:
                return recovered_crossing
            if track_id not in self.active_tracks:
                self.active_tracks[track_id] = self._build_state(
                    track_id=track_id,
                    point=point,
                    side=current_side,
                    distance=current_distance,
                    frame_number=frame_number,
                )
            return None

        previous_side = state.last_nonzero_side
        state.point = point
        state.side = current_side
        state.distance = current_distance
        state.last_seen_frame = frame_number
        if current_side != 0:
            state.last_nonzero_side = current_side

        if frame_number <= state.cooldown_until_frame:
            return None

        if current_side == 0:
            return None

        if previous_side is None or previous_side == current_side:
            return None

        if self._is_suppressed(frame_number):
            return None

        direction = self._direction_for(previous_side, current_side)
        state.cooldown_until_frame = frame_number + self.cooldown_frames
        self._suppress_after_event(frame_number)
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
        current_side = tracker.last_side_for(track_id)
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

    cv2.rectangle(frame, (16, 16), (500, 178), panel_color, -1)
    cv2.rectangle(frame, (16, 16), (500, 178), (210, 214, 220), 1)
    status_lines = [
        f"frames: {frame_count}",
        f"tracked people: {len(ids)}",
        f"recently lost tracks: {tracker.recently_lost_count(frame_count)}",
        f"published events: {event_count}",
        f"point mode: {crossing_point_mode}",
        f"line band: +/- {line_band_pixels}px",
        "press q to quit preview",
    ]
    if last_crossing is not None:
        if last_crossing.recovered_from_track_id is None:
            status_lines.append(
                f"last crossing: id={last_crossing.track_id} {last_crossing.direction} {last_crossing.source}"
            )
        else:
            status_lines.append(
                "last crossing: "
                f"id={last_crossing.track_id} from={last_crossing.recovered_from_track_id} "
                f"{last_crossing.direction} {last_crossing.source}"
            )

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
        "Configuration: door_id=%s publisher_id=%s mqtt=%s:%s model=%s tracker=%s confidence=%.2f enter_when=%s preview=%s",
        config.door_id,
        config.publisher_id,
        config.mqtt.host,
        config.mqtt.port,
        config.model_name,
        config.tracker_config,
        config.confidence_threshold,
        config.enter_when,
        config.debug_preview,
    )
    LOGGER.info(
        (
            "Crossing line: start=%s end=%s band=%spx point_mode=%s cooldown_frames=%s "
            "lost_grace_frames=%s match_distance=%spx event_suppression_frames=%s"
        ),
        config.line_start,
        config.line_end,
        config.line_band_pixels,
        config.crossing_point,
        config.track_cooldown_frames,
        config.track_lost_grace_frames,
        config.track_match_max_distance_pixels,
        config.track_event_suppression_frames,
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
        lost_grace_frames=config.track_lost_grace_frames,
        match_max_distance_pixels=config.track_match_max_distance_pixels,
        event_suppression_frames=config.track_event_suppression_frames,
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

            results = model.track(
                frame,
                persist=True,
                classes=[0],
                conf=config.confidence_threshold,
                tracker=config.tracker_config,
                verbose=False,
            )
            if not results:
                tracker.mark_missing_tracks(set(), frame_count)
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
                tracker.mark_missing_tracks(set(), frame_count)
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
            tracker.mark_missing_tracks(set(ids), frame_count)
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
                crossing = tracker.update(track_id=track_id, point=point, frame_number=frame_count)
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
