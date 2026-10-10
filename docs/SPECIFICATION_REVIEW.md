# Specification Review — Interval Assistance

**Status:** Records the read-only specification review and the approved Phase 1 decisions. Documentation only; no code, dependencies, commits or pushes accompany this document.

**Labels:** RESOLVED (approved project decision), OPEN, DEFERRED (scientific or later-phase decision).

---

## 1. Resolved Phase 1 boundary (RESOLVED)

This boundary amends Master Prompt Section 57 (Phases 1 and 2 only; all other phases are unchanged). Original Master Prompt Phase 1 = backend, frontend shell, configuration, logging, database, migrations, testing setup; original Phase 2 = sensor interface, simulator, raw sample model, validation, signal quality.

**Phase 1 includes**

- repository/project skeleton
- backend foundation
- frontend foundation
- configuration/settings
- authentication boundary
- logging
- `Clock` abstraction
- ID generation (UUID)
- API skeleton, error envelope
- sensor abstraction (`HeartRateSensor`, `SensorProvider`)
- normalized **in-memory** heart-rate sample type
- deterministic simulator
- manual sensor input
- SQLAlchemy foundation
- Alembic foundation with an empty baseline
- testing infrastructure
- CI foundation
- frontend typed API client
- frontend health/status shell
- repository guards

**Phase 2 includes**

- raw HR sample persistence and the `SensorSample` table
- ingestion
- validation
- signal quality
- replay
- related persistence infrastructure
- real sensor transport / BLE (**Part 2b**, separately gated; the rest is **Part 2a**; see Section 12)

**Consequences**

- No `SensorSample` table in Phase 1. The in-memory sample type is a domain contract, not persistence.
- Replay is Part 2a. The interval engine is Phase 3 or later.
- Physiological calculations, field VO₂max, CPET, calibration and personalization are later phases.
- ML is completely out of scope.
- No physiological or training-session endpoints in Phase 1; only `/api/v1` health/status.

## 2. Authentication boundary (RESOLVED)

Architectural boundary only: a dependency/injection seam, a development identity, three roles (`coach`, `athlete`, `researcher`), default deny. No login UI, no password database, no production identity provider, no JWT unless a later approved decision requires it. WebSocket authentication is not implemented; only a clean boundary is preserved.

## 3. Frontend tooling (RESOLVED)

React, TypeScript, Vite, Vitest. No state-management library, charting library or WebSocket client behavior yet. Phase 1 frontend = research-prototype shell: status/health view, role-aware navigation boundary, research-prototype notice, typed API client boundary. No physiological calculations.

## 4. Database (RESOLVED)

SQLAlchemy 2.x and Alembic. SQLite supported for development and fast CI; PostgreSQL remains the production target. UUID identifiers. No physiological/domain sample tables in Phase 1; an empty baseline migration is acceptable. Migration tests verify the infrastructure without introducing Phase 2 tables.

## 5. API (RESOLVED)

`/api/v1`; health/status endpoint(s); typed error envelope; typed response envelopes where applicable. No physiological or training-session endpoints.

## 6. Hardware boundary (RESOLVED)

Polar H10 is a future adapter boundary only. Phase 1 contains no Polar SDK, BLE transport, browser Bluetooth, proprietary Polar characteristics, or RR-interval/ECG/accelerometer assumptions. Whether the H10 exposes data through the standard GATT Heart Rate Service remains **UNVERIFIED**.

## 7. Explicitly deferred scientific decisions (DEFERRED)

Not implemented or inferred in Phase 1; each remains "requires scientific verification" until its source and methodology are approved. The reference register in `SCIENTIFIC_SPECIFICATION.md` is empty.

- HRR / HRmax / HRrest formulas and the %HRR (Karvonen-style) citation
- %VO₂max mappings
- field VO₂max equations and protocols
- confidence percentages (the specification forbids them)
- physiological execution scores, interval-quality and calibration-quality scores
- calibration formulas, fitting, validation and error metrics
- HR drift metrics
- recovery metrics (HRR30/60/120, recovery slope)
- tolerance semantics, debounce/hysteresis, signal-quality thresholds
- vendor-specific CPET formats and synchronization methods
- personalized-zone derivation; any scientifically derived physiological score

## 8. Remaining OPEN items

(Status update: items 1-6 and 8 below were resolved in Section 11; items 7 and 9 remain open. Phase 2 items are in Section 12.)

Phase 1 relevant (decide when scaffolding reaches them; not blockers for the boundary):

