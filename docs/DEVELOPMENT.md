# Development Guide (Phase 1)

Phase 1 foundation only: health/status API, authentication boundary, sensor abstraction with simulator and manual input, SQLAlchemy/Alembic foundation (empty baseline `0001`; Phase 2a adds the five-table schema in migration `0002`, with no repositories or ingestion yet), and a minimal frontend shell. See `SPECIFICATION_REVIEW.md` for scope.

## Backend

Requires Python 3.12 or newer.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows; use .venv/bin/python on Linux/macOS
cp .env.example .env
```

Run the API (development identity is enabled by `.env.example`):

```bash
python -m uvicorn interval_assistance.main:app_factory --factory --port 8000
```

Checks (the same ones CI runs):

```bash
ruff check . && ruff format --check .
mypy
lint-imports
python -m alembic -c alembic.ini upgrade head && python -m alembic -c alembic.ini check && python -m alembic -c alembic.ini downgrade base
pytest
```

Configuration is read from `IA_*` environment variables or `.env` (see `.env.example`). The development identity is disabled by default and is rejected when `IA_ENVIRONMENT=production`. Production requires a PostgreSQL URL; no PostgreSQL driver is installed in Phase 1 (driver choice is OPEN until PostgreSQL is first exercised).

## Frontend

Requires Node 22 or newer.

```bash
cd frontend
npm ci
npm run dev        # proxies /api to http://127.0.0.1:8000
npm run lint && npm run typecheck && npm test && npm run build
```

## Layout

- `src/interval_assistance/core` - settings, logging, `Clock`, id generation, errors, auth vocabulary
- `src/interval_assistance/api` - FastAPI app factory, `/api/v1` routes, authorization seam, error handlers
- `src/interval_assistance/schemas` - response/error envelopes and health schemas
- `src/interval_assistance/sensors` - `HeartRateSensor`, in-memory sample, simulator, manual input
- `src/interval_assistance/storage` - SQLAlchemy base/engine, the five Phase 2a table models, and Alembic migrations (`0001` empty baseline, `0002` Phase 2a tables)
- `frontend/` - React, TypeScript, Vite, Vitest shell
- `tests/` - `unit`, `integration`, `property` (`replay` is reserved for Phase 2)
