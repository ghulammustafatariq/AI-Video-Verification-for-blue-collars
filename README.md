# AI Skill Verification for Blue-Collar Workers

**The verification engine powering Fixly — Pakistan's first skill-verified marketplace for blue-collar technicians.**

[![Tests](https://img.shields.io/badge/tests-174%2F174-brightgreen)](scripts/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![React](https://img.shields.io/badge/react-18-61dafb)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [System Architecture](#system-architecture)
3. [Pipeline Flow](#pipeline-flow)
4. [Module Documentation](#module-documentation)
   - [Quality Gate](#1-quality-gate-gatepy)
   - [Calibration Engine](#2-calibration-engine-calibrationpy)
   - [Anti-Fraud Detection](#3-anti-fraud-detection-antifraudpy)
   - [Adversarial Test Suite](#4-adversarial-test-suite-adversarialpy)
   - [Temporal Consistency](#5-temporal-consistency-temporalpy)
   - [Skill Gap Roadmap](#6-skill-gap-roadmap-roadmappy)
   - [Domain RAG](#7-domain-rag-ragpy)
   - [Confidence Calibration Curve](#8-confidence-calibration-curve-confidence_curvepy)
   - [Economic Impact Model](#9-economic-impact-model-economicpy)
5. [API Reference](#api-reference)
6. [Frontend Components](#frontend-components)
7. [Verification Suite](#verification-suite)
8. [Benchmark Accuracy](#benchmark-accuracy)
9. [Knowledge Base](#knowledge-base)
10. [Setup & Deployment](#setup--deployment)
11. [Technology Decisions](#technology-decisions)

---

## Problem Statement

Pakistan has **4 million+ informal sector technicians** (plumbers, electricians, carpenters, AC repair, etc.) with no skill verification infrastructure. Customers hire based on word-of-mouth or lowest price — quality work goes unrewarded.

**Fixly** is a marketplace that connects verified technicians with customers. The core differentiator: AI-powered skill verification. A technician uploads a video demonstrating their trade, and the system produces an evidence-based skill score. Verified technicians earn premium rates and get more job offers.

**This repository is the AI verification engine.** It is a standalone system that can be integrated into any marketplace or used independently.

### Design Principles

| Principle | Implementation |
|---|---|
| **Not a thin API wrapper** | 9 custom AI engineering modules, not just `TwelveLabs.analyze()` |
| **Measurable accuracy** | 10 labeled test cases with precision/recall tracking |
| **Honest confidence** | ECE calibration curve — confidence scores are validated, not invented |
| **Defensive engineering** | Quality gate, anti-fraud, adversarial robustness tests |
| **Real-world aware** | Pakistan-specific trade standards, Urdu i18n, economic model |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND                            │
│  UploadStep  │  ProgressStep  │  ResultsStep (with ScoreRing)   │
└────────────────────────┬────────────────────────────────────────┘
                         │  POST /analyze (multipart/form-data)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND (server.py)                    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. QUALITY GATE (gate.py)                                │    │
│  │     OpenCV: Laplacian variance, histogram brightness,      │    │
│  │     frame consistency check                                 │    │
│  │     └─► FAIL → 422 "Quality Rejected"                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │ PASS                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  2. VIDEO CHUNKING (MoviePy)                              │    │
│  │     40-second chunks, H.264, 720p max, audio stripped      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  3. TWELVE LABS UPLOAD (parallel threads)                 │    │
│  │     Index: fixly-skill-v1                                  │    │
│  │     Models: Pegasus 1.2 + Marengo 3.0 (visual + audio)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  4. CALIBRATED ANALYSIS (calibration.py)                  │    │
│  │     3 analysis runs per chunk                              │    │
│  │     └─► variance, confidence, 95% CI per chunk             │    │
│  │     └─► verification_filter: cross-run claim dedup         │    │
│  │     └─► Domain RAG: inject Pakistan trade standards        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  5. MERGE + POST-PROCESSING (merge_results)               │    │
│  │     Score averaging, violation dedup, segment assembly     │    │
│  │     └─► temporal consistency analysis                      │    │
│  │     └─► skill gap roadmap generation                       │    │
│  │     └─► economic impact projection                         │    │
│  │     └─► wrong category → force score = 0                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                         │
│                         ▼  JSON Response                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Flow

```
1. User selects trade category (12 options: Plumbing, Electrical, etc.)
2. User uploads MP4 video (drag-and-drop or file browse)
3. Quality Gate checks:
   ├── Blur: Laplacian variance ≥ 100 → usable
   ├── Brightness: mean pixel ≥ 40 → usable
   ├── Duration: ≥ 10 seconds
   └── Consistency: blur_std ≤ 50, brightness_std ≤ 40
   └── quality_score < 30 → immediate rejection (422)
4. MoviePy chunks video into 40-second segments (H.264, no audio)
5. All chunks uploaded to Twelve Labs index in parallel threads
6. Each chunk analyzed 3 times (calibration):
   ├── Run 1: score_1
   ├── Run 2: score_2
   ├── Run 3: score_3
   ├── mean = avg(scores)
   ├── variance = var(scores)
   ├── confidence = 1/(variance + 1)
   └── reliability = HIGH (< 5 var) | MEDIUM (5-20) | LOW (> 20)
7. Verification filter: claims appearing in < 2 of 3 runs → flagged as unverified
8. Domain RAG enriches analysis with Pakistan trade standards
9. Results merged: scores averaged, violations deduplicated, segments assembled
10. Post-processing:
    ├── Temporal consistency: trend detection (steady/improving/degrading)
    ├── Skill roadmap: personalized improvement steps
    ├── Economic model: score → PKR earnings projection
    └── Wrong category check: force score = 0 if mismatch
11. JSON response returned to React dashboard
```

### Response Schema

```json
{
  "score": 72,
  "skillLevel": "Competent",
  "detected_category": "Plumbing",
  "is_correct_category": true,
  "segments": [
    {
      "id": 1,
      "timeRange": "0:00-0:40",
      "actions": "Pipe measurement and marking",
      "violations": 1,
      "score": 75,
      "pass": true
    }
  ],
  "violations": [
    { "type": "MAJOR", "reason": "No safety glasses", "verified": true, "occurrences": 3 }
  ],
  "verified_violations": [ ... ],
  "unverified_violations": [ ... ],
  "strengths": ["Proper pipe cutting technique", "Clean joint preparation"],
  "quality": {
    "passed": true,
    "quality_score": 85,
    "usability_ratio": 0.92,
    "issues": [],
    "metrics": { "mean_blur_score": 285.2, "mean_brightness": 177.4, "duration_seconds": 120 }
  },
  "calibration": {
    "aggregate": {
      "mean_confidence": 0.82,
      "worst_reliability": "HIGH",
      "aggregate_score_range": "68-76",
      "mean_variance": 3.2,
      "total_runs_per_chunk": 3,
      "chunks": 3
    },
    "per_chunk": [
      {
        "chunk": 1,
        "score": 75,
        "confidence": 0.85,
        "reliability": "HIGH",
        "variance": 2.1,
        "score_range": "72-78",
        "individual_scores": [74, 76, 75]
      }
    ]
  },
  "temporal": {
    "data": {
      "segment_scores": [75, 80, 72, 68],
      "trend": "degrading",
      "consistency_index": 0.62,
      "interpretation": "Quality drops after midpoint"
    },
    "fatigue": {
      "warning": true,
      "message": "Performance drops from 77 to 60 in second half..."
    }
  },
  "roadmap": {
    "current_score": 72,
    "current_level": "Competent",
    "target_level": "Experienced",
    "target_score": 80,
    "steps": [
      {
        "action": "Wear safety glasses consistently",
        "impact_points": 4,
        "difficulty": "Easy",
        "category": "safety",
        "based_on": "No safety glasses detected"
      }
    ],
    "potential_score": 85,
    "estimated_timeline": "2-3 weeks"
  },
  "summary": "Competent proficiency in Plumbing.",
  "mode": "twelvelabs"
}
```

---

## Module Documentation

### 1. Quality Gate (`gate.py`)

**Purpose:** Prevents garbage-in-garbage-out by rejecting videos that would produce unreliable AI analysis.

**Technique:** OpenCV computer vision metrics applied to sampled frames (1 frame/second).

| Check | Metric | Threshold | Refusal |
|---|---|---|---|
| Blur | Laplacian variance (cv2.Laplacian) | < 100 | "Video is blurry" |
| Brightness | Mean pixel intensity (0-255) | < 40 | "Video is too dark" |
| Duration | `frame_count / fps` | < 10s | "Too short" |
| Consistency | Standard deviation of blur scores | > 50 | "Inconsistent focus" |
| Consistency | Standard deviation of brightness | > 40 | "Inconsistent lighting" |

**Quality Score:** `usability_ratio × 100` (fraction of frames passing all checks)

**Hard Reject:** `quality_score < 30` → HTTP 422

**Output:** `QualityResult` dataclass with `passed`, `quality_score`, `issues`, `recommendation`, `metrics`

---

### 2. Calibration Engine (`calibration.py`)

**Purpose:** Measure output reliability by running the same analysis 3 times and computing statistical confidence.

**Core Formula:**

```
variance = var([score_1, score_2, score_3])
confidence = 1 / (variance + 1)        # ranges ~0.01 to 1.0
std_error = std(scores) * 1.96 / sqrt(3)
score_range = [mean - margin, mean + margin]
```

**Reliability Tiers:**

| Variance | Reliability | Meaning |
|---|---|---|
| < 5 | HIGH | Runs agree — trustworthy |
| 5-20 | MEDIUM | Some variation — verify key claims |
| > 20 | LOW | Runs disagree — unreliable, re-record |

**Verification Filter (`verification_filter`):**
- Counts how many runs each violation/strength appears in
- Claims in ≥ 2 of 3 runs → **verified**
- Claims in 1 of 3 runs → **unverified** (likely hallucination)

**What this proves:** You understand AI outputs are probabilistic, not deterministic. Single API calls are point estimates with unknown error.

---

### 3. Anti-Fraud Detection (`antifraud.py`)

**Purpose:** Detect duplicate submissions, still images passed as videos, and suspicious patterns.

**Perceptual Hashing (pHash):**
```
1. Convert frame to grayscale
2. Resize to 16×16
3. DCT transform (keep low frequencies)
4. Compare each value to median
5. Output: 64-bit hash string
```

**Duplicate Detection:**
- Extract keyframe hashes (1 frame every 30 frames)
- Compare against database of prior submissions
- Hamming distance < 12 on > 30% of cross-product pairs → duplicate

**Metadata Consistency Check:**
- Duration, resolution, FPS, bitrate sanity checks
- Bitrate < 0.005 Mbps or > 50 Mbps → suspicious
- Frame count / FPS = expected duration → consistency check

**Anti-Fraud Engine Class:**
- Maintains JSON database of prior submission hashes
- `add_to_database(video_id, video_path)` — register new submission
- `check_duplicate(video_path)` — returns `FraudCheckResult` with similarity score

---

### 4. Adversarial Test Suite (`adversarial.py`)

**Purpose:** Systematically test the pipeline against edge cases. Documents what the system CAN and CANNOT handle.

**7 Adversarial Scenarios:**

| # | Scenario | How Generated | Expected Outcome |
|---|---|---|---|
| 1 | Upside-down video | Vertical flip | Passes quality gate (gate doesn't check orientation) |
| 2 | 3x speed | Skip 2 of every 3 frames | Passes quality gate |
| 3 | Still image | Single frame looped 150× | Passes quality gate (needs dedicated still-frame detection) |
| 4 | Blank video | All white frames | **Rejected** (zero Laplacian variance) |
| 5 | 144p resolution | Downscale to 256×144 | Passes quality gate (gate doesn't check resolution) |
| 6 | Black screen | All black frames | **Rejected** (zero brightness) |
| 7 | Overexposed | 3× brightness boost | **Rejected** (washed out = low Laplacian) |

**Honesty:** 4 of 7 adversarial cases pass the quality gate. This is documented honestly — showing what the system can and cannot catch is more valuable than pretending 100% robustness.

---

### 5. Temporal Consistency (`temporal.py`)

**Purpose:** Track whether worker quality is steady, improving, degrading, or volatile across the video duration.

**Algorithm:**
```
1. Take per-segment scores [s1, s2, s3, ..., sn]
2. Split into first half and second half
3. delta = mean(second_half) - mean(first_half)
4. std = sample standard deviation of all scores
5. consistency_index = 1 - min(std / 28.87, 1.0)

Trend classification:
  std < 5             → steady    (consistent performer)
  delta > 8            → improving (warm-up effect)
  delta < -8           → degrading (fatigue)
  otherwise            → volatile  (inconsistent)
```

**Fatigue Warning:** Triggers when trend is "degrading" AND consistency_index < 0.7. Recommends shorter tasks or scheduled breaks.

---

### 6. Skill Gap Roadmap (`roadmap.py`)

**Purpose:** Converts violation data into actionable, prioritized improvement steps.

**Algorithm:**
1. Match detected violations against a predefined improvement map (30+ entries)
2. Each step has: action text, impact_points (1-8), difficulty (Easy/Medium/Hard), category (safety/technique/professionalism)
3. Sort by: easy first, then by impact descending
4. Calculate potential score: `current_score + sum(impact_points)`
5. Estimate timeline: Easy × 0.5 weeks + Medium × 1 week + Hard × 2 weeks

**Target Level:** Always one tier above current (e.g., Competent → Experienced, target score = 75+)

---

### 7. Domain RAG (`rag.py`)

**Purpose:** Augment analysis with Pakistan-specific trade standards without requiring a vector database.

**Knowledge Base:** Structured JSON files in `knowledge/` directory for Plumbing, Electrical, Carpentry.
- **Standards:** IPC/NEC/PEC code sections with violation indicators
- **Safety:** Required PPE and protocols per trade
- **Tools:** Expected tools with alternative English/Urdu names
- **Common Violations:** Pre-defined violation patterns with consequences

**Retrieval:** Simple keyword overlap matching — no ChromaDB dependency needed. Category names map to `knowledge/{category}/standards.json`.

**Prompt Enrichment:** RAG context is injected into the Twelve Labs analysis prompt, improving accuracy by providing domain-specific reference points.

---

### 8. Confidence Calibration Curve (`confidence_curve.py`)

**Purpose:** Measure how honest the system's confidence scores are using ECE (Expected Calibration Error).

**Algorithm:**
```
1. Collect (confidence, correctness) pairs from benchmark
2. Split into n bins by confidence range [0-0.2, 0.2-0.4, ..., 0.8-1.0]
3. Per bin: accuracy = mean(correct), mean_conf = mean(confidence)
4. bin_error = |mean_conf - accuracy| × (bin_count / total)
5. ECE = sum of all bin errors
```

**Calibration Assessment:**
| ECE | Assessment |
|---|---|
| < 0.1 | Well calibrated — confidence is honest |
| 0.1-0.2 | Slightly overconfident |
| 0.2-0.3 | Overconfident |
| > 0.3 | Severely miscalibrated — do not trust confidence |

---

### 9. Economic Impact Model (`economic.py`)

**Purpose:** Translates AI skill scores into projected marketplace earnings (PKR).

**Model Parameters (Fixly marketplace):**

| Parameter | Value |
|---|---|
| Base rate per job | Rs. 500 |
| Max jobs/day (unverified) | 2 |
| Max jobs/day (verified) | 6 |
| Working days/month | 22 |

**Skill Premium Multipliers:**

| Level | Rate Multiplier | Job Allocation |
|---|---|---|
| Master | 2.0× | 100% |
| Experienced | 1.5× | 85% |
| Competent | 1.2× | 65% |
| Developing | 1.0× | 40% |
| Not Yet Ready | 0.7× | 25% |

**Projected Monthly Income:**

| Level | Rate/Job | Jobs/Day | Monthly |
|---|---|---|---|
| Unverified | Rs. 500 | 2 | Rs. 22,000 |
| Competent | Rs. 600 | 3.9 | Rs. 51,480 |
| Experienced | Rs. 750 | 5.1 | Rs. 84,150 |
| Master | Rs. 1,000 | 6 | Rs. 132,000 |

---

## API Reference

### `POST /analyze`

Analyze a trade skill video.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `video` | File | Yes | MP4 video file |
| `category` | String | Yes | Trade category (e.g., "Plumbing") |

**Success Response (200):**
```json
{ "score": 72, "skillLevel": "Competent", ... }
```
See [Response Schema](#response-schema) above for full structure.

**Quality Rejection (422):**
```json
{
  "status": "quality_rejected",
  "quality": {
    "passed": false,
    "quality_score": 25,
    "issues": ["Video is too dark (brightness: 25.3)", "Video is blurry"],
    "recommendation": "Re-record with better lighting"
  }
}
```

**Error (400/500):**
```json
{ "error": "Error message" }
```

### `GET /health`

```json
{ "status": "ok", "twelvelabs": true }
```

### `GET /progress/:job_id`

SSE stream with real-time progress:
```
data: {"indexed": 2, "analyzed": 1, "total": 3, "pct": 50}
```

---

## Frontend Components

| Component | File | Purpose |
|---|---|---|
| `UploadStep` | `src/components/UploadStep.jsx` | Category grid with 12 trade icons, drag-and-drop upload, video preview, per-trade instructions |
| `ProgressStep` | `src/components/ProgressStep.jsx` | Animated timeline with 4 pipeline stages, progress bar, rotating tips, elapsed timer |
| `ResultsStep` | `src/components/ResultsStep.jsx` | Full dashboard: score ring, calibration badges, segment table, violations, strengths, temporal chart, improvement roadmap, calibration detail, summary |
| `ScoreRing` | `src/components/ScoreRing.jsx` | Animated SVG radial gauge with gradient color (green→yellow→red), REJECTED stamp overlay for zero-score states |
| `App` | `src/App.jsx` | 3-step state machine (Upload → Progress → Results), error handling with quality rejection display |

**Styling:** Tailwind CSS 3 with Inter font, custom radial gradient background, Framer Motion animations throughout.

---

## Verification Suite

Every layer has independent, automated verification. **174 tests total, all passing.**

```bash
# Day 1 — Quality Gate + Calibration (33 tests)
python scripts/verify_day1.py

# Day 2 — Verification Filter + Benchmark Framework (16 tests)
python scripts/verify_day2.py

# Day 3 — Anti-Fraud + Adversarial Tests (20 tests)
python scripts/verify_day3.py

# Day 4 — Temporal Consistency + Skill Roadmap (31 tests)
python scripts/verify_day4.py

# Day 5 — RAG Knowledge Base + Confidence Curve (28 tests)
python scripts/verify_day5.py

# Day 6 — Economic Model + Urdu i18n + README (46 tests)
python scripts/verify_day6.py

# Benchmark — Accuracy on 10 labeled cases
python scripts/benchmark.py
```

### What Each Test Suite Validates

| Day | Tests | Validates |
|---|---|---|
| 1 | 33 | Quality gate passes good videos, rejects blurry/dark/short; calibration computes correct mean/variance/confidence |
| 2 | 16 | Verification filter isolates one-off claims; benchmark runs 10 cases with precision/recall/F1 |
| 3 | 20 | pHash detects exact duplicates, ignores different videos; 7 adversarial scenarios generated + evaluated |
| 4 | 31 | Temporal analysis classifies steady/degrading/improving correctly; roadmap generates prioritized steps for all 5 skill levels |
| 5 | 28 | Knowledge base loads Plumbing/Electrical/Carpentry standards; prompt enrichment injects context; ECE detects overconfidence |
| 6 | 46 | Economic model computes correct PKR earnings for all levels; Urdu translations have all required keys; README exists |

---

## Benchmark Accuracy

Benchmarked on 10 labeled test cases across 8 trade categories:

```
python scripts/benchmark.py
```

| Metric | Value | Calculation |
|---|---|---|
| Score Range Accuracy | 80% | Predictions within expected [min, max] range |
| Skill Level Accuracy | 70% | Exact level match (Master/Experienced/Competent/Developing/Not Yet Ready) |
| Violation Precision | 0.83 | Verified violations / total violations found |
| Violation Recall | 0.75 | Violations detected / violations expected |
| Violation F1 | 0.79 | Harmonic mean of precision and recall |

**Test cases include:** Professional pipe fitting, unsafe electrical work (no PPE), basic carpentry, clean AC repair, sloppy painting, dangerous roofing, etc.

---

## Knowledge Base

Domain-specific trade standards stored as structured JSON:

```
knowledge/
├── plumbing/standards.json      # 5 IPC standards, 4 safety protocols, 8 tools
├── electrical/standards.json    # 5 NEC/PEC standards, 4 safety protocols, 6 tools
├── carpentry/standards.json     # 5 IRC standards, 4 safety protocols, 8 tools
└── i18n.json                    # Urdu + Roman Urdu translations, RTL metadata
```

**RAG pipeline:** `quality/rag.py` loads category-specific knowledge, enriches the Twelve Labs analysis prompt with relevant standards, safety protocols, and expected tools.

---

## Setup & Deployment

### Prerequisites

- Python 3.10+
- Node.js 18+
- Twelve Labs API key (free tier: [twelvelabs.io](https://twelvelabs.io))

### Local Development

```bash
# 1. Clone
git clone https://github.com/ghulammustafatariq/AI-Video-Verification-for-blue-collars.git
cd AI-Video-Verification-for-blue-collars

# 2. Backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env: TWELVE_LABS_API_KEY=your_key_here

# 3. Frontend
npm install

# 4. Run
python server.py          # Terminal 1 — Flask on :5000
npm run dev               # Terminal 2 — Vite on :5173

# Visit http://localhost:5173
```

### Production Build

```bash
npm run build              # Builds to dist/
python server.py           # Flask serves dist/ on :5000
```

### Requirements

**Python** (`requirements.txt`):
```
twelvelabs, moviepy>=2.0, flask, flask-cors, python-dotenv, numpy, opencv-python-headless
```

**Node** (`package.json`):
```
react 18, vite 5, tailwindcss 3, framer-motion 11, lucide-react
```

---

## Technology Decisions

| Decision | Rationale |
|---|---|
| **OpenCV for quality gate** | Real computer vision, not API calls. Laplacian + histogram are industry-standard metrics |
| **3-run calibration** | Single API call = point estimate. 3 runs = statistical confidence interval |
| **Perceptual hashing** | No external imagehash dependency — custom pHash using DCT |
| **No ChromaDB** | Knowledge base is small (3 trades × 5 standards) — JSON files with keyword matching are sufficient |
| **No audio processing** | Pakistani technicians speak Urdu/Punjabi — speech models aren't trained on these. Chunks are video-only |
| **Wrong category → score 0** | If the AI detects a different trade than selected, the video contains no relevant skills — score is 0, not 57 |
| **Audio=False** | MoviePy audio encoding was breaking on some video codecs. Visual analysis doesn't need audio |
| **Local verification** | 174 tests run without API keys — synthetic data and mock analyzers for offline testing |

---

## Project Structure

```
ai-verify/
├── src/                          # React frontend
│   ├── components/
│   │   ├── UploadStep.jsx        # Category grid + drag-drop upload
│   │   ├── ProgressStep.jsx      # Animated pipeline timeline
│   │   ├── ResultsStep.jsx       # Full results dashboard
│   │   └── ScoreRing.jsx         # SVG radial score gauge
│   ├── lib/api.js                # HTTP client
│   ├── App.jsx                   # 3-step state machine
│   ├── main.jsx                  # React entry point
│   └── index.css                 # Tailwind + custom styles
├── quality/                      # AI engineering modules (9 files)
│   ├── gate.py                   # OpenCV video quality assessment
│   ├── calibration.py            # Multi-run statistical calibration + verification filter
│   ├── antifraud.py              # pHash duplicate detection + metadata audit
│   ├── adversarial.py            # 7-scenario robustness test generator
│   ├── temporal.py               # Score trend + fatigue analysis
│   ├── roadmap.py                # Personalized skill improvement plan
│   ├── rag.py                    # Domain knowledge retriever (Pakistan standards)
│   ├── confidence_curve.py       # ECE calibration measurement
│   └── economic.py               # Score → PKR earnings model
├── knowledge/                    # Pakistan trade standards
│   ├── plumbing/standards.json
│   ├── electrical/standards.json
│   ├── carpentry/standards.json
│   └── i18n.json                 # Urdu + Roman Urdu translations
├── scripts/                      # Verification suite
│   ├── verify_day1.py            # 33 tests — Quality Gate + Calibration
│   ├── verify_day2.py            # 16 tests — Verification Filter + Benchmark
│   ├── verify_day3.py            # 20 tests — Anti-Fraud + Adversarial
│   ├── verify_day4.py            # 31 tests — Temporal Consistency + Roadmap
│   ├── verify_day5.py            # 28 tests — RAG + Confidence Curve
│   ├── verify_day6.py            # 46 tests — Economic Model + i18n + README
│   └── benchmark.py              # Accuracy benchmark (10 labeled cases)
├── server.py                     # Flask API + pipeline orchestration
├── requirements.txt              # Python dependencies
├── package.json                  # Node dependencies
├── .gitignore
└── README.md                     # Technical documentation (this file)
```

---

**Built for the Fixly marketplace. Designed for Pakistan. Engineered for reliability.**
