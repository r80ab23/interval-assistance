# PROJECT_STATE (canonical live memory)

## 1. Project identity and objective
Interval Assistance (`r80ab23/interval-assistance`): research-grade HR interval-training assistance in explicitly gated phases. Permanent instructions: root CLAUDE.md and AGENTS.md; normative specifications: docs/.

## 2. Architecture and dependency boundaries
`core` / `sensors` / pure `signal` / `storage` / application `ingestion` / `api`+`schemas`. Six import-linter contracts. Storage does not import domain/sensor/application layers. Repositories own no commits and expose no raw-sample/assessment update/delete. API/frontend remain health/status only.

## 3. Current verified Git state (pre-commit checkpoint)
- main; HEAD and local origin/main: `51566a535777f5ae7aca695ffe1e4c1f14ec6550`. No local ahead/behind difference. Live remote not queried in this task.
- Modified tracked: docs/ARCHITECTURE.md, docs/DATA_MODEL.md, docs/DEVELOPMENT.md, docs/SPECIFICATION_REVIEW.md, docs/TESTING_STRATEGY.md, docs/engineering/PROJECT_STATE.md, src/interval_assistance/ingestion/service.py, src/interval_assistance/storage/repositories.py, tests/integration/test_ingestion.py.
- Untracked Replay files: data/synthetic/replay-basic.fixture.json, src/interval_assistance/ingestion/replay.py, src/interval_assistance/ingestion/replay_fixture.py, tests/integration/test_replay.py, tests/unit/ingestion/test_replay_fixture.py.
- Existing untracked user AGENTS.md preserved; do not assume it belongs in a future Replay commit.
- Nothing staged. All Replay work is uncommitted/unpushed; User authorized one local Replay commit on 2026-11-06; push remains prohibited. Earlier approved spec edits are preserved alongside implementation.

## 4. Current phase and immediate objective
Phase 2a Replay implementation completed locally and verified; approved by the user. Current task creates one local commit containing the reviewed files, excluding AGENTS.md; no push.

## 5. Completed work
Phase 1 and Phase 2a specifications, signal core (PR #5), storage schema (`a9e00ee`, migration 0002), ingestion (`198a6f1`), and initial memory (`51566a5`) previously committed/pushed. Replay now adds closed-origin execution, deterministic logical time, provenance, registry reuse, canonical fixture hashing and tests, still uncommitted.

## 6. In-progress work
No known unfinished implementation fix. Replay is ready for review, not committed. Full code run passed 461 tests before two additional Replay regression tests; the focused follow-up passed 36 tests. The only initial full-suite failure was an old repository API allowlist omitting the newly approved insert_sensor operation; updated exactly that allowlist while retaining no-update/delete assertions. No application code changed after the successful final test run.

## 7. Next actions
1. Verify the local Replay commit and working tree after committing; preserve separate untracked user AGENTS.md.
2. Push only after explicit authorization. Do not start another feature automatically.
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
Read permanent instructions and this memory, verify real Git status/HEAD, then inspect the local Replay commit (or pending diff if the commit failed). Do not repeat completed implementation or treat saved status as live proof. Preserve user AGENTS.md. Commit authorization was granted on 2026-11-06; the next gate after local commit is explicit push authorization.

## 14. Last updated
2026-11-06 (Asia/Tehran); local commit authorized, pre-commit checkpoint. This file is included in that commit; its own commit SHA must be obtained from Git rather than embedded here. Push is not authorized.
