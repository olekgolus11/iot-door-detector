from __future__ import annotations

import os
from dataclasses import dataclass


def get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def get_int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def get_float_env(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class MqttConfig:
    host: str = get_env("MQTT_HOST", "localhost")
    port: int = get_int_env("MQTT_PORT", 1883)
    client_id: str = get_env("MQTT_CLIENT_ID", "iot-door-detector")
    keepalive: int = get_int_env("MQTT_KEEPALIVE", 60)


@dataclass(frozen=True)
class SubscriberConfig:
    mqtt: MqttConfig = MqttConfig(client_id=get_env("MQTT_CLIENT_ID", "subscriber-api"))
    database_path: str = get_env("DATABASE_PATH", "data/room_occupancy.db")
    api_host: str = get_env("API_HOST", "0.0.0.0")
    api_port: int = get_int_env("API_PORT", 8000)
    sse_retry_ms: int = get_int_env("SSE_RETRY_MS", 3000)


@dataclass(frozen=True)
class MockPublisherConfig:
    mqtt: MqttConfig = MqttConfig(client_id=get_env("MQTT_CLIENT_ID", "publisher-mock"))
    door_ids: tuple[str, ...] = tuple(
        item.strip() for item in get_env("MOCK_DOOR_IDS", "door-a").split(",") if item.strip()
    )
    min_interval_seconds: float = get_float_env("MOCK_MIN_INTERVAL", 0.75)
    max_interval_seconds: float = get_float_env("MOCK_MAX_INTERVAL", 2.5)
    seed: int = get_int_env("MOCK_SEED", 7)


@dataclass(frozen=True)
class YoloPublisherConfig:
    mqtt: MqttConfig = MqttConfig(client_id=get_env("MQTT_CLIENT_ID", "publisher-yolo"))
    stream_url: str = get_env("CAMERA_STREAM_URL", "")
    door_id: str = get_env("DOOR_ID", "door-a")
    model_name: str = get_env("YOLO_MODEL", "yolov8n.pt")
    confidence_threshold: float = get_float_env("YOLO_CONFIDENCE", 0.35)
    enter_when: str = get_env("ENTER_WHEN", "negative_to_positive")
    line_start: str = get_env("LINE_START", "100,100")
    line_end: str = get_env("LINE_END", "540,100")

