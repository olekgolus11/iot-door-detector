import unittest

from backend.publisher_yolo.main import DoorCrossingTracker, representative_point


class YoloPublisherTrackerTests(unittest.TestCase):
    def test_representative_point_defaults_to_bottom_center(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "bottom_center")
        self.assertEqual(point, (20.0, 80.0))

    def test_representative_point_supports_centroid_mode(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "centroid")
        self.assertEqual(point, (20.0, 50.0))

    def test_tracker_emits_event_after_crossing_entire_band(self) -> None:
        tracker = DoorCrossingTracker(
            line_start=(0.0, 50.0),
            line_end=(100.0, 50.0),
            enter_when="negative_to_positive",
            line_band_pixels=10,
            cooldown_frames=5,
        )

        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 20.0)))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 48.0)))

        crossing = tracker.update(track_id=1, point=(40.0, 80.0))
        self.assertIsNotNone(crossing)
        assert crossing is not None
        self.assertEqual(crossing.direction, "enter")

    def test_tracker_does_not_emit_when_staying_inside_band(self) -> None:
        tracker = DoorCrossingTracker(
            line_start=(0.0, 50.0),
            line_end=(100.0, 50.0),
            enter_when="negative_to_positive",
            line_band_pixels=20,
            cooldown_frames=5,
        )

        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 45.0)))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 50.0)))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 55.0)))

    def test_tracker_cooldown_prevents_duplicate_flips(self) -> None:
        tracker = DoorCrossingTracker(
            line_start=(0.0, 50.0),
            line_end=(100.0, 50.0),
            enter_when="negative_to_positive",
            line_band_pixels=10,
            cooldown_frames=3,
        )

        tracker.update(track_id=1, point=(40.0, 20.0))
        first = tracker.update(track_id=1, point=(40.0, 80.0))
        second = tracker.update(track_id=1, point=(40.0, 20.0))

        self.assertIsNotNone(first)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
