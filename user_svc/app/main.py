from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="user-svc", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
