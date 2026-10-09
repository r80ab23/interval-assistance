# Scientific Specification — Interval Assistance

**Status:** DRAFT baseline derived from `MASTER_PROMPT.md` (V2). Research prototype. Not independently validated. Nothing here constitutes validation evidence, and no validation, field test, CPET calibration or athlete study has been performed.

**Rule (MANDATED):** no equation, reference, threshold or sample-size requirement is invented. Where something is not defined by the Master Prompt or an approved source, it is marked below.

| Marker | Meaning |
|---|---|
| **DEFINITION** | A definition or identity given in the Master Prompt, or a pure arithmetic/dimensional identity. |
| **REQUIRES SCIENTIFIC VERIFICATION** | Plausibly standard, but no approved reference is in the repository. Must be cited and approved before implementation. |
| **UNSPECIFIED** | A parameter or method that has not been chosen. Implementation is blocked until it is. |
| **UNKNOWN** | Not known; must not be assumed. |

**Reference register:** *empty.* No scientific reference has been approved for this repository. Entries are added only with full citation and a note on which calculation they support. References must not be added from memory.

**Intended language:** *software estimate, field estimate, laboratory reference, calibration, research prototype, training assistance.* The system is not a medical device, makes no diagnostic claims and is not a replacement for clinical testing.

---

## 1. Value taxonomy

Raw, measured, estimated, calculated, calibrated and personalized values are different things and are stored and displayed separately (definitions in `ARCHITECTURE.md` Section 8).

Key separations:

- `field_estimated_vo2max` (field test) is never labelled a laboratory measurement.
- `laboratory_measured_vo2max` is what the laboratory reported, with its reporting conventions recorded (Section 9.4).
- `uncalibrated_estimate` and `calibrated_estimate` coexist; the original estimate is never overwritten.

---

## 2. Heart-rate quantities and notation

| Symbol | Meaning | Unit | Origin |
|---|---|---|---|
| HR | Heart rate | beats per minute (bpm) | measured by sensor or manual |
| HRrest | Resting heart rate | bpm | stored with origin and protocol |
| HRmax | Maximal heart rate used for zones | bpm | stored with origin |
| HRR | Heart-rate reserve | bpm | calculated |

**Origin of HRmax / HRrest (REQUIRED metadata):** each stored value records how it was obtained. Proposed categories: `measured_in_test`, `observed_in_session`, `entered_by_coach`, `predicted_by_formula`. **No age-based prediction formula is specified or approved**; none may be applied by default (REQUIRES SCIENTIFIC VERIFICATION if ever added). **HRrest protocol** (posture, duration, time of day) is UNSPECIFIED; the origin record should capture whatever the coach states.

---

## 3. Target and zone definitions

### 3.1 Heart-rate reserve — DEFINITION

```text
HRR = HRmax − HRrest
```

Valid only when HRmax > HRrest and both are within configured plausibility limits (limits UNSPECIFIED).

### 3.2 Intensity modes

| Mode | Target (bpm) | Status |
|---|---|---|
| Absolute BPM | `target = T` (coach-entered) | DEFINITION |
| %HRmax | `target = (p / 100) × HRmax` | DEFINITION (p = percent) |
| %HRR (Karvonen-style) | `target = HRrest + (p / 100) × HRR` | The Master Prompt calls for the "standard HRR/Karvonen-style calculation where scientifically appropriate". Formula as written is the commonly used form. **Citation REQUIRED before implementation**, and applicability limits recorded. |
| %VO₂max | none | **Not specified.** See 3.3. |
| Manual zone | coach gives lower, upper and target | DEFINITION; overrides derived values where configured |

### 3.3 %VO₂max mode

The Master Prompt forbids inventing a universal HR↔VO₂ relationship. Consequently:

