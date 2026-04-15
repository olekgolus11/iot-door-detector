import unittest

from backend.publisher_yolo.main import DoorCrossingTracker, representative_point


def make_tracker(**overrides) -> DoorCrossingTracker:
    options = {
        "line_start": (0.0, 50.0),
        "line_end": (100.0, 50.0),
        "enter_when": "negative_to_positive",
        "line_band_pixels": 10,
        "cooldown_frames": 5,
        "lost_grace_frames": 20,
        "match_max_distance_pixels": 160,
        "event_suppression_frames": 30,
    }
    options.update(overrides)
    return DoorCrossingTracker(**options)


class YoloPublisherTrackerTests(unittest.TestCase):
    def test_representative_point_defaults_to_bottom_center(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "bottom_center")
        self.assertEqual(point, (20.0, 80.0))

    def test_representative_point_supports_center_mode(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "center")
        self.assertEqual(point, (20.0, 50.0))

    def test_representative_point_supports_centroid_alias(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "centroid")
        self.assertEqual(point, (20.0, 50.0))

    def test_representative_point_normalizes_mode_text(self) -> None:
        point = representative_point([10.0, 20.0, 30.0, 80.0], "bottom-center")
        self.assertEqual(point, (20.0, 80.0))

    def test_tracker_emits_event_after_crossing_entire_band(self) -> None:
        tracker = make_tracker()

        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 48.0), frame_number=2))

        crossing = tracker.update(track_id=1, point=(40.0, 80.0), frame_number=3)
        self.assertIsNotNone(crossing)
        assert crossing is not None
        self.assertEqual(crossing.direction, "enter")
        self.assertEqual(crossing.source, "same-id")

    def test_tracker_does_not_emit_when_staying_inside_band(self) -> None:
        tracker = make_tracker(line_band_pixels=20)

        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 45.0), frame_number=1))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 50.0), frame_number=2))
        self.assertIsNone(tracker.update(track_id=1, point=(40.0, 55.0), frame_number=3))

    def test_tracker_cooldown_prevents_duplicate_flips(self) -> None:
        tracker = make_tracker(cooldown_frames=3, event_suppression_frames=0)

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        first = tracker.update(track_id=1, point=(40.0, 80.0), frame_number=2)
        second = tracker.update(track_id=1, point=(40.0, 20.0), frame_number=3)

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_tracker_recovers_crossing_after_id_drop_in_band(self) -> None:
        tracker = make_tracker()

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        tracker.update(track_id=1, point=(40.0, 48.0), frame_number=2)
        tracker.mark_missing_tracks(set(), frame_number=3)

        crossing = tracker.update(track_id=2, point=(42.0, 80.0), frame_number=4)

        self.assertIsNotNone(crossing)
        assert crossing is not None
        self.assertEqual(crossing.direction, "enter")
        self.assertEqual(crossing.source, "recovered-id")
        self.assertEqual(crossing.recovered_from_track_id, 1)

    def test_tracker_recovers_when_first_lost_point_was_inside_band(self) -> None:
        tracker = make_tracker()

        tracker.update(track_id=1, point=(40.0, 48.0), frame_number=1)
        tracker.mark_missing_tracks(set(), frame_number=2)

        crossing = tracker.update(track_id=2, point=(42.0, 80.0), frame_number=3)

        self.assertIsNotNone(crossing)
        assert crossing is not None
        self.assertEqual(crossing.direction, "enter")

    def test_tracker_does_not_recover_when_new_id_stays_on_same_side(self) -> None:
        tracker = make_tracker()

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        tracker.mark_missing_tracks(set(), frame_number=2)

        crossing = tracker.update(track_id=2, point=(42.0, 22.0), frame_number=3)

        self.assertIsNone(crossing)

    def test_tracker_does_not_recover_when_new_id_is_too_far_away(self) -> None:
        tracker = make_tracker(match_max_distance_pixels=15)

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        tracker.mark_missing_tracks(set(), frame_number=2)

        crossing = tracker.update(track_id=2, point=(90.0, 80.0), frame_number=3)

        self.assertIsNone(crossing)

    def test_tracker_does_not_recover_after_grace_window(self) -> None:
        tracker = make_tracker(lost_grace_frames=2)

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        tracker.mark_missing_tracks(set(), frame_number=2)

        crossing = tracker.update(track_id=2, point=(42.0, 80.0), frame_number=5)

        self.assertIsNone(crossing)

    def test_recovered_crossing_suppresses_old_id_returning(self) -> None:
        tracker = make_tracker(event_suppression_frames=30)

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        tracker.mark_missing_tracks(set(), frame_number=2)
        first = tracker.update(track_id=2, point=(42.0, 80.0), frame_number=3)
        second = tracker.update(track_id=1, point=(40.0, 20.0), frame_number=4)
        third = tracker.update(track_id=1, point=(41.0, 80.0), frame_number=5)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertIsNone(third)

    def test_event_suppression_prevents_jitter_duplicate_from_new_id(self) -> None:
        tracker = make_tracker(cooldown_frames=0, event_suppression_frames=30)

        tracker.update(track_id=1, point=(40.0, 20.0), frame_number=1)
        first = tracker.update(track_id=1, point=(40.0, 80.0), frame_number=2)
        tracker.mark_missing_tracks(set(), frame_number=3)
        tracker.update(track_id=2, point=(42.0, 20.0), frame_number=4)
        second = tracker.update(track_id=2, point=(42.0, 80.0), frame_number=5)

        self.assertIsNotNone(first)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
