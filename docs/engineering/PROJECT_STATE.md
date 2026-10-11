# PROJECT_STATE (canonical live memory)

## 1. Project identity and objective
Interval Assistance (`r80ab23/interval-assistance`): research-grade HR interval-training assistance, built in gated phases. Rules in root `CLAUDE.md`.

## 2. Architecture and dependency boundaries
`core` / `sensors` / `signal` (pure) / `storage` / `ingestion` / `api`+`schemas`. Enforced by 6 import-linter contracts (see CLAUDE.md). API routes pinned to `/health` and `/status` (`tests/integration/test_api.py`).

## 3. Git state (see `git log`/`git status` for current truth)
- Branch `main`. Local history after approval: `a9e00ee` (storage schema), then `feat(ingestion): add durable signal assessment ingestion` (Step 3 code + tests), then `docs: add project memory and ingestion notes`. All three were authorized for push to `origin/main` (fast-forward from `10ed2cc`); confirm with `git status --short --branch` that local and remote match.
- Re-run `git status --short --branch` at session start; do not trust this section blindly.

## 4. Current phase and immediate objective
Phase 2a, Step 3 "Ingestion and Durable Signal Assessment": Step 3 implemented, reviewed and committed. Next milestone: user-defined (not started).

## 5. Completed work
- Phases 0, 1 (PR #1), 2a specification (PRs #2-#4), 2a Step 1 signal core (PR #5, merged `10ed2cc`).
- Step 2 storage schema + migration `0002`: committed locally as `a9e00ee` (unpushed).
- Step 3 ingestion + assessment-failure recovery + large-number fix: committed (see section 3); details in section 6.

## 6. In-progress work
Step 3 is code-complete and committed; the assessment-failure correction (section 8) is implemented in `ingestion/service.py` + 6 new tests in `tests/integration/test_ingestion.py`:
- `storage/repositories.py`: append-only; only update is `close_recording_session`; never commits.
- `ingestion/mapping.py`, `ingestion/service.py`: `IngestionService(session_factory, clock, ids)` with `open_session`, `ingest`, `close`. Raw row committed first (txn 1), then assessment + gap (txn 2); in-memory stream state advances only after txn 2. Close persists due stale range, sets `ended_at`, `end_reason="completed"`.
- Signal fix: ints too large for float no longer raise `OverflowError` (`is_finite_number`, `_jump_exceeds`).
- Two new import-linter contracts in `pyproject.toml`; guard allowlist updated; `DEVELOPMENT.md` layout updated.
Remaining: nothing. Step 3 is committed.

## 7. Next actions
1. Verify the push landed (`git status` shows no ahead/behind).
2. Then plan the next step (user-defined).

## 8. Important decisions
- Ingestion uses an existing sensor; never creates/registers one (confirmed).
- Session closes only via explicit `close()`; no shutdown/restart recovery or auto-close (confirmed).
- `is_synthetic` fixed at open; mismatching samples rejected before any write or state change (confirmed).
- Finite-value validation and non-finite-to-marker conversion stay in ingestion; no numeric CHECK constraint, no schema change (confirmed).
- `end_reason="completed"` is in the documented vocabulary (DATA_MODEL 4.4a `completed | interrupted`, DB CHECK in `0002`) (confirmed by docs; using it for explicit close is still my choice).
- Sensor-kind vs `source_kind` compatibility is NOT required by docs, so it is intentionally unchecked (confirmed by docs).
- FIXED false A->C gap. When a committed raw sample's assessment persistence fails, `unassessed_pending` is set and the stream state does NOT advance. The next assessed sample is evaluated against an empty `StreamState` (no gap, duplicate, out-of-order or jump finding across the missing sample). Consecutive failures keep the flag; it clears only after a later assessment transaction commits, and only then does the stream state advance. No `GOOD` is fabricated; raw-first two-transaction persistence unchanged (confirmed; option (b) chosen by user).
- Stale: `close()` evaluates `stale` from the latest `received_at` among ALL committed raw samples, assessed or not (tracked in the service as `max_received_at`/`max_received_sample_id`, updated right after the raw commit, independent of assessment); `after_sample_id` is the first sample holding that maximum, possibly an unassessed one. After a restart the stream state's `max_received_at` is kept equal to this overall maximum. The flag and these fields are in memory only (sessions are not resumable). APPROVED by user; consistent with DATA_MODEL/ARCHITECTURE (stale = open range from the last received sample to the injected `now`).
- Replay sessions rejected at open; simulated/manual sessions must be synthetic (implemented, provisional).
- `METHOD_VERSION="1"` (UNCHANGED, still needs a project decision; DATA_MODEL only says "a string bumped on any rule change", no convention).
- Explicit close uses `end_reason="completed"` (provisional; `interrupted` reserved for dead-process sessions, not handled).
- Huge int beyond float range: signal layer says `impossible_hr`; mapper raises `ValueError` before any write (provisional).

## 9. Unresolved questions and blockers
- Confirm `METHOD_VERSION="1"` (docs only say "a string bumped on any rule change"; left unchanged).
- RESOLVED: assessment-failure behavior (section 8). Residual: findings involving the unassessed sample itself are never produced. Docs (DATA_MODEL 2.2) only say unassessed != GOOD and "Part 2a does not repair this"; they do not describe the restart behavior - consider one sentence there (not done; user's call).
- Minor: `list_signal_assessments` orders by (`created_at`, `id`); rows created in the same instant order by random id (cosmetic, tests don't depend on it).
- Edge: if a commit raised after actually committing, the unspent sequence would collide on the next insert (UNIQUE) and fail loudly; not silent.
- A naive device timestamp is stored NULL and cannot be reproduced when re-folding stored rows.
- `source_kind` vs sensor kind compatibility is not checked (no mapping defined).
- Stale range `after_sample_id` = first sample holding the max `received_at`.
- Sessions exist only in the opening process; no resume.
- PostgreSQL runtime untested (DDL compilation only).

## 10. Verification record (current code)
- `ruff check .`: passed. `ruff format --check .`: 80 files formatted.
- `mypy`: no issues, 67 source files. `lint-imports`: 6 kept, 0 broken.
- `pytest -q`: 421 passed, 1 warning (Starlette/httpx deprecation).
- Alembic (scratch SQLite): head `0002`, upgrade, check ("No new upgrade operations"), downgrade to base all OK.
- `git diff --check`: clean. No frontend checks were run in this step.
Fresh run in the finalization task (after the one-sentence DATA_MODEL edit): `ruff check .` passed; `ruff format --check .` 82 files formatted; `mypy` no issues in 67 files; `lint-imports` 6 kept, 0 broken; `pytest -q` 427 passed, 1 warning; `git diff --check` clean (fresh). Alembic cycle NOT re-run for the correction (no schema/migration change; last run before it was OK). PostgreSQL runtime NOT performed (DDL compilation only).
Final diff review (read-only; no code changed; no scope creep, transaction boundaries, import contracts, append-only repositories, guard allowlist and docs claims all consistent; no doc claims PostgreSQL runtime verification) found: raw-first durability, sequence gap-freeness, pre-write rejection of mismatches and huge ints, atomic close with retry, existing-sensors-only all hold and are tested.

## 11. Relevant files
- `src/interval_assistance/signal/`: pure quality assessment (`assess_sample`, `evaluate_stale`, `check_identity`).
- `src/interval_assistance/storage/models.py`, migration `0002`: five tables; `repositories.py`: append-only access.
- `src/interval_assistance/ingestion/{mapping,service}.py`: row mapping; open/ingest/close.
- Tests: `tests/integration/test_ingestion.py`, `tests/unit/ingestion/`, `tests/unit/signal/test_large_numbers.py`, `tests/unit/test_import_contracts.py`, `tests/unit/test_repository_guards.py`; shared helpers `tests/unit/signal/helpers.py`.
- Docs: `docs/DATA_MODEL.md` (4.x tables), `ARCHITECTURE.md` (5.1a), `DEVELOPMENT.md`.

## 12. Scope restrictions and approval requirements
Out of scope until approved: API/WebSocket/UI, replay, sensor registration, config loading/new settings, BLE/Polar, interval engine, interpolation/correction/reassessment, restart recovery, PostgreSQL runtime, schema/migration changes, concurrent ingestion, new physiology formulas/thresholds. No commit/push/merge without explicit instruction.

## 13. Resume instructions
Run `git status --short --branch`; ask the user whether to commit Step 3. Revalidate checks if code changed. Do not start new features.

## 14. Last updated
unknown (date not reliably determinable); updated after the final Step 3 diff review.
