# Architecture — Interval Assistance

**Status:** DRAFT specification baseline, derived from `MASTER_PROMPT.md` (V2). Phase 1 decisions approved and recorded in `SPECIFICATION_REVIEW.md`; remaining items stay labelled OPEN. No code exists.

**Labels used in this document**

| Label | Meaning |
|---|---|
| **MANDATED** | Stated directly in the Master Prompt. |
| **PROPOSED** | A design choice made here to make the specification coherent; needs approval. |
| **OPEN** | Unresolved; must be decided before the related phase starts. |

---

## 1. Purpose and scope

Interval Assistance is a research-oriented sports-technology platform for (1) real-time heart-rate-based interval assistance, (2) field VO₂max testing, (3) laboratory CPET/gas-analyzer calibration, (4) personalized physiological profiling, with analytics, reporting and provenance throughout.

**Machine learning is out of scope (MANDATED).** No ML training, inference, neural networks, online learning, model registry or ML dependencies. The architecture is ML-ready only in the sense that stable interfaces exist (Section 11 and `FUTURE_ML.md`).

**Positioning (MANDATED):** sports-performance and research software. Not a medical device, not diagnostic, not a replacement for clinical testing. Preferred vocabulary: *software estimate, field estimate, laboratory reference, calibration, research prototype, training assistance.*

---

## 2. Architectural principles

1. **Modular monolith** with clean internal boundaries (MANDATED). No microservices, message brokers, Kubernetes or ML platforms.
2. **Backend/domain engine is the single source of truth.** The UI renders state and sends commands only; it never computes interval state or physiological values (MANDATED).
3. **Raw data is append-only.** Raw sensor data, raw laboratory files, raw field-test inputs and measured values are never overwritten (MANDATED).
4. **Every derived value has provenance** (inputs, method id, method version, processing version, timestamp) and a **value kind** (Section 8).
5. **Determinism.** Same input stream plus same clock yields the same events and results.
6. **Explicit unknowns.** `UNKNOWN` or `REQUIRES SCIENTIFIC VALIDATION` is preferred over invention (MANDATED).
7. **Incremental delivery.** One phase at a time, each tested and documented (MANDATED).

---

## 3. Layers

```text
UI (React / TypeScript)
 ↓  REST commands + WebSocket state/events
API / WebSocket                (transport, validation, auth boundary)
 ↓
Application Services           (use-cases, orchestration, transactions)
 ↓
Domain / Physiological Engine  (pure logic: zones, state machine, analytics, calibration math)
 ↓
Infrastructure                 (sensor adapters, repositories, file importers, clock, logging)
 ↓
Database / Sensors / Files
```

**Layer rules (MANDATED / PROPOSED enforcement)**

- The domain layer has no imports from API, storage or sensor-vendor code. (PROPOSED: enforced by an import-linter style check in CI; tool OPEN.)
- Sensor adapters contain no interval rules.
- Database models do not carry business logic.
- API handlers are thin; no business logic in handlers.
- The domain receives time from an injected clock; it never reads system time directly.

---

## 4. Components (package map)

Target structure from Master Prompt Section 50. The structure may be adjusted if this document demonstrates a better solution; none is proposed at this time.

