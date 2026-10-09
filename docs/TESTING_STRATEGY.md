# Testing Strategy — Interval Assistance

**Status:** DRAFT derived from `MASTER_PROMPT.md` (V2). This describes **planned** testing. **No tests have been written or run, and no scientific validation has been performed.** Planned tests and planned validation are not evidence (MANDATED, Section 64).

**Labels:** MANDATED, PROPOSED, OPEN.

---

## 1. Principles

1. **Test every implemented phase before moving on** (MANDATED); a phase is not complete until its tests pass and documentation is updated.
2. **Domain logic is tested as pure code.** The domain layer has no I/O and takes an injected clock, so tests are fast and deterministic.
3. **No fabricated expectations.** Expected values for scientific calculations come from (a) definitions in `SCIENTIFIC_SPECIFICATION.md`, (b) worked examples in an approved cited source, or (c) independent hand/analytical calculation documented in the test. Never from running the implementation and pasting its output as "expected".
4. **Synthetic data only** in the repository, always labelled synthetic (MANDATED). No real athlete data or real CPET reports in Git.
5. **Unhappy paths are first-class.** The Master Prompt's list of failure cases is covered explicitly (Section 8).
6. **Provenance and immutability are tested**, not assumed.

---

## 2. Tooling (MANDATED/PROPOSED)

Backend: pytest, pytest-asyncio, Hypothesis; Ruff (lint/format) and Mypy (types) as quality gates. Frontend: Vitest (approved Phase 1 decision). CI: runs lint, type check and tests on every change (PROPOSED). Coverage thresholds: OPEN; no numeric target is set here. Dependencies are added only when the first test needs them.

Layout (MANDATED): `tests/unit`, `tests/integration`, `tests/property`, `tests/replay`. Synthetic fixtures live under `data/synthetic/` with metadata declaring them synthetic.

---

## 3. Unit tests (MANDATED coverage list)

| Area | What is tested |
|---|---|
| HRR | `HRR = HRmax − HRrest`; invalid inputs (HRmax ≤ HRrest, out of range) raise errors |
| Target calculations | Each intensity mode against the definitions; %HRR form only after its reference is approved |
| Zone boundaries | lower/upper from tolerance; boundary inclusivity and rounding once specified; manual zone override |
| Tolerance | Symmetric/asymmetric (if specified), invalid tolerance |
| State transitions | Every allowed transition; every disallowed transition raises `InvalidStateTransition` |
| Timing | Phase durations follow protocol timing regardless of HR; fake clock; pause/resume accounting once specified |
| Event generation | Each event type emitted exactly when specified, with required fields (timestamp, session id, type, HR, phase, interval number, source, metadata) |
| Signal quality | Each state and detection rule (impossible HR, malformed, duplicate/invalid/out-of-order timestamps, stale, missing, jumps, gaps) with parameters from the approved configuration |
| Debounce/hysteresis | One noisy sample does not cause a transition; behavior at configured thresholds |
| Field-test calculations | Only for approved protocols; fixtures from the source's worked examples; protocols with `EQUATION NOT SPECIFIED` must refuse to calculate |
| Calibration calculations | Application of `a × estimate + b`; fitting method once chosen, verified against independent analytical solutions; error before/after |
| Provenance | Every derived value has kind, unit, method id/version, inputs; raw rows unchanged after processing |
| Unit conversion | Each conversion, round trips, unknown units raise `UnitConversionError` |
| Analytics availability | Metrics return `unavailable` with reasons when data are insufficient; never a default number |

---

## 4. Property-based tests (Hypothesis)

Invariants (MANDATED categories: state transitions, timing, interval completion, zone behavior):

- Any generated sequence of commands and samples never produces an invalid state; terminal states stay terminal.
- Total elapsed time equals the sum of phase durations on the session clock; HR input never alters phase duration.
- Interval completion count equals the number of completed work/recovery pairs under each completion mode.
- `lower ≤ target ≤ upper` for every constructed zone; classification is consistent with bounds.
- A single out-of-zone sample never changes the debounced zone status (once debounce is specified).
- Event sequence numbers are strictly increasing; no event without a cause.
- Unit conversions are monotonic and invertible within tolerance.
- Event replay reproduces the same final state.

Generators produce synthetic streams only.

---

## 5. Integration tests (MANDATED list)