- **No generic mapping is defined here.** The mode is declared in the data model and UI as *unavailable until an approved mapping is specified*.
- Any future generic mapping must be labelled an approximation (kind `estimated`, flagged `approximation`), carry a source and applicability limits, and be versioned.
- The architecture must allow an athlete-specific relationship later (`personalization`), derived from that athlete's own data. How such a relationship would be derived is UNSPECIFIED.
- UNKNOWN: whether a time-aligned HR/VO₂ relationship from CPET will be used for this (see Section 12).

### 3.4 Zone construction from a tolerance — DEFINITION (from Master Prompt example)

With a symmetric tolerance `tol`:

```text
lower = target − tol
upper = target + tol
```

Example in the Master Prompt: target 165, tol ±3 → lower 162, upper 168.

UNSPECIFIED: tolerance units (absolute bpm vs percent of a reference), asymmetric tolerance, rounding rules (rounding to integer bpm, rounding direction), and whether bounds are inclusive. These must be fixed before the engine is implemented and covered by tests.

### 3.5 Classification and debounce

Position is classified as `BELOW` (HR < lower), `WITHIN`, or `ABOVE` (HR > upper), with boundary inclusivity UNSPECIFIED (3.4).

The Master Prompt requires hysteresis/debounce so a single noisy sample does not cause a transition. Candidate mechanisms (none selected): require N consecutive samples; require a minimum dwell time; use a hysteresis margin around the bounds. **The mechanism and its parameters are UNSPECIFIED.** Whichever is chosen must be documented here with rationale, configurable with an approved default, and recorded in every session's provenance (so historical sessions remain interpretable).

---

## 4. Interval timing

All DEFINITION from Master Prompt Section 7:

- Protocol timing (work, recovery, warm-up, cool-down) is authoritative and measured on the session clock.
- HR response is measured independently. A phase is not extended or shortened because HR reached or missed the target.
- `time_to_target`: elapsed time from phase start to target entry; recorded as an analytical metric.
- If the target is never reached in a phase, that is **recorded** (not-reached outcome), not hidden or replaced by a number.

UNSPECIFIED: the exact definition of "target reached" for `time_to_target` (first WITHIN sample vs first debounced WITHIN entry), and how paused time is counted (`ARCHITECTURE.md` Section 6).

---

## 5. Signal validation and quality

States (MANDATED): `UNKNOWN, GOOD, ACCEPTABLE, POOR, INVALID, STALE, MISSING`.

Conditions to detect (MANDATED): impossible HR, malformed sample, duplicate timestamps, invalid timestamps, stale samples, missing samples, implausible jumps, gaps, out-of-order timestamps.

**All numeric thresholds are UNSPECIFIED**: HR plausibility bounds, maximum plausible change between samples, stale timeout, gap length, and the rules that separate GOOD / ACCEPTABLE / POOR. They must be set as named, versioned configuration with an approved default and a rationale (or declared as project-defined conventions, not physiological claims). The sampling behavior of the Polar H10 is UNVERIFIED.

Corrections: none are silent. Any correction/interpolation records original value, corrected value, method, timestamp, reason and processing version. Whether any correction method is allowed at all in the first implementation is OPEN; the safe default is **flag, do not repair**.

### 5.1 Part 2a rules and configuration mechanism (decided; no values selected)

This subsection defines *structure*. It selects **no numeric value** and makes **no physiological claim**: bounds and timeouts are project-defined conventions supplied by configuration.

**Conditions and reason codes** (nine MANDATED conditions mapped to codes):

