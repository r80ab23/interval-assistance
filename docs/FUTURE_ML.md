# Future ML — Interval Assistance

> **NOT IMPLEMENTED. NOT IN SCOPE FOR THE CURRENT IMPLEMENTATION.**
> This document describes future possibilities and data requirements only. It contains no design commitments, no model choices, no code, and no dependency requirements. The repository must not require any ML package (`MASTER_PROMPT.md`, Sections 2 and 32).

**Phase 1 note (approved decision):** Phase 1 contains no ML and no ML-specific dependency, table, endpoint, UI element or class; repository guards (see `TESTING_STRATEGY.md`) check that no ML package is introduced. The word "predicted" in the origin category `predicted_by_formula` (HRmax/HRrest) refers to a deterministic formula that is not yet approved; it is unrelated to the reserved future value kind `predicted` below. The README's "Machine learning" contribution item and learning/retraining language are scope drift listed in `README_SCOPE_REVIEW.md`.

---

## 1. Current position

The present system is deterministic and scientifically transparent: explicit formulas, rules, measurements, field-test equations (once approved), deterministic calibration and deterministic personalization. Nothing below is built, stubbed or scaffolded.

Explicitly **not** present now: ML training, neural networks, predictive ML, online learning, reinforcement learning, model registries, automatic retraining, ML inference, athlete clustering, deep learning, automatic feature learning, ML-based VO₂max prediction. No placeholder or "fake" ML classes may be added (Master Prompt Section 66).

---

## 2. Possible future applications (Master Prompt Section 32)

For discussion only; none is planned, scheduled or validated:

- Personalized VO₂max estimation
- Physiological response prediction
- Recovery prediction
- Dynamic zones
- Interval performance prediction

Whether any of these would be scientifically justified or better than the deterministic methods is **UNKNOWN**. Any future ML method would have to be compared against the deterministic baseline and would need its own validation.

---

## 3. Data that could eventually be relevant

- Longitudinal HR data (Polar/other sensors), with signal-quality metadata
- CPET reference data (laboratory measured)
- Field-test data and inputs
- Calibration history (candidates, results, states)
- Recovery metrics
- Interval execution data (planned vs observed, events)

The current data model is designed so these exist as raw, provenance-tracked, versioned records. That is a property of good record keeping, not an ML implementation.

---

## 4. Prerequisites that would have to be met first

None of these is satisfied today.

1. **Real, consented, sufficient data.** Quantity and diversity required are **UNKNOWN**. No real athlete or CPET data are in the repository, and none may be fabricated. Synthetic data cannot substitute for real data in any claim about model quality.
2. **Consent and legal basis for secondary use** of physiological data for model development (jurisdiction UNKNOWN), including retention and withdrawal.
3. **Privacy design** for training data: pseudonymization, access control, data-minimization, storage outside the public repository.
4. **Data-quality labels.** Signal-quality and QC outcomes must be usable to include/exclude records.
5. **Leakage-aware evaluation design.** Records from the same athlete are correlated; evaluation would need to be defined so that results are not inflated (for example evaluation on athletes not seen in development). Method selection is a future scientific decision.
6. **A deterministic baseline** (calibrated or personalized deterministic estimate) to compare against.
7. **Independent reference measurements** (CPET) for supervised targets; the number of matched field/lab pairs per athlete is expected to be small, which is a fundamental constraint (UNKNOWN until real data exist).
8. **Scientific and regulatory review** of intended claims. Wording must not become medical or diagnostic.

---

## 5. Where ML could connect (boundaries only)

| Existing boundary | Possible future relationship |
|---|---|
| `CalibrationMethod` interface | An alternative method could implement the same interface, taking provenance-tracked estimate/reference observations and returning a typed result. |
| `ProfileProvider` / personalization | A future provider could supply personalized estimates, with the same provenance fields and a label distinguishing it from deterministic personalization. |
| `AnalyticsProvider` | Could add derived features or predictions as separate, labelled outputs. |
| `PhysiologyCalculator` | Could host a future alternative estimator behind the same typed interface. |
| Data layer | Versioned, provenance-tracked raw data and processing runs are the natural source for future dataset snapshots. |

These are extension points that already exist for non-ML reasons (the Master Prompt requires the interfaces). No ML-specific table, field, queue, endpoint or UI exists now.

---

## 6. Rules for any future ML work (guardrails to carry forward)

1. **Separate phase and explicit approval.** ML is introduced only after a new, approved specification; it is not an incremental change to the current phases.
2. **Never overwrite** raw, measured, field-estimated, calibrated or deterministic values with predicted ones.
3. **A new value kind** (for example `predicted`) would be added at that time and shown distinctly in the UI and API; it must never be presented as measured or as a laboratory result.
4. **Full provenance** for every prediction: model identifier and version, training-data snapshot reference, parameters, software version, inputs, timestamp.
5. **No online learning** that changes behavior without review; any model update is a versioned, reviewed release.
6. **Uncertainty and applicability** must be reported according to a validated method, not invented confidence percentages.
7. **Fallback** to deterministic methods must always remain available.
8. **No real athlete data** in the repository for development; synthetic data labelled as synthetic.
9. **No performance claims** without independent validation.

---

## 7. Open questions (for a future decision, not now)

1. Is there a scientific case that ML improves on the deterministic calibration/personalization for this use?
2. How much real, consented data could be collected, and over what period?
3. Who owns and governs a future model and its training data?
4. What validation design would be acceptable for sports-performance claims?
5. Would a model registry be needed at all, or are simple versioned artifacts sufficient?
