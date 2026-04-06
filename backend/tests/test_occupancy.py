import tempfile
import unittest

from backend.common.events import DoorEvent
from backend.subscriber_api.store import EventStore


class EventStoreTests(unittest.TestCase):
    def test_leave_events_do_not_go_negative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            occupancy = store.add_event(
                DoorEvent(timestamp="2026-04-06T18:00:00Z", door_id="door-a", direction="leave")
            )
            self.assertEqual(occupancy, 0)
            self.assertEqual(store.get_current_occupancy(), 0)

    def test_summary_counts_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            store.add_event(DoorEvent("2026-04-06T18:00:00Z", "door-a", "enter"))
            store.add_event(DoorEvent("2026-04-06T18:01:00Z", "door-a", "leave"))
            store.add_event(DoorEvent("2026-04-06T18:02:00Z", "door-b", "enter"))

            summary = store.get_summary()
            self.assertEqual(summary["occupancy"], 1)
            self.assertEqual(summary["total_enters"], 2)
            self.assertEqual(summary["total_leaves"], 1)
            self.assertEqual(len(summary["per_door"]), 2)


if __name__ == "__main__":
    unittest.main()

