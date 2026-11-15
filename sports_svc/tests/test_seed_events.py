import os
import unittest

from app.seed_events import build_seed_events
from app.seed_events import seed_events_enabled


class SeedEventTests(unittest.TestCase):
    def test_seed_is_off_unless_requested(self):
        os.environ.pop("SPORTS_SEED_EVENTS", None)
        self.assertFalse(seed_events_enabled())

    def test_finished_matches_start_with_scheduled(self):
        events = build_seed_events()
        types = [(event["match_id"], event["event_type"]) for event in events]

        self.assertEqual(
            types,
            [
                (1, "match.scheduled"),
                (1, "match.finished"),
                (2, "match.scheduled"),
                (2, "match.finished"),
                (3, "match.scheduled"),
            ],
        )
        finished = [event for event in events if event["event_type"] == "match.finished"]
        self.assertEqual(finished[0]["outcome"], "home")
        self.assertEqual(finished[0]["score"], {"home": 2, "away": 1})
        self.assertEqual(finished[1]["outcome"], "draw")
        self.assertNotIn("score", events[-1])
        self.assertEqual(len({event["event_id"] for event in events}), len(events))


if __name__ == "__main__":
    unittest.main()
