from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata for Postgres tables.

    Engine, sessions and migrations are intentionally not created yet.
    Postgres is already in compose; repositories will use settings.database_url.
    """