| Package (`src/interval_assistance/`) | Responsibility | Layer |
|---|---|---|
| `api/` | FastAPI routers, WebSocket endpoint, request/response mapping | API |
| `schemas/` | Pydantic v2 input/output schemas (value-kind aware) | API / shared |
| `core/` | Configuration, logging, clock abstraction, error types, IDs | Cross-cutting |
| `storage/` | SQLAlchemy 2.x models, repositories, Alembic migrations | Infrastructure |
| `sensors/` | `HeartRateSensor` interface, simulator, manual input, Polar H10 adapter boundary (replay is not here: it is an `ingestion/` service, see 7.2) | Infrastructure |
| `ingestion/` | Raw sample intake, timestamp handling, persistence of raw samples, and the replay service (**Part 2a; not created in Phase 1**) | Application |
| `signal/` | Validation and signal-quality assessment (**Part 2a; not created in Phase 1**; recorded corrections are not part of Part 2a) | Domain |
| `intervals/` | Protocol model, zone computation, state machine, timing, events | Domain |
| `physiology/` | Definitions and calculations (HRR, targets, unit conversion), each method versioned | Domain |
| `analytics/` | Session metrics, availability rules, summaries | Domain |
| `field_tests/` | Field-protocol framework (descriptors, inputs, calculation hooks) | Domain |
| `calibration/` | CPET import mapping, QC, synchronization, calibration methods, lifecycle | Domain + Infra |
| `personalization/` | Profile assembly, personalized zones, auditable overrides | Domain |
| `reporting/` | CSV (required) and later exports with provenance | Application |
| `frontend/` | React/TypeScript UI | UI |

(PROPOSED) CPET file parsing lives in `calibration/` infrastructure submodules, while QC rules and calibration math stay in the domain submodules, so the layer rules hold.

---

## 5. Real-time data flow (MANDATED)

```text
Heart Rate Sensor
  → Sensor Adapter
  → Raw Ingestion            (persist raw sample exactly as received)
  → Validation
  → Signal Quality
  → [Optional Signal Processing, recorded]
  → Interval Engine
  → Domain Events
       ├→ UI (WebSocket)
       ├→ Audio (event subscriber, client side — OPEN, see 5.2)
       └→ Storage (events + derived records)
  → Analytics
```

### 5.1 Properties

- The real-time engine does not depend on the UI.
- Events are the only output the UI/audio/storage consume from the engine.
- Raw samples are persisted before any processing; filtering never replaces raw values.
- If a correction or interpolation is applied, it is recorded (original value, corrected value, method, timestamp, reason, processing version). No silent repair.

### 5.1a Part 2a pipeline definitions (decided)

Part 2a implements only: adapter, ingestion (raw persistence), validation, signal quality. Nothing downstream of signal quality exists in Part 2a (no interval engine, analytics or events).

