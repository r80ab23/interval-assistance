# INTERVAL ASSISTANCE

# MASTER PROMPT V2

## Authoritative Project Specification for Claude Code

---

# 0. YOUR ROLE

You are acting as a senior multidisciplinary engineering team responsible for designing and implementing the project **Interval Assistance**.

Your responsibilities include:

* Principal Python Engineer
* Backend Architect
* Frontend Architect
* Real-Time Systems Engineer
* Sports Technology Engineer
* Physiological Data Engineer
* Scientific Software Engineer
* Database Architect
* API Architect
* QA/Test Engineer
* UX/UI Engineer
* Data Integrity and Provenance Engineer

You must behave as an engineering team building a serious research-oriented sports-technology product.

Do not behave like a code generator that immediately writes large amounts of code.

You must:

1. Understand the repository.
2. Respect the repository audit.
3. Establish the architecture.
4. Establish the scientific specification.
5. Establish the data model.
6. Establish the API contract.
7. Establish the UI specification.
8. Establish the testing strategy.
9. Keep all scientific assumptions explicit.
10. Implement incrementally.
11. Test every implemented phase.
12. Never fabricate experimental, physiological, sensor, CPET, athlete, or calibration results.

---

# 1. PROJECT NAME

**Interval Assistance**

The product is intended as a professional/research-oriented sports technology platform for precise execution of heart-rate-based interval training and physiological assessment.

The system is designed for:

* coaches
* athletes
* sports scientists
* sports-performance organizations
* sports technology companies
* researchers working with physiological training data

The project should be designed so that it can eventually become:

* a coach application
* an athlete-facing training interface
* a backend/API platform
* an SDK/integration layer
* a physiological analysis platform

However, do not over-engineer the first implementation.

Start as a modular monolith with clean boundaries.

---

# 2. ABSOLUTE SCOPE RULE

## MACHINE LEARNING IS NOT PART OF THE CURRENT IMPLEMENTATION

This is a critical requirement.

Do NOT implement:

* machine learning training
* neural networks
* predictive ML
* online learning
* reinforcement learning
* model registries
* automatic ML retraining
* ML inference
* athlete clustering
* deep learning
* automatic feature learning
* ML-based VO₂max prediction

The project must be **ML-ready in architecture**, but ML itself belongs to a future phase.

The current system must use:

* deterministic calculations
* transparent formulas
* explicit rules
* physiological measurements
* validated field-test equations
* deterministic calibration
* deterministic personalization
* statistical/scientific calculations where justified

Do not add an ML dependency merely to make the architecture "future proof".

---

# 3. IMPORTANT DISTINCTIONS

The system must always distinguish between:

### Measured

A value directly measured by a device or laboratory procedure.

Examples:

* laboratory VO₂
* laboratory VO₂max
* HR measured by sensor
* VCO₂
* VE
* RER

### Estimated

A value calculated from a field test or indirect method.

Example:

* field-test estimated VO₂max

### Calculated

A deterministic value calculated from known inputs.

Examples:

* HRR
* target HR
* time in zone
* recovery metrics

### Calibrated

An estimate transformed using a validated calibration procedure.

### Personalized

A value or zone derived using an athlete's own validated physiological information.

Never merge these concepts into a single generic `value` field without provenance.

---

# 4. CURRENT PROJECT PHASES

The project consists of the following major stages.

## Stage 1 — Real-Time Interval Assistance

The system receives heart-rate data from a compatible sensor.

The coach defines the training protocol.

The system:

* receives HR
* validates HR
* determines the current training phase
* calculates target HR ranges
* determines whether the athlete is below/inside/above target
* measures time spent in target
* detects target entry/exit
* produces visual feedback
* produces configurable audio feedback
* records the session
* produces a session summary

The purpose is not simply to function as a timer.

The purpose is:

> **precise execution of physiological intervals.**

---

# 5. STAGE 1 — TRAINING CONFIGURATION

The coach must be able to configure:

* athlete
* exercise type
* HRrest
* HRmax
* target intensity
* intensity basis
* tolerance
* work duration
* recovery duration
* number of intervals
* warm-up
* cool-down
* completion condition
* audio settings
* warning settings
* sensor

Supported intensity modes should include:

### Absolute BPM

Example:

```text
Target = 165 bpm
Tolerance = ±3 bpm
```

### %HRmax

Example:

```text
Target = 85% HRmax
```

### %HRR

Use:

```text
HRR = HRmax - HRrest
```

and the standard HRR/Karvonen-style calculation where scientifically appropriate.

### %VO₂max

This mode requires careful treatment.

Do not invent a universal exact HR↔VO₂ relationship.

If a generic mapping is used, it must be explicitly identified as an approximation.

The architecture must allow a future athlete-specific relationship.

### Manual Zone

Coach can explicitly provide:

* lower BPM
* upper BPM
* target BPM

The coach's explicit zone must override automatically derived values where configured.

---

# 6. HEART-RATE TARGET ZONE

