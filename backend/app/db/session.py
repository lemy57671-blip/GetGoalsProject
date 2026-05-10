import logging
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_odbc_connection_string(raw_connection_string: str) -> tuple[list[str], dict[str, str]]:
    segments: list[str] = []
    options: dict[str, str] = {}

    for item in raw_connection_string.split(";"):
        segment = item.strip()
        if not segment:
            continue
        segments.append(segment)
        if "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        options[key.strip().lower()] = value.strip()

    return segments, options


def _normalize_odbc_connection_string(raw_connection_string: str) -> str:
    segments, options = _parse_odbc_connection_string(raw_connection_string)
    driver = options.get("driver", "")

    if "odbc driver 18 for sql server" in driver.lower() and "encrypt" not in options:
        segments.append("Encrypt=no")
    if "trustservercertificate" not in options:
        segments.append("TrustServerCertificate=yes")
    if "connection timeout" not in options and "connect timeout" not in options:
        segments.append("Connect Timeout=5")

    return ";".join(segments) + ";"


def _sanitize_odbc_connection_string(raw_connection_string: str) -> str:
    segments, _ = _parse_odbc_connection_string(raw_connection_string)
    sanitized_segments: list[str] = []

    for segment in segments:
        if "=" not in segment:
            sanitized_segments.append(segment)
            continue
        key, value = segment.split("=", 1)
        if key.strip().lower() in {"pwd", "password"}:
            sanitized_segments.append(f"{key}=***")
        else:
            sanitized_segments.append(f"{key}={value}")

    return ";".join(sanitized_segments) + ";"


def _build_engine_url(raw_connection_string: str) -> str:
    value = (raw_connection_string or "").strip()
    if "://" in value:
        return value
    if not value:
        raise ValueError("SQLSERVER_CONNECTION_STRING is missing.")
    normalized_connection_string = _normalize_odbc_connection_string(value)
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(normalized_connection_string)}"


def _log_engine_configuration(raw_connection_string: str) -> None:
    _, options = _parse_odbc_connection_string(raw_connection_string)
    logger.info(
        "Initializing SQL Server engine with driver=%s server=%s database=%s trusted_connection=%s",
        options.get("driver", "<missing>"),
        options.get("server", "<missing>"),
        options.get("database", "<missing>"),
        options.get("trusted_connection", "<missing>"),
    )
    logger.debug("ODBC connection string: %s", _sanitize_odbc_connection_string(raw_connection_string))


raw_connection_string = (settings.SQLSERVER_CONNECTION_STRING or "").strip()
_log_engine_configuration(raw_connection_string)


engine = create_engine(
    _build_engine_url(raw_connection_string),
    pool_pre_ping=True,
    fast_executemany=True,
)
if engine.dialect.name == "mssql":
    # SQL Server/pyodbc can report rowcount as -1 for otherwise successful
    # statements. This app does not use ORM version tokens, so do not turn
    # that driver value into a false StaleDataError during submit/review writes.
    engine.dialect.supports_sane_rowcount = False
    engine.dialect.supports_sane_multi_rowcount = False

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@event.listens_for(engine, "connect")
def _on_connect(_, __):
    logger.info("SQL Server connection established successfully.")


@event.listens_for(engine, "handle_error")
def _on_handle_error(exception_context):
    logger.exception("SQL Server operation failed: %s", exception_context.original_exception)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
