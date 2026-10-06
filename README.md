# Interval Assistance

> **A personalized physiological training assistance platform for precision interval training, real-time heart-rate guidance, and progressive VO₂max modeling.**

**Interval Assistance** is a sports technology project designed to help coaches and athletes execute interval training with greater physiological precision.

The system combines **real-time heart-rate monitoring**, configurable training protocols, tolerance-based feedback, physiological analytics, laboratory calibration data, field-test data, and progressively personalized physiological modeling.

The initial product focuses on a simple but important problem:

> **Can we help an athlete perform an interval at the intensity the coach actually prescribed — rather than simply telling them when to work and when to rest?**

The long-term vision goes further.

By combining data from heart-rate sensors such as the **Polar H10**, laboratory gas-analysis measurements, field tests, and repeated training sessions, Interval Assistance aims to build an evolving **individual physiological profile** capable of supporting personalized intensity estimation and VO₂max prediction without requiring a gas analyzer for every future assessment.

---

# Table of Contents

* [Vision](#vision)
* [The Problem](#the-problem)
* [The Core Idea](#the-core-idea)
* [Three-Layer Architecture](#three-layer-architecture)
* [Layer 1 — Real-Time Training Engine](#layer-1--real-time-training-engine)
* [Training Intensity Models](#training-intensity-models)
* [Interval Execution](#interval-execution)
* [Visual Feedback](#visual-feedback)
* [Audio Feedback](#audio-feedback)
* [Layer 2 — Physiological Analytics](#layer-2--physiological-analytics)
* [HR Kinetics](#hr-kinetics)
* [Heart-Rate Recovery Profile](#heart-rate-recovery-profile)
* [Heart-Rate Drift](#heart-rate-drift)
* [Interval Quality](#interval-quality)
* [Physiological Execution Score](#physiological-execution-score)
* [Layer 3 — Personalization Engine](#layer-3--personalization-engine)
* [VO₂max Calibration](#vo2max-calibration)
* [Personal HR → VO₂ Modeling](#personal-hr--vo2-modeling)
* [Calibration Quality](#calibration-quality)
* [Confidence Score](#confidence-score)
* [Dynamic Personalized Training Zones](#dynamic-personalized-training-zones)
* [Physiological Fingerprint](#physiological-fingerprint)
* [Athlete Physiological Profile](#athlete-physiological-profile)
* [Model Versioning](#model-versioning)
* [Field Tests](#field-tests)
* [Sensor Integration](#sensor-integration)
* [Data Architecture](#data-architecture)
* [Data Quality](#data-quality)
* [Validation Strategy](#validation-strategy)
* [Current Prototype](#current-prototype)
* [Current Status](#current-status)
* [Roadmap](#roadmap)
* [Research Directions](#research-directions)
* [Safety and Scientific Principles](#safety-and-scientific-principles)
* [Limitations](#limitations)
* [Project Goals](#project-goals)
* [Contributing](#contributing)
* [License](#license)
* [Disclaimer](#disclaimer)

---

# Vision

Interval Assistance is intended to evolve from a training assistant into a **personalized physiological intelligence layer** for sports training.

The long-term concept can be represented as:

```text
                    REAL-TIME TRAINING
                           │
                           ▼
                    Heart-Rate Data
                           │
                           ▼
                  Physiological Analytics
                           │
                           ▼
              Personal Physiological Profile
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       Laboratory Data              Field Tests
       Gas Analyzer                Training Data
             │                           │
             └─────────────┬─────────────┘
                           ▼
                 Personal Calibration
                           │
                           ▼
                Personalized Model
                           │
                           ▼
             Personalized Training Zones
                           │
                           ▼
               More Precise Training
```

The system is therefore designed around a feedback loop:

> **Measure → Analyze → Calibrate → Personalize → Train → Measure again**

---

# The Problem

A traditional interval timer answers:

> **When should I work?**

Interval Assistance is designed to answer:

> **Am I performing the work at the intended physiological intensity?**

Consider a training prescription:

```text
Work:              4 minutes
Recovery:          2 minutes
Target intensity:  85% HRR
Tolerance:         ±3%
```

A conventional timer simply counts four minutes.

Interval Assistance continuously evaluates the athlete's physiological response.

The system can determine whether the athlete is:

```text
Below target
     ↓
Within target
     ↓
Above target
```

This allows training to be evaluated according to both:

* **Time**
* **Physiological response**

---

# The Core Idea

Interval Assistance combines three types of information:

### 1. Continuous physiological data

Primarily heart-rate data from compatible sensors.

### 2. Exercise and training context

Including:

* Exercise type
* Work/rest structure
* Target intensity
* Protocol
* Duration
* Tolerance
* Training phase

### 3. Reference physiological measurements

Including:

* CPET / gas analyzer measurements
* VO₂max measurements
* Field-test results
* Repeated calibration sessions

Together, these create a much richer dataset than a simple:

```text
Heart Rate → VO₂max
```

relationship.

The intended model is closer to:

```text
Heart Rate
    +
Time
    +
Exercise Protocol
    +
Workload / Test Context
    +
Training Phase
    +
Individual History
          │
          ▼
  Physiological State
          │
          ▼
  VO₂ / Intensity Estimate
```

This distinction is fundamental to the project's long-term direction.

---

# Three-Layer Architecture

The system is conceptually divided into three major layers.

```text
┌───────────────────────────────────────────────┐
│ Layer 1                                      │
│ REAL-TIME TRAINING ENGINE                    │
│                                               │
│ Sensor → HR → Zone → Interval → Feedback    │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 2                                      │
│ PHYSIOLOGICAL ANALYTICS                      │
│                                               │
│ HR Kinetics → Recovery → Drift → Quality    │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 3                                      │
│ PERSONALIZATION ENGINE                       │
│                                               │
│ CPET + Field Tests + Sessions → Model       │
└───────────────────────────────────────────────┘
```

This architecture allows the project to begin with a practical training product while maintaining a path toward deeper physiological modeling.

---

# Layer 1 — Real-Time Training Engine

The first layer is the operational core of the product.

It receives live heart-rate data and compares the athlete's current physiological state with the coach's prescription.

## Main responsibilities

* Receive heart-rate data
* Detect work/recovery phases
* Calculate target zones
* Apply tolerance
* Monitor time
* Detect zone transitions
* Trigger audio events
* Update visualization
* Record training data

---

# Training Intensity Models

The coach should not be forced to use a single definition of intensity.

Interval Assistance is designed to support multiple methods.

## Absolute Heart Rate

```text
Target = 170 bpm
Tolerance = ±5 bpm
```

## Percentage of HRmax

```text
Target = 85% HRmax
```

## Percentage of Heart-Rate Reserve

```text
HRR = HRmax - HRrest

Target = 85% HRR
```

## Percentage of VO₂max

When the coach wants to prescribe intensity based on VO₂max, the system can use VO₂max-related intensity as the physiological reference.

Laboratory CPET measurements can serve as the gold-standard reference during calibration.

## Manual / Coach-Defined Intensity

The coach can directly define:

* Target HR
* Lower limit
* Upper limit
* Training zone
* Tolerance

This makes the system useful even when no personalized VO₂max model is available.

---

# Interval Execution

A training session can contain:

* Work intervals
* Recovery intervals
* Target intensity
* Tolerance
* Exercise type
* Session duration
* Number of intervals
* Completion criteria

The session can terminate based on:

### Designed Interval Completion

All prescribed intervals are completed.

### Time-Based Completion

The predefined total duration is reached.

This allows the same engine to support different coaching methodologies.

---

# Visual Feedback

The real-time interface is designed to show:

* Current HR
* Target HR
* Target zone
* Current zone
* Current phase
* Elapsed time
* Remaining time
* Training progress
* Actual HR history
* Expected training trajectory
* HRmax reference

The current prototype demonstrates this concept through a live interactive graph.

Conceptually:

```text
Heart Rate
    │
HRmax ─────────────────────────────────
    │
    │             Actual HR
    │          ╭──────────────╮
Target ────────┼──────────────┼────────
    │          │              │
    │          ╰──────────────╯
    │
    └────────────────────────────────── Time
              Work       Recovery
```

---

# Audio Feedback

Audio feedback is intentionally event-driven rather than continuous.

The system can provide:

### Tolerance Alerts

A beep can indicate that HR has crossed the permitted tolerance boundary.

### Work Start

Audio notification when a work phase begins.

### Recovery Start

Audio notification when recovery begins.

### Phase End

Audio notification when a phase ends.

### Transition Preparation

A three-beep sequence can warn the athlete that a work/recovery transition is approaching.

The purpose is to let the athlete train without constantly watching the screen.

---

# Layer 2 — Physiological Analytics

The second layer turns raw HR data into meaningful physiological features.

Instead of storing only:

```text
12:31:04 → 171 bpm
12:31:05 → 172 bpm
12:31:06 → 173 bpm
```

the system can derive higher-level information.

Examples include:

* HR activation response
* Time to target
* HR slope
* Peak HR
* Stabilization time
* Recovery slope
* HR drift
* Time in target
* Time above target
* Time below target
* Interval-to-interval consistency

These features can later become inputs to the personalization model.

---

# HR Kinetics

Heart rate is not just a number.

The **shape and speed of its response** to exercise can contain useful information.

For each work interval, the system can analyze:

```text
Time to 80% target
Time to 90% target
Time to target
HR slope
Peak HR
Time to stabilization
```

For example:

```text
Work begins
    │
    ▼
HR
│             ─────────
│          ╭──
│       ╭──
│    ╭──
│ ╭──
└──────────────────────── Time
```

The resulting features can become part of the athlete's physiological profile.

---

# Heart-Rate Recovery Profile

One of the most valuable features available from continuous HR monitoring is recovery behavior.

Example:

```text
End of interval: 182 bpm

30 sec → 168 bpm
60 sec → 151 bpm
120 sec → 132 bpm
```

The system can derive metrics such as:

```text
HRR30
HRR60
HRR120
Recovery slope
Recovery half-time
```

Repeated sessions can create a personalized **Heart-Rate Recovery Signature**.

The purpose is not to treat one metric as a standalone diagnostic measurement, but to track individual response patterns over time.

---

# Heart-Rate Drift

The system can monitor changes in HR response under comparable workloads or repeated intervals.

For example:

```text
Session A
HR at comparable workload = 168 bpm

Session B
HR at comparable workload = 173 bpm

Session C
HR at comparable workload = 177 bpm
```

A persistent shift may indicate a change in physiological response.

The system can flag:

> **Potential physiological response drift detected**

The next stage can then investigate context such as:

* Protocol differences
* Exercise differences
* Fatigue
* Recovery
* Environmental conditions
* Data quality

The system should treat drift as a **signal for investigation**, not as an automatic diagnosis.

---

# Interval Quality

After a session, the coach should be able to understand how accurately the athlete executed each interval.

Example:

```text
INTERVAL QUALITY

Interval 1   ██████████  96%
Interval 2   █████████   91%
Interval 3   ██████████  95%
Interval 4   ████████    83%
Interval 5   ███████     76%
Interval 6   █████████   89%
Interval 7   █████████   90%
Interval 8   ██████████  94%
```

The underlying calculation can incorporate:

* Time inside target
* Time above target
* Time below target
* Overshoot
* Undershoot
* Time-to-target
* HR stability
* Recovery behavior
* Interval consistency

The exact scoring formula will be validated during development.

---

# Physiological Execution Score

A session-level score can summarize how accurately the athlete followed the physiological prescription.

Example:

```text
PHYSIOLOGICAL EXECUTION SCORE

91 / 100
```

The score can be decomposed into:

```text
Time in target           92%
Intensity accuracy       89%
HR stability             94%
Recovery execution       90%
Interval consistency     91%
```

The score is intended as a **training analytics metric**, not a medical measurement.

---

# Layer 3 — Personalization Engine

The third layer is the long-term research component.

Its purpose is to build an individualized relationship between:

* Exercise
* Heart rate
* Workload
* Time
* Protocol
* VO₂
* Individual physiological response

The goal is not to assume that one universal equation works equally well for every athlete.

Instead:

> **The model should learn the individual whenever sufficient valid data are available.**

---

# VO₂max Calibration

Calibration uses laboratory measurements as reference data.

During a calibration session:

1. The athlete performs a controlled CPET assessment.
2. A gas analyzer measures physiological variables.
3. A heart-rate sensor records HR simultaneously.
4. Relevant measurements are imported into the system.
5. Estimated and measured values are compared.
6. Error is calculated.
7. The athlete's personal calibration dataset is updated.
8. The personalized model can be retrained or updated.

Conceptually:

```text
                  GAS ANALYZER
                       │
                       ▼
                Measured VO₂
                       │
                       │
                       ▼
H10 ─────────► Estimation Model
 │                     │
 │                     ▼
 └────────────► Estimated VO₂
                       │
                 ┌─────┴─────┐
                 ▼           ▼
              Compare      Error
                 │           │
                 └─────┬─────┘
                       ▼
             Personal Calibration
                       │
                       ▼
                Model Update
```

The existing project documentation describes a calibration approach where measured and software-estimated values are retained separately, with a conceptual calibration relationship such as:

```text
calibrated = a × estimate + b
```

The final personalization methodology remains under development.

---

# Personal HR → VO₂ Modeling

A major long-term goal is to develop an individualized mapping between physiological response and VO₂.

Instead of assuming:

```text
HR = 170 → VO₂ = X
```

for everyone, the system can learn an athlete-specific relationship.

Conceptually:

```text
               VO₂
                │
                │            ●
                │         ●
                │      ●
                │   ●
                │ ●
                └────────────────── HR
```

Every valid calibration can provide additional information about this relationship.

```text
Calibration #1
      ↓
Personal Model v1
      ↓
Calibration #2
      ↓
Personal Model v2
      ↓
Calibration #3
      ↓
Personal Model v3
```

The model should therefore be treated as an evolving representation of the athlete rather than a fixed universal equation.

---

# Calibration Quality

Not every calibration session should have equal influence on the model.

Each calibration should receive a quality assessment.

Example:

```text
CALIBRATION QUALITY

Overall                91%

Signal quality          98%
Protocol adherence      94%
HR stability            89%
Data completeness       93%
```

Poor-quality calibrations can then be:

* Rejected
* Flagged
* Given lower model weight
* Sent for manual review

This prevents low-quality data from unnecessarily changing the athlete's model.

---

# Confidence Score

Predictions should not be presented as if every estimate has equal certainty.

A future model can return:

```text
Estimated VO₂max
51.8 ml/kg/min

Confidence
87%
```

with supporting information:

```text
3 laboratory calibrations
5 field tests
42 training sessions
18 high-quality HR recordings
```

Or:

```text
Estimated VO₂max
51.8 ml/kg/min

Confidence
LOW

Reason:
Insufficient personalized calibration data
```

The confidence system is intended to make uncertainty visible rather than hiding it behind a single number.

---

# Dynamic Personalized Training Zones

Training zones can evolve as the athlete's physiological profile becomes better understood.

Instead of permanently storing:

```text
Zone 4 = 170–180 bpm
```

the system can maintain an individualized model:

```text
ATHLETE-SPECIFIC ZONES

Z1   120–138 bpm
Z2   139–153 bpm
Z3   154–166 bpm
Z4   167–178 bpm
Z5   179–191 bpm
```

These values should be derived from the athlete's validated physiological information and the coach's selected methodology.

The goal is:

> **Dynamic, evidence-based personalization rather than static generic zones.**

---

# Physiological Fingerprint

The system can eventually represent each athlete through a multidimensional physiological profile.

Example:

```text
ATHLETE #001

VO₂max
54.2 ml/kg/min

HRmax
191 bpm

Resting HR
52 bpm

HR Response
────────────
Activation          Fast
Stabilization       Moderate
Recovery            Excellent
Drift               Low

Interval Response
─────────────────
High intensity      Excellent
Repeated intervals  Good
Recovery intervals  Excellent
Consistency         High
```

This is more informative than storing VO₂max alone.

The goal is to capture **how the athlete responds to exercise**, not merely one maximum value.

---

# Athlete Physiological Profile

The long-term athlete profile may contain:

```text
┌────────────────────────────────────┐
│ ATHLETE PHYSIOLOGICAL PROFILE      │
├────────────────────────────────────┤
│ Basic Parameters                   │
│                                    │
│ HRrest                             │
│ HRmax                              │
│ VO₂max                             │
│                                    │
│ HR Kinetics                        │
│                                    │
│ Time to Target                     │
│ Activation Slope                   │
│ Stabilization                      │
│ Recovery Slope                     │
│ HRR30 / HRR60 / HRR120             │
│                                    │
│ Training Response                  │
│                                    │
│ Interval Quality                   │
│ Execution Score                    │
│ HR Drift                           │
│ Consistency                        │
│                                    │
│ Model                              │
│                                    │
│ Calibration Count                 │
│ Model Version                      │
│ Confidence                         │
└────────────────────────────────────┘
```

This profile can become the foundation for future personalized training assistance.

---

# Model Versioning

Every model update should be traceable.

Example:

```text
Model v0.1
Model v0.2
Model v0.3
```

Each model version should retain information about:

* Training/calibration data used
* Date
* Number of calibration sessions
* Number of field tests
* Model parameters
* Validation results
* Prediction error
* Confidence
* Data quality

This makes it possible to answer an important question:

> **Did the latest calibration actually improve the model?**

Rather than simply assuming that more data always means a better model.

---

# Field Tests

Interval Assistance is intended to support commonly used VO₂max estimation protocols that can be performed without a laboratory gas analyzer.

Examples may include:

* Yo-Yo-based testing
* Bruce protocol
* Other appropriate field or exercise protocols

The intended workflow is:

```text
Coach selects protocol
        ↓
System displays required measurements
        ↓
Coach performs test
        ↓
Required data entered
        ↓
Validated calculation
        ↓
VO₂max estimate
        ↓
Athlete profile update
```

Where appropriate, field-test results can later be compared with laboratory reference measurements.

This creates another calibration pathway:

```text
Field Test
    +
H10 Data
    +
Previous Personal Model
          ↓
     Updated Estimate
          ↓
   Future Calibration
```

---

# Sensor Integration

The primary hardware reference is the **Polar H10 chest strap**.

However, the architecture is intentionally sensor-agnostic.

The goal is to support any compatible sensor capable of providing the required heart-rate data.

```text
Polar H10 ──────┐
                │
BLE HR Sensor ──┤
                ├──► Sensor Abstraction Layer
Other Sensors ──┤             │
                │             ▼
                └──────► Normalized HR Stream
                              │
                              ▼
                       Interval Assistance
```

The sensor layer should ideally isolate the rest of the application from hardware-specific implementations.

This enables future integration with:

* Sports wearables
* Mobile applications
* Research systems
* Coach platforms
* Third-party wearable ecosystems

---

# Data Architecture

A major project principle is to design the data architecture **before large-scale model development**.

Raw measurements should remain available so that derived features can be recalculated later.

A conceptual session schema includes:

```text
Athlete ID
Session ID
Timestamp
Sensor ID
Sensor Type

Exercise
Protocol
Work/Rest Phase

Target HR
Lower Bound
Upper Bound
Tolerance

Actual HR
Signal Quality

Time in Zone
Time Above Zone
Time Below Zone

Peak HR
Time to Target
HR Slope
HR Stabilization

HRR30
HRR60
HRR120
Recovery Slope

HR Drift
Interval Quality
Execution Score

VO₂ Measured
VO₂ Estimated
VO₂ Error

Calibration ID
Model Version
Confidence
```

The actual production schema will evolve as implementation progresses.

---

# Raw Data vs Derived Data

The system should distinguish between:

### Raw data

Measurements directly obtained from:

* Heart-rate sensors
* Gas analyzers
* Field tests
* Coach inputs

### Derived data

Values calculated by software:

* Zones
* HR kinetics
* Recovery metrics
* VO₂ estimates
* Calibration coefficients
* Confidence scores
* Execution scores

Raw data should remain preserved wherever practical.

This allows future models to use information that may not have been considered during the original development.

---

# Data Quality

Physiological modeling is only as reliable as the data entering the model.

The system should therefore detect or flag:

* Missing values
* Invalid units
* Duplicate measurements
* Impossible values
* Sensor dropouts
* Poor signal quality
* Incomplete protocols
* Incorrect test configuration
* Unexpected protocol deviations

A data-quality layer should operate before calibration data are allowed to influence the personal model.

---

# Validation Strategy

The project deliberately separates:

### Development data

Used to build and improve the model.

### Validation data

Used to evaluate model performance.

### Unseen participant data

Used to evaluate whether the model generalizes beyond the people and sessions used during development.

A model should not be considered successful simply because it fits the training dataset.

The project documentation proposes avoiding deployment decisions based on very small datasets and emphasizes broader validation before reliability claims are made.

---

# Current Prototype

The current HTML prototype demonstrates the initial real-time interaction model.

It includes:

* HRmax input
* Resting HR input
* %HRR
* %HRmax
* Approximate %VO₂max mode
* Absolute BPM
* High/low/steady intensity
* Configurable tolerance
* Work/recovery timing
* Simulated HR
* Manual HR input
* Session controls
* Simulation speed
* Audio feedback
* Live graph
* Phase detection
* Zone evaluation

The prototype is intended to validate the training interaction and core logic.

It is **not yet the production implementation**.

---

# Current Status

## Completed / Prototyped

* [x] Project concept
* [x] Interval training interaction model
* [x] Live HR visualization prototype
* [x] Target-zone logic
* [x] Configurable tolerance
* [x] Work/recovery phase logic
* [x] Audio event concept
* [x] Manual/simulated HR input
* [x] Initial calibration concept
* [x] Synthetic-data calibration development
* [x] Initial physiological analytics concept
* [x] Personalization architecture concept

## In Development

* [ ] Production architecture
* [ ] Polar H10 integration
* [ ] Generic BLE HR interface
* [ ] Real-time data pipeline
* [ ] Persistent athlete profiles
* [ ] Training history
* [ ] HR kinetics extraction
* [ ] Recovery analysis
* [ ] Drift detection
* [ ] Interval quality scoring
* [ ] Physiological Execution Score
* [ ] Calibration Quality Score
* [ ] Confidence estimation
* [ ] Personal HR → VO₂ model
* [ ] Dynamic personalized zones
* [ ] Model versioning
* [ ] Field-test workflows
* [ ] Production API
* [ ] Production UI

## Planned Validation

Real-world validation will be performed after the core implementation is ready.

The project does **not** claim that planned participant tests have already been completed.

---

# Roadmap

## Phase 1 — Interaction Prototype

* [x] Define interval model
* [x] Build live graph
* [x] Implement simulated HR
* [x] Implement tolerance
* [x] Implement work/recovery transitions
* [x] Prototype audio feedback

## Phase 2 — Sensor Layer

* [ ] BLE heart-rate interface
* [ ] Polar H10 integration
* [ ] Sensor abstraction
* [ ] Signal-quality handling
* [ ] Connection management
* [ ] Missing-data handling

## Phase 3 — Training Engine

* [ ] Production interval engine
* [ ] Coach session builder
* [ ] Exercise configuration
* [ ] Intensity configuration
* [ ] Session templates
* [ ] Athlete profiles
* [ ] Session history

## Phase 4 — Physiological Analytics

* [ ] HR kinetics
* [ ] Time-to-target
* [ ] HR slope
* [ ] Stabilization analysis
* [ ] Recovery metrics
* [ ] HRR30 / HRR60 / HRR120
* [ ] HR drift
* [ ] Interval Quality
* [ ] Physiological Execution Score

## Phase 5 — Laboratory Calibration

* [ ] Import real anonymized CPET/COSMED reports
* [ ] Validate report formats
* [ ] Match synchronized HR and VO₂ measurements
* [ ] Calculate estimation error
* [ ] Implement calibration quality scoring
* [ ] Implement personal calibration datasets

The initial development plan calls for testing the data-import workflow using a small number of anonymized real COSMED reports before broader validation.

## Phase 6 — Personalization

* [ ] Personal HR → VO₂ model
* [ ] Confidence score
* [ ] Dynamic training zones
* [ ] Physiological fingerprint
* [ ] Athlete physiological profile
* [ ] Model versioning
* [ ] Continuous calibration

## Phase 7 — Field Tests

* [ ] Yo-Yo workflows
* [ ] Bruce workflow
* [ ] Additional validated protocols
* [ ] Automated calculations
* [ ] Field-test quality checks
* [ ] Comparison with laboratory reference data

## Phase 8 — Validation

* [ ] Real participant data collection
* [ ] Unseen-participant validation
* [ ] Cross-session validation
* [ ] Cross-protocol evaluation
* [ ] Error analysis
* [ ] Calibration effectiveness
* [ ] Generalization testing

---

# Research Directions

Several research questions will become increasingly important as the project develops.

## 1. Can individual calibration outperform a generic model?

The primary hypothesis is that repeated athlete-specific calibration may reduce estimation error compared with a universal model.

## 2. How stable is the HR → VO₂ relationship?

The relationship may vary according to:

* Exercise modality
* Protocol
* Fatigue
* Recovery
* Training status
* Environment
* Individual physiology

The model should therefore explicitly account for context.

## 3. How much data does personalization require?

The project should investigate the relationship between:

```text
Number of calibrations
        ↓
Model confidence
        ↓
Prediction error
```

## 4. Does repeated calibration actually improve predictions?

Every model update should be evaluated rather than assumed to be beneficial.

## 5. Can field tests progressively replace laboratory measurements?

The long-term research objective is not to claim that field tests are automatically equivalent to CPET.

Instead, the project should investigate whether:

```text
CPET
 +
Field Tests
 +
H10 Data
 +
Personal Calibration
```

can progressively produce sufficiently useful individual estimates for practical training applications.

---

# Research Principle: Context Matters

A major architectural principle is that the model should not treat every heart-rate measurement as interchangeable.

For example:

```text
HR = 170 bpm
```

may have different physiological meaning during:

* Treadmill running
* Cycling
* Uphill running
* Interval work
* Recovery
* Continuous endurance work

Therefore, future models should incorporate contextual variables whenever sufficient data are available.

The intended modeling direction is:

```text
HR
+
Time
+
Exercise
+
Protocol
+
Workload
+
Phase
+
Athlete History
        ↓
Physiological State
        ↓
VO₂ / Intensity Estimate
```

---

# Safety and Scientific Principles

## No Data Manipulation

The system should never alter raw measurements simply to improve model performance or produce more favorable results.

## Raw and Calibrated Values Stay Separate

Raw reference measurements and model-corrected values should remain distinguishable.

## No Automatic Trust

A prediction should not automatically be treated as accurate simply because a model produced it.

Confidence and data quality should be visible.

## Validation on Unseen Data

Models should be evaluated on participants and sessions not used to train them.

## Quality Before Quantity

More data are not necessarily better if the data are poor quality.

## No Premature Medical Claims

The system is not currently presented as:

* A medical device
* A diagnostic system
* A replacement for laboratory testing
* A guarantee of athletic improvement

The project documentation explicitly emphasizes validation, data quality, privacy, and avoiding unsupported medical or performance claims.

---

# Limitations

Interval Assistance is currently a research and development project.

Important limitations include:

1. Production sensor integration is not yet complete.
2. The personalized VO₂max model has not yet been validated.
3. Real-world COSMED/CPET report integration still requires testing.
4. Planned participant validation has not yet been completed.
5. The current live chart is a prototype.
6. Field-test and laboratory relationships require empirical validation.
7. Confidence estimation has not yet been scientifically validated.
8. Physiological Execution Score is a proposed training metric, not a validated clinical metric.
9. Drift detection should be interpreted as a monitoring signal, not a diagnosis.
10. No specific performance improvement is currently guaranteed.

---

# Project Goals

The project ultimately aims to connect:

```text
                 SPORTS SCIENCE
                       │
                       ▼
              WEARABLE SENSORS
                       │
                       ▼
              REAL-TIME TRAINING
                       │
                       ▼
            PHYSIOLOGICAL ANALYTICS
                       │
                       ▼
             LABORATORY CALIBRATION
                       │
                       ▼
              PERSONALIZED MODEL
                       │
                       ▼
          PERSONALIZED TRAINING ZONES
                       │
                       ▼
             PRECISION EXECUTION
```

The long-term objective is to create a system that learns from reliable physiological measurements and progressively makes training assistance more individualized.

---

# Product Evolution

The intended evolution of Interval Assistance is:

```text
Stage 1
Interval Timer
      ↓
Stage 2
Heart-Rate Guided Intervals
      ↓
Stage 3
Physiological Interval Analytics
      ↓
Stage 4
Laboratory-Calibrated Athlete Model
      ↓
Stage 5
Personalized VO₂ / Intensity Estimation
      ↓
Stage 6
Adaptive Personalized Training Assistance
```

This progression is deliberate.

The product should become more intelligent as the quality and quantity of physiological data increase.

---

# What Makes Interval Assistance Different?

The project is not based on the idea that a wearable sensor alone can solve physiological personalization.

Instead, it attempts to connect four worlds:

### Wearable Data

Continuous physiological response from real-world training.

### Laboratory Data

High-quality reference measurements from CPET / gas analysis.

### Field Testing

Accessible performance protocols that can be repeated outside the laboratory.

### Training Context

Information about exactly what the athlete was asked to do.

The combination creates the opportunity for a continuously improving athlete-specific model.

---

# Future Platform Potential

The architecture is intentionally suitable for multiple product forms.

Potential future implementations include:

* Coach web application
* Athlete mobile application
* Wearable companion
* Training analytics dashboard
* Research platform
* API
* SDK
* Integration layer for sports technology companies

The underlying physiological engine should ideally remain independent of the user interface.

---

# Contributing

The project is currently under active development.

Potential future contribution areas include:

* BLE sensor integrations
* Polar H10 support
* Other wearable integrations
* Physiological modeling
* Statistical modeling
* Machine learning
* Training protocol implementation
* Data validation
* Visualization
* Mobile development
* Web development
* API development
* Sports science research
* Validation methodology

Contribution guidelines will be added as the project moves toward a stable public development stage.

---

# License

License information will be added when the project reaches the appropriate release stage.

---

# Disclaimer

**Interval Assistance is a research and development project.**

It is not currently a medical device, diagnostic system, or replacement for laboratory physiological testing.

VO₂max estimates, physiological profiles, training scores, personalized zones, and other model outputs require appropriate validation before being used for high-stakes decisions.

---

# Status

> **🚧 Work in Progress**

Interval Assistance currently consists of an interactive training prototype and a developing physiological calibration/personalization architecture.

The production sensor layer, complete data architecture, personalized modeling, field-test integration, and real-world validation remain under development.

The long-term goal is simple:

> **Turn physiological data into more precise, more personalized, and more actionable training assistance.**
