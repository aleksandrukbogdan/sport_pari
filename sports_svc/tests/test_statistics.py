import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.sample_data import MATCHES
from app.schemas import Match
from app.statistics import team_statistics, standings

from db_case import DatabaseTestCase


def test_match(number, home, away, home_score, away_score, status="finished", season=1):
    #создаем вымышленный матч для проверки расчётов
    return Match(
        match_id=number, season_id=season,
        home={"id": home, "name": f"Команда {home}"},
        away={"id": away, "name": f"Команда {away}"},
        starts_at="2026-10-01T15:00:00Z", status=status,
        score={"home": home_score, "away": away_score},
    )


class StatisticsTests(DatabaseTestCase):
    def test_home_and_away_results(self):
        matches = [
            test_match(1, 1, 2, 2, 1),
            test_match(2, 2, 1, 0, 0),
            test_match(3, 2, 1, 3, 1),
        ]
        result = team_statistics(matches, 1, 1)
        self.assertEqual(result["played"], 3)
        self.assertEqual((result["wins"], result["draws"], result["losses"]), (1, 1, 1))
        self.assertEqual((result["goals_for"], result["goals_against"]), (3, 4))
        self.assertEqual(result["goal_difference"], -1)
        self.assertEqual(result["points"], 4)

    def test_ignore_unfinished_cancelled_and_other_season(self):
        matches = [
            test_match(1, 1, 2, 2, 1),
            test_match(2, 1, 2, 5, 0, status="live"),
            test_match(3, 1, 2, 5, 0, status="cancelled"),
            test_match(4, 1, 2, 5, 0, season=2),
        ]
        result = team_statistics(matches, 1, 1)
        self.assertEqual(result["played"], 1)
        self.assertEqual(result["points"], 3)

    def test_scheduled_team_has_zero_statistics(self):
        match = Match(match_id=1, season_id=1,
                      home={"id": 1, "name": "А"}, away={"id": 2, "name": "Б"},
                      starts_at="2026-11-01T15:00:00Z", status="scheduled")
        self.assertEqual(team_statistics([match], 1, 1)["played"], 0)
        self.assertIsNone(team_statistics([match], 99, 1))

    def test_standings_order(self):
        table = standings(MATCHES, 1)
        self.assertEqual([row["team_id"] for row in table], [1, 3, 2])
        self.assertEqual([row["position"] for row in table], [1, 2, 3])
        self.assertEqual(standings(MATCHES, 99), [])

    def test_api_statistics_and_errors(self):
        client = TestClient(app)
        response = client.get("/teams/1/stats?season_id=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["points"], 4)
        self.assertEqual(client.get("/teams/999/stats?season_id=1").status_code, 404)
        self.assertEqual(client.get("/standings?season_id=0").status_code, 422)


if __name__ == "__main__":
    unittest.main()
