import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"

# Always resolve the backend environment file relative to this backend folder,
# not the caller's current working directory.
load_dotenv(dotenv_path=ENV_FILE, override=True)


def _resolve_backend_path(raw_value: str, default_relative_path: str) -> Path:
    value = (raw_value or default_relative_path).strip()
    path = Path(value)
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


@dataclass
class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_LOG_LEVEL: str = os.getenv("APP_LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    APP_ENABLE_BACKGROUND_JOBS: bool = os.getenv("APP_ENABLE_BACKGROUND_JOBS", "true").lower() == "true"

    FRONTEND_ALLOWED_ORIGINS: str = os.getenv(
        "FRONTEND_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )

    SQLSERVER_CONNECTION_STRING: str = os.getenv("SQLSERVER_CONNECTION_STRING", "")
    SQLSERVER_ODBC_DRIVER: str = os.getenv("SQLSERVER_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

    FASTAPI_RUNTIME_ROOT: Path = field(
        default_factory=lambda: _resolve_backend_path(os.getenv("FASTAPI_RUNTIME_ROOT", ""), "runtime")
    )
    TOEIC_STATIC_ROOT: Path = field(
        default_factory=lambda: _resolve_backend_path(os.getenv("TOEIC_STATIC_ROOT", ""), "runtime/static/toeic")
    )
    AUDIO_STATIC_ROOT: Path = field(
        default_factory=lambda: _resolve_backend_path(os.getenv("AUDIO_STATIC_ROOT", ""), "runtime/media/audio")
    )
    IMAGE_STATIC_ROOT: Path = field(
        default_factory=lambda: _resolve_backend_path(os.getenv("IMAGE_STATIC_ROOT", ""), "runtime/media/images")
    )
    ROADMAP_RULES_PATH: Path = field(
        default_factory=lambda: _resolve_backend_path(
            os.getenv("ROADMAP_RULES_PATH", ""),
            "runtime/config/toeic_roadmap_rules.json",
        )
    )

    AUTH_JWT_KEY: str = os.getenv("AUTH_JWT_KEY", "dev-only-super-secret-key-change-me-123456789")
    AUTH_ISSUER: str = os.getenv("AUTH_ISSUER", "GetGoals")
    AUTH_AUDIENCE: str = os.getenv("AUTH_AUDIENCE", "GetGoals.Web")
    AUTH_GOOGLE_CLIENT_ID: str = os.getenv("AUTH_GOOGLE_CLIENT_ID", "")
    AUTH_GOOGLE_EXCHANGE_SECRET: str = os.getenv("AUTH_GOOGLE_EXCHANGE_SECRET", "")

    PAYMENT_BANK_CODE: str = os.getenv("PAYMENT_BANK_CODE", "")
    PAYMENT_BANK_ACCOUNT_NO: str = os.getenv("PAYMENT_BANK_ACCOUNT_NO", "")
    PAYMENT_BANK_ACCOUNT_NAME: str = os.getenv("PAYMENT_BANK_ACCOUNT_NAME", "")
    PAYOS_CLIENT_ID: str = os.getenv("PAYOS_CLIENT_ID", "")
    PAYOS_API_KEY: str = os.getenv("PAYOS_API_KEY", "")
    PAYOS_CHECKSUM_KEY: str = os.getenv("PAYOS_CHECKSUM_KEY", "")
    PAYOS_RETURN_URL: str = os.getenv("PAYOS_RETURN_URL", "http://localhost:5173/payment-success")
    PAYOS_CANCEL_URL: str = os.getenv("PAYOS_CANCEL_URL", "http://localhost:5173/payment-cancel")

    @property
    def payos_client_id(self) -> str:
        return self.PAYOS_CLIENT_ID

    @property
    def payos_api_key(self) -> str:
        return self.PAYOS_API_KEY

    @property
    def payos_checksum_key(self) -> str:
        return self.PAYOS_CHECKSUM_KEY

    @property
    def payos_return_url(self) -> str:
        return self.PAYOS_RETURN_URL

    @property
    def payos_cancel_url(self) -> str:
        return self.PAYOS_CANCEL_URL

    @property
    def payment_bank_code(self) -> str:
        return self.PAYMENT_BANK_CODE

    @property
    def payment_bank_account_no(self) -> str:
        return self.PAYMENT_BANK_ACCOUNT_NO

    @property
    def payment_bank_account_name(self) -> str:
        return self.PAYMENT_BANK_ACCOUNT_NAME

    @property
    def roadmap_rules_path(self) -> Path:
        return self.ROADMAP_RULES_PATH


settings = Settings()
