"""Run the recommendation preview with disposable data and mocked interests."""

import argparse
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn


async def _serve(port: int) -> None:
    from app.db import Base, SessionLocal, engine
    from app.demo_data import load_demo, use_demo_profiles
    from app.main import app

    try:
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
    args = parser.parse_args()
    with TemporaryDirectory(prefix="news-svc-demo-") as directory:
        database = Path(directory) / "demo.sqlite"
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
        asyncio.run(_serve(args.port))


if __name__ == "__main__":
    main()