| Component | Code | Meaning (structural) |
|---|---|---|
| Validation (per sample) | `malformed_sample` | a value or payload was delivered but the value is null or not a finite number (NaN, +Infinity and -Infinity are preserved by class as stored and are always `malformed_sample`; they are never treated as a number out of range) |
| Validation | `missing` | a delivery carried neither a value nor a payload |
| Validation | `impossible_hr` | value finite but outside the configured `[hr_min_bpm, hr_max_bpm]` |
| Validation | `invalid_timestamp` | `device_timestamp` present but naive (not timezone-aware). A timezone-aware value in any offset is valid: it is normalized to UTC with its instant preserved. No other timestamp validity rule is defined |
| Signal quality (stateful) | `duplicate_timestamp` | timestamp equal to the previous sample's |
| Signal quality | `out_of_order_timestamp` | timestamp earlier than the previous sample's |
| Signal quality | `implausible_jump` | absolute change from the previous *validation-passing* sample's value exceeds `max_jump_bpm` |
| Signal quality | `gap` | closed range: time between consecutive samples' `received_at` exceeds `gap_after_seconds` |
| Signal quality | `stale` | open range: at an explicitly supplied evaluation time, age of the latest `received_at` exceeds `stale_after_seconds` |

Timestamp checks use `device_timestamp` when present and valid, otherwise `received_at`; comparisons use the normalized UTC instants. A sample with no previous sample has no stateful findings.

**State assignment.** Any validation finding gives `INVALID` (fixed, not configurable). Signal-quality codes map to states through the configuration's `state_by_reason`. A sample or range with several findings takes the highest-precedence state in the fixed order `INVALID > MISSING > STALE > POOR > ACCEPTABLE > GOOD > UNKNOWN` (a project convention for aggregation, not a physiological ordering). With no findings the state is the configuration's `no_findings_state`. The criteria that would separate `GOOD`, `ACCEPTABLE` and `POOR` beyond this reason-code mapping remain UNSPECIFIED.

**`stale` persistence.** Evaluation is a pure function of an explicit `now`. The close-time `stale` range is owned by the recording session's processing run (`DATA_MODEL.md` 2.2). A `stale` range is persisted only when a recording session is closed and its last sample is older than `stale_after_seconds` at the closing time (open range ending at that time). If samples resume, the interval is recorded as a closed `gap` instead.

**Versioned configuration.** A `SignalQualityConfig` has: `config_id`, `config_version`, `hr_min_bpm`, `hr_max_bpm`, `max_jump_bpm`, `stale_after_seconds`, `gap_after_seconds`, `state_by_reason` (for the five signal-quality codes) and `no_findings_state`. **Every field is required and has no default in code**; `hr_min_bpm` must be below `hr_max_bpm`. The configuration is loaded from a file referenced by settings. Its SHA-256 over the canonical serialization defined in 5.1.1 is its identity: a `(config_id, config_version)` pair is immutable, and presenting different content under an existing pair is an error. Each recording session records the id, version and hash in force, and each `processing_run.parameters` stores the complete validated hashed document defined in 5.1.1 (including the `format` tag), so the hash can be recomputed from the stored snapshot. Any change to a value requires a new `config_version`; any change to a rule requires a new `method_version`.

#### 5.1.1 Configuration identity: canonical serialization (decided)

This fixes only how a validated configuration becomes bytes for hashing. It selects no threshold and changes no signal-quality policy.