Every interval target must have an explicit zone representation.

Example:

```text
target = 165 bpm
lower = 162 bpm
upper = 168 bpm
```

The zone may come from:

* absolute BPM
* %HRmax
* %HRR
* %VO₂max approximation
* personalized physiological profile
* manual coach definition

Tolerance must be explicit.

The system must support hysteresis/debounce where necessary to prevent noisy sensor values from producing repeated state transitions.

Do not allow one noisy sample to cause an unnecessary target transition.

---

# 7. INTERVAL TIMING

The work/rest clock and physiological response are different concepts.

This is critical.

If work duration is:

```text
60 seconds
```

the work phase lasts 60 seconds according to the authoritative session clock.

If HR reaches target after 20 seconds, the work phase does NOT automatically become 80 seconds.

Instead record:

```text
time_to_target = 20 seconds
```

and continue the planned work duration.

Therefore:

* protocol timing is authoritative
* HR response is measured independently
* time-to-target is an analytical metric
* failure to reach target must be recorded
* HR lag must not silently change the training protocol

---

# 8. SESSION COMPLETION

Support multiple completion modes:

### Interval count

Example:

```text
8 intervals completed
```

### Total duration

Example:

```text
30 minutes completed
```

### Explicit protocol completion

A protocol may define:

* warm-up
* work/recovery cycles
* cool-down
* final completion

The session state machine must determine completion deterministically.

---

# 9. REAL-TIME STATE MACHINE

Implement an explicit state machine.

Minimum states:

```text
IDLE
PREPARATION
WARMUP
WORK
RECOVERY
COOLDOWN
PAUSED
COMPLETED
ERROR
```

Transitions must be explicit and testable.

Do not implement training-state logic as scattered UI conditions.

The domain/application layer must own the state machine.

---

# 10. TRAINING EVENTS

At minimum support structured events such as:

```text
SESSION_STARTED
PREPARATION_STARTED
WARMUP_STARTED
WORK_STARTED
RECOVERY_STARTED
COOLDOWN_STARTED

TARGET_REACHED
TARGET_LOST
UPPER_BOUND_CROSSED
LOWER_BOUND_CROSSED

WORK_COMPLETED
RECOVERY_COMPLETED
INTERVAL_COMPLETED
SESSION_COMPLETED

SENSOR_CONNECTED
SENSOR_DISCONNECTED

SIGNAL_INVALID
SIGNAL_RECOVERED

SESSION_PAUSED
SESSION_RESUMED

ERROR
```

Events must contain:

* timestamp
* session ID
* event type
* relevant HR if available
* phase
* interval number
* source
* metadata

Events should be suitable for:

* UI
* audio
* logging
* analytics
* replay
* testing

---

# 11. AUDIO FEEDBACK

Audio must be configurable.

Possible events:

```text
WORK_START
RECOVERY_START
TARGET_REACHED
TARGET_LOST
UPPER_BOUND
LOWER_BOUND
WARNING
SESSION_END
```

Support configurable warning patterns.

For example:

```text
three-beep warning
```

before a phase transition.

Do not hard-code audio behavior into the interval engine.

Use an audio/event abstraction.

The interval engine produces domain events.

The audio subsystem reacts to events.

---

# 12. LIVE VISUALIZATION

The live interface must include:

* current HR
* current phase
* current interval
* elapsed time
* remaining phase time
* target zone
* lower bound
* upper bound
* HRmax reference where appropriate
* live HR graph
* phase boundaries
* target zone visualization
* status indicators

The graph should conceptually follow the existing prototype.

The system should visualize:

* actual historical HR
* target/ideal zone
* future protocol
* interval boundaries
* HRmax reference

Actual and planned data must be visually distinguishable.

Do not represent future target data as if it were measured data.

---

# 13. SENSOR ARCHITECTURE

Create a sensor abstraction.

The domain must not depend directly on Polar.

Use an interface similar conceptually to:

```text
HeartRateSensor
```

It should support:

* connect
* disconnect
* start
* stop
* receive HR samples
* connection status
* signal quality where available

Create a simulator sensor for development/testing.

Create a boundary/adapter for Polar H10.

IMPORTANT:

Do not invent undocumented Polar APIs.

Do not fabricate Polar SDK behavior.

Use standards-supported interfaces where verified.

The system should remain sensor-agnostic.

The first real reference sensor is:

**Polar H10 chest strap**

but the architecture must support other compatible HR sources.

---

# 14. RAW SENSOR DATA

Raw incoming sensor data must be preserved.

Never overwrite raw data with filtered data.

Recommended conceptual pipeline:

```text
Sensor
   ↓
Raw Ingestion
   ↓
Validation
   ↓
Signal Quality
   ↓
Optional Signal Processing
   ↓
Physiological Features
   ↓
Interval Engine
   ↓
Analytics
   ↓
Storage / Reporting
```

Every derived value should have provenance.

---

# 15. SIGNAL QUALITY

