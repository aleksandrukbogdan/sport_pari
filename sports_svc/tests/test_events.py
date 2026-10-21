import unittest

from app import database
from db_case import DatabaseTestCase


class EventTests(DatabaseTestCase):

    def test_scheduled_event(self):
        data = self.client.get("/matches/3").json()
        data["match_id"] = 10
        self.assertEqual(self.client.post("/matches", json=data).status_code, 201)

        event = self.client.get("/events").json()[0]
        self.assertEqual(event["event_type"], "match.scheduled")
        self.assertEqual(event["match_id"], 10)

        for field in [
            "event_id", "occurred_at", "version", "home",
            "away", "starts_at", "sport", "status"
        ]:
            self.assertIn(field, event)

        self.assertEqual(self.client.post("/matches", json=data).status_code, 409)
        self.assertEqual(len(database.read_events()), 1)
        
    def test_finish_and_correction(self):
        self.assertEqual(self.client.post("/matches/3/start").status_code, 200)
        self.assertIn("started_at", database.read_events()[0])

        response = self.client.post(
            "/matches/3/finish",
            json={"home": 2, "away": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.read_events()[-1]["outcome"], "home")
        self.assertEqual(
            self.client.get("/teams/2/stats?season_id=1").json()["points"],
            3
        )

        response = self.client.post(
            "/matches/3/correct-result",
            json={"home": 1, "away": 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.read_events()[-1]["outcome"], "away")
        self.assertEqual(
            self.client.get("/teams/2/stats?season_id=1").json()["points"],
            0
        )
        self.assertEqual(
            [event["event_type"] for event in database.read_events()],
            ["match.started", "match.finished", "match.result_corrected"]
        )

        # Старое событие сохраняет старый результат.
        self.assertEqual(database.read_events()[1]["score"], {"home": 2, "away": 1})
        self.assertEqual(len({event["event_id"] for event in database.read_events()}), 3)

    def test_invalid_transition_and_score(self):
        response = self.client.post(
            "/matches/3/finish",
            json={"home": 1, "away": 0}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post("/matches/999/start").status_code, 404)
        self.assertEqual(self.client.post("/matches/3/start").status_code, 200)
        self.assertEqual(self.client.post("/matches/3/start").status_code, 409)

        response = self.client.post(
            "/matches/3/finish",
            json={"home": -1, "away": 0}
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/matches/3").json()["status"], "live")
        self.assertEqual(len(database.read_events()), 1)

    def test_cancel_match(self):
        self.assertEqual(self.client.post("/matches/3/cancel").status_code, 200)
        self.assertEqual(database.read_events()[-1]["event_type"], "match.cancelled")
        self.assertNotIn("outcome", database.read_events()[-1])
        self.assertEqual(self.client.post("/matches/3/start").status_code, 409)
        self.assertEqual(self.client.post("/matches/3/cancel").status_code, 409)
        self.assertEqual(len(database.read_events()), 1)

    def test_live_score_updates(self):
        stats_before = self.client.get("/teams/2/stats?season_id=1").json()
        standings_before = self.client.get("/standings?season_id=1").json()
        self.client.post("/matches/3/start")

        for score in [{"home": 1, "away": 0}, {"home": 1, "away": 1}]:
            response = self.client.post("/matches/3/score", json=score)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["score"], score)
            self.assertEqual(response.json()["status"], "live")
            self.assertEqual(database.read_events()[-1]["event_type"], "match.score_changed")
            self.assertEqual(database.read_events()[-1]["score"], score)
            self.assertNotIn("outcome", database.read_events()[-1])

        # Пока матч идёт, таблица и статистика не меняются.
        self.assertEqual(
            self.client.get("/teams/2/stats?season_id=1").json(),
            stats_before
        )
        self.assertEqual(
            self.client.get("/standings?season_id=1").json(),
            standings_before
        )
        self.assertEqual(database.read_events()[1]["score"], {"home": 1, "away": 0})
        self.assertEqual(len(database.read_events()), 3)
        self.assertEqual(
            self.client.get("/matches/3").json()["score"],
            {"home": 1, "away": 1}
        )

        self.client.post(
            "/matches/3/finish",
            json={"home": 1, "away": 1}
        )
        stats_after = self.client.get("/teams/2/stats?season_id=1").json()

        self.assertEqual(stats_after["points"], stats_before["points"] + 1)
        self.assertNotEqual(
            self.client.get("/standings?season_id=1").json(),
            standings_before
        )

    def test_unchanged_live_score(self):
        self.client.post("/matches/3/start")
        response = self.client.post(
            "/matches/3/score",
            json={"home": 0, "away": 0}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(database.read_events()), 1)

    def test_score_requires_live_match(self):
        score = {"home": 1, "away": 0}

        self.assertEqual(
            self.client.post("/matches/999/score", json=score).status_code,
            404
        )
        self.assertEqual(
            self.client.post("/matches/1/score", json=score).status_code,
            409
        )
        self.assertEqual(
            self.client.post("/matches/3/score", json=score).status_code,
            409
        )

        self.client.post("/matches/3/cancel")

        self.assertEqual(
            self.client.post("/matches/3/score", json=score).status_code,
            409
        )
        self.assertEqual(len(database.read_events()), 1)

    def test_negative_live_score(self):
        self.client.post("/matches/3/start")
        response = self.client.post(
            "/matches/3/score",
            json={"home": -1, "away": 0}
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.get("/matches/3").json()["score"],
            {"home": 0, "away": 0}
        )
        self.assertEqual(len(database.read_events()), 1)

    def test_draw_and_unchanged_correction(self):
        self.client.post("/matches/3/start")
        self.client.post(
            "/matches/3/finish",
            json={"home": 1, "away": 1}
        )

        self.assertEqual(database.read_events()[-1]["outcome"], "draw")
        self.assertEqual(
            self.client.post(
                "/matches/3/correct-result",
                json={"home": 1, "away": 1}
            ).status_code,
            409
        )
        self.assertEqual(len(database.read_events()), 2)


if __name__ == "__main__":
    unittest.main()