1. **Hashed document.** The hashed document is a JSON object holding exactly these keys: `format` (the constant string `"signal-quality-config/1"`), `config_id`, `config_version`, `hr_min_bpm`, `hr_max_bpm`, `max_jump_bpm`, `stale_after_seconds`, `gap_after_seconds`, `state_by_reason` and `no_findings_state`. `state_by_reason` is an object with exactly the five keys `duplicate_timestamp`, `out_of_order_timestamp`, `implausible_jump`, `gap`, `stale`. Every key is required. **Unknown keys are an error** (otherwise two different sources could share one hash). A source file may carry `format`, but if present it must equal the constant. Nothing else participates: not the file path, file bytes, comments, whitespace or key order of the source.
2. **Value types.** `config_id` and `config_version` are strings matching `^[A-Za-z0-9._-]{1,64}$`. The five numeric fields are finite JSON numbers read as IEEE-754 binary64; booleans, strings, NaN and ±Infinity are rejected. `state_by_reason` values and `no_findings_state` are one of the seven state names exactly as written in Section 5 (`UNKNOWN`, `GOOD`, `ACCEPTABLE`, `POOR`, `INVALID`, `STALE`, `MISSING`). **Non-finite numbers are never serialized**: they fail validation before hashing.
3. **Format and encoding.** RFC 8259 JSON text, UTF-8 without a byte order mark, no whitespace outside strings, no trailing newline. Because every string value is restricted to ASCII letters, digits and `.` `_` `-` `/`, no string escaping is ever needed.
4. **Key order.** Object keys are sorted ascending by Unicode code point at every level. There are no arrays.
5. **Number representation (normative).** Let `x` be a configuration number as a binary64 value. Steps (a) to (c) fully define the text; there is no other rule.
   - **(a) Parsing.** A numeric literal in a source is converted to binary64 by IEEE-754 round-to-nearest, ties-to-even, for decimal and integer literals alike. An integer literal above 2^53 is therefore rounded to the nearest representable binary64 (ties to even) and is not rejected. A literal whose magnitude rounds to infinity is non-finite and is rejected (item 2). A literal that rounds to zero is zero.
   - **(b) Digit selection.** For nonzero `x`, apply to `|x|` the digit selection of ECMA-262 `Number::toString`, that is, its choice of integers `n`, `k`, `s`: `k >= 1`, `10^(k-1) <= s < 10^k`, the binary64 obtained by converting `s x 10^(n-k)` (round-to-nearest, ties-to-even) equals `|x|`, and `k` is as small as possible (so `s` is not divisible by 10). If more than one `s` satisfies this for that minimal `k`, choose the `s` for which `s x 10^(n-k)` is closest in value to `|x|`; if two are exactly equally close, choose the even `s`. That closest-then-even choice is part of the ECMA-262 selection itself, not a second algorithm. Only the selection of `n`, `k`, `s` is used; ECMA-262's string construction, which can use exponent notation, is **not** used. If this paragraph and the ECMA-262 text ever differ, the ECMA-262 selection governs and this document must be corrected.
   - **(c) Plain positional rendering.** Zero of either sign is written `0`. Otherwise let `d` be the `k` decimal digits of `s`. If `n >= k`, write `d` followed by `n-k` zeros. If `0 < n < k`, write the first `n` digits, then `.`, then the remaining `k-n` digits. If `n <= 0`, write `0.`, then `-n` zeros, then `d`. For `x < 0`, prefix `-` to the rendering of `|x|`. There is never an exponent or a `+` sign, and because `s` is not divisible by 10 there are no trailing zeros after a decimal point and no trailing `.`. Integral-valued floats have no fractional part, so `100` and `100.0` serialize identically and share one hash (intended).
   - **Why an informal algorithm is insufficient.** "Try the nearest `k`-digit decimal for increasing `k` until it round-trips" is not equivalent to (b). The set of decimals that round-trip is the rounding interval around `x`, and at a power of two that interval is asymmetric (half as wide below `x` as above). A `k`-digit decimal on the wider side can round-trip while the nearest `k`-digit decimal, on the narrower side, does not, so the informal method emits one digit too many. In one check, this happened for 46 of the 2098 positive powers of two (for example `2^-1017`, where (b) gives `7120236347223045` with `k = 16`, `n = -306`, while the informal method gives 17 digits, `71202363472230444`). Separately, several `k`-digit strings can round-trip at once (for `5e-324` the one-digit strings `3e-324` to `7e-324` all do), so the closest-value rule is required, not optional.
   - **Informative only.** Taking the digits of Python's `repr(float(x))` and rendering them with `format(Decimal(...), "f")` gives the same text on every vector below and on every case the authors compared, but it is a convenience, not the definition. Implementations must be validated against (a) to (c).