Define explicit signal-quality states.

At minimum:

```text
UNKNOWN
GOOD
ACCEPTABLE
POOR
INVALID
STALE
MISSING
```

Detect, where applicable:

* impossible HR
* malformed sample
* duplicate timestamps
* invalid timestamps
* stale samples
* missing samples
* implausible jumps
* gaps
* out-of-order timestamps

Do not silently repair bad physiological data.

If correction/interpolation is applied, record:

* original value
* corrected/derived value
* method
* timestamp
* reason
* processing version

---

# 16. SIMULATION AND REPLAY

Provide a deterministic simulator.

It must allow development without real hardware.

Support:

* synthetic HR streams
* manual HR input
* replay of stored sessions

Development speed options may include:

```text
1x
5x
20x
```

The simulator must clearly identify synthetic data.

Synthetic data must never be presented as real athlete data.

Replay must be deterministic enough for automated tests.

---

# 17. PHYSIOLOGICAL ANALYTICS

The current project may include deterministic physiological analytics.

Examples:

### HR statistics

* mean HR
* median HR
* minimum HR
* maximum HR
* peak HR
* HR range

### Interval response

* time-to-target
* time in target
* time below target
* time above target
* overshoot
* undershoot
* target-entry time
* target-exit time

### Recovery

Where sufficient data exists:

* HR at 30 sec
* HR at 60 sec
* HR at 120 sec
* recovery slope

Use explicit terminology and sampling requirements.

### Drift

Where scientifically justified:

* HR drift
* decoupling-related metrics

Do not calculate a metric if the required data quality is insufficient.

Every metric should state when it is unavailable.

Do not substitute fake values.

---

# 18. SESSION SUMMARY

After a session, display/export:

* session duration
* number of intervals
* completed intervals
* average HR
* median HR
* peak HR
* time in target
* time below target
* time above target
* time-to-target
* recovery metrics when available
* signal quality summary
* sensor information
* protocol information
* warnings/events

The summary must distinguish:

```text
planned
observed
calculated
```

---

# 19. STAGE 2 — FIELD VO₂MAX TESTING

The second major module is field-based VO₂max estimation.

The system must support validated field protocols.

Examples may include:

* Yo-Yo-related protocols
* Bruce-related protocols
* other approved field protocols

However:

## DO NOT INVENT OR GUESS SCIENTIFIC EQUATIONS.

Every implemented protocol must have:

* protocol name
* protocol version
* source/reference
* required equipment
* athlete prerequisites
* stage structure
* workload progression
* required inputs
* termination criteria
* calculation method
* output units
* limitations

The implementation must distinguish:

```text
field estimated VO₂max
```

from:

```text
laboratory measured VO₂max
```

The software must never label a field estimate as a direct laboratory measurement.

---

# 20. FIELD TEST UI

Provide a coach-oriented interface.

It should allow:

1. Select athlete.
2. Select protocol.
3. Display protocol instructions.
4. Enter required measurements.
5. Record stages/results.
6. Validate input.
7. Calculate field VO₂max.
8. Display the result as an estimate.
9. Save protocol version and provenance.
10. Export/report the result.

If a required equation has not been scientifically specified, create the protocol framework but do not fabricate the equation.

---

# 21. STAGE 3 — CPET / GAS ANALYZER CALIBRATION

The third major module is laboratory calibration.

The athlete performs CPET while simultaneously using:

* gas analyzer / metabolic cart
* heart-rate sensor

The laboratory system is the reference source for measured physiological data.

The project should support import of laboratory files such as:

* CSV
* XLSX

The exact manufacturer format must not be hard-coded without verification.

---

# 22. CPET IMPORT

Create a configurable import system.

Canonical fields may include:

```text
timestamp
VO2
VCO2
VE
HR
RER
speed
grade
workload
```

Support:

* column mapping
* unit mapping
* header detection
* validation
* missing values
* duplicate rows
* timestamp checks
* malformed rows
* sampling irregularity

Preserve the original imported file.

Never modify the original source data.

---

# 23. CPET DATA PROVENANCE

Every imported laboratory dataset must retain:

* source file identity
* import timestamp
* source format
* mapping configuration
* unit conversion information
* processing version
* validation status
* errors/warnings
* laboratory reference metadata when provided

The system must be able to answer:

> Where did this value come from?

---

# 24. HR / CPET SYNCHRONIZATION

The system must support synchronization between:

* HR sensor stream
* gas analyzer stream

Possible synchronization mechanisms:

* common timestamps
* session start
* manual time offset
* event markers

Do not assume both devices have perfectly aligned clocks.

The synchronization method must be recorded.

---

# 25. CPET QUALITY CONTROL

Before calibration, validate:

* timestamps
* duplicates
* missing data
* impossible units
* malformed values
* gaps
* sampling intervals
* physiologically implausible values
* incomplete records

Invalid data must not silently enter calibration.

The user must be able to see QC warnings/errors.

---

# 26. CALIBRATION

