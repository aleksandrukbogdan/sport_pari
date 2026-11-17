import unittest

from app.sample_data import MATCHES
from app.schemas import Match
from app.statistics import team_statistics


def match(match_id, day, home_score, away_score, *, home=1, season=1, status="finished"):
    return Match(
        match_id=match_id,
        season_id=season,
        home={"id": home, "name": f"Команда {home}"},
        away={"id": 3 - home, "name": f"Команда {3 - home}"},
        starts_at=f"2026-10-{day:02}T15:00:00Z",
        status=status,
        score={"home": home_score, "away": away_score},
    )


class RecentFormTests(unittest.TestCase):
    def test_five_latest_finished_matches_from_requested_season(self):
        matches = [
            match(50, 2, 1, 0),
            match(70, 7, 3, 1, home=2),  # Команда 1 проиграла в гостях.
            match(20, 7, 1, 1),
            match(31, 6, 0, 1, home=2),  # Команда 1 выиграла в гостях.
            match(4, 4, 0, 0),
            match(80, 3, 2, 0),
            match(90, 8, 2, 0, status="live"),
            match(91, 9, 0, 0, status="cancelled"),
            match(92, 10, 2, 0, season=2),
        ]
        result = team_statistics(matches, 1, 1)
        self.assertEqual(result["recent_form"], ["loss", "draw", "win", "draw", "win"])
        self.assertEqual(result["played"], 6)
        self.assertEqual(result["points"], 11)

    def test_short_and_empty_form(self):
        self.assertEqual(team_statistics(MATCHES, 1, 1)["recent_form"], ["draw", "win"])
        self.assertEqual(team_statistics([MATCHES[2]], 2, 1)["recent_form"], [])
