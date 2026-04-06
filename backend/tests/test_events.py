import unittest

from backend.common.events import EventValidationError, parse_event


class ParseEventTests(unittest.TestCase):
    def test_parse_valid_event(self) -> None:
        event = parse_event(
            {"timestamp": "2026-04-06T18:00:00Z", "door_id": "door-a", "direction": "enter"}
        )
        self.assertEqual(event.door_id, "door-a")
        self.assertEqual(event.direction, "enter")

    def test_reject_invalid_direction(self) -> None:
        with self.assertRaises(EventValidationError):
            parse_event(
                {"timestamp": "2026-04-06T18:00:00Z", "door_id": "door-a", "direction": "sideways"}
            )

    def test_reject_non_json_payload(self) -> None:
        with self.assertRaises(EventValidationError):
            parse_event("not-json")


if __name__ == "__main__":
    unittest.main()