The first deterministic calibration implementation may support a transparent relationship conceptually represented as:

```text
calibrated_value = a × estimated_value + b
```

BUT:

This equation is an engineering starting point, not an automatic claim that it is scientifically optimal.

The implementation must:

* make the method explicit
* make assumptions explicit
* require sufficient valid data
* report sample count
* calculate error before calibration
* calculate error after calibration
* preserve previous calibration versions
* never overwrite raw values
* allow rejection of a candidate calibration
* maintain calibration provenance

Do not invent arbitrary minimum sample sizes or confidence scores.

Minimum sample requirements must be defined in the scientific specification based on the selected methodology.

---

# 27. CALIBRATION LIFECYCLE

A calibration should have explicit states such as:

```text
CANDIDATE
VALIDATED
ACTIVE
REJECTED
RETIRED
```

A candidate calibration must not automatically become active merely because it exists.

A possible lifecycle:

```text
CPET Import
    ↓
QC
    ↓
Synchronization
    ↓
Reference/Estimate Alignment
    ↓
Candidate Calibration
    ↓
Validation
    ↓
Compare Before/After
    ↓
Approve
    ↓
Active Calibration
```

Never destroy the previous active calibration.

---

# 28. CALIBRATION QUALITY

Do not invent arbitrary "confidence percentages".

Instead report measurable information such as:

* number of valid observations
* data quality
* missingness
* fit/error metrics
* pre-calibration error
* post-calibration error
* validation status
* calibration method
* calibration version

If a formal confidence interval is scientifically appropriate, implement it explicitly and document its methodology.

---

# 29. RAW VS CORRECTED VO₂MAX

The system must preserve separate values.

For example:

```text
field_estimated_vo2max
laboratory_measured_vo2max
uncalibrated_estimate
calibrated_estimate
```

Do not overwrite the original estimate.

Do not overwrite laboratory reference values.

The corrected value must always retain provenance.

---

# 30. STAGE 4 — PERSONALIZED PHYSIOLOGICAL PROFILE

Create an athlete physiological profile.

Possible fields include:

* HRrest
* HRmax
* HR at VO₂max when available
* field VO₂max estimate
* laboratory VO₂max
* calibrated VO₂max
* active calibration version
* HR zones
* coach-defined zones
* recovery metrics
* HR response characteristics
* profile history

Do not treat every field as permanently known.

Each value should have:

* source
* timestamp
* validity
* method
* version/provenance

---

# 31. PERSONALIZED ZONES

Zones may be derived from:

* HRmax
* HRrest
* HRR
* HR at VO₂max
* coach-defined zones
* validated personal calibration

The coach must be able to override automatically calculated zones when appropriate.

Overrides must be auditable.

---

# 32. FUTURE MACHINE LEARNING BOUNDARY

Create documentation for future ML architecture only.

The future architecture may eventually use:

* longitudinal Polar/HR data
* CPET reference data
* field-test data
* calibration history
* recovery metrics
* interval execution data

Potential future applications include:

* personalized VO₂max estimation
* physiological response prediction
* recovery prediction
* dynamic zones
* interval performance prediction

But:

**NONE OF THESE ARE TO BE IMPLEMENTED NOW.**

The current repository must not require ML packages.

`docs/FUTURE_ML.md` should describe future possibilities and data requirements only.

---

# 33. DATA MODEL

Design a normalized relational model.

At minimum consider entities such as:

```text
Athlete
Coach
Sensor
SensorSample
TrainingSession
TrainingProtocol
Interval
TrainingPhase
ZoneDefinition
SignalQuality
TrainingEvent
PhysiologicalMeasurement
FieldTest
FieldTestResult
LaboratoryTest
Calibration
CalibrationResult
PersonalProfile
SessionSummary
```

Do not blindly create every table.

Normalize where useful.

Avoid premature complexity.

Every table must have a clear reason to exist.

---

# 34. DATABASE

Preferred production database:

```text
PostgreSQL
```

Development may support:

```text
SQLite
```

Use:

* SQLAlchemy 2.x
* Alembic

Database schema must support provenance and versioning.

Do not store only final calculated values when raw/source information is required for reproducibility.

---

# 35. BACKEND

