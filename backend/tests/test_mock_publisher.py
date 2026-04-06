import random
import unittest

from backend.publisher_mock.main import MockDoorState, build_next_event


class MockPublisherTests(unittest.TestCase):
    def test_first_event_enters_when_room_empty(self) -> None:
        state = MockDoorState()
        event = build_next_event(state, "door-a", random.Random(1))
        self.assertEqual(event.direction, "enter")

    def test_mock_state_never_goes_negative(self) -> None:
        state = MockDoorState(occupancy_by_door={"door-a": 1})
        rng = random.Random(2)
        for _ in range(20):
            event = build_next_event(state, "door-a", rng)
            self.assertIn(event.direction, ("enter", "leave"))
            self.assertGreaterEqual(state.occupancy_by_door["door-a"], 0)


if __name__ == "__main__":
    unittest.main()

