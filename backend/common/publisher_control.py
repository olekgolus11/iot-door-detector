from __future__ import annotations

import json
from typing import Any


MOCK_PUBLISHER_CONTROL_TOPIC = "control/publishers/mock"


def build_mock_publisher_control_payload(enabled: bool) -> str:
    return json.dumps({"enabled": enabled}, separators=(",", ":"))


def parse_mock_publisher_control_payload(raw: Any) -> bool:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Mock publisher control payload must be valid JSON") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("enabled"), bool):
        raise ValueError("Mock publisher control payload must include a boolean enabled field")
    return raw["enabled"]