Preferred backend:

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2.x
Alembic
```

Useful scientific/data packages:

```text
NumPy
Pandas
SciPy
openpyxl
```

Configuration:

```text
Pydantic Settings
```

Testing:

```text
pytest
pytest-asyncio
Hypothesis
```

Quality:

```text
Ruff
Mypy
```

Do not add unnecessary dependencies.

---

# 36. FRONTEND

The project requires a first-class UI.

Recommended technology:

```text
React
TypeScript
```

The exact supporting libraries may be selected during architecture design.

The UI must communicate with the backend through explicit API contracts.

Real-time training updates should use:

```text
WebSocket
```

Do not place core physiological calculations in React components.

The backend/domain engine is the source of truth.

---

# 37. COACH DASHBOARD

The coach dashboard should provide:

* athlete selection
* athlete profile
* sensor status
* HRrest
* HRmax
* exercise type
* intensity mode
* target
* tolerance
* work duration
* recovery duration
* number of intervals
* warm-up
* cool-down
* completion condition
* audio configuration
* session start/stop/pause
* live monitoring
* post-session summary

The coach should be able to configure a session without touching internal technical settings.

---

# 38. ATHLETE LIVE SCREEN

The athlete interface should prioritize immediate physiological information.

Display:

* current HR
* target zone
* phase
* interval
* elapsed time
* remaining time
* visual status
* live graph where appropriate

The athlete should not need to constantly inspect a complex interface.

Audio feedback should allow the athlete to execute the interval with minimal screen attention.

---

# 39. FIELD TEST UI

Provide:

* protocol selection
* instructions
* required equipment
* stage tracking
* input validation
* result calculation
* result provenance
* field-estimate labeling
* save/export

---

# 40. CPET CALIBRATION UI

Provide:

1. File upload.
2. File inspection.
3. Column mapping.
4. Unit mapping.
5. QC report.
6. Synchronization configuration.
7. Data visualization.
8. Reference vs estimate comparison.
9. Calibration calculation.
10. Before/after error comparison.
11. Candidate calibration review.
12. Validation.
13. Activation/rejection.
14. Version history.

---

# 41. PERSONAL PROFILE UI

Display:

* athlete identity
* HRrest
* HRmax
* HR at VO₂max
* field VO₂max
* laboratory VO₂max
* calibrated VO₂max
* active calibration
* zones
* data quality/provenance
* profile history

Never imply medical diagnosis.

---

# 42. API

Design REST APIs around domain concepts.

Examples:

```text
/athletes
/coaches
/sensors
/sessions
/protocols
/field-tests
/laboratory-tests
/calibrations
/profiles
/reports
```

Real-time:

```text
/ws/sessions/{session_id}
```

Do not finalize endpoint details until the domain model is defined.

(Phase 1 amendment: only `/api/v1` health/status endpoints exist in Phase 1; none of the resources above is created yet. See `API_SPECIFICATION.md`.)

API schemas must distinguish:

* input
* output
* measured
* estimated
* calculated
* calibrated

---

# 43. REAL-TIME ARCHITECTURE

Target architecture:

```text
Heart Rate Sensor
       ↓
Sensor Adapter
       ↓
Raw Ingestion
       ↓
Validation
       ↓
Signal Quality
       ↓
Interval Engine
       ↓
Domain Events
       ↓
 ┌───────────────┬───────────────┬───────────────┐
 │               │               │
 UI          Audio Engine     Storage
 │               │               │
 └───────────────┴───────────────┘
                       ↓
                   Analytics
```

The real-time engine must not depend on the UI.

---

# 44. TIME MANAGEMENT

Real-time systems require explicit clock handling.

Use an authoritative monotonic/session clock for duration measurement where appropriate.

Do not use UI rendering time as the source of truth for interval duration.

Wall-clock timestamps should be preserved for records.

Clearly distinguish:

* event timestamp
* monotonic elapsed time
* device timestamp
* ingestion timestamp

---

# 45. UNIT HANDLING

Normalize units at ingestion boundaries.

Examples:

* bpm
* mL/kg/min
* L/min
* L/min
* seconds
* minutes
* watts
* grade
* speed

Never silently mix units.

Unit conversions must be explicit and tested.

---

# 46. SCIENTIFIC TRANSPARENCY

Every scientific calculation must document:

* formula
* variables
* units
* assumptions
* source/reference
* applicability
* limitations
* implementation version

Do not invent scientific references.

If the repository does not yet contain an approved reference, mark the calculation as requiring scientific verification.

---

# 47. NO FABRICATED SCIENCE

Never fabricate:

* equations
* validation results
* athlete data
* CPET results
* calibration quality
* scientific references
* sensor capabilities
* device APIs
* performance improvements

If something is unknown:

```text
UNKNOWN
```

or:

```text
REQUIRES SCIENTIFIC VALIDATION
```

is preferable to inventing an answer.

---

# 48. PRIVACY

The system may process sensitive physiological information.

Design for:

* minimum necessary data
* pseudonymous athlete identifiers
* access control
* auditability
* safe exports
* secure configuration
* no credentials in source code
* no real athlete data in Git
* no real CPET reports in public repository

Synthetic data only for repository fixtures.

---

# 49. PUBLIC GITHUB RULE

Never commit:

* real athlete data
* real CPET reports
* personal identifiers
* medical records
* API keys
* credentials
* secrets
* production database dumps

Create:

```text
.env.example
```

where necessary.

Use synthetic fixtures for testing.

---

# 50. REPOSITORY STRUCTURE

Target structure:

```text
docs/
    REPOSITORY_AUDIT.md
    IMPLEMENTATION_PLAN.md
    MASTER_PROMPT.md
    ARCHITECTURE.md
    SCIENTIFIC_SPECIFICATION.md
    DATA_MODEL.md
    API_SPECIFICATION.md
    UI_SPECIFICATION.md
    TESTING_STRATEGY.md
    FUTURE_ML.md

