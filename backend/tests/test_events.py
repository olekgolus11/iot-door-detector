import unittest

from backend.common.events import EventValidationError, parse_event


class ParseEventTests(unittest.TestCase):
    def test_parse_valid_event(self) -> None:
        event = parse_event(
            {
                "timestamp": "2026-04-06T18:00:00Z",
                "door_id": "door-a",
                "direction": "enter",
                "source_type": "mock",
                "publisher_id": "mock-1",
            }
        )
        self.assertEqual(event.door_id, "door-a")
        self.assertEqual(event.direction, "enter")
        self.assertEqual(event.source_type, "mock")
        self.assertEqual(event.publisher_id, "mock-1")

    def test_reject_invalid_direction(self) -> None:
        with self.assertRaises(EventValidationError):
            parse_event(
                {"timestamp": "2026-04-06T18:00:00Z", "door_id": "door-a", "direction": "sideways"}
            )

    def test_reject_non_json_payload(self) -> None:
        with self.assertRaises(EventValidationError):
            parse_event("not-json")

    def test_reject_invalid_source_type(self) -> None:
        with self.assertRaises(EventValidationError):
            parse_event(
                {
                    "timestamp": "2026-04-06T18:00:00Z",
                    "door_id": "door-a",
                    "direction": "enter",
                    "source_type": "mystery",
                }
            )


if __name__ == "__main__":
    unittest.main()
