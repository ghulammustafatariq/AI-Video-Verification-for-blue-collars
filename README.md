# AI Skill Verification System

**The verification engine powering Fixly — Pakistan's first skill-verified marketplace for blue-collar workers.**

---

## What This Is

An AI engineering system that analyzes trade skill demonstration videos with multi-run calibration, statistical confidence measurement, anti-fraud detection, and explainable scoring. Deployed in production on the Fixly marketplace where verified technicians earn premium rates.

**Not a thin API wrapper.** This demonstrates genuine AI engineering across these layers:

| Layer | Technology |
|---|---|
| **Video Quality Gate** | OpenCV — Laplacian blur detection, brightness analysis, frame consistency |
| **Calibration Engine** | 3-run statistical analysis with variance-based confidence, 95% CI |
| **Verification Filter** | Cross-run claim verification — hallucination/one-off detection |
| **Anti-Fraud** | Perceptual hashing (pHash) — duplicate + near-duplicate detection |
| **Adversarial Suite** | 7 edge-case robustness tests (blank, dark, overexposed, etc.) |
| **Temporal Consistency** | Trend detection — tracks fatigue/degradation across video duration |
| **Skill Gap Roadmap** | Personalized improvement steps ranked by impact + difficulty |
| **Domain RAG** | Pakistan-specific trade standards (IPC, NEC, PEC) — local knowledge base |
| **Confidence Curve** | ECE (Expected Calibration Error) — honest confidence measurement |
| **Economic Model** | Score → PKR earnings projection (Fixly marketplace integration) |
| **i18n** | Urdu + Roman Urdu translations with RTL layout support |

---

## Architecture

```
Video Upload
    │
    ├── Quality Gate ──────► Reject if unusable (422)
    │   (blur, brightness, duration)
    │
    ├── Anti-Fraud ────────► Flag duplicates, suspicious content
    │   (pHash, metadata)
    │
    ├── 3-Run Calibration ─► Per-chunk: variance, confidence, 95% CI
    │   │
    │   ├── Verification ───► Cross-run claim filter
    │   │
    │   └── Domain RAG ─────► Inject Pakistan trade standards
    │
    ├── Merge + Analysis ──► Temporal consistency, skill roadmap
    │
    └── Dashboard ─────────► Confidence, score range, economic impact
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS, Framer Motion |
| Backend | Python Flask |
| Video AI | Twelve Labs (Pegasus 1.2 + Marengo 3.0) |
| Computer Vision | OpenCV (quality gate, pHash, adversarial generation) |
| Statistical | NumPy (variance, confidence intervals, ECE) |

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
npm install

# 2. Set Twelve Labs API key
cp .env.example .env
# Edit .env: TWELVE_LABS_API_KEY=your_key_here

# 3. Start backend
python server.py

# 4. Start frontend (separate terminal)
npm run dev
```

Open `http://localhost:5173` and upload a trade skill video.

---

## Verification Suite

Every layer has independent, automated verification:

```bash
python scripts/verify_day1.py   # Quality Gate + Calibration
python scripts/verify_day2.py   # Verification Filter + Benchmark
python scripts/verify_day3.py   # Anti-Fraud + Adversarial Tests
python scripts/verify_day4.py   # Temporal Consistency + Roadmap
python scripts/verify_day5.py   # RAG Knowledge Base + Confidence Curve
python scripts/verify_day6.py   # Economic Model + i18n + README
```

**All 6 days tested. All tests passing.**

---

## Benchmark Accuracy

Tested on 10 labeled test cases across 8 trade categories:

| Metric | Score |
|---|---|
| Score Range Accuracy | ~80% |
| Skill Level Accuracy | ~70% |
| Violation Precision | 0.83 |
| Violation Recall | 0.75 |
| Mean Confidence | 0.72 |

Full benchmark: `python scripts/benchmark.py`

---

## Pakistan Market Context

Pakistan has 4 million+ informal sector technicians with no skill verification. Customers hire based on word-of-mouth. The Fixly marketplace bridges this trust gap — verified technicians earn premium rates, and customers get quality assurance.

**Economic impact of verification** (Fixly model):
- Unverified: Rs. 22,000/month (500/job, 2 jobs/day)
- Verified (Experienced): Rs. 49,500/month (750/job, 3.7 jobs/day)
- Verified (Master): Rs. 132,000/month (1000/job, 6 jobs/day)

---

## Project Structure

```
ai-verify/
├── src/                      # React frontend
│   ├── components/           # UploadStep, ProgressStep, ResultsStep, ScoreRing
│   └── lib/api.js            # API client
├── quality/                  # AI engineering modules
│   ├── gate.py               # OpenCV quality assessment
│   ├── calibration.py        # Multi-run statistical calibration
│   ├── antifraud.py          # pHash duplicate detection
│   ├── adversarial.py        # Robustness test suite
│   ├── temporal.py           # Consistency/fatigue analysis
│   ├── roadmap.py            # Skill gap improvement plan
│   ├── rag.py                # Domain knowledge retriever
│   ├── confidence_curve.py   # ECE calibration measurement
│   └── economic.py           # PKR earnings projection
├── knowledge/                # Pakistan trade standards
│   ├── plumbing/standards.json
│   ├── electrical/standards.json
│   ├── carpentry/standards.json
│   └── i18n.json             # Urdu translations
├── scripts/                  # Verification suite
│   ├── verify_day1.py        # 33 tests
│   ├── verify_day2.py        # 16 tests
│   ├── verify_day3.py        # 20 tests
│   ├── verify_day4.py        # 31 tests
│   ├── verify_day5.py        # 28 tests
│   ├── verify_day6.py        # ~30 tests
│   └── benchmark.py          # Labeled accuracy benchmark
├── server.py                 # Flask API + pipeline
├── requirements.txt
└── README.md
```

---

**Built for the Fixly marketplace. Designed for Pakistan. Engineered for reliability.**
