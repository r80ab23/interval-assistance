# PROJECT_STATE (canonical live memory)

## 1. Project identity and objective
Interval Assistance (`r80ab23/interval-assistance`): research-grade HR interval-training assistance in explicitly gated phases. Permanent instructions: root CLAUDE.md and AGENTS.md; normative specifications: docs/.

## 2. Architecture and dependency boundaries
`core` / `sensors` / pure `signal` / `storage` / application `ingestion` / `api`+`schemas`. Six import-linter contracts. Storage does not import domain/sensor/application layers. Repositories own no commits and expose no raw-sample/assessment update/delete. API/frontend remain health/status only.

## 3. Current verified Git state
2026-11-10: main and local origin/main at f8b91eb3f6b2ac96509c6c78c38ee4fcbeff2233 (Replay committed and pushed 2026-11-06). Uncommitted: this memory file and the mypy typing fix in tests/integration/test_replay.py. AGENTS.md untracked and untouched. Nothing staged. Older OneDrive copy (OneDrive/Documents/GitHub/interval-assistance, cd09719, 12 behind, docs only) is obsolete; this checkout is canonical.

## 4. Current phase and immediate objective
Phase 2a complete. Immediate objective: user decides commit/push of the mypy fix, then the next phase (not started; needs explicit approval).