6. **Hash.** SHA-256 over the UTF-8 bytes of that text, recorded as 64 lowercase hexadecimal characters with no prefix (`signal_quality_config_hash`).
7. **Immutability.** The same `(config_id, config_version)` with the same hash is accepted (idempotent). The same pair with a different hash is a `ConfigurationError`. Any value change requires a new `config_version`.
8. **Unchanged by this section.** Source-file format and the settings key that locates it are not part of the identity: any source that yields the same validated values yields the same hash. They remain an implementation choice to be recorded with the loader. Value-range rules beyond `hr_min_bpm < hr_max_bpm` are not defined here.

**Compatibility consequences.** (a) This is intentionally simpler than RFC 8785 (JCS): it differs for numbers whose JCS form uses an exponent, so these hashes will not match a JCS implementation. Practical thresholds are unaffected, but a later move to JCS would need a new `format` tag. (b) The `format` tag is hashed, so any future change to these rules must change the tag; old hashes then stay verifiable under the old rules. (c) The identifier pattern restricts `config_id` and `config_version`; no configuration exists yet, so nothing breaks.

**Test vector** (a labelled test convention, not a physiological claim, and not a recommended configuration). Canonical text (354 bytes):

`{"config_id":"example-test-config","config_version":"1","format":"signal-quality-config/1","gap_after_seconds":7,"hr_max_bpm":20,"hr_min_bpm":10,"max_jump_bpm":5,"no_findings_state":"GOOD","stale_after_seconds":3.5,"state_by_reason":{"duplicate_timestamp":"POOR","gap":"MISSING","implausible_jump":"POOR","out_of_order_timestamp":"POOR","stale":"STALE"}}`

SHA-256: `b7f6ab26ad1f4cf4792f7378859d79b36ea7d705134e46d0a35f1dc2cb53eb08`

Number vectors (input to canonical text): `100` → `100`; `100.0` → `100`; `0.1` → `0.1`; `1.5` → `1.5`; `-0.0` → `0`; `-3.0` → `-3`; `1e-7` → `0.0000001`; `2.5e-5` → `0.000025`; `1e21` → `1000000000000000000000`; `123456789.125` → `123456789.125`.

Extreme-value vectors (the output text is given by its structure and the SHA-256 of its exact UTF-8 bytes):
- Smallest positive subnormal, input `5e-324` (`n = -323`, `k = 1`, `s = 5`): the text is `0.` followed by 323 zeros followed by `5` (326 characters). SHA-256 `90620a380b105dc799edca0bcb5c167ec1a00ff0fd1cd5f577593725fafb476d`.
- Largest finite binary64, input `1.7976931348623157e308` (`n = 309`, `k = 17`, `s = 17976931348623157`): the text is `17976931348623157` followed by 292 zeros (309 characters). SHA-256 `9a8a48349f1f23a94cc13b2f7dd1a5cb791c6cb8912f77cb425eca0f4f9b5a73`.
- Power-of-two asymmetry case, input `2^-1017` (the double written `7.120236347223045e-307`; `n = -306`, `k = 16`, `s = 7120236347223045`): the text is `0.` followed by 306 zeros followed by `7120236347223045` (324 characters). SHA-256 `ed157d6d5c5a705a0c030f0d7d47d6ab7ccf44fc34131e06d158e6794a43889a`.
- Powers of ten: `1e22` (exactly representable) → `10000000000000000000000`; `1e23` (the nearest double lies slightly below `10^23`, yet the selection still gives `k = 1`, `s = 1`, `n = 24`) → `100000000000000000000000`.

These vectors are examples, not a proof of conformance. An implementation should also be cross-checked against an independent exact implementation of (b) over all 2098 positive powers of two and a large random sample of finite doubles.

**Configuration values.** Tests use explicitly labelled test configurations ("test convention, not a physiological claim"). A configuration for real use needs the project owner's approval with a rationale. That approval is OPEN and blocks use with real athlete data, **not** implementation.

---

## 6. Session analytics

