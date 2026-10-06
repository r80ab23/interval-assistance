# API Specification — Interval Assistance

**Status:** DRAFT and **PROVISIONAL by design.** The Master Prompt says not to finalize endpoint details until the domain model is defined and accepted. This document fixes conventions, resource boundaries and message *shapes*, not final paths, payloads or status codes. No API exists yet.

**Labels:** MANDATED, PROPOSED, OPEN.

---

## 1. Principles

1. REST resources are organized around domain concepts (MANDATED): `/athletes`, `/coaches`, `/sensors`, `/sessions`, `/protocols`, `/field-tests`, `/laboratory-tests`, `/calibrations`, `/profiles`, `/reports`.
2. Real-time channel: `/ws/sessions/{session_id}` (MANDATED).
3. The API is transport. It contains **no physiological logic** (MANDATED): handlers validate, call application services, and map results to schemas.
4. Schemas distinguish **input, output, measured, estimated, calculated, calibrated** (MANDATED). No bare numeric `value` without kind, unit and provenance.
5. The UI never computes zones, interval state or metrics; it displays what the API returns.
6. (PROPOSED) URL versioning: `/api/v1/...`. Pydantic v2 schemas generate an OpenAPI document, which becomes the contract the frontend client is generated from or checked against.
7. (PROPOSED) Synthetic data is flagged in responses (`is_synthetic`), and clients must display that flag.

---

## 2. Common schema conventions (PROPOSED)

### 2.1 Typed value envelope

All physiological values in responses use this shape:

```json
{
  "kind": "measured | estimated | calculated | calibrated | personalized | raw",
  "quantity": "<enumerated quantity name>",
  "value": "<number or null>",
  "unit": "<normalized unit>",
  "availability": "available | unavailable",
  "unavailable_reason": "<code or null>",
  "provenance": {
    "method_id": "<id or null>",
    "method_version": "<version or null>",
    "processing_run_id": "<id>",
    "source_refs": ["<entity refs>"]
  },
  "is_synthetic": false
}
```

Placeholders in angle brackets are schema types, not example data.

Field-test results always have `kind = estimated` and a `label` of field estimate; laboratory values have `kind = measured`. A calibrated value includes a reference to the calibration id and version and to the uncalibrated estimate.

### 2.2 Input schemas

Inputs never carry `kind` for derived quantities (the server decides). Coach-entered values (HRmax, HRrest, manual zones) carry an `origin` field (see Scientific Specification Section 2).

### 2.3 Identifiers and time

Identifiers are opaque strings (UUID proposed). Timestamps are ISO 8601 UTC. Elapsed times are seconds as numbers, named `elapsed_seconds`. Device, ingestion and event timestamps are separate fields wherever more than one applies.

### 2.4 Pagination, filtering

OPEN (list endpoints will need it; style to be selected in Phase 1).

---

## 3. Resource overview (PROVISIONAL)

| Resource | Purpose | Candidate operations |
|---|---|---|
| `/athletes` | Pseudonymous athlete records | create, read, list, update non-identifying attributes |
| `/coaches` | Coach records | read, list |
| `/sensors` | Registered sensors; connection state | register, read, list, connect/disconnect commands |
| `/protocols` | Versioned training protocols | create (new version), read, list versions |
| `/sessions` | Training sessions and control | create, read, list; commands: start, pause, resume, stop; read summary, events, samples (raw, paginated) |
| `/field-tests` | Field-test runs and results | list protocols, create test, add stage inputs, calculate (only for approved protocols), read result |
| `/laboratory-tests` | CPET uploads and parsed data | upload file, inspect, set mapping, run import, read QC report, read samples |
| `/calibrations` | Calibration candidates and lifecycle | create candidate, read result (before/after), validate, activate, reject, retire, list versions |
| `/profiles` | Athlete physiological profile | read current, read history, set coach override (audited) |
| `/reports` | Exports with provenance | request export (CSV required), download |

**Command endpoints** (start/pause/resume/stop, activate/reject calibration) are explicit action resources rather than status fields that clients set, so the application layer can enforce state-machine and lifecycle rules.

Rules specific to resources:

- Raw resources (sensor samples, source files, lab samples) are read-only after creation.
- A session's protocol is referenced by id **and version**.
- Calibration activation requires the candidate to be `VALIDATED` and records actor and reason.
- `/field-tests` calculation returns an error if the protocol status is `EQUATION_NOT_SPECIFIED`.
- Endpoints that produce metrics return `unavailable` envelopes with reason codes rather than omitting or defaulting values.