- Sensor adapter → ingestion (simulator, manual; BLE mock for the adapter contract in Part 2b). Replay is an ingestion service and is tested as such (Section 6), not through the adapter contract.
- Ingestion → engine → events.
- API → application layer (REST and WebSocket, including auth once defined).
- Database persistence and migrations (SQLite and PostgreSQL where both are supported); append-only constraints on raw tables.
- CPET import pipeline against **synthetic, clearly labelled minimal fixtures**; plus verification against real anonymized files, if the project owner provides them, kept outside the public repository.
- Calibration workflow end to end: import → QC → synchronization → candidate → validation → activation, including rejection and retirement.
- WebSocket reconnect: snapshot after disconnect; ordering with `seq`.

---

## 6. Replay tests (MANDATED), Part 2a

Replay is a Part 2a feature; no replay tests exist in Phase 1.

**Fixture metadata (decided, minimal).** A replay fixture is a metadata file under `data/synthetic/` (for example `<fixture_id>.fixture.json`) containing: `fixture_id`, `format_version`, `is_synthetic` (must be `true`), `generator` (`simulator`), `software_version`, the complete simulator parameters (`seed`, `start_value`, `min_value`, `max_value`, `max_step`, `interval_seconds`, `speed`), `clock_start_utc`, `sample_count`, and a SHA-256 of the canonical generated stream. The stream is regenerated by the deterministic simulator under a `ManualClock`, ingested, then replayed from the database; no real data and no binary sample files are committed. Simulator bounds in fixtures are test conventions, not physiological claims.

**Determinism criterion.** For the same origin session, configuration and injected clock, replay yields the same sequence of replayed fields (`received_hr`, `raw_payload`, `device_timestamp`, `received_at`) and the same assessment states and reasons. `ingestion_timestamp` and `elapsed_seconds` are clock-derived and are identical only under an identical injected clock; tests use `ManualClock`. Pacing (speeds 1x, 5x, 20x) is applied through an injected sleep and must not change any stored value. Simulator determinism (Section 10, Phase 1 row) is the Phase 1 precursor.

Same input stream plus same clock ⇒ same domain events and same results. Replay fixtures are synthetic recordings produced by the deterministic simulator and checked in with their generation seed/parameters. These tests lock down engine behavior and guard against regressions when thresholds or methods are versioned. A change in expected events requires a deliberate method version bump.

---

## 7. Scientific validation (planned, not performed)

Distinct from software testing:

- **Verification of implementation against specification** (automated, as above).
- **Validation of scientific claims** requires real data and independent reference measurement, and is outside the automated suite. None exists. Any future validation study must be defined (protocol, sample, metrics, acceptance criteria) before data are collected and is reported separately.
- Until validation is complete, outputs are labelled software/field estimates, research prototype; documentation never claims accuracy figures that have not been measured.
- Calibration "quality" is reported from measurable quantities only (Scientific Specification 11.4); tests ensure no confidence percentage is produced.
- Regression datasets (when real anonymized data become available under appropriate consent) are stored outside the public repository.

---

## 8. Data quality and failure-case tests (MANDATED, Section 53)

Each case below has explicit tests at the layer where it is handled:

missing values; duplicated rows; invalid timestamps; impossible HR; gaps; out-of-order samples; invalid units; malformed files; empty datasets; insufficient calibration data; failed QC; calibration worse than baseline (must be reported and must not activate silently); sensor disconnection; recovery from sensor disconnection; pause/resume; early session termination.

Additional (PROPOSED): corrupted XLSX/CSV encodings, very large files, header detection ambiguity, mixed units within a column, duplicate imports of the same file (same hash), clock offsets, extremely long sessions.

---

## 9. Non-functional tests (PROPOSED)

- Latency from sample ingestion to WebSocket delivery under a defined load (targets OPEN).
- Concurrent sessions soak test (target concurrency OPEN).
- Security tests: authentication/authorization on every endpoint and the WebSocket; confirmation that logs contain no raw physiological data or identifiers; secrets scanning in CI; checks that no real data files are committed (path/pattern rules).
- Frontend: component tests for rendering from recorded message streams; tests asserting that UI components contain no physiological calculations; accessibility checks; audio-trigger mapping from events (audio output mocked).
- Architecture tests: import rules enforcing layer boundaries (domain does not import API/storage/sensor vendors).

---

## 10. Test plan by phase (Master Prompt Section 57)

