# UI Specification — Interval Assistance

**Status:** DRAFT derived from `MASTER_PROMPT.md` (V2). Requirements and behavior only; no visual design, mockups or code yet. Frontend: React and TypeScript (MANDATED as recommended). Supporting libraries are OPEN except as decided below.

**Phase 1 scope (approved decision):** React, TypeScript, Vite and Vitest. The Phase 1 frontend is only a minimal research-prototype shell: a status/health view, a role-aware navigation boundary (roles `coach`, `athlete`, `researcher`, using the development identity; no login UI), the research-prototype notice (Section 1, rule 6) and a typed API client boundary. **No state-management library, no charting library, no WebSocket client behavior and no physiological calculations in Phase 1.** Sections 2 to 7 describe later phases. See `SPECIFICATION_REVIEW.md`.

**Labels:** MANDATED, PROPOSED, OPEN.

---

## 1. Global rules

1. **The UI never decides.** It does not calculate zones, interval state, time-in-zone, metrics, calibration or profile values. It renders what the backend returns and sends commands (MANDATED).
2. **Every physiological value shows its kind.** Measured, estimated, calculated, calibrated and personalized values are visually and textually distinguishable (for example a consistent badge and a label such as "Field estimate" or "Laboratory measured"). A field estimate is never styled or worded like a laboratory value.
3. **Unavailable is shown as unavailable.** When a metric is `unavailable`, the UI shows the reason; it never shows zero, a blank that looks like zero, or a previous value.
4. **Planned vs measured are visually distinct.** Future/planned protocol data is never drawn in a way that could be read as measured data (MANDATED, Section 12).
5. **Synthetic is obvious.** Simulator, replay and manual sessions display a persistent, unmistakable banner (for example "SYNTHETIC / SIMULATED DATA"). Synthetic data is never presented as real athlete data.
6. **Language.** Use "software estimate", "field estimate", "laboratory reference", "calibration", "research prototype", "training assistance". Never imply diagnosis, medical advice, clinical validity or guaranteed performance (MANDATED). A short research-prototype notice is available from every screen.
7. **Provenance is one interaction away** for any displayed value (method, version, inputs, time).
8. **Errors are visible and specific**: show domain error messages; never silently continue with invalid data.
9. **Accessibility (PROPOSED):** color is never the only carrier of meaning (zone status also shown by text/icon), sufficient contrast, keyboard operability for coach screens, scalable text. Targets and standards to be set in Phase 1.
10. **Responsive:** coach screens target desktop/tablet; athlete live screen must work on a phone-sized viewport (PROPOSED).

---

## 2. Coach dashboard (MANDATED content, Section 37)

Purpose: configure and supervise sessions without touching internal technical settings.

**Session configuration**

- Athlete selection and a compact athlete profile view.
- Sensor selection and sensor status (connected, signal quality state, last sample age).
- HRrest and HRmax, each showing its **origin** (measured in test, observed in session, entered by coach, predicted by formula; "predicted by formula" is a deterministic-formula origin, not ML, and no formula is approved yet); editing requires choosing the origin. No silent defaults from age formulas.
- Exercise type.
- Intensity mode: Absolute BPM, %HRmax, %HRR, %VO₂max, Manual zone. %VO₂max is disabled with an explanation while no approved mapping exists (Scientific Specification 3.3).
- Target and tolerance, with an immediate **zone preview** (lower/target/upper) obtained from the backend, not computed in the browser.
- Work duration, recovery duration, number of intervals, warm-up, cool-down.
- Completion condition (interval count, total duration, explicit protocol).
- Audio configuration (events enabled, warning pattern such as three-beep before a transition) and warning settings.
- Validation messages come from the backend (`InvalidTrainingProtocol`).

**Session control and monitoring**

- Start, pause, resume, stop; a clear "early termination" confirmation.
- Live monitoring view mirroring the athlete view plus sensor/connection and signal-quality indicators and the event log.
- Post-session summary (Section 4).

Manual zone: coach supplies lower, upper and target; the UI states that the explicit zone overrides derived values, and overrides are logged (audit).

---

## 3. Athlete live screen (MANDATED content, Sections 12 and 38)

Priority: immediate physiological information at a glance; audio carries execution so the athlete need not study the screen.

**Always visible**

- Current HR (large) with signal-quality indicator.
- Current phase (warm-up / work / recovery / cool-down / paused) and interval index (for example "3 of 8").
- Elapsed time and remaining phase time (from the backend session clock; the UI does not run its own authoritative timer, it may only interpolate between updates for display).
- Target zone with lower, upper and target values, and status: below / within / above (text plus color).
- Connection state; sensor lost/recovered notices.

**Live graph** (conceptually following the existing prototype; its source is not in the repository, so details are specified here, not copied)

- Measured HR history (solid line, from `hr_sample` messages).
- Target zone band and bounds over time, including the **planned future protocol** (visibly different style, e.g. dashed or faded, labelled "planned").
- Phase boundaries and interval boundaries.
- HRmax reference line where appropriate.
- Gaps (missing/stale/invalid signal) are drawn as gaps, not interpolated.

**Audio** (MANDATED events: work start, recovery start, target reached, target lost, upper bound, lower bound, warning, session end)