---

## 4. WebSocket: `/ws/sessions/{session_id}` (PROVISIONAL shapes)

### 4.1 Envelope

```json
{
  "type": "<message type>",
  "session_id": "<id>",
  "seq": "<per-session monotonically increasing integer>",
  "server_time": "<UTC ISO 8601>",
  "elapsed_seconds": "<session clock>",
  "payload": { }
}
```

`seq` lets clients detect gaps and ordering problems.

### 4.2 Server → client messages

| `type` | Payload (summary) |
|---|---|
| `snapshot` | Full current state: engine state (`IDLE`…`ERROR`), phase, interval index, remaining phase time, resolved zone (lower/target/upper with origin), latest HR with quality state, connection state, recent HR history window, planned protocol outline. Sent on connect and reconnect. |
| `hr_sample` | HR value as typed envelope, signal-quality state, device/ingestion/elapsed times. |
| `state_changed` | Previous and new engine state, phase info. |
| `event` | A domain event exactly as defined in Master Prompt Section 10 (type, timestamp, session id, HR if available, phase, interval number, source, metadata). |
| `zone_status` | `BELOW | WITHIN | ABOVE` classification after debounce. |
| `summary_ready` | Reference to the post-session summary resource. |
| `error` | Structured error (Section 6). |

Audio cues are derived client-side from `event` messages using the session's audio configuration (OPEN, `ARCHITECTURE.md` 5.2). Future planned data (protocol outline) is delivered in `snapshot`, separate from measured `hr_sample` data, so clients cannot confuse planned and measured series.

### 4.3 Client → server messages

Commands only: `start`, `pause`, `resume`, `stop`, and `manual_hr` (accepted only when the session's sensor is a manual or simulator source). Each command is validated by the application layer; clients never send derived state. Responses arrive as `state_changed`, `event`, or `error`.

### 4.4 Reliability (PROPOSED)

- On reconnect the server sends a `snapshot` and then resumes from live messages; clients may request replay from a `seq` (OPEN, depends on retention of recent messages).
- Multiple viewers (coach, athlete) can observe the same session; only authorized controllers may send commands.
- Backpressure: slow clients are dropped and must reconnect (OPEN).

---

## 5. Authentication and authorization boundary

OPEN. Required decisions before Phase 1 completes: authentication mechanism, token handling for WebSocket upgrade (query string tokens leak into logs; header- or first-message-based auth preferred), roles (coach, athlete, researcher/admin), per-athlete access rules, consent handling, and audit logging for sensitive actions. All endpoints and the WebSocket must require authorization once implemented; unauthenticated public endpoints are limited to health checks (PROPOSED).

Direct identifiers, if stored, are exposed only through a dedicated restricted endpoint (PROPOSED).

---

## 6. Errors

Structured error body (PROPOSED):

```json
{
  "error": {
    "code": "<machine code>",
    "message": "<human readable>",
    "details": { },
    "request_id": "<id>"
  }
}
```

Domain error to API mapping (codes MANDATED as domain errors; HTTP status PROPOSED):

| Domain error | Suggested HTTP status |
|---|---|
| `InvalidTrainingProtocol` | 422 |
| `InvalidSensorSample` | 422 (REST) / `error` message (WS) |
| `InvalidStateTransition` | 409 |
| `SensorConnectionError` | 502 or 409 (OPEN) |
| `CPETImportError` | 422 |
| `UnitConversionError` | 422 |
| `SynchronizationError` | 422 |
| `InsufficientCalibrationData` | 422 |
| `CalibrationValidationError` | 422 |

Validation errors from Pydantic map to 422 with field-level details. Errors are never used to mask invalid physiological data; invalid data is reported, not silently dropped.

---

## 7. Export and reporting

CSV is required where appropriate (MANDATED). Exports (session, interval execution, field test, CPET import/QC, calibration, profile) preserve provenance: each row or accompanying metadata file states value kind, unit, method id/version, processing run, synthetic flag, and generation time. Synthetic data is never exported without its label. Exact formats are OPEN until Phase 11.

---

## 8. Open items

1. Final path structure, pagination, filtering.
2. Authentication mechanism and roles.
3. WebSocket reconnect/replay policy and backpressure.
4. Where audio rendering occurs (client vs other).
5. Handling large raw-sample reads (paging/streaming).
6. File upload limits and storage for CPET files.
7. Idempotency for command endpoints.