- **Raw-first and no silent loss.** Every sample delivered to ingestion (by an adapter, or by the replay service) is persisted as a `SensorSample` exactly as received, **including malformed input** (null value, retained `raw_payload`). The guarantee has **one documented, bounded exception**: a naive `device_timestamp` delivered without a `raw_payload` (see the timestamp bullet below and `SPECIFICATION_REVIEW.md` 12.2). Persistence is committed before validation and signal quality run. Nothing a sensor delivered is dropped, repaired or overwritten. Non-finite values (NaN, +Infinity, -Infinity) are stored as a class marker with a NULL value (`DATA_MODEL.md` 4.6), so they survive SQLite and replay.
- **Invalid samples are assessed, not rejected.** A sample that fails validation receives a `SignalAssessment` with state `INVALID` and reason codes. The assessment is the record that it is invalid. Downstream consumers (Phase 3 onward) must treat `INVALID` samples as unusable; Part 2a has no consumers.
- **`InvalidSensorSample` is narrow.** It is raised only when the *delivery contract* is broken so that no raw record can be made: unknown or closed recording session (including a session that is not active in this process, since sessions cannot be resumed), sensor not belonging to the session, or a sample whose `source_kind` differs from its session's. It is never raised because a heart-rate *value* or a timestamp is implausible, malformed or in a non-UTC offset (those are normalized or assessed).
- **Timestamp delivery contract (decided).** All stored timestamps are UTC. A timezone-aware `received_at` or `device_timestamp` in any offset is normalized to UTC: the represented *instant* is preserved, the original offset is not stored, and the delivery is not rejected for its offset. No timestamp is invented or repaired. `received_at` must be timezone-aware: this is the existing Phase 1 sample-type invariant, so a naive `received_at` cannot be constructed and never reaches ingestion; it fails in the adapter at sample construction (a `ValueError`, not `InvalidSensorSample`), and no zone is guessed. The Phase 1 type does not validate `device_timestamp`, so it can arrive naive: a naive `device_timestamp` represents no instant and cannot be normalized, so it is stored as NULL, the sample is persisted, and validation records `invalid_timestamp` (state `INVALID`). The naive wall-clock value is **not stored in any column**. `raw_payload` is exactly the bytes an adapter supplied from the delivered representation ("where the adapter has one"); ingestion never synthesizes or re-serializes a payload from a parsed value, so the original value survives only if the adapter-supplied payload carries it, and is **lost when no payload was supplied**. The affected samples remain identifiable by their `invalid_timestamp` assessment. Exposure is currently latent: no Part 2a source supplies a `device_timestamp` (the simulator and manual adapters leave it null and replay copies stored values), so this can only arise from a future adapter (Part 2b) or a direct caller. Whether to preserve the value in a dedicated column is **OPEN for owner approval** (`SPECIFICATION_REVIEW.md` 12.2); no column is added without that approval. No other `device_timestamp` validity rule is defined in Part 2a. A value that cannot be parsed by an adapter is still delivered as a sample with a null value and its payload.
- **Validation** (stateless, per sample): is the delivery usable as a value and a time. Reason codes: `malformed_sample`, `missing`, `impossible_hr`, `invalid_timestamp`. Any validation finding yields `INVALID`.
- **Signal quality** (stateful, over a recording session in sequence order, plus explicit evaluation at a supplied time): is the stream behaving as a stream. Reason codes: `duplicate_timestamp`, `out_of_order_timestamp`, `implausible_jump`, `gap`, `stale`. These produce a per-sample assessment (duplicate, out-of-order, jump) or a time-range assessment (`gap`: closed range between two received samples; `stale`: open range from the last received sample up to the evaluation time).
- **Not in Part 2a:** filtering, interpolation, correction, smoothing, analytics, any physiological interpretation. `SampleCorrection` is not created. Flag, do not repair.
- **Evaluation is explicit and clock-injected.** `stale` evaluation is a function called with an explicit `now` supplied from the injected `Clock`; Part 2a includes no background scheduler or thread.
- **Time axis for stateful checks:** `received_at` (adapter-observed receive time, preserved through persistence and replay) for `gap` and `stale`; duplicate and out-of-order timestamp checks use `device_timestamp` when present and valid (not naive) and `received_at` otherwise, on normalized UTC instants. Rules and configuration: `SCIENTIFIC_SPECIFICATION.md` 5.1.
- **Concurrency:** one recording session is ingested serially in arrival order (`sequence`); database access in Part 2a uses the synchronous SQLAlchemy sessions already in Phase 1.

### 5.2 Audio

The interval engine emits domain events; an audio subsystem reacts to them. Audio behavior is not hard-coded into the engine. (MANDATED)

**OPEN:** where audio is rendered. The athlete screen is likely a browser or mobile client, so playback would be client-side, triggered by backend events, with configuration (warning patterns, e.g. three-beep before a transition) stored with the session. Browser autoplay restrictions require a user gesture to unlock audio; this must be reflected in the UI flow.

### 5.3 Concurrency model

(PROPOSED) Single asyncio event loop per process handling ingestion and WebSocket fan-out; per-session engine instance with serialized input (samples and clock ticks processed in order). Multi-process scaling is not a requirement and is not designed for. Session state is reconstructible from persisted events plus raw samples. **OPEN:** expected number of concurrent sessions.

---

## 6. Time model (MANDATED, Section 44)

Four time notions are kept distinct and stored separately:

| Name | Meaning |
|---|---|
| **Device timestamp** | Timestamp supplied by the sensor, if any. May be absent or unreliable. |
| **Ingestion timestamp** | When the backend received the sample (wall clock, UTC). |
| **Event timestamp** | Wall-clock time recorded on a domain event (UTC). |
| **Monotonic elapsed time** | Session-relative elapsed time from the authoritative session clock. Source of truth for phase durations. |

