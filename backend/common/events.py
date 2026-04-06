from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional


Direction = Literal["enter", "leave"]
SourceType = Literal["mock", "camera", "unknown"]


class EventValidationError(ValueError):
    """Raised when an incoming doorway event is malformed."""


@dataclass(frozen=True)
class DoorEvent:
    timestamp: str
    door_id: str
    direction: Direction
    source_type: SourceType = "unknown"
    publisher_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @property
    def topic(self) -> str:
        return topic_for_door(self.door_id)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def topic_for_door(door_id: str) -> str:
    return f"doors/{door_id}/events"


def parse_event(raw: Any) -> DoorEvent:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EventValidationError("Payload is not valid JSON") from exc

    if not isinstance(raw, dict):
        raise EventValidationError("Payload must be a JSON object")

    timestamp = raw.get("timestamp")
    door_id = raw.get("door_id")
    direction = raw.get("direction")
    source_type = raw.get("source_type", "unknown")
    publisher_id = raw.get("publisher_id")

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise EventValidationError("timestamp is required")
    if not isinstance(door_id, str) or not door_id.strip():
        raise EventValidationError("door_id is required")
    if direction not in ("enter", "leave"):
        raise EventValidationError("direction must be 'enter' or 'leave'")
    if source_type not in ("mock", "camera", "unknown"):
        raise EventValidationError("source_type must be 'mock', 'camera', or 'unknown'")
    if publisher_id is not None and not isinstance(publisher_id, str):
        raise EventValidationError("publisher_id must be a string when provided")

    _validate_iso8601(timestamp)
    return DoorEvent(
        timestamp=timestamp,
        door_id=door_id.strip(),
        direction=direction,
        source_type=source_type,
        publisher_id=publisher_id.strip() if isinstance(publisher_id, str) and publisher_id.strip() else None,
    )


def _validate_iso8601(value: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EventValidationError("timestamp must be ISO 8601") from exc
