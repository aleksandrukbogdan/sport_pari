import unittest

from psycopg.errors import UniqueViolation

from app import database
from app.events import create_event
from app.schemas import Match
from db_case import DatabaseTestCase


class DatabaseTests(DatabaseTestCase):
    def test_initialization_keeps_saved_changes(self):
        self.client.post("/matches/3/start")
        self.client.post(
            "/matches/3/score",
            json={"home": 2, "away": 0}
        )
        events_before = database.read_events()

        #Повторная подготовка базы не сбрасывает результат
        database.init_db()

        self.assertEqual(database.read_match(3).score.home, 2)
        self.assertEqual(database.read_events(), events_before)
        self.assertEqual(len(database.read_matches()), 3)

    def test_saved_match_and_event(self):
        data = database.read_match(3).model_dump(mode="json")
        data["match_id"] = 20

        response = self.client.post("/matches", json=data)
        self.assertEqual(response.status_code, 201)

        #Чтение открывает новое подключение к базе
        saved = database.read_match(20).model_dump(mode="json")
        self.assertEqual(saved, data)
        self.assertEqual(database.read_events()[-1]["match_id"], 20)

    def test_event_error_rolls_back_match_change(self):
        old_match = database.read_match(3)

        data = old_match.model_dump()
        data.update(status="live", score={"home": 0, "away": 0})
        new_match = Match.model_validate(data)
        event = create_event(new_match, "match.started")

        with database.get_connection() as connection:
            database.insert_event(connection, event)

        #Повтор event_id вызовет ошибку при сохранении события
        with self.assertRaises(UniqueViolation):
            database.update_match(old_match, new_match, event)

        #Изменение матча тоже должно отмениться, так как оно в одной транзакции с событием
        self.assertEqual(database.read_match(3), old_match)
        self.assertEqual(len(database.read_events()), 1)

    def test_outdated_match_does_not_overwrite_new_score(self):
        old_match = database.read_match(3)

        self.client.post("/matches/3/start")
        self.client.post(
            "/matches/3/score",
            json={"home": 1, "away": 0}
        )

        data = old_match.model_dump()
        data["status"] = "cancelled"
        cancelled_match = Match.model_validate(data)

        #Пробуем сохранить изменение на основе старых данных
        with self.assertRaises(database.MatchChangedError):
            database.update_match(
                old_match,
                cancelled_match,
                create_event(cancelled_match, "match.cancelled")
            )

        self.assertEqual(database.read_match(3).status, "live")
        self.assertEqual(database.read_match(3).score.home, 1)
        self.assertEqual(len(database.read_events()), 2)


if __name__ == "__main__":
    unittest.main()