Rules:

- Protocol timing is authoritative: a 60 s work phase lasts 60 s on the session clock regardless of HR response. Time-to-target is an analytical metric, not a timing input.
- UI rendering time is never a source of truth for durations.
- A `Clock` abstraction is injected so tests can control time and replay can be deterministic.
- **OPEN:** pause semantics. Does the session clock stop during `PAUSED` (phase time frozen), and how is paused time recorded for analytics? Must be decided before Phase 3.

---

## 7. Sensor abstraction

### 7.1 Interface (MANDATED concept, signatures PROPOSED)

`HeartRateSensor` supports: connect, disconnect, start, stop, receive HR samples (async stream), connection status, and signal quality where available. A `SensorProvider` registry/factory selects implementations (Section 11).

Normalized sample emitted by every adapter (PROPOSED fields): value as received, device timestamp (nullable), adapter-observed receive time, sensor id, source kind (`real | simulated | replay | manual`), `is_synthetic` flag, optional adapter-supplied quality hint. Raw payload bytes retained where an adapter has them.

**Part 2a amendment (decided, `SPECIFICATION_REVIEW.md` Section 12):** the in-memory sample type gains an optional `raw_payload` (bytes) and its value becomes nullable (`received_hr: float | None`), so malformed input can be represented without loss. The Phase 1 invariant "non-real sources are synthetic" is narrowed to `simulated` and `manual`; a `replay` sample inherits `is_synthetic` from the sample it replays. The field-by-field mapping to `SensorSample` is in `DATA_MODEL.md` 4.6.

### 7.2 Implementations

| Adapter | Status |
|---|---|
| Simulator | Deterministic synthetic HR streams; speeds 1x/5x/20x; every sample flagged synthetic (MANDATED). **Phase 1**, in-memory only (not persisted). |
| Replay | **Decided: an ingestion/replay service, not a `HeartRateSensor` adapter** (`ingestion/replay.py`). It reads the stored samples of an origin recording session and ingests them into a new `replay` recording session through the normal ingestion path, linking each sample to its origin and preserving provenance. Rationale: it must read persistence and attach `origin_sample_id`, which the sensor contract has no carrier for, and `sensors/` may not import storage. **Part 2a** (requires persisted samples). |
| Manual input | Coach/developer-entered HR; flagged `manual`. **Phase 1**, in-memory only. |
| Polar H10 / real BLE transport | **Boundary only in Phase 1 and Part 2a. Part 2b** (separately gated, after verification and approval). See 7.3. |

The normalized sample in 7.1 is an in-memory domain/contract type in Phase 1. It has no database table until Part 2a (`SensorSample`, `DATA_MODEL.md` 4.6).

### 7.3 Polar H10 boundary

- Phase 1 contains no Polar code: no Polar SDK, no BLE transport, no browser Bluetooth, no proprietary Polar characteristics, and no RR-interval, ECG or accelerometer assumptions. The generic `HeartRateSensor` abstraction with simulator and manual adapters is sufficient for Phase 1.
- No Polar API behavior is specified here. Nothing in this repository may assume Polar-specific capabilities (data fields, SDK calls, undocumented characteristics).
- The only candidate interface currently identified is the standard Bluetooth GATT Heart Rate Service, which Bluetooth SIG publishes as a standard. **Whether the Polar H10 exposes the needed data through it, and what it carries, is UNVERIFIED** and must be checked against the Bluetooth SIG specification and Polar's official documentation before the adapter is built.
- **OPEN (blocks Part 2b real hardware work; does not block Part 2a):** transport path. Browser Web Bluetooth, a native/mobile app, or a local bridge process are different architectures, and browser support varies by platform (**verify current support**). The adapter boundary is designed so the choice does not change the domain.

