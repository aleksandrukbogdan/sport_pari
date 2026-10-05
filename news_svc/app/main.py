from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="news-svc", version="0.1.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(NotImplementedError)
async def not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
