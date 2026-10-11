# CLAUDE.md - permanent operating instructions

Permanent rules only. Live status lives in `docs/engineering/PROJECT_STATE.md`; do not keep a diary here.

## Project
Interval Assistance: research-grade heart-rate interval-training assistance. Python 3.12+ backend (FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic; SQLite for dev/CI, PostgreSQL is the production target), React/TypeScript/Vite/Vitest frontend. Specs: `docs/` (ARCHITECTURE, DATA_MODEL, SCIENTIFIC_SPECIFICATION, TESTING_STRATEGY, DEVELOPMENT, API_SPECIFICATION).

## Architecture and boundaries (enforced by import-linter, `lint-imports`)
Layers under `src/interval_assistance/`: `core` / `sensors` / `signal` (pure) / `storage` / `ingestion` (application layer) / `api` + `schemas`.
- `signal`: no storage, sqlalchemy or fastapi. `sensors`: no signal, storage or sqlalchemy. `storage`: no api, sensors or signal.
- Nothing below `ingestion` imports it; `ingestion` does not import `api`/web frameworks.
- Only `storage/models.py`, `storage/repositories.py` and migration `0002` may name the raw-sample table (guard test `tests/unit/test_repository_guards.py`).
- Repositories are append-only for raw samples and assessments; the service owns transactions.

## Scientific integrity
- Never invent physiological formulas, thresholds, defaults, claims, hardware capabilities or undocumented domain semantics. Numbers must come from documents or be clearly test-only.
- Preserve raw sensor data and provenance exactly; derived data is separate, linked and reproducible.
- All stored timestamps are UTC. No BLE/Polar, interval engine, VO2max/CPET/calibration, ML, filtering/correction/interpolation, WebSocket/UI or production auth unless the user explicitly approves that phase.

## Code and verification standards
- Match surrounding style; strict mypy; ruff (lint + format); deterministic tests (injected `Clock`/ids, no wall-clock or randomness without seeds).
- Before claiming done, run and report actual results of: `ruff check .`, `ruff format --check .`, `mypy`, `lint-imports`, `pytest -q`, and for schema work an Alembic upgrade/check/downgrade on a scratch SQLite DB. Never claim a check passed unless it ran and passed; list skipped or failed checks.
- Windows: use `.venv/Scripts/python` and `.venv/Scripts/<tool>`; working files are CRLF. For large multi-quote scripts use the Write tool, not shell heredocs.

## Git safety
- Never commit, stage, push, merge, rebase, reset, amend, switch branches or force-push unless the user explicitly asks in that message. Never push or merge to `main` without explicit instruction. Do not modify `README.md`. Do not bypass hooks.
- Approval is per action; earlier approval does not carry over.
- Commit trailer when asked to commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Memory protocol
1. Start of any repository task: read this file and `docs/engineering/PROJECT_STATE.md`; run `git status --short --branch` and `git rev-parse HEAD`; read only the code/docs relevant to the task.
2. If memory and repository disagree, trust verifiable repository facts, reconcile, and update the memory before changing files. Never assume remembered uncommitted changes still exist; revalidate old test results when the covered code changed.
3. Simple questions that change nothing: no broad inspection, no file edits.
4. Update `PROJECT_STATE.md` at checkpoints (task start/scope change/block/finish, decision, verification run, failure, Git change, new risk or question, next action change) and always before the final reply of any task involving work, investigation or verification. Record real commands and results; mark assumptions as unverified.
5. Keep it compact and current: remove superseded status, but never drop an unresolved risk/decision without recording its resolution. Do not use today's date unless known; otherwise write `unknown`.
6. Final report to the user, compact: what changed, what was verified, what remains, next recommended action. Do not claim a memory update unless the file was edited and rechecked.
7. Save the memory before context gets critically low; files are the handoff between sessions.

## Uncertainty and incomplete work
- Do not silently resolve a material ambiguity: stop before that behavior, give the evidence and name the smallest decision needed. Record it under "Unresolved questions" in the state file.
- Failing tests or incomplete work are reported as such, with output and the exact point to resume; never hidden or papered over.
- Keep context use small: targeted reads, bounded output, no pasted full diffs or logs.
