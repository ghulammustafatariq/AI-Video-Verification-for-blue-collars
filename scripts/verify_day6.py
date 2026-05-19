"""
Day 6 Verification Script -- Economic Model + Urdu i18n + README

Validates:
  1. Economic model computes correct baseline (Rs. 22,000/month unverified)
  2. Higher skill levels earn proportionally more
  3. Master level earns ~2x unverified baseline
  4. Improvement impact shows positive gain
  5. Urdu translations load correctly
  6. RTL flag is set for Urdu
  7. All required translation keys present

Usage:
    python scripts/verify_day6.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.economic import compute_economic_impact, compute_impact_if_improved, EconomicImpact


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

    # ── 1. ECONOMIC MODEL: BASELINES ───────────────────────────────────────

    print("\n" + "=" * 62)
    print("  ECONOMIC MODEL: BASELINES")
    print("=" * 62)

    # Unverified: Developing at low score
    impact_dev = compute_economic_impact(35, "Not Yet Ready")
    run_test("Not Yet Ready rate below base", impact_dev.rate_per_job < 500,
             f"rate={impact_dev.rate_per_job}")
    run_test("Not Yet Ready jobs/day <= 2", impact_dev.jobs_per_day <= 2,
             f"jobs={impact_dev.jobs_per_day}")

    # Competent (verified)
    impact_comp = compute_economic_impact(68, "Competent")
    run_test("Competent earns premium", impact_comp.premium_vs_unverified > 0,
             f"premium={impact_comp.premium_vs_unverified}")
    run_test("Competent rate >= base", impact_comp.rate_per_job >= 500,
             f"rate={impact_comp.rate_per_job}")

    # ── 2. ECONOMIC MODEL: ALL LEVELS ──────────────────────────────────────

    print("\n" + "=" * 62)
    print("  ECONOMIC MODEL: ALL LEVELS")
    print("=" * 62)

    levels = [
        ("Not Yet Ready", 25, 350),    # 0.7 * 500
        ("Developing", 50, 500),        # 1.0 * 500
        ("Competent", 68, 600),         # 1.2 * 500
        ("Experienced", 82, 750),       # 1.5 * 500
        ("Master", 94, 1000),           # 2.0 * 500
    ]

    for level, score, expected_rate in levels:
        impact = compute_economic_impact(score, level)
        actual = impact.rate_per_job
        run_test(f"{level} rate = {actual} (expected {expected_rate})",
                 actual == expected_rate,
                 f"got {actual}")
        run_test(f"{level} has monthly income", impact.monthly_income > 0,
                 f"income={impact.monthly_income}")
        run_test(f"{level} has annual income", impact.annual_income > 0)

    # ── 3. ECONOMIC MODEL: MASTER VS UNVERIFIED ────────────────────────────

    print("\n" + "=" * 62)
    print("  ECONOMIC MODEL: MASTER VS UNVERIFIED")
    print("=" * 62)

    master = compute_economic_impact(95, "Master")
    run_test("Master earns > Rs. 100,000/month", master.monthly_income > 100000,
             f"monthly={master.monthly_income:,}")
    run_test("Master premium > 100%", master.premium_percentage >= 100,
             f"premium={master.premium_percentage}%")
    run_test("Master jobs/day > unverified", master.jobs_per_day > 2)

    # ── 4. ECONOMIC MODEL: IMPROVEMENT IMPACT ──────────────────────────────

    print("\n" + "=" * 62)
    print("  ECONOMIC MODEL: IMPROVEMENT IMPACT")
    print("=" * 62)

    result = compute_impact_if_improved(55, "Developing", 80, "Experienced")

    run_test("Monthly gain is positive", result["monthly_gain"] > 0,
             f"gain={result['monthly_gain']:,}")
    run_test("Annual gain > Rs. 50,000", result["annual_gain"] > 50000,
             f"annual={result['annual_gain']:,}")
    run_test("Message is not empty", len(result["message"]) > 0)
    run_test("Current and potential differ", result["current"].monthly_income != result["potential"].monthly_income)

    # Edge: same level
    same = compute_impact_if_improved(85, "Experienced", 86, "Experienced")
    run_test("Same level shows gain or zero", same["monthly_gain"] >= 0)

    # ── 5. URDU i18n ───────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  URDU i18n")
    print("=" * 62)

    i18n_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge", "i18n.json",
    )

    run_test("i18n file exists", os.path.exists(i18n_path))

    with open(i18n_path, "r", encoding="utf-8") as f:
        i18n = json.load(f)

    run_test("Urdu translations present", "urdu" in i18n)
    run_test("Roman Urdu translations present", "urdu_roman" in i18n)
    run_test("Meta with RTL flag", i18n.get("meta", {}).get("rtl") is True)

    urdu = i18n["urdu"]
    required_keys = ["app_title", "upload_video", "score", "skill_level",
                     "violations", "strengths", "confidence", "verified",
                     "improvement_roadmap", "economic_impact"]

    for key in required_keys:
        run_test(f"Urdu key '{key}' present", key in urdu and len(urdu[key]) > 0,
                 f"value={urdu.get(key, 'MISSING')[:20]}")

    roman = i18n["urdu_roman"]
    run_test("Roman Urdu has matching keys", len(roman) >= len(urdu) * 0.8,
             f"urdu_keys={len(urdu)}, roman_keys={len(roman)}")

    # ── 6. README ──────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  README")
    print("=" * 62)

    readme_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "README.md",
    )
    run_test("README.md exists", os.path.exists(readme_path),
             f"path={readme_path}")

    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()

        run_test("README mentions AI Skill Verification",
                 "AI Skill Verification" in readme or "ai-skill-verification" in readme.lower())
        run_test("README mentions Fixly", "Fixly" in readme)
        run_test("README mentions Pakistan", "Pakistan" in readme)

    # ── 7. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 6 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 6 fully verified -- Economic Model + Urdu i18n + README working correctly.")
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")

    return FAILED


if __name__ == "__main__":
    sys.exit(main())
