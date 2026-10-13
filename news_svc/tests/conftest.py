import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "news_svc_pytest.sqlite")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