1. Python and Node versions, package manager, lock-file policy.
2. Layer-boundary check tool (import-linter style).
3. Repository-guard implementation (secret scanning, real-data path rules, ML-dependency check).
4. Exact shape of the development-identity configuration, and how default deny is expressed per route.
5. Simulator stream parameter format (seed and profile); the simulator must not encode any physiological model beyond a declared synthetic generator.
6. UUID version.
7. Whether CI also runs PostgreSQL (Phase 1 decision is SQLite; PostgreSQL parity remains OPEN).
8. Logging format and the mechanism that keeps physiological data and identifiers out of logs.
9. Accessibility target and supported devices.

Later phases:

10. Production authentication mechanism, WebSocket auth and token handling, per-athlete access rules, whether `researcher` equals an admin role, consent.
11. BLE transport path (browser, native, local bridge) and verification of the Polar H10 interface.
12. Pagination/filtering style; WebSocket reconnect, replay and backpressure; audio location; wake-lock; localization.
13. Pause semantics, end-of-protocol recovery, ERROR-state exit and disconnect policy.
14. Retention, deletion and jurisdiction-specific privacy policy; export formats.
15. All items in Section 7 and in `SCIENTIFIC_SPECIFICATION.md` Section 14.

## 9. Documents referenced but not present

Not recreated and not to be fabricated:

- `docs/REPOSITORY_AUDIT.md` — not currently present.
- `docs/IMPLEMENTATION_PLAN.md` — not currently present.
- `interval_live_chart.html` (the prototype) — not currently present.

Master Prompt Sections 50, 60 and 63 and `ARCHITECTURE.md` Section 13 reference them. The phase-mapping table in `ARCHITECTURE.md` Section 13 relies on `IMPLEMENTATION_PLAN.md`, which cannot be verified.

## 10. Documentation reconciliation performed

- Phase 1/2 boundary amended in `MASTER_PROMPT.md` Section 57 and referenced from `ARCHITECTURE.md`, `API_SPECIFICATION.md`, `DATA_MODEL.md`, `TESTING_STRATEGY.md`, `UI_SPECIFICATION.md`.
- Origin category naming aligned to `predicted_by_formula` (UI spec), distinct from the reserved future value kind `predicted` (`FUTURE_ML.md`).
- README is **not** modified; its scope drift is catalogued in `README_SCOPE_REVIEW.md`.
- `SCIENTIFIC_SPECIFICATION.md` is unchanged: its content is consistent with the decisions above.

## 11. Phase 1 implementation record

Technical choices made for items that were OPEN (smallest conservative option; none is a scientific or hardware assumption):

| Item | Choice |
|---|---|
| Python | `requires-python >=3.12`; CI uses 3.12; local development verified on 3.14. setuptools, `src` layout. |
| Node | 22; npm with committed `package-lock.json`; exact dependency versions pinned in `package.json`. |
| Layer-boundary tool | `import-linter` (contracts in `pyproject.toml`; run in CI). |
| Repository guards | `tests/unit/test_repository_guards.py` (no ML/BLE/chart/state packages, no `.env`/data/spreadsheet files, no out-of-scope terms in source, no tables, sensors do not log). |
| UUID version | Version 4 (`UuidGenerator`); deterministic `SequentialIdGenerator` for tests. |
| Development identity | `IA_DEV_IDENTITY_ENABLED` (default false) and `IA_DEV_IDENTITY_ROLE`; fixed id; rejected in production. Default deny enforced at request time by an app-level dependency requiring every route to declare `PUBLIC` or `require_roles(...)`. |
| Public routes | `GET /api/v1/health` only. `GET /api/v1/status` requires any of the three roles. |
| Logging | Standard-library logging with JSON or console format; `SensitiveDataFilter` redacts physiological/identifying field names; sensor adapters do not log. |
| Simulator | Seeded bounded random walk; bounds, start value and step are required (no defaults, no physiological model); nominal timestamps; speeds 1x/5x/20x scale pacing only. |
| Sample flags | Simulator and manual samples are `is_synthetic=True`; non-real sources cannot be constructed without the flag. The sample type performs no plausibility checks (Phase 2). |
| SQLite/PostgreSQL | SQLite in development and CI; PostgreSQL URL accepted and required in production; no PostgreSQL driver installed (OPEN). |
| API documentation routes | Disabled in production (they bypass default deny). |
| Frontend API types | Hand-written; backend test pins the exposed paths. A generated client remains OPEN. |
| Pagination | Not needed in Phase 1; still OPEN. |
| License | Not chosen; the repository owner must decide. |

`README.md` is still unmodified (see `README_SCOPE_REVIEW.md`). Setup and check commands are in `DEVELOPMENT.md`.

## 12. Phase 2 reconciliation (Part 2a / Part 2b)

Resolves the blockers found by the Phase 2 specification audit. Documentation only; no code, migration or dependency accompanies it. It amends Master Prompt Section 57 (Phase 2) and supersedes the Phase 2 wording in Sections 1 and 8 above.

### 12.1 Decisions