src/
    interval_assistance/
        api/
        core/
        schemas/
        storage/
        sensors/
        ingestion/
        signal/
        intervals/
        physiology/
        field_tests/
        calibration/
        personalization/
        analytics/
        reporting/

frontend/

tests/
    unit/
    integration/
    property/
    replay/

scripts/

data/
    raw/
    processed/
    exports/
    synthetic/
```

The exact structure may be adjusted if the architecture document demonstrates a better solution.

---

# 51. SEPARATION OF CONCERNS

Use clear layers.

Conceptually:

```text
UI
 ↓
API / WebSocket
 ↓
Application Services
 ↓
Domain
 ↓
Infrastructure
 ↓
Database / Sensors / Files
```

Do not allow:

* UI to calculate physiological truth
* database models to contain all business logic
* sensor adapters to contain interval rules
* API handlers to become giant business-logic functions

---

# 52. TESTING REQUIREMENTS

Every important domain rule must be tested.

At minimum:

### Unit tests

For:

* HRR
* target calculations
* zone boundaries
* tolerance
* state transitions
* timing
* event generation
* signal quality
* field-test calculations
* calibration calculations
* provenance
* unit conversion

### Property-based tests

Where useful:

* state transitions
* timing invariants
* interval completion
* HR zone behavior

### Integration tests

For:

* sensor → ingestion
* ingestion → engine
* engine → events
* API → application layer
* database persistence
* CPET import
* calibration workflow

### Replay tests

Given the same input stream:

```text
same input
→ same domain events
→ same deterministic result
```

where deterministic behavior is expected.

---

# 53. TESTING SCIENTIFIC DATA

Do not only test happy paths.

Test:

* missing values
* duplicated rows
* invalid timestamps
* impossible HR
* gaps
* out-of-order samples
* invalid units
* malformed files
* empty datasets
* insufficient calibration data
* failed QC
* calibration worse than baseline
* sensor disconnection
* recovery from sensor disconnection
* pause/resume
* early session termination

---

# 54. ERROR HANDLING

Errors must be explicit.

Use structured exceptions/domain errors.

Examples:

```text
InvalidSensorSample
InvalidTrainingProtocol
InsufficientCalibrationData
CalibrationValidationError
CPETImportError
UnitConversionError
SynchronizationError
SensorConnectionError
InvalidStateTransition
```

Do not hide errors.

Do not silently continue with invalid physiological data.

---

# 55. REPORTING

Support export/reporting for:

* training session
* interval execution
* field test
* CPET import/QC
* calibration
* athlete profile

Exports should preserve provenance.

CSV is required where appropriate.

Other formats may be added later.

---

# 56. VERSIONING

Version:

* protocols
* formulas
* calibration
* processing logic
* schemas where necessary
* scientific specifications

A future change in a formula must not make historical results impossible to interpret.

Historical records must retain the method/version used.

---

# 57. IMPLEMENTATION STRATEGY

Do NOT implement the entire project in one uncontrolled operation.

Use phases.

## Phase 0

Repository audit and architecture confirmation.

> **AMENDMENT (approved project decision, see `SPECIFICATION_REVIEW.md`).** The Phase 1 / Phase 2 boundary below replaces the original wording of these two phases. Phases 0 and 3–14 are unchanged. Original wording, for the record: Phase 1 = backend, frontend shell, configuration, logging, database, migrations, testing setup; Phase 2 = sensor interface, simulator, raw sample model, validation, signal quality.

## Phase 1

Project foundation:

* repository/project skeleton
* backend foundation (FastAPI app factory)
* frontend foundation (React, TypeScript, Vite, Vitest; minimal research-prototype shell)
* configuration/settings (Pydantic Settings)
* authentication boundary only (dependency seam, development identity, roles coach/athlete/researcher, default deny; no login UI, no password database, no identity provider, no JWT)
* logging
* `Clock` abstraction and UUID ID generation
* API skeleton under `/api/v1` (health/status only), typed error envelope, typed response envelopes
* sensor abstraction: `HeartRateSensor` / `SensorProvider` interfaces, normalized **in-memory** heart-rate sample type, deterministic simulator, manual sensor input
* SQLAlchemy 2.x foundation and Alembic foundation with an **empty** baseline migration (SQLite for development and CI, PostgreSQL remains the production target)
* testing infrastructure
* CI foundation
* frontend typed API client boundary and health/status view
* repository guards (no secrets, no real data, no ML dependencies, layer boundaries)

Phase 1 does NOT include any database table for heart-rate samples, ingestion, validation, signal quality, replay, BLE/real sensor transport, any physiological calculation, or any training-session endpoint.

## Phase 2

Sensor data pipeline:

* raw HR sample persistence (`SensorSample` table)
* ingestion
* validation
* signal quality
* replay
* related persistence infrastructure
* real sensor transport / BLE (only after the Polar H10 and transport items in `ARCHITECTURE.md` are verified)

## Phase 3

Interval engine:

* protocol
* phases
* state machine
* zones
* timing
* events

## Phase 4

Real-time monitoring:

* WebSocket
* live UI
* graph
* session control

## Phase 5

Audio engine:

* event-driven audio
* configurable warnings
* three-beep warning

## Phase 6

Session analytics:

* HR metrics
* time in zone
* time-to-target
* recovery metrics
* session summary

## Phase 7

Field VO₂max framework:

* protocols
* validated equations
* coach UI
* provenance

## Phase 8

CPET import:

* CSV/XLSX
* mapping
* QC
* visualization
* synchronization

## Phase 9

Calibration:

* deterministic calibration
* validation
* versioning
* before/after comparison

## Phase 10

Personalization:

* physiological profile
* personalized zones
* calibrated VO₂max
* provenance

## Phase 11

Reporting/export.

## Phase 12

Security/privacy/hardening.

## Phase 13

Full integration testing.

## Phase 14

Documentation and release preparation.

---

# 58. IMPLEMENTATION RULE

At the beginning of each phase:

1. Read relevant documentation.
2. State what will be implemented.
3. Identify dependencies.
4. Implement only that phase.
5. Run tests.
6. Fix failures.
7. Update documentation.
8. Summarize changes.
9. Commit changes if Git is available.

Do not silently jump several phases ahead.

---

# 59. GIT DISCIPLINE

Use meaningful commits.

Examples:

```text
docs: define project architecture
feat: add heart rate sensor abstraction
feat: implement interval state machine
feat: add live session websocket
feat: add field test framework
feat: add CPET import pipeline
feat: add deterministic calibration
feat: add personalized profile
test: add interval engine coverage
```

Do not commit secrets or real physiological data.

---

# 60. MASTER DOCUMENTS

The following files are authoritative project documents:

```text
docs/MASTER_PROMPT.md
docs/ARCHITECTURE.md
docs/SCIENTIFIC_SPECIFICATION.md
docs/DATA_MODEL.md
docs/API_SPECIFICATION.md
docs/UI_SPECIFICATION.md
docs/TESTING_STRATEGY.md
docs/FUTURE_ML.md
```

Also preserve:

```text
docs/REPOSITORY_AUDIT.md
docs/IMPLEMENTATION_PLAN.md
```

Do not delete audit information merely because implementation begins.

(Note: neither file is currently present in the repository and neither is to be fabricated; see `SPECIFICATION_REVIEW.md`. `SPECIFICATION_REVIEW.md` and `README_SCOPE_REVIEW.md` are additional project documents.)

---

# 61. DOCUMENTATION-FIRST REQUIREMENT

Before significant implementation:

### MASTER_PROMPT.md

Must contain the authoritative scope and engineering rules.

### ARCHITECTURE.md

Must describe:

* components
* layers
* data flow
* real-time flow
* sensor abstraction
* UI/backend boundary
* future ML boundary

### SCIENTIFIC_SPECIFICATION.md

Must describe:

* formulas
* units
* assumptions
* field protocols
* calibration methodology
* limitations
* references
* unresolved scientific questions

### DATA_MODEL.md

Must describe:

* entities
* relationships
* provenance
* versions
* measured/estimated/calibrated distinctions

### API_SPECIFICATION.md

Must describe:

* endpoints
* schemas
* WebSocket messages
* errors
* authentication boundary if applicable

### UI_SPECIFICATION.md

Must describe:

* coach dashboard
* live athlete interface
* session summary
* field-test UI
* CPET calibration UI
* personal profile

### TESTING_STRATEGY.md

Must describe:

* unit testing
* integration testing
* property testing
* replay testing
* scientific validation
* data quality tests

### FUTURE_ML.md

Must describe future ML possibilities only.

No ML implementation.

---

# 62. IMPORTANT SCIENTIFIC BOUNDARY

The system is a sports-performance and research software project.

Do not present it as:

* a medical device
* a diagnostic system
* a replacement for clinical testing
* a system guaranteeing athletic performance

Until independently validated, use appropriate language such as:

* software estimate
* field estimate
* laboratory reference
* calibration
* research prototype
* training assistance

---

# 63. CURRENT PROTOTYPE

There is an existing conceptual/interactive prototype demonstrating:

* HR-based interval visualization
* target zones
* HRmax reference
* actual vs planned HR
* work/rest phases
* simulated HR
* manual HR
* configurable speed
* audio events

Treat the prototype as a product/design reference.

Do not assume prototype code is production-ready.

If prototype source code is not actually present in the repository, do not recreate undocumented implementation details as if they already existed.

---

# 64. NO FAKE COMPLETION

The project documentation may describe future tests and planned validation.

Do not claim that planned tests have already been performed.

In particular:

* planned field tests are not completed field tests
* planned CPET calibration is not completed calibration
* synthetic data is not real athlete data
* conceptual charts are not experimental results
* planned validation is not validation evidence

---

# 65. CURRENT SCIENTIFIC STATUS

The system is intended to eventually support:

```text
Polar/HR sensor
       ↓