---

## 8. Value kinds and provenance (MANDATED)

Every stored or transmitted physiological value carries a **value kind**:

| Kind | Meaning | Examples |
|---|---|---|
| `raw` | Exactly as received/imported, unmodified | Raw HR sample; original CPET file rows |
| `measured` | Directly measured by a device or laboratory procedure | Lab VO₂max, sensor HR, VCO₂, VE, RER |
| `estimated` | Computed by a field or indirect method | Field-test VO₂max |
| `calculated` | Deterministic result from known inputs | HRR, target HR, time in zone, recovery metrics |
| `calibrated` | An estimate transformed by an approved calibration | Calibrated VO₂max estimate |
| `personalized` | Derived using the athlete's own validated information | Personalized zone |

A generic untyped `value` field without provenance is not allowed (MANDATED). Provenance record (PROPOSED minimum): input references, method id, method version, processing/software version, created-at (UTC), actor (user or system), synthetic flag. Detail in `DATA_MODEL.md`.

Distinct preserved values (MANDATED, Section 29): `field_estimated_vo2max`, `laboratory_measured_vo2max`, `uncalibrated_estimate`, `calibrated_estimate`.

---

## 9. Interval engine (state machine)

### 9.1 States (MANDATED)

`IDLE, PREPARATION, WARMUP, WORK, RECOVERY, COOLDOWN, PAUSED, COMPLETED, ERROR`

### 9.2 Transitions (PROPOSED — requires approval)

| From | To | Trigger |
|---|---|---|
| IDLE | PREPARATION | start command |
| PREPARATION | WARMUP | preparation complete, protocol has warm-up |
| PREPARATION | WORK | preparation complete, no warm-up |
| WARMUP | WORK | warm-up duration elapsed on session clock |
| WORK | RECOVERY | work duration elapsed |
| RECOVERY | WORK | recovery elapsed, more intervals remain |
| RECOVERY | COOLDOWN | recovery elapsed, completion rule met, protocol has cool-down |
| RECOVERY | COMPLETED | recovery elapsed, completion rule met, no cool-down |
| WORK | COOLDOWN / COMPLETED | completion rule met without trailing recovery (**OPEN**: does the final interval include recovery?) |
| COOLDOWN | COMPLETED | cool-down elapsed |
| any active state | PAUSED | pause command |
| PAUSED | previous state | resume command |
| any non-terminal state | COMPLETED | stop command (early termination, recorded as such) |
| any state | ERROR | unrecoverable condition |

Invalid transitions raise `InvalidStateTransition`. Terminal states: `COMPLETED`, `ERROR`. **OPEN:** whether `ERROR` can be left (e.g. sensor failure policy), and the policy when the sensor disconnects mid-session (continue on protocol timing while flagging missing data is consistent with Section 7 of the Master Prompt but must be confirmed).

### 9.3 Completion modes (MANDATED)

Interval count; total duration; explicit protocol completion (warm-up, work/recovery cycles, cool-down, final completion). Completion is determined deterministically by the state machine.

### 9.4 Zones and classification

Each interval target has an explicit zone: target, lower, upper, plus its origin (absolute, %HRmax, %HRR, %VO₂max approximation, personalized, manual) and tolerance. Manual zones override derived ones where configured. Position relative to the zone is classified `BELOW | WITHIN | ABOVE`, with hysteresis/debounce so one noisy sample does not cause a transition. Formulas and parameters are in `SCIENTIFIC_SPECIFICATION.md`; **debounce/hysteresis parameters are currently unspecified.**

### 9.5 Events (MANDATED)

Types listed in Master Prompt Section 10. Required fields: timestamp, session id, event type, relevant HR (if available), phase, interval number, source, metadata. (PROPOSED additions: monotonic elapsed time, per-session sequence number, engine version.) Events are suitable for UI, audio, logging, analytics, replay and testing.

---

