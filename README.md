# interval-assistance
# Interval Assistance

> **A heart-rate-driven interval training assistance system with personalized VO₂max calibration and real-time exercise guidance.**

**Interval Assistance** is a sports technology project designed to help coaches and athletes execute interval training sessions with greater precision.

The system combines **real-time heart-rate monitoring**, configurable training zones, interval timing, tolerance-based feedback, visual guidance, and an evolving **VO₂max estimation and personalization framework**.

The long-term goal is to move from generic heart-rate-based training prescriptions toward **individualized intensity control**, using laboratory measurements and field tests to progressively improve each athlete's physiological profile.

> **Project status:** Work in progress — prototype stage
> **Project type:** Sports Technology / Wearable Integration / Training Assistance / Physiological Modeling

---

## Table of Contents

* [Overview](#overview)
* [The Problem](#the-problem)
* [The Solution](#the-solution)
* [Core Concept](#core-concept)
* [Training Intensity](#training-intensity)
* [Real-Time Interval Assistance](#real-time-interval-assistance)
* [VO₂max Calibration](#vo2max-calibration)
* [Personalized VO₂max Estimation](#personalized-vo2max-estimation)
* [Field Tests](#field-tests)
* [Sensor Integration](#sensor-integration)
* [Visual and Audio Feedback](#visual-and-audio-feedback)
* [System Architecture](#system-architecture)
* [Current Prototype](#current-prototype)
* [Safety and Data Principles](#safety-and-data-principles)
* [Current Status](#current-status)
* [Roadmap](#roadmap)
* [Future Research](#future-research)
* [Limitations](#limitations)
* [Project Goals](#project-goals)
* [License](#license)

---

## Overview

Interval training is often prescribed using a combination of:

* Work and recovery durations
* Target heart-rate ranges
* Training intensity
* Individual physiological characteristics
* Coach-defined tolerances

In practice, however, maintaining the intended physiological intensity during an interval session can be difficult.

Heart rate changes dynamically, athletes may respond differently to the same workload, and the coach cannot continuously monitor every athlete and every physiological variable.

**Interval Assistance** is intended to act as an intelligent assistant between the coach's training prescription and the athlete's real-time physiological response.

The coach defines the training session, and the system continuously evaluates the athlete's heart rate against the prescribed target.

The system can then provide:

* Real-time visual feedback
* Audio alerts
* Work/recovery phase transitions
* Tolerance monitoring
* Heart-rate zone information
* Session progression
* Historical data for further analysis

---

## The Problem

A conventional interval timer answers:

> "When should the athlete work or rest?"

Interval Assistance aims to answer a more useful question:

> **"Is the athlete actually performing the interval at the intended physiological intensity?"**

For example, a coach may prescribe:

```text
Work: 4 minutes
Recovery: 2 minutes
Target intensity: 85% HRR
Allowed tolerance: ±3%
```

The system should not simply count four minutes.

It should continuously monitor the athlete's heart rate and determine whether the athlete is:

* Below the target range
* Inside the target range
* Above the target range

This allows the interval to be guided by both **time and physiological response**.

---

# The Solution

Interval Assistance is designed around four major components:

### 1. Training Session Definition

The coach defines:

* Exercise type
* Number and structure of intervals
* Work duration
* Recovery duration
* Target intensity
* Intensity calculation method
* Acceptable tolerance
* Session completion criteria

### 2. Real-Time Heart-Rate Monitoring

A compatible heart-rate sensor provides live physiological data.

The system evaluates the incoming heart rate against the target range defined by the coach.

### 3. Visual and Audio Assistance

The athlete and/or coach can immediately see the current physiological state.

Audio signals can notify the athlete when:

* Heart rate leaves the permitted range
* Work begins
* Recovery begins
* A phase ends
* A transition is approaching

### 4. Physiological Calibration

When laboratory or field-test data are available, they can be used to improve the athlete's individual physiological model.

The long-term objective is to progressively reduce dependence on laboratory gas-analysis measurements for future VO₂max estimation.

---

# Core Concept

The central idea is simple:

```text
Coach Prescription
        │
        ▼
Training Configuration
        │
        ▼
Heart-Rate Sensor
        │
        ▼
Real-Time Physiological Data
        │
        ▼
Target Zone Evaluation
        │
   ┌────┴────┐
   ▼         ▼
Visual      Audio
Feedback    Feedback
        │
        ▼
Training Data
        │
        ▼
Personalized Physiological Model
```

The system is therefore not intended to be only an interval timer.

It is designed as a **physiological assistance layer for interval training**.

---

# Training Intensity

One of the key design principles is that coaches should not be forced to use a single definition of intensity.

Interval Assistance is designed to support multiple intensity representations.

## Supported / Planned Intensity Modes

### Absolute Heart Rate

The coach can directly specify a heart-rate target:

```text
Target = 170 bpm
Tolerance = ±5 bpm
```

### Percentage of HRmax

The target can be defined relative to maximum heart rate:

```text
Target = 85% HRmax
```

### Percentage of Heart-Rate Reserve

The coach can use heart-rate reserve:

```text
HRR = HRmax - HRrest
```

and prescribe intensity as a percentage of HRR.

### Percentage of VO₂max

For coaches who prescribe intensity based on VO₂max, the system can use VO₂max-related intensity as the physiological reference.

This is particularly important because the project treats laboratory CPET measurements as a potential **gold-standard reference for calibration**.

### Coach-Defined Values

The coach can also manually define the target heart-rate range or intensity criteria.

This is important because different coaches, sports, protocols, and athletes may require different training methodologies.

---

# Real-Time Interval Assistance

The prototype demonstrates the intended real-time training interface.

A session can contain:

* Work phases
* Recovery phases
* Target intensity
* Target heart-rate range
* Tolerance
* Elapsed time
* Remaining time
* Current heart rate
* Current training zone
* Session progress

The graph is designed to show both the athlete's actual response and the intended target.

Conceptually:

```text
Heart Rate
   │
HRmax ───────────────────────────────
   │
   │             Actual HR
   │          ╭─────────────╮
Target ───────┼─────────────┼────────
   │          │             │
   │          ╰─────────────╯
   │
   └────────────────────────────────── Time
             Work      Recovery
```

The prototype also distinguishes between:

* Actual historical heart-rate data
* Expected/future training trajectory
* Training zones
* Upper physiological limits

The current HTML prototype implements simulated/manual heart-rate input, interval timing, zone evaluation, tolerance handling, graph visualization, and audio events.

---

# VO₂max Calibration

VO₂max calibration is a major research and development component of Interval Assistance.

The purpose is **not** to replace laboratory testing immediately.

Instead, laboratory testing provides a reference against which the system can evaluate its own estimations.

## Calibration Concept

During a calibration session:

1. The athlete performs a controlled VO₂max/CPET assessment.
2. A gas analyzer measures physiological variables.
3. A heart-rate sensor records heart rate simultaneously.
4. The system receives the relevant measurement data.
5. The software compares the estimated value with the measured reference.
6. The difference/error is recorded.
7. The calibration information is incorporated into the athlete's personalized model.

Conceptually:

```text
                CPET / Gas Analyzer
                       │
                       ▼
              Measured VO₂max
                       │
                       │
                       ▼
Heart Rate ─────► Estimation Model
                       │
                       ▼
                Estimated VO₂max
                       │
                ┌──────┴──────┐
                ▼             ▼
             Compare        Error
                │             │
                └──────┬──────┘
                       ▼
             Personal Calibration
                       │
                       ▼
            Improved Future Estimate
```

The project documentation describes a calibration approach in which the measured value and software estimate are kept separately and the calibration model can conceptually be represented as:

```text
calibrated = a × estimate + b
```

The final personalization model is still under development and should not be considered finalized.

---

# Personalized VO₂max Estimation

The long-term objective is to build an individualized model capable of estimating VO₂max **without requiring a gas analyzer for every future assessment**.

The important principle is that personalization should improve progressively.

Each valid calibration session can provide additional information about the relationship between:

* Heart rate
* Exercise protocol
* Athlete response
* Estimated VO₂max
* Measured VO₂max
* Estimation error

Over time, the system can use these observations to develop a more individualized estimation model.

### Intended progression

```text
Initial Estimate
      │
      ▼
Field / Laboratory Data
      │
      ▼
Calibration
      │
      ▼
Model Update
      │
      ▼
Improved Individual Estimate
      │
      ▼
Additional Calibration
      │
      └──────────────► Model Update
```

This is an ongoing research direction rather than a completed clinical or scientific validation claim.

---

# Field Tests

The project is also intended to support commonly used VO₂max estimation protocols that can be performed without laboratory gas analysis.

Examples include protocols such as:

* Yo-Yo-based testing
* Bruce protocol
* Other appropriate field or exercise tests

The intended workflow is:

```text
Coach selects test
       ↓
System provides required protocol/data fields
       ↓
Coach performs the test
       ↓
Required measurements are entered
       ↓
Calculation model is applied
       ↓
VO₂max estimate is produced
```

The goal is to make the process practical for coaches:

> **The coach should not need to manually perform the underlying mathematical calculations.**

Instead, the coach follows the appropriate test protocol and enters the required measurements.

The resulting estimate can then become part of the athlete's physiological profile and, where appropriate, contribute to further personalization.

---

# Sensor Integration

The primary development reference for heart-rate acquisition is the **Polar H10 chest strap**.

However, Interval Assistance is not intended to be locked to Polar hardware.

The preferred architecture is sensor-agnostic:

```text
Polar H10
    │
    ├─────────────┐
    │             │
Other BLE HR ─────┤
Sensors           │
                  ▼
           Sensor Interface
                  │
                  ▼
          Normalized HR Data
                  │
                  ▼
        Interval Assistance
```

Any compatible heart-rate sensor capable of providing the required data should ideally be usable through the same abstraction layer.

This makes the system more suitable for:

* Sports technology companies
* Wearable platforms
* Training applications
* Research environments
* Coach-facing software
* Future SDK/API integrations

---

# Visual and Audio Feedback

Real-time feedback is an essential part of the system.

The athlete should not need to constantly look at a screen to understand whether a training transition has occurred.

## Visual Feedback

The interface is designed to communicate:

* Current heart rate
* Current zone
* Current phase
* Elapsed time
* Remaining time
* Target intensity
* Tolerance
* Session progress
* Historical heart-rate response
* Planned/expected training trajectory

## Audio Feedback

Audio signals are intentionally limited to meaningful events.

### Tolerance Events

A beep can indicate that the athlete has crossed the allowed tolerance boundary.

For example:

```text
Target zone
     │
     ▼
 ┌───────────┐
 │   TARGET  │
 └───────────┘
      ▲
      │
   tolerance
      │
      ▼
  Audio alert
```

### Work / Recovery Transitions

Audio signals can indicate:

* Start of work
* Start of recovery
* End of a phase

### Preparation Signal

A three-beep sequence can be used before a transition to prepare the athlete for the upcoming change.

The intention is to provide useful feedback **without flooding the athlete with unnecessary sounds**.

---

# Session Completion

The system is designed to support different session completion criteria.

A coach may define a session to end based on:

### Designed Interval Completion

The session ends after all prescribed intervals and phases have been completed.

### Time-Based Completion

The session ends when the specified total duration has been reached.

This allows the same assistance system to support different coaching methodologies.

---

# System Architecture

The long-term architecture is intended to separate sensor acquisition, physiological calculations, training logic, and user interfaces.

A conceptual architecture is:

```text
                    ┌────────────────────┐
                    │   Coach Interface  │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Training Definition│
                    └─────────┬──────────┘
                              │
                              ▼
┌───────────────┐     ┌────────────────────┐
│ Heart-Rate    │────►│ Sensor Data Layer  │
│ Sensors       │     └─────────┬──────────┘
└───────────────┘               │
                                ▼
                     ┌────────────────────┐
                     │ Training Engine    │
                     │                    │
                     │ • Zones            │
                     │ • Tolerance        │
                     │ • Timing           │
                     │ • Phase Logic      │
                     └─────────┬──────────┘
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
           ┌────────────────┐     ┌────────────────┐
           │ Visual Feedback│     │ Audio Feedback │
           └────────────────┘     └────────────────┘
                              
                               │
                               ▼
                    ┌────────────────────┐
                    │ Data / Athlete     │
                    │ Profile            │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Calibration &      │
                    │ Modeling Layer     │
                    └────────────────────┘
```

The exact production architecture has not yet been implemented.

---

# Current Prototype

The current repository concept includes an interactive HTML prototype demonstrating the core interaction model.

The prototype includes:

* HRmax input
* Resting HR input
* Multiple intensity calculation modes
* %HRR
* %HRmax
* Approximate %VO₂max conversion
* Absolute BPM
* High/low/steady intensity modes
* Adjustable tolerance
* Work/recovery timing
* Real-time heart-rate simulation
* Manual HR input
* Session controls
* Speed controls for simulation
* Audio feedback
* Live graph
* Training phase detection
* Zone evaluation

The prototype's purpose is to validate the interaction and training logic before production implementation.

**Important:** the current HTML file is a prototype / proof of concept. It is not the final production application and does not represent the complete sensor-connected system.

---

# Current Status

## Implemented / Prototyped

* [x] Initial project concept
* [x] Interval training interaction model
* [x] Live heart-rate visualization prototype
* [x] Training zones
* [x] Configurable tolerance
* [x] Work/recovery phases
* [x] Audio event concept
* [x] Manual/simulated heart-rate input
* [x] Basic calibration workflow concept
* [x] Synthetic-data calibration development

## In Development

* [ ] Production application architecture
* [ ] Real heart-rate sensor integration
* [ ] Polar H10 integration
* [ ] Sensor-agnostic HR input layer
* [ ] Athlete profile system
* [ ] Coach interface
* [ ] Persistent training data
* [ ] Personalized calibration model
* [ ] Field-test workflows
* [ ] Production API
* [ ] Production UI

## Planned Validation

Real-world validation will be performed after the core system is implemented.

The project specifically does **not** claim that planned tests have already been completed.

---

# Safety and Data Principles

Interval Assistance is being developed with a conservative approach to physiological data.

## No Artificial Improvement of Results

The system must not manipulate data simply to produce a better-looking result.

Raw measurements and corrected/calibrated values should remain distinguishable.

## Validation on Unseen Participants

A model should not be considered reliable merely because it performs well on the data used to create it.

Future evaluation should therefore include previously unseen participants.

## Minimum Data Requirements

The project documentation proposes that a model should not be considered ready for deployment when the available dataset is too small.

A larger validation dataset is planned before making claims about model reliability.

## Data Quality

Invalid or suspicious data should be rejected or flagged, including:

* Invalid units
* Duplicate measurements
* Unreasonable values
* Incorrect input formats

## Privacy

The intended system should minimize unnecessary personal information.

The calibration concept focuses on physiological measurements rather than unnecessary identifying information.

## Medical Claims

Interval Assistance is **not currently presented as a medical device**.

It does not claim to:

* Replace laboratory testing
* Diagnose disease
* Guarantee a specific performance improvement
* Produce clinically validated VO₂max measurements

Any such claims would require appropriate validation and regulatory consideration.

The project's original documentation explicitly emphasizes these limitations and the need for real-world validation before deployment claims are made.

---

# Roadmap

## Phase 1 — Prototype

* [x] Define training interaction model
* [x] Build live interval visualization
* [x] Implement simulated HR input
* [x] Implement zone/tolerance logic
* [x] Prototype audio feedback

## Phase 2 — Sensor Integration

* [ ] Implement BLE heart-rate input
* [ ] Integrate Polar H10
* [ ] Normalize sensor data
* [ ] Handle connection/disconnection
* [ ] Handle missing or invalid measurements

## Phase 3 — Coach Platform

* [ ] Training session builder
* [ ] Exercise configuration
* [ ] Intensity configuration
* [ ] Tolerance configuration
* [ ] Session templates
* [ ] Athlete profiles
* [ ] Training history

## Phase 4 — Calibration

* [ ] Import real CPET/COSMED reports
* [ ] Validate real-world report formats
* [ ] Match HR and VO₂ measurements
* [ ] Calculate estimation error
* [ ] Build individual calibration workflow
* [ ] Store raw and calibrated values separately

The initial development plan calls for testing the data-import workflow with a small number of anonymized real COSMED reports before broader validation.

## Phase 5 — Field Testing

* [ ] Implement selected field-test protocols
* [ ] Define required coach inputs
* [ ] Automate VO₂max estimation
* [ ] Compare field estimates against reference measurements
* [ ] Improve individual models

## Phase 6 — Validation

* [ ] Collect real participant data
* [ ] Evaluate model performance on unseen participants
* [ ] Measure calibration improvement
* [ ] Evaluate error reduction
* [ ] Define deployment criteria
* [ ] Determine whether the model is sufficiently reliable for practical use

---

# Future Research

Several areas remain open for research and development.

## Personalized Models

The central research question is:

> **Can repeated individual calibration produce a sufficiently accurate personalized VO₂max estimation model without requiring a gas analyzer for every future assessment?**

## Cross-Protocol Generalization

A future model may need to determine whether calibration obtained from one exercise/test protocol can reliably transfer to another.

## Sensor Differences

Different heart-rate sensors may introduce differences in:

* Sampling
* Signal quality
* Latency
* Missing data
* Noise

Sensor-independent architecture is therefore important.

## Physiological Response

Heart rate does not respond instantly to changes in workload.

The training engine may therefore need to account for:

* Physiological response delay
* Recovery dynamics
* Individual response characteristics
* Exercise modality
* Session history

These are research considerations and are not claimed to be solved by the current prototype.

---

# Limitations

This project is currently under development.

The following limitations are important:

1. **Production sensor integration is not yet complete.**
2. **The final personalized VO₂max model has not yet been validated.**
3. **Real-world COSMED/CPET report integration still requires testing with anonymized reports.**
4. **Planned participant testing has not yet been completed.**
5. **The current live chart is a prototype, not a production application.**
6. **The relationship between field-test estimates and laboratory measurements requires empirical validation.**
7. **No clinical accuracy claim is currently made.**
8. **No specific performance improvement is guaranteed.**

The project is intentionally being developed so that these limitations can be tested rather than hidden.

---

# Project Goals

The long-term vision of Interval Assistance is to create a practical bridge between:

```text
Sports Science
      +
Wearable Sensors
      +
Coach Knowledge
      +
Real-Time Feedback
      +
Personalized Modeling
```

The ultimate objective is to allow a coach to prescribe an intensity in a physiologically meaningful way and have the system help the athlete execute that prescription as accurately as possible.

The intended evolution is:

```text
Generic Training Prescription
            ↓
Heart-Rate Guided Training
            ↓
Individual Calibration
            ↓
Personalized Physiological Model
            ↓
Personalized Intensity Assistance
```

---

# Project Philosophy

Interval Assistance follows a simple principle:

> **Measure first. Calibrate honestly. Personalize progressively.**

Laboratory measurements are valuable reference data.

Field tests make physiological assessment more accessible.

Wearable sensors provide continuous real-time information.

A personalized model can potentially connect all three.

The project therefore aims not to replace measurement, but to **learn from reliable measurements and gradually make practical training assistance more individualized**.

---

# Contributing

This project is currently under active development.

As the architecture matures, contribution areas may include:

* Sensor integrations
* Training protocols
* Physiological modeling
* Data validation
* Visualization
* Mobile/web interfaces
* API development
* Testing and validation
* Sports science research

Contribution guidelines will be added as the project moves toward a stable public development stage.

---

# License

License information will be added when the project reaches the appropriate release stage.

---

## Disclaimer

**Interval Assistance is a research and development project.**

It is not currently a medical device, diagnostic system, or replacement for laboratory physiological testing.

All physiological models, VO₂max estimations, training recommendations, and calibration methods must be appropriately validated before being used for high-stakes applications.

---

## Status

**🚧 Work in Progress**

The project currently consists primarily of a functional interaction prototype and developing calibration concepts. The production system, real sensor integration, personalized modeling, and real-world validation remain under development.
