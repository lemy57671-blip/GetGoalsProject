import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import ApiError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GetGoals FastAPI",
    version="0.1.0",
    openapi_version="3.1.0",
)

origins = [x.strip() for x in settings.FRONTEND_ALLOWED_ORIGINS.split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError):
    logger.warning("ApiError on %s %s: %s", request.method, request.url.path, exc.content)
    return JSONResponse(status_code=exc.status_code, content=exc.content)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTPException on %s %s: %s", request.method, request.url.path, exc.detail)

    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    if isinstance(exc.detail, str):
        return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

    return JSONResponse(status_code=exc.status_code, content={"message": "Request failed"})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    logger.warning("ValidationError on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=400,
        content={
            "message": "Validation failed",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(OperationalError)
async def handle_operational_error(request: Request, exc: OperationalError):
    logger.exception("OperationalError on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "message": "Database connection failed. Check SQL Server availability and SQLSERVER_CONNECTION_STRING.",
            "detail": str(exc.orig) if getattr(exc, "orig", None) else str(exc),
        },
    )


@app.exception_handler(ProgrammingError)
async def handle_programming_error(request: Request, exc: ProgrammingError):
    logger.exception("ProgrammingError on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Database schema/query mismatch. Verify table and mapped columns exist.",
            "detail": str(exc.orig) if getattr(exc, "orig", None) else str(exc),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError):
    logger.exception("SQLAlchemyError on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Database operation failed.",
            "detail": str(exc.orig) if getattr(exc, "orig", None) else str(exc),
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "detail": str(exc),
        },
    )


class CORSStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

def _mount_static_directory(url_path: str, directory: Path) -> None:
    if directory.exists():
        app.mount(url_path, CORSStaticFiles(directory=directory), name=url_path.strip("/"))
        logger.info("Mounted static path %s -> %s", url_path, directory)
    else:
        logger.warning(
            "Skipped static mount %s because directory does not exist: %s",
            url_path,
            directory,
        )


_mount_static_directory("/toeic", settings.TOEIC_STATIC_ROOT)
_mount_static_directory("/audio", settings.AUDIO_STATIC_ROOT)
_mount_static_directory("/images", settings.IMAGE_STATIC_ROOT)

# Quan trọng:
# router.py đã định nghĩa các route con như /chat, /auth, /toeic...
# main.py phải gắn prefix="/api" để frontend gọi được /api/chat, /api/auth, /api/toeic...
app.include_router(api_router)