| # | Topic | Decision | Where |
|---|---|---|---|
| 1 | Phase boundary | **Part 2a** = persistence, ingestion, validation, signal quality, replay. **Part 2b** = real BLE/Polar transport, separately gated on verifying the Polar H10 interface and approving the transport path. Contradictory wording removed (`ARCHITECTURE.md` 7.2, 7.3; Master Prompt Section 57). | MASTER_PROMPT 57, ARCHITECTURE 7 |
| 2 | Invalid samples | Raw-first: every delivered sample is persisted exactly as received, malformed ones included (null value, retained payload). Invalid samples receive a `SignalAssessment` with state `INVALID` and reason codes; they are never dropped or repaired. `InvalidSensorSample` is only for delivery-contract violations. | ARCHITECTURE 5.1a |
| 3 | Sample model | In-memory sample gains nullable `received_hr` and optional `raw_payload`; the "non-real is synthetic" invariant narrows to `simulated` and `manual`; replay inherits `is_synthetic`. Field-by-field mapping to `sensor_sample` (HR, raw payload, device timestamp, `received_at`, ingestion timestamp, elapsed time, quality hint) with nothing discarded except the one documented, bounded exception in 12.2 (naive `device_timestamp` without a retained payload). | ARCHITECTURE 7.1, DATA_MODEL 4.6 |
| 4 | Session identity | New minimal `RecordingSession`: no athlete, protocol, phase or interval semantics; `TrainingSession` (Phase 3) will reference it later; not resumable after a process restart; `elapsed_seconds` is recording-session elapsed time, not a training clock. | DATA_MODEL 4.4a, 4.6 |
| 5 | Validation vs signal quality | Validation = stateless per-sample (`malformed_sample`, `missing`, `impossible_hr`, `invalid_timestamp`, always `INVALID`). Signal quality = stateful (`duplicate_timestamp`, `out_of_order_timestamp`, `implausible_jump`, `gap`, `stale`). No filtering, interpolation, correction or analytics. | ARCHITECTURE 5.1a, SCIENTIFIC 5.1 |
| 6 | Tables | Part 2a creates exactly: `sensor`, `recording_session`, `sensor_sample`, `processing_run` (**proposed entity promoted**, documented reason), `signal_assessment`. `ProcessingInput`, `SampleCorrection`, `Athlete`, `Coach`, `TrainingSession` and everything else are not created. | DATA_MODEL top note, 2.2, 3 |
| 7 | Replay | Replays an origin recording session into a new `replay` session; origin untouched; copies raw fields, links `origin_sample_id`; fixture metadata file with simulator parameters and stream hash; determinism criterion defined. | DATA_MODEL 4.6a, TESTING_STRATEGY 6 |
| 8 | Thresholds | All numeric values stay OPEN. Mechanism defined: required, default-free, immutable-by-hash `SignalQualityConfig`; snapshot stored per session and per processing run; fixed state-precedence convention. | SCIENTIFIC 5.1 |
| 9 | API | Part 2a adds no endpoints and no WebSocket; raw-sample reads deferred until access semantics, consent, pagination and large-read handling are decided. | API_SPECIFICATION top note |

Two further points were resolved before commit:

| # | Topic | Decision | Where |
|---|---|---|---|
| 10 | Non-finite HR | NaN, +Infinity and -Infinity are stored as a class marker (`received_hr_nonfinite`: `nan`, `+inf`, `-inf`) with `received_hr` NULL, because SQLite stores NaN as NULL and backends differ. The class is preserved exactly; NaN sign/payload bits are not (any raw payload is retained). Always `malformed_sample`/`INVALID`; reproduced by replay; never converted, clipped or dropped. | DATA_MODEL 4.6, SCIENTIFIC 5.1, ARCHITECTURE 5.1a |
| 11 | Replay shape | Replay is an **ingestion/replay service** (`ingestion/replay.py`), not a `HeartRateSensor` adapter: it reads storage and must attach `origin_sample_id`, and `sensors/` may not import storage. Replay sessions reference a `sensor` row of kind `replay`. | ARCHITECTURE 4, 7.2; MASTER_PROMPT 57; DATA_MODEL 4.6a; TESTING 5, 6 |

Follow-up to the PR #2 review (two MAJOR findings):