## 5. Completed work
Phase 1 and Phase 2a specifications, signal core (PR #5), storage schema (`a9e00ee`, migration 0002), ingestion (`198a6f1`), memory (`51566a5`), Replay (`f8b91eb`: closed-origin execution, deterministic logical time, provenance, registry reuse, canonical fixture hashing, tests). 2026-11-10: user-authorized fix of the CI mypy failure: `fail_third` in tests/integration/test_replay.py now typed `(db: Session, **values: Any) -> SignalAssessment`, matching `second_call_fails` in test_ingestion.py. Test-only; no runtime code changed.

## 6. In-progress work
None. Mypy fix verified locally, not committed/pushed.

## 7. Next actions
1. Commit and push the mypy fix only on explicit authorization; confirm CI turns green.
2. User questions raised 2026-11-10 (unanswered): AGENTS.md tracked or local-only and which commit trailer (AGENTS.md says Codex, CLAUDE.md says Claude Sonnet 5.5, current session model Claude Opus 5.5); local .venv is Python 3.14.7 while CI uses 3.12; whether to create a local .env; which phase next (Part 2b transport choice OPEN).
3. Decide METHOD_VERSION convention when required; keep the current value meanwhile.

## 8. Important decisions
- Approved Replay contracts: DATA_MODEL 4.6a.1-3, TESTING_STRATEGY 6, SPECIFICATION_REVIEW decisions 18-22. Required explicit config, logical_start_utc, close_elapsed_seconds and speed; no physiological defaults.
- Closed origin only, fixed sequence-order snapshot, empty/replay-of-replay allowed. Original timestamps/payload/synthetic flag preserved; new session/run/IDs and immediate origin links; assessments recomputed, never copied.
- Logical elapsed follows origin elapsed; sleep only paces. Explicit close uses the approved completed reason and must commit before reporting completion. First failure/cancellation is terminal, without retry/resume/auto-close; failed destination may remain open.
- Registry identity exactly (replay, interval-assistance.replay): reuse one, create/commit zero, reject multiple. In-process serialized only, no schema uniqueness or cross-process guarantee. Generic ingestion still requires a registered sensor and rejects Replay at its public open seam.
- Fixture format replay-fixture-stream/1: compact sorted UTF-8 JSON, six sample fields, finite HR bit hex/nonfinite class, UTC microseconds, Base64 payload. String whitespace preserved; no syntactic whitespace. Hash is before SQLite storage.
- Ingestion raw-first transactions unchanged: raw commit precedes assessment commit; state advances only after assessment commit. Failure sets unassessed_pending; next successful sample starts comparison from empty state, so no false bridge findings. No GOOD fabricated.
- Stale references maximum received_at among all committed raw rows, including unassessed; first holder supplies after_sample_id. This is independent of comparison-state reset. No restart recovery.
- Session synthetic flag fixed at open; mismatches rejected before writes. Sensor-kind/source-kind mapping intentionally absent. Nonfinite conversion enforced in ingestion; DB CHECK only excludes simultaneous marker/value. Huge finite integers outside float storage raise before writes.

## 9. Unresolved questions and limitations
- METHOD_VERSION="1" unchanged; concrete versioning convention remains OPEN, not resolved by Replay.
- Naive device timestamps stored as NULL cannot recreate historical invalid_timestamp findings; formerly unassessed rows receive fresh assessments. Replay equality is between equivalent executions, not guaranteed with historical origin assessments.
- No cross-process registry protection, concurrent session writers, retry/resume or automatic disposition of failed open destinations.
- Processing an origin holds its fixed sample set in memory; large-stream scaling is not implemented.
- Existing assessment listing sorts (created_at,id); ties need not be meaningful. A transaction commit that succeeds but raises afterward remains an unresolved failure ambiguity; no automatic recovery is claimed.
- PostgreSQL runtime untested; DDL compilation only. Frontend unchanged and not rerun for Replay.

## 10. Verification record
2026-11-10 (Python 3.14.7 local .venv; caches redirected outside repo): before fix, full pytest 463 passed, 1 Starlette/httpx warning; mypy reproduced exactly the two CI errors; frontend vitest 13 passed, tsc --noEmit clean. After fix: `ruff check .` passed; `ruff format --check .` 87 files formatted; `mypy` no issues in 71 source files; `lint-imports` 6 kept, 0 broken; `pytest -q` 463 passed, 1 warning (50.14s); git diff --check clean. Alembic not run (no schema change). CI not rerun (nothing pushed).

2026-11-06 push/CI: git ls-remote confirmed remote 51566a5 equals parent of f8b91eb; git push origin main succeeded fast-forward. Remote verified at full f8b91eb SHA. CI run 42172296343 (push, exact head f8b91eb) completed FAILURE: backend Mypy failed with two arg-type errors at tests/integration/test_replay.py:381 (expected Session, got forwarded object args); frontend SUCCESS. Logs fetched via gh run view --job 127742689513 --log-failed. Earlier successful mypy predates the two added tests and does not cover them. No code fix or new commit performed. Initial restricted network lookup failed DNS; elevated lookup/push succeeded.

2026-11-06 narrow follow-up: added only two tests in tests/integration/test_replay.py (third assessment fails after two committed successes; nonempty two-generation Replay immediate provenance and unchanged origins). Clarified historical vs subsequent implementation authorization in docs/SPECIFICATION_REVIEW.md. No runtime code changed.
- `.venv/Scripts/python -m pytest -q tests/integration/test_replay.py tests/unit/ingestion/test_replay_fixture.py --basetemp .pytest_cache/replay-nov6-extra`: 36 passed, 1 existing Starlette/httpx warning, 8.70s.
- Ruff check and format check on tests/integration/test_replay.py passed; git diff --check passed (only existing CRLF normalization warning). Full suite, mypy, import-linter and migrations not rerun for these test/documentation-only edits; prior results below are historical. HEAD unchanged, nothing staged/committed/pushed. Next action: explicit user approval for commit scope.

Observed 2026-11-05 before the final documentation-only checkpoint (not rerun or inferred from CI):
- `.venv/Scripts/python -m pytest -q --basetemp .pytest_cache/replay-final-nov5b`: 461 passed, 1 warning in 37.68s. Warning: existing Starlette/httpx deprecation.
- `.venv/Scripts/python -m ruff check .`: passed.
- `.venv/Scripts/python -m ruff format --check .`: 87 files already formatted.
- `.venv/Scripts/python -m mypy`: no issues in 71 source files.
- `.venv/Scripts/lint-imports`: 6 kept, 0 broken (71 files, 234 dependencies).
- Scratch SQLite via TemporaryDirectory + make_alembic_config: command.upgrade(head), command.check, command.downgrade(base) passed; "No new upgrade operations detected." No local/project database used.
- Initial full run: 458 passed, 1 failed, 1 warning (old repository mutation allowlist); fixed and superseded by final run above. Restricted runs stalled or could not create temporary resources and were cancelled; successful tests used approved elevated execution. Earlier Nov4 elevation attempt was rejected for usage limit and did not run.
- Final checkpoint: git diff --check and fresh status/staged/HEAD inspection; documentation-only edits after tests, no need to repeat the suite. No live GitHub/CI or PostgreSQL runtime checks. Earlier 427-test result belongs to committed ingestion, not Replay.

## 11. Relevant files and responsibilities
- ingestion/replay.py: preflight, logical clock, registry identity, execution lifecycle, safe failure context; private provenance seams in ingestion/service.py preserve existing transaction behavior.
- ingestion/replay_fixture.py: exact canonical bytes and SHA-256; data/synthetic/replay-basic.fixture.json: synthetic metadata only.
- storage/repositories.py: minimal exact-identity lookup and sensor insert, caller-owned transactions.
- tests/integration/test_replay.py: deterministic pacing/provenance, failures, registry, closed origins, fresh assessment, fixture round trip and time boundaries; tests/unit/ingestion/test_replay_fixture.py: canonical bytes/digest and encoding vectors.
- tests/integration/test_ingestion.py: only mutation allowlist expanded for insert_sensor.
- docs/DEVELOPMENT.md: Replay invocation; normative contracts in DATA_MODEL/TESTING_STRATEGY/ARCHITECTURE/SPECIFICATION_REVIEW.

## 12. Scope restrictions and approval requirements
No new schema/migration, dependency, API/UI/WebSocket, BLE/Polar, interval engine, physiology, ML, correction/filtering, production auth or runtime PostgreSQL setup. README unchanged. No staging/commit/push/merge or branch changes without explicit authorization.

## 13. Resume instructions
Read permanent instructions and this memory, verify real Git status/HEAD, then inspect the pending diff (mypy fix + this file). Do not repeat completed implementation or treat saved status as live proof. Preserve user AGENTS.md. No commit or push is currently authorized; earlier authorizations do not carry over.

## 14. Last updated
2026-11-10; mypy fix verified, uncommitted. Push is not authorized.
