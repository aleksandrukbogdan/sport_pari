from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError

from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.config import settings
from app.errors import NewsNotFound
from app.preview import error_response
from app.preview import router as preview_router
from app.ui import ROOT


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="news-svc", version="0.1.0", lifespan=lifespan)
if settings.preview_enabled:
    app.include_router(preview_router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(NewsNotFound)
async def news_not_found(_: Request, __: NewsNotFound) -> JSONResponse:
    if _.url.path.startswith("/preview"):
        return error_response(
            _,
            "Материал не найден",
            "Эта публикация недоступна. Вернитесь к новостям.",
            status_code=404,
        )
    return JSONResponse(status_code=404, content={"detail": "News not found"})


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, error: StarletteHTTPException):
    if request.url.path.startswith("/preview"):
        return error_response(
            request,
            "Не удалось выполнить действие",
            "Проверьте подключение или войдите в профиль ещё раз. Вы можете вернуться к новостям и повторить попытку.",
            status_code=error.status_code,
        )
    return await http_exception_handler(request, error)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    if request.url.path.startswith("/preview"):
        return error_response(
            request,
            "Проверьте введённые данные",
            "Параметры страницы или отправленные данные некорректны. Вернитесь к новостям и повторите действие.",
            status_code=422,
        )
    return await request_validation_exception_handler(request, error)


@app.exception_handler(SQLAlchemyError)
async def storage_error(request: Request, error: SQLAlchemyError):
    if request.url.path.startswith("/preview"):
        return error_response(
            request,
            "Не удалось загрузить новости",
            "Хранилище временно недоступно. Попробуйте ещё раз.",
            status_code=503,
        )
    return JSONResponse(
        status_code=503, content={"detail": "Storage temporarily unavailable"}
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