| # | Topic | Decision | Where |
|---|---|---|---|
| 12 | Timestamp delivery contract | Timezone-aware `received_at` and `device_timestamp` in any offset are normalized to UTC (instant preserved, offset not stored); never rejected for their offset. `received_at` is aware by the existing Phase 1 type invariant, so a naive one fails at sample construction and never reaches ingestion. A naive `device_timestamp` is stored NULL with the sample persisted and `invalid_timestamp`/`INVALID` recorded. `InvalidSensorSample` stays limited to unknown/closed/inactive session, sensor mismatch and source-kind mismatch. | ARCHITECTURE 5.1a; DATA_MODEL 4.6; SCIENTIFIC 5.1 |
| 13 | ProcessingRun lifecycle | One run per recording session, created with the session in the same transaction; it owns all that session's assessments including `gap` ranges and the close-time `stale` range. Reassessment is **deferred** (it must later create a new run and never overwrite history). Unique `(processing_run_id, sample_id)` for per-sample rows; samples without an assessment are "unassessed", not `GOOD`. Replay sessions get their own run. | DATA_MODEL 2.2, 4.7; SCIENTIFIC 5.1 |

Pre-implementation clarification:

| # | Topic | Decision | Where |
|---|---|---|---|
| 14 | Configuration identity | Canonical serialization fixed: hashed JSON document with a `format` tag, sorted keys, UTF-8, no whitespace, finite numbers only, numbers via the ECMA-262 `Number::toString` digit selection (n, k, s) rendered in plain positional notation, SHA-256 as 64 lowercase hex; unknown keys rejected; `(id, version)` immutable. Test vectors included. No threshold or policy chosen. Source-file format and settings key stay an implementation choice. | SCIENTIFIC 5.1.1; DATA_MODEL 4.4a; TESTING 10 |

Owner decisions on the stateful signal-quality semantics (PR #5 review):

| # | Topic | Decision | Where |
|---|---|---|---|
| 15 | Timestamp axes | `duplicate_timestamp` and `out_of_order_timestamp` compare only samples on the same axis (`device` or `receive`); a mixed-axis pair produces neither finding and the current sample becomes the reference. A naive `device_timestamp` falls back to the receive axis. `implausible_jump` stays value-based. A previous timestamp whose axis is unknown is never compared (the in-memory stream state cannot represent one). Accepted consequence: findings are not produced across an axis switch. | SCIENTIFIC 5.1 |
| 16 | Invalid arrivals | An invalid sample is still a receive event for `gap` and `stale`; validity and arrival are kept separate. State precedence and reason-to-state mapping are unchanged. | SCIENTIFIC 5.1 |
| 17 | Receive-time references | `gap` uses the `received_at` of the last-arrived sample in arrival order (unchanged); `stale` uses the maximum `received_at` observed, which an older later-arriving sample cannot lower. `received_at` is always present and timezone-aware (sample invariant), so no missing-receive-time handling is needed. | SCIENTIFIC 5.1 |

### 12.2 Remaining OPEN items

- **Naive `device_timestamp` preservation (documented limitation; OPEN for owner approval).** The table has only a UTC `device_timestamp` column, so a naive wall-clock value has nowhere to be stored without inventing a time zone or adding a column. The existing sample contract cannot preserve it either: `raw_payload` holds only bytes the adapter actually supplied, and ingestion must not fabricate or re-serialize one. Part 2a therefore stores NULL, flags `invalid_timestamp`, and **the original value is lost unless the adapter-supplied payload carries it**. This is a bounded exception to the raw-first guarantee, not a silent one. It is latent in Part 2a (no Part 2a source supplies a `device_timestamp`). Options for the owner: (a) accept the limitation, (b) require adapters that supply device timestamps to also supply a payload carrying them, (c) add a nullable text column for the unparsed value. No column is added without approval. A decision is needed before Part 2b (the first adapter that may supply device timestamps); it does not block Part 2a.
- Reassessment operation (deferred; no Part 2a code).
- Numeric values of the signal-quality configuration and the owner's approval of a configuration for real use (blocks real-data use, not implementation).
- Criteria separating `GOOD`, `ACCEPTABLE` and `POOR` beyond the reason-code mapping.
- Database-level append-only enforcement for `sensor_sample` (repository-level in Part 2a).
- PostgreSQL driver, CI service and feature parity (SQLite only in Part 2a); UUID version.
- Whether correction or interpolation is ever permitted (not in Part 2a).
- Association of a recording session with an athlete; per-athlete access, consent and raw-sample read API.
- All of Part 2b: transport path (browser, native, bridge), Polar H10 data availability and sampling behavior, any beat-interval data.
- Migration numbering convention for `0002` onward; layer-boundary contract names for `ingestion` and `signal`.
- Retention and deletion policy versus append-only (Phase 12).

### 12.3 Consistency notes

- Documents updated: `MASTER_PROMPT.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `SCIENTIFIC_SPECIFICATION.md`, `API_SPECIFICATION.md`, `TESTING_STRATEGY.md`, this file.
- Unchanged by design: `UI_SPECIFICATION.md`, `FUTURE_ML.md`, `README.md`.
- Sections 8 items 1-6 and 8 were resolved by Section 11; items 7 and 9 remain.
