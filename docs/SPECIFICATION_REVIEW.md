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
- real sensor transport / BLE

**Consequences**

- No `SensorSample` table in Phase 1. The in-memory sample type is a domain contract, not persistence.
- Replay is Phase 2. The interval engine is Phase 3 or later.
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
