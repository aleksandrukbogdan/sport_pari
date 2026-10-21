from contextlib import contextmanager
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import sql

from app import database
from app.main import app


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        #Для каждого теста создаём отдельную схему
        self.schema = "test_" + uuid4().hex
        self.original_connection = database.get_connection

        with self.original_connection() as connection:
            connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(
                    sql.Identifier(self.schema)
                )
            )

        self.addCleanup(self.drop_schema)

        replacement = patch(
            "app.database.get_connection",
            self.connection_for_test
        )
        replacement.start()
        self.addCleanup(replacement.stop)

        database.init_db()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @contextmanager
    def connection_for_test(self):
        with self.original_connection() as connection:
            connection.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(self.schema)
                )
            )
            yield connection

    def drop_schema(self):
        with self.original_connection() as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(
                    sql.Identifier(self.schema)
                ))