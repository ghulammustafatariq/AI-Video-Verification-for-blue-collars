"""
Day 4 Verification Script -- Temporal Consistency + Skill Gap Roadmap

Validates:
  1. Temporal analysis correctly classifies steady/improving/degrading trends
  2. Consistency index computed correctly
  3. Fatigue warning triggers only for degrading + inconsistent
  4. Skill roadmap generates prioritized improvement steps
  5. Roadmap calculates correct target level and score
  6. Improvement steps have all required fields

Usage:
    python scripts/verify_day4.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.temporal import analyze_temporal_consistency, compute_fatigue_warning, TemporalResult
from quality.roadmap import generate_roadmap, ImprovementStep, SkillGapRoadmap


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

    # ── 1. TEMPORAL: STEADY TREND ──────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  TEMPORAL: STEADY TREND")
    print("=" * 62)

    steady_scores = [82, 83, 81, 82, 83]
    result = analyze_temporal_consistency(steady_scores)

    run_test("Steady trend classified correctly", result.trend == "steady",
             f"trend={result.trend}")
    run_test("Consistency index > 0.95 for steady", result.consistency_index > 0.95,
             f"index={result.consistency_index}")
    run_test("First half avg computed", result.first_half_avg > 0,
             f"first={result.first_half_avg}")
    run_test("No fatigue warning for steady", not compute_fatigue_warning(result)["warning"])

    # ── 2. TEMPORAL: DEGRADING TREND ───────────────────────────────────────

    print("\n" + "=" * 62)
    print("  TEMPORAL: DEGRADING TREND")
    print("=" * 62)

    degrading_scores = [85, 80, 72, 65, 55]
    result2 = analyze_temporal_consistency(degrading_scores)

    run_test("Degrading trend classified correctly", result2.trend == "degrading",
             f"trend={result2.trend}")
    run_test("Consistency index < 0.7 for degrading", result2.consistency_index < 0.7,
             f"index={result2.consistency_index}")
    run_test("Second half lower than first", result2.second_half_avg < result2.first_half_avg)

    fatigue = compute_fatigue_warning(result2)
    run_test("Fatigue warning triggers for degrading", fatigue["warning"],
             f"message={fatigue['message'][:60]}")
    run_test("Fatigue message contains 'recommend'", "recommend" in fatigue["message"].lower(),
             f"message={fatigue['message'][:80]}")

    # ── 3. TEMPORAL: IMPROVING TREND ───────────────────────────────────────

    print("\n" + "=" * 62)
    print("  TEMPORAL: IMPROVING TREND")
    print("=" * 62)

    improving_scores = [55, 62, 70, 78, 85]
    result3 = analyze_temporal_consistency(improving_scores)

    run_test("Improving trend classified correctly", result3.trend == "improving",
             f"trend={result3.trend}")
    run_test("Second half higher than first", result3.second_half_avg > result3.first_half_avg)

    # ── 4. TEMPORAL: EDGE CASES ────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  TEMPORAL: EDGE CASES")
    print("=" * 62)

    # Single segment
    single = analyze_temporal_consistency([75])
    run_test("Single segment -> steady", single.trend == "steady")

    # Empty
    empty = analyze_temporal_consistency([])
    run_test("Empty scores -> steady", empty.trend == "steady")
    run_test("Empty scores -> index 0", empty.consistency_index == 0.0)

    # Too few for fatigue
    short = analyze_temporal_consistency([80, 60])
    fw_short = compute_fatigue_warning(short)
    run_test("2 segments -> no fatigue warning", not fw_short["warning"])

    # ── 5. SKILL GAP ROADMAP ───────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  SKILL GAP ROADMAP")
    print("=" * 62)

    violations = [
        {"type": "MAJOR", "reason": "No gloves detected during work"},
        {"type": "MINOR", "reason": "Wrong tool used for pipe cutting"},
        {"type": "MAJOR", "reason": "No safety glasses worn"},
        {"type": "MINOR", "reason": "Messy workspace observed"},
        {"type": "MAJOR", "reason": "Unsafe position while working"},
    ]

    roadmap = generate_roadmap(violations, current_score=58, current_level="Developing")

    run_test("Roadmap generated with steps", len(roadmap.steps) > 0,
             f"steps={len(roadmap.steps)}")
    run_test("Target level higher than current", roadmap.target_score > roadmap.current_score,
             f"current={roadmap.current_score}, target={roadmap.target_score}")
    run_test("Target is 'Competent' from 'Developing'", roadmap.target_level == "Competent",
             f"target={roadmap.target_level}")
    run_test("Potential score > current", roadmap.potential_score > roadmap.current_score,
             f"potential={roadmap.potential_score}")
    run_test("Timeline is not empty", len(roadmap.estimated_timeline) > 0)
    run_test("Each step has action text", all(s.action for s in roadmap.steps))
    run_test("Each step has impact_points > 0", all(s.impact_points > 0 for s in roadmap.steps))
    run_test("Each step has difficulty", all(s.difficulty in ["Easy", "Medium", "Hard"] for s in roadmap.steps))
    run_test("Easy steps come first", all(
        roadmap.steps[i].difficulty in ["Easy", "Medium"]
        for i in range(min(2, len(roadmap.steps)))
    ), f"first difficulties: {[s.difficulty for s in roadmap.steps[:3]]}")

    # ── 6. ROADMAP: ALL LEVELS ─────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  ROADMAP: ALL LEVELS")
    print("=" * 62)

    levels = [
        ("Not Yet Ready", 25),
        ("Developing", 50),
        ("Competent", 68),
        ("Experienced", 82),
        ("Master", 94),
    ]

    for level, score in levels:
        r = generate_roadmap(violations, score, level)
        valid_targets = ["Developing", "Competent", "Experienced", "Master"]
        run_test(f"Level '{level}' -> valid target", r.target_level in valid_targets,
                 f"target={r.target_level}")

    # Empty violations
    empty_roadmap = generate_roadmap([], 72, "Competent")
    run_test("Empty violations -> target Experienced", empty_roadmap.target_level == "Experienced")
    run_test("Empty violations -> 0 steps", len(empty_roadmap.steps) == 0)

    # ── 7. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 4 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 4 fully verified -- Temporal Consistency + Skill Gap Roadmap working correctly.")
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")

    return FAILED


if __name__ == "__main__":
    sys.exit(main())