General rules (MANDATED): each metric states when it is unavailable; no fake or substituted values; a metric is not calculated when required data quality is insufficient. Each metric returns either a value (with kind `calculated`, unit and provenance) or an `unavailable` result with a reason code (for example `insufficient_samples`, `poor_signal_quality`, `phase_not_reached`, `method_not_specified`).

| Metric | Definition | Status |
|---|---|---|
| Mean, median, min, max HR; HR range | Standard descriptive statistics over valid samples in the chosen window | DEFINITION (inclusion rules for samples of each quality state UNSPECIFIED) |
| Peak HR | Maximum valid HR in window | DEFINITION (note: sensitive to artifacts; relies on quality rules) |
| Time in / below / above target | Duration spent in each classification | Weighting method UNSPECIFIED (e.g. sample-and-hold vs interval-between-samples); gaps must not be counted as in-zone |
| Time-to-target | See Section 4 | Partly UNSPECIFIED |
| Target-entry / exit time | Times of debounced transitions | Depends on 3.5 |
| Overshoot / undershoot | Excursion beyond upper / lower bound | Exact definition (maximum excess in bpm? duration? per phase?) UNSPECIFIED |
| HR at 30 / 60 / 120 s after phase end (recovery) | HR at specified offset from end of the work phase | Reference-point definition, tolerance for nearest sample, and required recovery posture/activity context UNSPECIFIED |
| Recovery slope | Rate of HR change during recovery | Method (e.g. which window and fit) UNSPECIFIED; REQUIRES SCIENTIFIC VERIFICATION |
| HR drift, decoupling-related metrics | — | **Not defined.** Calculated only "where scientifically justified" (Master Prompt). REQUIRES SCIENTIFIC VERIFICATION; deferred. Drift is a signal influenced by heat, hydration, fatigue and other factors; it is not a diagnosis. |

**Scores** (for example interval quality or execution score) mentioned in the README have no formula and are **not part of this specification**. They may be added only after a method is defined, versioned and approved.

Session summary (MANDATED, Section 18) separates **planned** (from protocol), **observed** (raw/validated data) and **calculated** (derived metrics).

---

## 7. Units (MANDATED handling; canonical choices PROPOSED)

Units are normalized at ingestion boundaries; conversions are explicit, versioned and tested; unit errors raise `UnitConversionError`.

| Quantity | Canonical unit (PROPOSED) | Notes |
|---|---|---|
| HR | bpm | |
| Time | seconds | minutes only for display/input |
| VO₂, VCO₂ (absolute) | L/min | mL/min accepted at import with explicit conversion |
| VO₂ (relative to body mass) | mL/kg/min | requires body mass; mass value, date and origin must be recorded with the conversion |
| VE | L/min | BTPS/STPD reporting convention is UNKNOWN per source; record what the file states, do not assume |
| RER | dimensionless | Defined as VCO₂ / VO₂ (DEFINITION); stored as imported and checked against recomputation if both present |
| Speed, grade, workload | **UNSPECIFIED** | Units depend on the laboratory file (for example km/h vs m/s, percent vs degrees, watts). Recorded per source. |

Dimensional identity (DEFINITION): relative VO₂ in mL/kg/min = absolute VO₂ in L/min × 1000 / body mass in kg.

---

## 8. Field VO₂max testing framework

**No field protocol and no field-test equation is approved or specified.** The framework is defined; protocol content is not.

Candidate families named in the Master Prompt: Yo-Yo-related protocols, Bruce-related protocols, other approved field protocols. Which variants, if any, are in scope is UNSPECIFIED.

Every protocol definition must contain (MANDATED, Section 19):

protocol name; protocol version; source/reference (from the approved register); required equipment; athlete prerequisites; stage structure; workload progression; required inputs; termination criteria; calculation method; output units; limitations.

Rules:

