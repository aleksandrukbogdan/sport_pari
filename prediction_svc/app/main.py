from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.questions import router as questions_router
from app.routers.session import router as session_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.service_name)
    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(session_router)
    app.include_router(questions_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
