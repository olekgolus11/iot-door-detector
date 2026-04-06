import tempfile
import unittest
import sqlite3

from backend.common.events import DoorEvent
from backend.subscriber_api.store import EventStore


class EventStoreTests(unittest.TestCase):
    def test_leave_events_do_not_go_negative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            result = store.add_event(
                DoorEvent(timestamp="2026-04-06T18:00:00Z", door_id="door-a", direction="leave")
            )
            self.assertTrue(result["accepted"])
            self.assertEqual(result["occupancy"], 0)
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

    def test_paused_collection_rejects_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            store.update_control_state(collection_enabled=False)
            result = store.add_event(
                DoorEvent(
                    timestamp="2026-04-06T18:00:00Z",
                    door_id="door-a",
                    direction="enter",
                    source_type="mock",
                )
            )

            self.assertFalse(result["accepted"])
            self.assertEqual(result["reason_code"], "collection_paused")
            self.assertEqual(store.get_current_occupancy(), 0)
            self.assertEqual(len(store.list_rejected_events()), 1)

    def test_source_mode_gates_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            store.update_control_state(active_source_mode="camera")
            result = store.add_event(
                DoorEvent(
                    timestamp="2026-04-06T18:00:00Z",
                    door_id="door-a",
                    direction="enter",
                    source_type="mock",
                )
            )

            self.assertFalse(result["accepted"])
            self.assertEqual(result["reason_code"], "inactive_source")

    def test_baseline_update_sets_current_occupancy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = EventStore(f"{tmp_dir}/test.db")
            store.update_control_state(baseline_occupancy=4)
            self.assertEqual(store.get_current_occupancy(), 4)
            self.assertEqual(store.get_control_state()["baseline_occupancy"], 4)

    def test_legacy_events_table_is_migrated_on_startup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = f"{tmp_dir}/legacy.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    door_id TEXT NOT NULL,
                    direction TEXT NOT NULL
                );

                CREATE TABLE state (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );

                INSERT INTO state(key, value) VALUES ('occupancy', 0);
                """
            )
            conn.close()

            store = EventStore(db_path)
            result = store.add_event(
                DoorEvent(
                    timestamp="2026-04-06T18:00:00Z",
                    door_id="door-a",
                    direction="enter",
                    source_type="mock",
                    publisher_id="mock-1",
                )
            )

            self.assertTrue(result["accepted"])
            events = store.list_events(limit=10)
            self.assertEqual(events[0]["source_type"], "mock")
            self.assertEqual(events[0]["publisher_id"], "mock-1")


if __name__ == "__main__":
    unittest.main()