- If a protocol's equation has not been scientifically specified and approved, the protocol exists as a framework entry with status `EQUATION NOT SPECIFIED` and **cannot produce a result**.
- Test fixtures for a calculation come only from worked examples in the approved source, never from invented numbers. Synthetic inputs may exercise validation logic but expected scientific outputs may not be fabricated.
- Outputs are kind `estimated`, labelled "field estimate", with protocol name and version attached.
- Population and conditions in which a published equation applies are recorded as applicability limits and shown to the coach.

---

## 9. CPET / gas-analyzer import

### 9.1 Principles

- The original file is preserved unmodified and identified by a content hash.
- No manufacturer format is assumed or hard-coded without verification against real examples supplied by the project owner (none are in the repository). Import is configuration-driven.
- Parsed rows form `measured` values with a pointer back to file, sheet/row and column.

### 9.2 Canonical fields (MANDATED list)

`timestamp, VO2, VCO2, VE, HR, RER, speed, grade, workload`

### 9.3 Import features (MANDATED)

Column mapping, unit mapping, header detection, validation, missing values, duplicate rows, timestamp checks, malformed rows, sampling-irregularity detection. Mapping and unit-conversion configuration are stored, versioned and attached to every import.

### 9.4 Lab-reported conventions to capture, not infer

Averaging method (breath-by-breath vs time/breath averaged and the window), the laboratory's own VO₂max vs VO₂peak labelling, and the criteria it used, if provided. **The software does not decide whether a test achieved VO₂max.** It records what the laboratory reported. Any software-side criteria would require approved methodology (UNSPECIFIED).

### 9.5 Quality control

QC checks before calibration (MANDATED): timestamps, duplicates, missing data, impossible units, malformed values, gaps, sampling intervals, physiologically implausible values, incomplete records. Plausibility ranges and gap/sampling tolerances are UNSPECIFIED and handled as named, versioned configuration. QC results are `pass | warning | error` with reasons visible to the user; records with errors do not enter calibration.

---

## 10. Synchronization of HR sensor and gas-analyzer streams

Clocks are never assumed aligned. Supported mechanisms (MANDATED): common timestamps, session start, manual time offset, event markers. Requirements:

- The method used and the resulting offset (including sign convention, e.g. offset applied to HR stream) are recorded with the calibration dataset.
- Synchronization is a transformation recorded separately; underlying timestamps remain unchanged.
- UNSPECIFIED: automatic alignment methods, acceptable residual offset, and how offset uncertainty is reported. Errors raise `SynchronizationError`.

---

## 11. Calibration methodology

### 11.1 Starting form (MANDATED, as an engineering starting point only)

```text
calibrated_value = a × estimated_value + b
```

This is not claimed to be scientifically optimal or valid for all populations.

### 11.2 Required elements (MANDATED)

Explicit method; explicit assumptions; sufficient valid data; sample count reported; error before calibration; error after calibration; previous versions preserved; raw values never overwritten; candidate calibrations may be rejected; full provenance.

### 11.3 What is UNSPECIFIED and blocks Phase 9

1. **Unit of observation.** A VO₂max estimate and a laboratory VO₂max are each one value per test occasion, so a per-athlete calibration has one data point per matched test pair, which is very few. Alternatively the calibration could be population-level (across athletes) or based on time-aligned HR/VO₂ samples within a CPET. **Which of these is intended is not stated** and fundamentally changes data requirements and validity.
2. **Fitting method** for `a` and `b` (for example least squares, robust alternatives, constrained forms such as offset-only or scale-only when data are few). Not selected.
3. **Minimum valid observations** and conditions on their spread. The Master Prompt forbids inventing these; they must be defined from the chosen methodology.
4. **Error metrics** to report before/after (candidates include bias, mean absolute error, root-mean-square error; none selected).
5. **Validation procedure.** Evaluating a calibration on the same data used to fit it overstates its quality; an approach that avoids this (for example holding out observations) must be chosen and documented, and may be infeasible with few points. Selection UNSPECIFIED.
6. **Validity range.** Extrapolation outside the range of estimates seen during fitting must be flagged; the rule is UNSPECIFIED.
7. **Uncertainty.** No "confidence percentage" is produced. A formal confidence interval is implemented only if scientifically appropriate and with a documented method.
8. **Rule for "calibration worse than baseline"** (post-calibration error not better than pre-calibration error): the system must report it and prevent silent activation; the exact criterion is UNSPECIFIED.

