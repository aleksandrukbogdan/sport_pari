import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.sample_data import MATCHES
from app.schemas import Match


def meeting(match_id, day, score=(2, 1), *, reverse=False, **changes):
    source = MATCHES[2]
    home, away = (source.away, source.home) if reverse else (source.home, source.away)
    return Match.model_validate({
        "match_id": match_id, "season_id": 2, "home": home, "away": away,
        "starts_at": f"2026-10-{day:02}T15:00:00Z",
        "status": "finished", "score": {"home": score[0], "away": score[1]},
        **changes,
    })


class HeadToHeadTests(unittest.TestCase):
    def test_recent_meetings_count_wins_for_current_teams(self):
        current = meeting(3, 20)
        matches = [
            current, meeting(10, 4), meeting(11, 8, (0, 1), reverse=True),
            meeting(12, 8, (1, 1)), meeting(13, 15, status="live"),
            meeting(14, 23), MATCHES[0],
        ]
        with patch("app.database.read_match", return_value=current), patch(
            "app.database.read_matches", return_value=matches
        ), TestClient(app) as client:
            result = client.get("/matches/3/head-to-head?limit=2")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([m["match_id"] for m in result.json()["matches"]], [12, 11])
        self.assertEqual(result.json()["summary"], {"home_wins": 1, "draws": 1, "away_wins": 0})

    def test_empty_history_missing_match_and_invalid_limit(self):
        with patch("app.database.read_match", side_effect=[MATCHES[2], None]), patch(
            "app.database.read_matches", return_value=MATCHES
        ), TestClient(app) as client:
            result = client.get("/matches/3/head-to-head")
            self.assertEqual(result.json(), {
                "matches": [], "summary": {"home_wins": 0, "draws": 0, "away_wins": 0},
            })
            self.assertEqual(client.get("/matches/99/head-to-head").status_code, 404)
            self.assertEqual(client.get("/matches/3/head-to-head?limit=11").status_code, 422)
