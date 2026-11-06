# Development Guide

Phase 1 foundation plus Phase 2a signal assessment, five-table storage (`0002`), ingestion and closed-session Replay. The API and frontend remain a health/status shell. See `SPECIFICATION_REVIEW.md` for scope.

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
- `src/interval_assistance/storage` - SQLAlchemy base/engine, the five Phase 2a table models, and the append-only `repositories` (caller-owned transactions), and Alembic migrations (`0001` empty baseline, `0002` Phase 2a tables)
- `src/interval_assistance/ingestion` - recording-session open/ingest/close service and sample-to-row mapping (raw row committed first, then the assessment; explicit close only)
- `frontend/` - React, TypeScript, Vite, Vitest shell
- `tests/` - `unit`, `integration`, `property` (Replay integration tests are in `tests/integration/test_replay.py`)

## Replay (Phase 2a)

Use `ingestion.replay.ReplayService(session_factory, ids, sleep=...)` with an injectable asynchronous pacing function (default: `asyncio.sleep`). Call `open(origin_session_id, config=..., logical_start_utc=..., close_elapsed_seconds=..., speed=...)` with all four inputs explicit. The origin must be closed. Then `await execution.run_samples()` and explicitly `execution.close()`; `completed` becomes true only after close commits.

The logical clock follows stored elapsed offsets; sleep affects pacing only. Original receive/device timestamps are retained. Each destination has new IDs and assessments linked to the immediate origin. The exact Replay registry identity is reused or registered separately from generic ingestion. Failures stop the execution without retry or automatic close; a failed destination may remain open. Registration is serialized only within this process. There is no restart recovery or new API endpoint.

Synthetic fixture metadata is in `data/synthetic/replay-basic.fixture.json`; stream hashing and its fixed byte/digest vector are tested in `tests/unit/ingestion/test_replay_fixture.py`. Tests use temporary migrated SQLite databases; PostgreSQL runtime behavior has not been verified.
