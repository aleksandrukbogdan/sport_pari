import os

import psycopg
from psycopg.types.json import Jsonb

from app.sample_data import MATCHES
from app.schemas import Match


class MatchChangedError(Exception):
    pass


def get_connection():
    address = os.getenv(
        "SPORTS_DATABASE_URL",
        "postgresql://sports:sports_local@127.0.0.1:5433/sports"
    )
    return psycopg.connect(address, connect_timeout=5)


def init_db():
    #При ошибке изменения этой операции отменяются
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                data JSONB NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                number BIGSERIAL PRIMARY KEY,
                event_id UUID NOT NULL UNIQUE,
                data JSONB NOT NULL
            )
        """)

        count = connection.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        #Исходные матчи добавляем только в пустую таблицу
        if count == 0:
            for match in MATCHES:
                connection.execute(
                    "INSERT INTO matches (match_id, data) VALUES (%s, %s)",
                    (match.match_id, Jsonb(match.model_dump(mode="json")))
                )


def read_matches():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT data FROM matches ORDER BY match_id"
        ).fetchall()

    return [Match.model_validate(row[0]) for row in rows]


def read_match(match_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT data FROM matches WHERE match_id = %s",
            (match_id,)
        ).fetchone()

    if row is None:
        return None

    return Match.model_validate(row[0])


def insert_event(connection, event: dict):
    connection.execute(
        "INSERT INTO events (event_id, data) VALUES (%s, %s)",
        (event["event_id"], Jsonb(event))
    )


def insert_match(match: Match, event: dict | None):
    #Матч и событие сохраняем вместе
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO matches (match_id, data) VALUES (%s, %s)",
            (match.match_id, Jsonb(match.model_dump(mode="json")))
        )

        if event is not None:
            insert_event(connection, event)


def update_match(old_match: Match, new_match: Match, event: dict):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE matches SET data = %s WHERE match_id = %s AND data = %s",
            (
                Jsonb(new_match.model_dump(mode="json")),
                old_match.match_id,
                Jsonb(old_match.model_dump(mode="json"))
            )
        )

        #Проверяем, не изменил ли матч другой запрос
        if cursor.rowcount == 0:
            raise MatchChangedError(
                "Матч уже изменился. Получите его заново."
            )

        insert_event(connection, event)


def read_events():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT data FROM events ORDER BY number"
        ).fetchall()

    return [row[0] for row in rows]


if __name__ == "__main__":
    init_db()
    print("Таблицы созданы, исходные матчи загружены")