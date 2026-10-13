import logging
import os
from contextlib import asynccontextmanager

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.keycloak import KeycloakClient, KeycloakUnavailable
from app.routers.auth import router as auth_router

logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None


def cleanup_deleted_users() -> None:
    """Hard-delete users scheduled for deletion >6 months ago."""
    from app.config import get_settings
    from app.keycloak import KeycloakClient

    settings = get_settings()
    kc = KeycloakClient(settings)
    try:
        users = kc.get_users_scheduled_for_deletion()
        for u in users:
            kc.hard_delete_user(u["id"])
            logger.info("Hard-deleted user %s (%s)", u["id"], u.get("username"))
    except Exception:
        logger.exception("cleanup_deleted_users failed")
    finally:
        kc.close()


def get_postgres_url() -> str:
    """Build PostgreSQL URL from environment (same as Keycloak)."""
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "keycloak")
    user = os.getenv("POSTGRES_USER", "keycloak")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    app.state.keycloak = KeycloakClient(get_settings())

    if os.getenv("RUN_SCHEDULER") == "true":
        jobstores = {"default": SQLAlchemyJobStore(url=get_postgres_url(), tablename="apscheduler_jobs")}
        scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
        scheduler.add_job(
            cleanup_deleted_users,
            "cron",
            hour=3,
            minute=0,
            id="cleanup_deleted_users",
            replace_existing=True,
            coalesce=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        logger.info("Scheduler started (cleanup at 03:00 UTC)")

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
    app.state.keycloak.close()


app = FastAPI(title="user-svc", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)


@app.exception_handler(KeycloakUnavailable)
async def keycloak_unavailable_handler(_: Request, __: KeycloakUnavailable) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "identity provider unavailable"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