| Phase | Primary tests |
|---|---|
| 1 Foundation (amended) | Smoke tests, CI gates, config loading, layer-boundary checks; migration up/down on the empty baseline verifying that **no Phase 2 tables** (e.g. `SensorSample`) exist; health/status and error-envelope tests; default-deny authorization and role tests with the development identity; `Clock` and UUID generation tests; `HeartRateSensor` contract tests for the simulator and manual adapters; simulator determinism (same seed, same stream); in-memory sample flagging (`is_synthetic`, `source_kind`); frontend (Vitest) tests of the health/status view, role-aware navigation boundary, research-prototype notice and typed client; repository guards (no secrets, no real data files, no ML dependencies). No physiological-calculation tests exist because none are implemented. |
| 2a Persistence, ingestion, validation, signal quality, replay (amended) | Migration `0002` up/down on SQLite creating exactly the five Part 2a tables (`sensor`, `recording_session`, `sensor_sample`, `processing_run`, `signal_assessment`) and nothing else; raw immutability (no update/delete path, malformed input persisted exactly as received with null value and retained payload); non-finite values (NaN, +inf, -inf) round-trip on SQLite as a `received_hr_nonfinite` class with NULL `received_hr`, the two-way check constraint rejects inconsistent rows, finite values never set the marker, such samples are `malformed_sample`/`INVALID`, and replay reproduces the original non-finite value; sequence gap-free and unique per session; `InvalidSensorSample` only for delivery-contract violations (unknown/closed/inactive session, sensor mismatch, source-kind mismatch), never for a non-UTC offset; timezone-aware `received_at`/`device_timestamp` in non-UTC offsets are stored as the same UTC instant; a naive `device_timestamp` is stored NULL, the sample persisted, and `invalid_timestamp`/`INVALID` recorded; each session's single `ProcessingRun` is created with the session and owns all its assessments including the close-time `stale` range; unique `(processing_run_id, sample_id)` rejects a duplicate per-sample row while multiple range rows with NULL `sample_id` in one run are accepted (no uniqueness is claimed for range rows); a naive `device_timestamp` is stored NULL with any supplied `raw_payload` retained byte-for-byte and no payload fabricated when none was supplied; a sample with no assessment is unassessed, not `GOOD`; replay sessions get their own run and copy no origin assessments; one test per reason code in `SCIENTIFIC_SPECIFICATION.md` 5.1 using a labelled test configuration; precedence and `no_findings_state` rules; configuration immutability by `(id, version, hash)`; canonical-serialization conformance against the test vector, number vectors and extreme-value vectors (`5e-324`, largest finite binary64, `2^-1017`) in `SCIENTIFIC_SPECIFICATION.md` 5.1.1, plus a cross-check of the implementation against an independent exact implementation of the ECMA-262 digit selection over all positive powers of two and a random sample (key order, number formatting, `100` equals `100.0`, NaN/Infinity/unknown keys/missing keys rejected, source key order irrelevant); sensor/session consistency; replay determinism and non-mutation of the origin session; replay provenance (`origin_sample_id`, inherited `is_synthetic`); clock-injected `elapsed_seconds`; property tests over generated synthetic streams; layer-boundary contracts extended to `ingestion` and `signal`; no new API route (route set unchanged from Phase 1). |
| 2b Real transport (separately gated) | Adapter contract tests against a mock transport first; real-hardware tests only after the transport path and Polar H10 interface are verified and approved |
| 3 Interval engine | Unit, property and replay tests for zones, state machine, timing, events |
| 4 Real-time monitoring | WebSocket integration, snapshot/reconnect, UI rendering from recorded streams |
| 5 Audio engine | Event-to-cue mapping, warning-pattern timing with fake clock |
| 6 Session analytics | Metric definitions, availability rules, summary separation of planned/observed/calculated |
| 7 Field framework | Protocol descriptor validation, refusal when equation unspecified, approved-protocol fixtures |
| 8 CPET import | Parser, mapping, unit conversion, QC, malformed inputs, synchronization |
| 9 Calibration | Method tests, lifecycle transitions, before/after error, worse-than-baseline handling |
| 10 Personalization | Profile history immutability, provenance, override audit |
| 11 Reporting | CSV content and provenance fields, synthetic labelling |
| 12 Hardening | Security, privacy, backup/restore |
| 13 Integration | End-to-end flows with synthetic data, provenance audit across the chain |
| 14 Release | Documentation consistency checks |

Each phase's acceptance requires its tests to pass and its documentation to be updated.

---

## 11. Open items

1. Frontend testing tools: resolved for Phase 1 (Vitest); component-testing and accessibility tooling remain OPEN.
2. Coverage/quality thresholds (none invented here).
3. Availability of real anonymized lab files for import verification, and the handling procedure outside the public repository.
4. Latency and concurrency targets.
5. Whether PostgreSQL-specific behaviors need a PostgreSQL service in CI.
