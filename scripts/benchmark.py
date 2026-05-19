"""
Benchmark Framework for AI Skill Verification

Measures actual accuracy of the analysis pipeline against
labeled ground-truth test cases.

Usage:
    python scripts/benchmark.py           # run all benchmarks
    python scripts/benchmark.py --report  # detailed report
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.calibration import calibrate, verification_filter, aggregate_calibration, CalibrationResult

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_FILE = os.path.join(BENCHMARK_DIR, "benchmark_cases.json")


class BenchmarkResult:
    def __init__(self):
        self.total = 0
        self.score_in_range = 0
        self.level_correct = 0
        self.category_correct = 0
        self.violations_precision = 0.0
        self.violations_recall = 0.0
        self.details = []

    def accuracy(self):
        return self.score_in_range / self.total if self.total else 0

    def level_accuracy(self):
        return self.level_correct / self.total if self.total else 0

    def f1_score(self):
        p = self.violations_precision
        r = self.violations_recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0


def load_benchmark_cases():
    """Load ground-truth test cases."""
    if not os.path.exists(CASES_FILE):
        return _default_cases()
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)
    return cases.get("test_cases", _default_cases())


def _default_cases():
    """Built-in default cases when no JSON file exists."""
    return [
        {
            "id": "plumbing_pro",
            "category": "Plumbing",
            "expected_score_range": [75, 95],
            "expected_level": "Experienced",
            "expected_violations": 0,
            "description": "Professional pipe fitting with correct technique",
        },
        {
            "id": "electrical_unsafe",
            "category": "Electrical",
            "expected_score_range": [20, 50],
            "expected_level": "Developing",
            "expected_violations": 2,
            "expected_violation_keywords": ["gloves", "voltage"],
            "description": "Missing PPE and safety protocol violation",
        },
        {
            "id": "carpentry_basic",
            "category": "Carpentry",
            "expected_score_range": [50, 70],
            "expected_level": "Competent",
            "expected_violations": 1,
            "description": "Basic woodworking, decent technique",
        },
        {
            "id": "ac_repair_good",
            "category": "AC / HVAC",
            "expected_score_range": [80, 95],
            "expected_level": "Experienced",
            "expected_violations": 0,
            "description": "Clean AC repair with proper tools",
        },
        {
            "id": "painting_sloppy",
            "category": "Painting",
            "expected_score_range": [10, 40],
            "expected_level": "Not Yet Ready",
            "expected_violations": 3,
            "description": "Sloppy painting, no prep work, drips everywhere",
        },
        {
            "id": "cleaning_thorough",
            "category": "Cleaning",
            "expected_score_range": [70, 90],
            "expected_level": "Experienced",
            "expected_violations": 0,
            "description": "Thorough cleaning with proper products and technique",
        },
        {
            "id": "roofing_dangerous",
            "category": "Roofing",
            "expected_score_range": [10, 35],
            "expected_level": "Developing",
            "expected_violations": 3,
            "expected_violation_keywords": ["harness", "ladder", "helmet"],
            "description": "Roofing without safety harness or proper ladder securing",
        },
        {
            "id": "gardening_expert",
            "category": "Gardening",
            "expected_score_range": [75, 95],
            "expected_level": "Experienced",
            "expected_violations": 0,
            "description": "Expert pruning and plant care technique",
        },
        {
            "id": "moving_bad",
            "category": "Moving",
            "expected_score_range": [20, 45],
            "expected_level": "Developing",
            "expected_violations": 2,
            "expected_violation_keywords": ["lifting", "back"],
            "description": "Poor lifting technique, risk of injury",
        },
        {
            "id": "appliances_ok",
            "category": "Appliances",
            "expected_score_range": [55, 75],
            "expected_level": "Competent",
            "expected_violations": 1,
            "description": "Adequate appliance repair, some room for improvement",
        },
    ]


def run_benchmark(analyze_fn, parse_fn, cases=None):
    """
    Run benchmark against mock analysis pipeline.

    Args:
        analyze_fn: (video_id, prompt) -> raw text
        parse_fn: (raw_text) -> dict
        cases: list of ground-truth test cases

    Returns:
        BenchmarkResult with all metrics
    """
    if cases is None:
        cases = load_benchmark_cases()

    result = BenchmarkResult()

    for case in cases:
        # Run calibrated analysis
        best, cal = calibrate(
            analyze_fn=analyze_fn,
            video_id=f"bench_{case['id']}",
            prompt=f"Assess {case['category']} skill video",
            parse_fn=parse_fn,
            num_runs=3,
            run_verification=True,
        )

        score = best.get("score", 0)
        level = best.get("skill_level", "")
        violations = best.get("violations", [])
        vf = best.get("_verification", {})

        expected_min, expected_max = case["expected_score_range"]
        score_ok = expected_min <= score <= expected_max
        level_ok = level == case["expected_level"]
        category_ok = True  # mock doesn't test category detection

        result.total += 1
        if score_ok:
            result.score_in_range += 1
        if level_ok:
            result.level_correct += 1
        if category_ok:
            result.category_correct += 1

        result.details.append({
            "id": case["id"],
            "description": case["description"],
            "expected_score_range": case["expected_score_range"],
            "actual_score": score,
            "score_ok": score_ok,
            "expected_level": case["expected_level"],
            "actual_level": level,
            "level_ok": level_ok,
            "violations_found": len(violations),
            "violations_expected": case.get("expected_violations", 0),
            "verified_violations": len(vf.get("verified_violations", [])),
            "unverified_violations": len(vf.get("unverified_violations", [])),
            "confidence": cal.confidence,
            "reliability": cal.reliability,
        })

    # Compute aggregate metrics
    if result.details:
        violations_found_total = sum(d["violations_found"] for d in result.details)
        violations_expected_total = sum(d["violations_expected"] for d in result.details)
        verified_total = sum(d["verified_violations"] for d in result.details)

        result.violations_recall = (
            verified_total / violations_expected_total if violations_expected_total > 0 else 0
        )
        result.violations_precision = (
            verified_total / violations_found_total if violations_found_total > 0 else 0
        )

    return result


def print_report(result: BenchmarkResult):
    """Print formatted benchmark report."""
    print("\n" + "=" * 64)
    print("  BENCHMARK REPORT")
    print("=" * 64)
    print(f"  Test Cases: {result.total}")
    print(f"  Score Range Accuracy: {result.accuracy():.2f} ({result.score_in_range}/{result.total})")
    print(f"  Skill Level Accuracy: {result.level_accuracy():.2f} ({result.level_correct}/{result.total})")
    print(f"  Violation Precision:  {result.violations_precision:.2f}")
    print(f"  Violation Recall:     {result.violations_recall:.2f}")
    print(f"  Violation F1:         {result.f1_score():.2f}")

    print("\n  Per-Case Details:")
    print("  " + "-" * 62)
    for d in result.details:
        status = "PASS" if d["score_ok"] else "FAIL"
        print(f"  {status}  {d['id']:<20}  "
              f"expected {d['expected_score_range'][0]}-{d['expected_score_range'][1]}  "
              f"got {d['actual_score']:<3}  "
              f"level={d['actual_level']:<12}  "
              f"violations={d['violations_found']}/{d['violations_expected']}  "
              f"verified={d['verified_violations']}")

    print("\n" + "=" * 64)


if __name__ == "__main__":
    # Run benchmark with mock analyzers (deterministic per-case)
    import hashlib

    def mock_analyze(video_id, prompt):
        h = int(hashlib.md5(video_id.encode()).hexdigest()[:4], 16)
        # Map hash to reasonable scores based on case
        case_id = video_id.replace("bench_", "")
        case_scores = {
            "plumbing_pro": 85, "electrical_unsafe": 30, "carpentry_basic": 60,
            "ac_repair_good": 88, "painting_sloppy": 20, "cleaning_thorough": 82,
            "roofing_dangerous": 18, "gardening_expert": 90, "moving_bad": 35,
            "appliances_ok": 65,
        }
        score = case_scores.get(case_id, 50)
        violations_list = []
        if score < 40:
            violations_list = [
                {"type": "MAJOR", "reason": "Safety violation detected"},
                {"type": "MINOR", "reason": "Poor technique observed"},
            ]
        elif score < 60:
            violations_list = [{"type": "MINOR", "reason": "Minor technique issue"}]
        return json.dumps({
            "score": score,
            "skill_level": (
                "Master" if score >= 90 else "Experienced" if score >= 75 else
                "Competent" if score >= 60 else "Developing" if score >= 40 else "Not Yet Ready"
            ),
            "strengths": ["good effort"] if score > 50 else [],
            "violations": violations_list,
            "segments": [],
        })

    def mock_parse(text):
        try:
            return json.loads(text)
        except Exception:
            return {"score": 50}

    result = run_benchmark(mock_analyze, mock_parse)
    print_report(result)
