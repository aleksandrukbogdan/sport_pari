"""Run the recommendation preview with disposable data and mocked interests."""

import argparse
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn


async def _serve(port: int, real: bool = False) -> None:
    from app.db import Base, SessionLocal, engine
    from app.demo_data import load_demo, use_demo_profiles
    from app.main import app

    try:
        if real:
            import httpx
            from alembic.config import Config

            from alembic import command
            from app.config import settings
            from app.ingest import import_sources

            await asyncio.to_thread(command.upgrade, Config("alembic.ini"), "head")
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as http:
                print(await import_sources(http, settings.news_sources), flush=True)
        else:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with SessionLocal.begin() as session:
                await load_demo(session)
            use_demo_profiles(app)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port))
        print(f"Демо рекомендаций: http://127.0.0.1:{port}/preview", flush=True)
        await server.serve()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=8001, type=int)
    parser.add_argument(
        "--real",
        action="store_true",
        help="Import real RSS into a persistent local database",
    )
    parser.add_argument("--user-service-url", help="Address of the running user_svc")
    args = parser.parse_args()
    if args.user_service_url:
        os.environ["USER_SERVICE_URL"] = args.user_service_url
    if args.real:
        database = Path(".local/news.sqlite").resolve()
        database.parent.mkdir(exist_ok=True)
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
        asyncio.run(_serve(args.port, real=True))
        return
    with TemporaryDirectory(prefix="news-svc-demo-") as directory:
        database = Path(directory) / "demo.sqlite"
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
        os.environ["TRUST_GATEWAY_HEADERS"] = "true"
        asyncio.run(_serve(args.port))


if __name__ == "__main__":
    main()
