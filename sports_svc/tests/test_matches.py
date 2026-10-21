import unittest

from db_case import DatabaseTestCase


class MatchTests(DatabaseTestCase):
    def test_unknown_match(self):
        response = self.client.get("/matches/999")
        self.assertEqual(response.status_code, 404)

    def test_season_filter(self):
        response = self.client.get("/matches?season_id=99")
        self.assertEqual(response.json(), [])

    def test_add_match(self):
        data = self.client.get("/matches/1").json()
        data["match_id"] = 10

        response = self.client.post("/matches", json=data)
        self.assertEqual(response.status_code, 201)

        saved_match = self.client.get("/matches/10").json()
        self.assertEqual(saved_match, data)

        response = self.client.post("/matches", json=data)
        self.assertEqual(response.status_code, 409)

    def test_negative_score(self):
        data = self.client.get("/matches/1").json()
        data["match_id"] = 10
        data["score"]["home"] = -1

        response = self.client.post("/matches", json=data)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.get("/matches/10").status_code,
            404
        )


if __name__ == "__main__":
    unittest.main()