- Cues triggered by backend `event` messages and the session's audio configuration, via an audio/event abstraction; the interval engine contains no audio logic.
- Browsers restrict autoplay: the screen includes an explicit "enable sound" step with a test tone before the session starts (PROPOSED).
- Configurable warning pattern (for example three beeps before a transition).
- OPEN: screen wake-lock/keep-awake behavior during sessions; behavior when the browser tab is backgrounded.

**Simulator/manual mode (development)**

- Speed selection (1x, 5x, 20x) and manual HR entry, available only for simulator/manual sensors, always with the synthetic banner.

---

## 4. Session summary (MANDATED content, Section 18)

Displays and exports: session duration; number of intervals and completed intervals; average, median and peak HR; time in, below and above target; time-to-target (per interval, including "not reached"); recovery metrics when available; signal-quality summary; sensor information; protocol information; warnings and events.

Layout separates three groups, always labelled: **Planned** (from the protocol), **Observed** (from recorded data), **Calculated** (derived metrics with method/version). Unavailable metrics show a reason (for example insufficient samples, poor signal). Export to CSV with provenance (Phase 11).

---

## 5. Field-test UI (MANDATED content, Sections 20 and 39)

Flow:

1. Select athlete.
2. Select protocol (list shows status; protocols with `EQUATION NOT SPECIFIED` are visible but cannot be calculated, with an explanation).
3. Read protocol instructions: required equipment, prerequisites, stage structure, workload progression, termination criteria, limitations, source reference.
4. Enter required measurements and record stages/results; stage tracking.
5. Input validation (field-level messages from the backend).
6. Calculate (only for approved protocols).
7. Display the result clearly as a **field estimate** with units, protocol name and version, and applicability limits. Never described as a laboratory measurement.
8. Save with protocol version and provenance; export/report.

If a protocol's equation has not been specified, the UI offers the framework (instructions and data entry) but no result; it never shows a placeholder number.

---

## 6. CPET calibration UI (MANDATED, Section 40)

A guided workflow with 14 steps, each resumable:

1. **File upload** (CSV/XLSX); the original is stored unmodified and its hash shown.
2. **File inspection** (sheets, detected header row, preview rows).
3. **Column mapping** to canonical fields (timestamp, VO2, VCO2, VE, HR, RER, speed, grade, workload).
4. **Unit mapping** with explicit conversions shown.
5. **QC report**: errors and warnings per category with row references; errors block progress.
6. **Synchronization configuration**: method (common timestamps, session start, manual offset, event markers), offset value and sign convention; recorded.
7. **Data visualization**: laboratory series and HR series on a shared time axis, with the synchronization offset applied visibly (underlying timestamps unchanged).
8. **Reference vs estimate comparison** (laboratory measured vs field estimate).
9. **Calibration calculation** using the approved method version.
10. **Before/after error comparison**, including sample count and missingness; a clear message when calibration does not improve on baseline.
11. **Candidate review** (parameters, method, assumptions, validity range, warnings).
12. **Validation** result.
13. **Activate or reject** with required reason; confirmation that the previous active calibration will be retired, not deleted.
14. **Version history** of calibrations with state timeline.

No confidence percentage is shown (MANDATED). If the approved methodology is not yet specified, the calculation step is disabled with an explanation. A candidate calibration is never auto-activated.

---

## 7. Personal profile UI (MANDATED, Section 41)

Shows: athlete identity (pseudonym; identifying details only if stored and permitted), HRrest, HRmax, HR at VO₂max, field VO₂max (field estimate), laboratory VO₂max (laboratory measured), calibrated VO₂max (calibrated, with active calibration id and version), zones (with source: derived, personalized, coach-defined), data quality and provenance indicators, profile history (superseded values remain viewable).

Each value displays its date and validity, so stale values are recognizable. Coach overrides require a reason and appear in the history. No diagnosis, medical interpretation, or "health score" appears anywhere (MANDATED).

---

## 8. Screen inventory and navigation (PROPOSED)

Athlete list and profile; protocol list/builder; session setup; live session (coach monitor and athlete screen); session history and summary; field tests; laboratory tests and calibration workflow; calibrations list/history; reports/exports; settings (audio defaults, sensors). Login and role-based visibility follow the authorization design (OPEN).

---

## 9. Frontend architecture constraints

- React with TypeScript; a typed API client generated from or validated against the OpenAPI contract.
- State: server state is authoritative; local state limited to presentation. The WebSocket client applies `snapshot` and incremental messages, detects `seq` gaps and requests/awaits a fresh snapshot.
- No physiological formulas or state-machine logic in components. A lint/review rule and tests assert this (Testing Strategy).
- Build tool and test runner: Vite and Vitest (approved). Charting library, state library, component library: OPEN, to be chosen in the phase that first needs them, with justification and minimal dependencies.

---

## 10. Open items

1. Existing prototype source (not in repository): obtain it to document its behavior as a UX reference; until then, requirements come only from the Master Prompt.
2. BLE path (browser vs native app) affects the athlete screen platform.
3. Wake-lock and background-tab behavior.
4. Accessibility standard and target devices.
5. Localization (language support).
6. Final visual design.