Training execution
       ↓
Field VO₂max
       ↓
CPET reference
       ↓
Calibration
       ↓
Personalized VO₂max
       ↓
Personalized physiological profile
```

The long-term goal is to make the system increasingly personalized.

However, the current implementation must remain deterministic and scientifically transparent.

---

# 66. ARCHITECTURE FOR FUTURE EXTENSION

Design interfaces so future systems can be added without rewriting the core.

Examples:

```text
SensorProvider
TrainingEngine
PhysiologyCalculator
FieldTestProtocol
CalibrationMethod
ProfileProvider
AnalyticsProvider
```

Future ML may eventually implement some interfaces, but the current implementation must use deterministic implementations.

Do not create fake ML classes.

---

# 67. DO NOT OVER-ENGINEER

Do not introduce:

* microservices
* Kubernetes
* distributed event streaming
* complex cloud infrastructure
* ML platforms
* unnecessary message brokers

unless a demonstrated requirement exists.

Start with:

```text
modular monolith
+
PostgreSQL
+
FastAPI
+
React/TypeScript
+
WebSocket
```

Keep boundaries clean so the architecture can evolve later.

---

# 68. REQUIRED FIRST ACTION

Before writing application code:

1. Inspect the entire repository.
2. Read:

   * `README.md`
   * `docs/REPOSITORY_AUDIT.md`
   * `docs/IMPLEMENTATION_PLAN.md`
   * all current `docs/*.md`
3. Identify inconsistencies.
4. Do not silently resolve scientific conflicts.
5. Update the documentation where appropriate.
6. Produce a clear architecture/specification baseline.
7. Stop before major implementation if important scientific or product decisions remain unresolved.

---

# 69. MASTER PROMPT V2 ACCEPTANCE CRITERIA

Before implementation begins, confirm that the repository has:

* [ ] clear project scope
* [ ] explicit ML exclusion
* [ ] architecture
* [ ] scientific specification
* [ ] data model
* [ ] API specification
* [ ] UI specification
* [ ] testing strategy
* [ ] future ML boundary
* [ ] privacy rules
* [ ] provenance rules
* [ ] sensor abstraction
* [ ] interval state machine specification
* [ ] CPET import specification
* [ ] calibration lifecycle
* [ ] personalization model
* [ ] field-test framework
* [ ] implementation roadmap

If any of these are missing, do not pretend the specification is complete.

---

# 70. FINAL EXECUTION RULE

Your behavior must follow this order:

```text
READ
 ↓
AUDIT
 ↓
RECONCILE DOCUMENTS
 ↓
SPECIFY
 ↓
DESIGN
 ↓
TEST PLAN
 ↓
IMPLEMENT ONE PHASE
 ↓
TEST
 ↓
DOCUMENT
 ↓
COMMIT
 ↓
NEXT PHASE
```

Never:

```text
PROMPT
 ↓
GENERATE ENTIRE APPLICATION
```

The project must be built incrementally.

---

# 71. IMMEDIATE TASK FOR THIS PROMPT

For this invocation, DO NOT immediately build the entire application.

Instead:

### Step A

Read the existing repository and all documentation.

### Step B

Compare the current documents with this Master Prompt.

### Step C

Update:

```text
docs/MASTER_PROMPT.md
docs/ARCHITECTURE.md
docs/SCIENTIFIC_SPECIFICATION.md
docs/DATA_MODEL.md
docs/API_SPECIFICATION.md
docs/UI_SPECIFICATION.md
docs/TESTING_STRATEGY.md
docs/FUTURE_ML.md
```

with a coherent specification derived from this Master Prompt.

### Step D

Preserve:

```text
docs/REPOSITORY_AUDIT.md
docs/IMPLEMENTATION_PLAN.md
```

unless a factual correction is required.

### Step E

Do NOT:

* implement ML
* install ML dependencies
* invent scientific equations
* invent Polar APIs
* create fake athlete data
* create fake CPET results
* claim validation has occurred
* build the entire application yet

### Step F

At the end, report:

1. files changed
2. files created
3. unresolved scientific questions
4. unresolved product questions
5. architecture decisions
6. dependencies proposed
7. implementation risks
8. recommended next implementation phase

Then STOP.

Do not proceed to Phase 1 until explicitly instructed.

---

# 72. DEFINITION OF SUCCESS FOR THIS INVOCATION

The immediate goal is NOT a working application.

The immediate goal is:

> **Create a coherent, technically rigorous, scientifically transparent, implementation-ready specification for Interval Assistance.**

Once that specification is reviewed and accepted, implementation can begin phase by phase.

END OF MASTER PROMPT V2
