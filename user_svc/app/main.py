from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.keycloak import KeycloakClient, KeycloakUnavailable
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.keycloak = KeycloakClient(get_settings())
    yield
    app.state.keycloak.close()


app = FastAPI(title="user-svc", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)


@app.exception_handler(KeycloakUnavailable)
async def keycloak_unavailable_handler(_: Request, __: KeycloakUnavailable) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "identity provider unavailable"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
