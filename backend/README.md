# FastAPI Backend

This backend now lives inside the frontend repository as `backend/`.

## Runtime Principles
- SQL Server is the only supported database target.
- The existing SQL schema is the source of truth.
- FastAPI does not create schema, run migrations, or alter SQL at startup.
- Runtime config comes from `.env` and process environment variables only.
- Runtime assets are owned by `backend/runtime/`.
- Canonical API routes use lowercase FastAPI-style paths only.

## Project Layout
- `app/main.py`: FastAPI bootstrap, middleware, lifespan, static mounts
- `app/api/routes/`: HTTP route modules
- `app/core/config.py`: environment-driven configuration
- `app/core/security.py`: JWT and password hashing
- `app/db/session.py`: SQLAlchemy engine/session setup
- `app/models/`: DB-first SQLAlchemy mappings
- `app/schemas/`: request/response models
- `app/services/`: domain logic
- `scripts/check_environment.ps1`: local environment validation
- `scripts/run_local.ps1`: local uvicorn startup
- `scripts/smoke_test.ps1`: basic smoke checks after startup
- `runtime/`: FastAPI-owned static, media, and config files

Environment files and runtime paths are resolved relative to this `backend/` folder, so the service can be moved inside another repo without relying on the caller's current working directory.

## Setup
Recommended Python:
- `3.12` or `3.13`

Install and run:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File .\scripts\check_environment.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Optional smoke test:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

## Required Configuration
Always required:
- `SQLSERVER_CONNECTION_STRING`
- `AUTH_JWT_KEY`

Usually configured:
- `APP_ENV`
- `APP_HOST`
- `APP_PORT`
- `APP_LOG_LEVEL`
- `APP_ENABLE_BACKGROUND_JOBS`
- `FRONTEND_ALLOWED_ORIGINS`
- `SQLSERVER_ODBC_DRIVER`

Feature-specific when used:
- `AUTH_GOOGLE_CLIENT_ID`
- `AUTH_GOOGLE_EXCHANGE_SECRET`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `PAYMENT_BANK_CODE`
- `PAYMENT_BANK_ACCOUNT_NO`
- `PAYMENT_BANK_ACCOUNT_NAME`
- `PAYOS_CLIENT_ID`
- `PAYOS_API_KEY`
- `PAYOS_CHECKSUM_KEY`
- `PAYOS_RETURN_URL`
- `PAYOS_CANCEL_URL`

Runtime path overrides are available, but the default permanent locations are:
- `runtime/static/toeic`
- `runtime/media/audio`
- `runtime/media/images`
- `runtime/config/toeic_roadmap_rules.json`

## Runtime Assets
FastAPI serves:
- `/toeic/*` from `runtime/static/toeic`
- `/audio/*` from `runtime/media/audio`
- `/images/*` from `runtime/media/images`

SQL continues to store relative media paths only.

## Legacy Status
- The ASP.NET Core runtime has been retired.
- Legacy C# appsettings files are no longer used.
- Old C# host/runtime files were removed from the active repo layout.
- Import-only and backup-only materials were moved to `legacy_import/`.
- Old PascalCase API compatibility aliases were removed.

## Verification Checklist
- Verify `/api/health`
- Verify `/docs`
- Verify register/login and a JWT-protected endpoint
- Verify TOEIC summary, runner, and static media URLs
- Verify attempts, weekly check, roadmap, dashboard, progress, and review flows
- Verify PayOS order flow and webhook behavior in a safe environment
- Verify chat entitlement behavior with Gemini configured
