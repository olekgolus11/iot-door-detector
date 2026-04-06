from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Literal


Direction = Literal["enter", "leave"]


class EventValidationError(ValueError):
    """Raised when an incoming doorway event is malformed."""


@dataclass(frozen=True)
class DoorEvent:
    timestamp: str
    door_id: str
    direction: Direction

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

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise EventValidationError("timestamp is required")
    if not isinstance(door_id, str) or not door_id.strip():
        raise EventValidationError("door_id is required")
    if direction not in ("enter", "leave"):
        raise EventValidationError("direction must be 'enter' or 'leave'")

    _validate_iso8601(timestamp)
    return DoorEvent(timestamp=timestamp, door_id=door_id.strip(), direction=direction)


def _validate_iso8601(value: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EventValidationError("timestamp must be ISO 8601") from exc

