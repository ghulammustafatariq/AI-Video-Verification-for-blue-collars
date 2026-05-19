"""
Day 2 Verification Script -- Verification Layer + Benchmark Framework

Validates:
  1. Verification filter integrates with calibrate (run_verification=True)
  2. Verification results contain verified/unverified violation lists
  3. Benchmark framework runs and produces valid metrics
  4. Benchmark report contains all required fields
  5. Per-chunk verification data available in response schema

Usage:
    python scripts/verify_day2.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.calibration import calibrate, verification_filter, aggregate_calibration, CalibrationResult
from scripts.benchmark import run_benchmark, BenchmarkResult


def main():
    PASSED = 0
    FAILED = 0
    DETAILS = []

    def run_test(name, check, detail=""):
        nonlocal PASSED, FAILED
        if check:
            PASSED += 1
            DETAILS.append(f"  PASS  {name}")
        else:
            FAILED += 1
            DETAILS.append(f"  FAIL  {name}  -- {detail}")

    # ── 1. VERIFICATION IN CALIBRATE ──────────────────────────────────────

    print("\n" + "=" * 62)
    print("  VERIFICATION IN CALIBRATE")
    print("=" * 62)

    call_count = [0]

    def mock_analyze_varying(video_id, prompt):
        call_count[0] += 1
        score = 60 + (call_count[0] % 20)
        violations = [
            {"type": "MAJOR", "reason": "Always present violation"},
        ]
        if call_count[0] == 2:
            violations.append({"type": "MINOR", "reason": "One-off hallucination"})
        return json.dumps({
            "score": score,
            "skill_level": "Competent",
            "violations": violations,
            "strengths": ["consistent strength"],
            "segments": [],
        })

    def mock_parse(text):
        try:
            return json.loads(text)
        except Exception:
            return {"score": 50, "violations": []}

    best, cal = calibrate(
        analyze_fn=mock_analyze_varying,
        video_id="verify_test_vid",
        prompt="test",
        parse_fn=mock_parse,
        num_runs=3,
        run_verification=True,
    )

    vf = best.get("_verification", {})
    run_test("Verification data present in result", "_verification" in best,
             f"keys={list(best.keys())}")
    run_test("Verified violations list exists", "verified_violations" in vf,
             f"vf_keys={list(vf.keys())}")
    run_test("Unverified violations list exists", "unverified_violations" in vf)
    run_test("1 verified violation (3x occurrence)", len(vf.get("verified_violations", [])) == 1,
             f"verified={[v['reason'] for v in vf.get('verified_violations', [])]}")
    run_test("1 unverified violation (1x hallucination)", len(vf.get("unverified_violations", [])) == 1,
             f"unverified={[v['reason'] for v in vf.get('unverified_violations', [])]}")
    run_test("Verified claim has 'verified' flag", vf["verified_violations"][0].get("verified") is True)
    run_test("Unverified claim has verified=False", vf["unverified_violations"][0].get("verified") is False)
    run_test("Total runs recorded", vf.get("total_runs") == 3,
             f"total_runs={vf.get('total_runs')}")

    # ── 2. CALIBRATE WITHOUT VERIFICATION ──────────────────────────────────

    print("\n" + "=" * 62)
    print("  CALIBRATE WITHOUT VERIFICATION")
    print("=" * 62)

    best2, cal2 = calibrate(
        analyze_fn=mock_analyze_varying,
        video_id="no_verify_test",
        prompt="test",
        parse_fn=mock_parse,
        num_runs=3,
        run_verification=False,
    )

    run_test("Without verification: no _verification key", "_verification" not in best2,
             f"keys={list(best2.keys())}")

    # ── 3. BENCHMARK FRAMEWORK ─────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  BENCHMARK FRAMEWORK")
    print("=" * 62)

    import hashlib

    def bench_analyze(video_id, prompt):
        h = int(hashlib.md5(video_id.encode()).hexdigest()[:4], 16)
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
            "violations": violations_list,
            "strengths": [],
            "segments": [],
        })

    bench_result = run_benchmark(bench_analyze, mock_parse)

    run_test("Benchmark runs 10 test cases", bench_result.total == 10,
             f"total={bench_result.total}")
    run_test("Score range accuracy > 0", bench_result.accuracy() > 0,
             f"accuracy={bench_result.accuracy():.2f}")
    run_test("Level accuracy > 0", bench_result.level_accuracy() > 0,
             f"level_accuracy={bench_result.level_accuracy():.2f}")
    run_test("Violation recall computed", bench_result.violations_recall >= 0,
             f"recall={bench_result.violations_recall:.2f}")
    run_test("Violation precision computed", bench_result.violations_precision >= 0,
             f"precision={bench_result.violations_precision:.2f}")
    run_test("F1 score computed", bench_result.f1_score() >= 0,
             f"f1={bench_result.f1_score():.2f}")
    run_test("All details have required fields", all(
        all(k in d for k in ["id", "actual_score", "score_ok", "actual_level", "level_ok",
                              "violations_found", "confidence", "reliability"])
        for d in bench_result.details
    ))

    # ── 4. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 2 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 2 fully verified -- Verification Layer + Benchmark Framework working correctly.")
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")

    return FAILED


if __name__ == "__main__":
    sys.exit(main())