### 11.4 Quality report (MANDATED content)

Number of valid observations; data quality; missingness; fit/error metrics; pre- and post-calibration error; validation status; calibration method and version.

### 11.5 Lifecycle (MANDATED states)

```text
CANDIDATE → VALIDATED → ACTIVE
CANDIDATE → REJECTED
VALIDATED → REJECTED
ACTIVE → RETIRED
```

Rules (PROPOSED unless marked): a candidate never becomes active by existing (MANDATED); activation is an explicit, recorded user action (actor, time, reason); at most one ACTIVE calibration per defined scope (scope per 11.3-1); activating a new calibration retires, never deletes, the previous one (MANDATED); retired and rejected calibrations stay queryable; each state change is logged.

Pipeline: CPET import → QC → synchronization → reference/estimate alignment → candidate → validation → before/after comparison → approval → active.

---

## 12. Personalized profile and zones

Profile fields (MANDATED, Section 30): HRrest, HRmax, HR at VO₂max (when available), field VO₂max estimate, laboratory VO₂max, calibrated VO₂max, active calibration version, HR zones, coach-defined zones, recovery metrics, HR response characteristics, history.

Each profile value stores source, timestamp, validity, method, version/provenance. Values may become stale or superseded; none is treated as permanently known.

Zone sources (MANDATED, Section 31): HRmax, HRrest, HRR, HR at VO₂max, coach-defined, validated personal calibration. **Methods for deriving personalized zones from these (and what "HR at VO₂max" means operationally, i.e. how it is read from the CPET trace) are UNSPECIFIED.** Coach overrides are allowed and auditable (who, when, previous value, new value, reason).

"Personalized" is applied only to values derived from the athlete's own validated data. Nothing is described as an individualized physiological truth.

---

## 13. Versioning and reproducibility

Every method has `method_id` and `method_version`. A change to any formula, threshold, mapping or processing step creates a new version; historical results keep the version used and remain recomputable from raw inputs. Scientific specification changes are themselves versioned (document version and date in this header when approved).

---

## 14. Unresolved scientific questions

1. Approved reference for the %HRR (Karvonen-style) formula and its applicability limits.
2. Whether any generic %VO₂max → HR mapping will be used, and if so which source; or whether the mode stays unavailable until athlete-specific data exist.
3. How athlete-specific HR↔VO₂ relationships are derived and validated.
4. HRmax and HRrest handling: allowed origins, HRrest measurement protocol, whether any predicted-HRmax formula is ever allowed.
5. Tolerance semantics: units, asymmetric tolerance, rounding, bound inclusivity.
6. Debounce/hysteresis mechanism and parameters.
7. Signal-quality thresholds and the GOOD/ACCEPTABLE/POOR criteria; whether any correction/interpolation is permitted.
8. Definitions of time-to-target, overshoot/undershoot, time-in-zone weighting, recovery reference points and recovery slope.
9. Whether and how drift/decoupling are defined.
10. Which field protocols are approved, with sources, equations, applicability limits and fixtures from published worked examples.
11. Vendor-specific CPET formats; averaging conventions; VO₂max vs VO₂peak reporting; STPD/BTPS conventions.
12. Calibration: unit of observation, fitting method, minimum data, error metrics, validation, validity range, uncertainty, "worse than baseline" criterion (Section 11.3).
13. Synchronization: automatic alignment methods and acceptable offset.
14. Personalized-zone derivation methods and the operational definition of HR at VO₂max.
15. Body-mass handling for relative VO₂ (source, date, and tolerance for staleness).