## 10. Persistence, privacy, configuration, errors

- **Database:** PostgreSQL for production; SQLite permitted for development; SQLAlchemy 2.x with Alembic migrations (MANDATED). Schema supports provenance and versioning (`DATA_MODEL.md`). **OPEN:** whether SQLite dev parity is maintained, given feature differences.
- **Privacy (MANDATED):** minimum necessary data; pseudonymous athlete identifiers; access control; audit trail; safe exports; no secrets in source; `.env.example` instead of real environment files; no real athlete data or real CPET reports in Git; synthetic fixtures only. (PROPOSED) Direct identifiers stored separately from the pseudonymous athlete record.
- **Database (Phase 1 decision):** SQLite supported for development and fast CI tests; PostgreSQL remains the production target; UUID is the identifier strategy. Phase 1 contains an empty baseline Alembic migration and no physiological or sample tables.
- **Authentication boundary (Phase 1 decision):** an architectural boundary only: a dependency/injection seam, a development identity, three roles (`coach`, `athlete`, `researcher`) and default-deny authorization. No login UI, no password database, no production identity provider, no JWT. WebSocket authentication is not implemented in Phase 1; the boundary must stay clean enough to add it later (token handling remains OPEN, `API_SPECIFICATION.md` 5).
- **Configuration:** Pydantic Settings; no credentials in source.
- **Logging:** structured; must not contain raw physiological data or identifiers.
- **Errors (MANDATED):** structured domain errors, never swallowed: `InvalidSensorSample`, `InvalidTrainingProtocol`, `InsufficientCalibrationData`, `CalibrationValidationError`, `CPETImportError`, `UnitConversionError`, `SynchronizationError`, `SensorConnectionError`, `InvalidStateTransition`. Invalid physiological data never silently continues through the pipeline.
- **Units:** normalized at ingestion boundaries; conversions explicit and tested; never silently mixed.
- **Versioning (MANDATED):** protocols, formulas, calibration, processing logic, schemas and scientific specifications are versioned; historical records keep the method/version used.

---

## 11. Extension interfaces and the ML boundary

Interfaces (MANDATED names, Section 66): `SensorProvider`, `TrainingEngine`, `PhysiologyCalculator`, `FieldTestProtocol`, `CalibrationMethod`, `ProfileProvider`, `AnalyticsProvider`.

All current implementations are deterministic. **No ML classes, stubs, dependencies or placeholder models exist or may be added.** A future ML component could only appear as another implementation of an existing interface (for example `CalibrationMethod` or `ProfileProvider`), receiving provenance-tracked inputs and returning a typed result with provenance. A new value kind (for example `predicted`) would be introduced at that time; it is deliberately not defined now. See `FUTURE_ML.md`.

---

## 12. Technology baseline

**MANDATED as "preferred"** by the Master Prompt; exact versions and frontend libraries are OPEN.

- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Pydantic Settings.
- Scientific/data (add only when first needed): NumPy, Pandas, SciPy, openpyxl.
- Testing: pytest, pytest-asyncio, Hypothesis. Quality: Ruff, Mypy.
- Frontend (Phase 1 decision): React, TypeScript, Vite (build tool), Vitest (test runner). No state-management library, no charting library and no WebSocket client behavior in Phase 1; those are chosen in the phase that first needs them.
- Realtime: WebSocket. Database: PostgreSQL (SQLite dev).
- Explicitly excluded: any ML package, message broker, container orchestration (unless a demonstrated requirement appears).

"Do not add unnecessary dependencies": each dependency is added in the phase that first needs it, not up front.

---

## 13. Document reconciliation

Findings from comparing the existing documents against the Master Prompt:

1. **Phase numbering differs.** `IMPLEMENTATION_PLAN.md` (Phase 0 audit) uses 15 phases ordered differently from Master Prompt Section 57. **The Master Prompt numbering is authoritative.** Both preserved files are left unchanged. Mapping:

(Phase 1/2 amendment: the approved boundary in `MASTER_PROMPT.md` Section 57 and `SPECIFICATION_REVIEW.md` supersedes the original Master Prompt Phase 1/2 split. Phase 1 additionally includes the sensor interface, in-memory sample type, simulator and manual input; Phase 2 is raw sample persistence, ingestion, validation, signal quality, replay and real transport. `IMPLEMENTATION_PLAN.md` is not currently present in the repository, so the right-hand column cannot be verified.)

| Master Prompt phase (authoritative) | Corresponding `IMPLEMENTATION_PLAN.md` phase(s) |
|---|---|
| 0 Audit and architecture confirmation | 0 |
| 1 Foundation (amended: includes sensor abstraction, simulator, manual input) | 1 (plus the domain-model skeleton of 2) |
| 2 Sensor data pipeline (amended: Part 2a persistence, ingestion, validation, signal quality, replay; Part 2b real transport, separately gated) | 3 (plus ingestion/signal parts of 5) |
| 3 Interval engine | 4 |
| 4 Real-time monitoring | 5, 6 (live parts), 7 |
| 5 Audio engine | part of 7 |
| 6 Session analytics | 8 |
| 7 Field VO₂max framework | 9 |
| 8 CPET import | 10 |
| 9 Calibration | 11 |
| 10 Personalization | 12 |
| 11 Reporting/export | parts of 8 |
| 12 Security/privacy/hardening | 14 |
| 13 Full integration testing | 13 |
| 14 Documentation and release | no direct equivalent |

2. **Tech stack and earlier open decisions.** The audit listed backend language/database as open. The Master Prompt now names a preferred stack, resolving that item at the "preferred" level. The BLE transport path remains open.
3. **ML language in the README.** The audit flagged README wording about models learning and retraining. The Master Prompt confirms ML is out of scope, so that wording must be reinterpreted as deterministic methods or removed. The README has not been modified; the exact items to correct are listed in `README_SCOPE_REVIEW.md`.
4. **Calibration fitting.** The audit asked whether deterministic regression-based calibration is in scope as "non-ML". The Master Prompt allows deterministic calibration and statistical calculations "where justified". The fitting method itself is still unspecified (`SCIENTIFIC_SPECIFICATION.md`).
5. **Prototype.** Per Master Prompt Section 63, the source of `interval_live_chart.html` is not in the repository, so its undocumented implementation details are not assumed or recreated. UX requirements here come from the Master Prompt text only.

---

## 14. Specification readiness (Master Prompt Section 69 checklist)

| Item | Status |
|---|---|
| Clear project scope | Documented (this file, Master Prompt) |
| Explicit ML exclusion | Documented |
| Architecture | Draft (this file) |
| Scientific specification | Draft, **with unresolved scientific items** |
| Data model | Draft |
| API specification | Draft, **provisional by design** (endpoint details not finalized until the data model is accepted) |
| UI specification | Draft |
| Testing strategy | Draft |
| Future ML boundary | Documented |
| Privacy rules | Documented at principle level; jurisdiction-specific rules unknown |
| Provenance rules | Documented at model level |
| Sensor abstraction | Specified at interface level; Polar H10 transport **open** |
| Interval state machine spec | Draft; transitions **proposed**, pause/disconnect semantics **open** |
| CPET import specification | Framework only; **no vendor format verified** |
| Calibration lifecycle | Draft; methodology parameters **unspecified** |
| Personalization model | Draft; derivation methods **unspecified** |
| Field-test framework | Framework only; **no protocol/equation approved** |
| Implementation roadmap | Present (Master Prompt Section 57; Phase 0 plan preserved) |

The specification is therefore **a coherent baseline, not complete**. The unresolved items are listed in `SCIENTIFIC_SPECIFICATION.md` (Section 14) and in the final report. Implementation should not begin on any phase whose blocking items remain unresolved.
