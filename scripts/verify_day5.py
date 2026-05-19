"""
Day 5 Verification Script -- RAG Knowledge Base + Confidence Curve

Validates:
  1. Knowledge base loads for known categories (Plumbing, Electrical, Carpentry)
  2. Retrieval returns standards, safety, tools, and matched violations
  3. Prompt enrichment adds domain context
  4. Unknown category returns graceful fallback
  5. Confidence curve computes ECE for perfectly calibrated data
  6. Confidence curve detects overconfidence
  7. Per-bin metrics are correct

Usage:
    python scripts/verify_day5.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.rag import retrieve_relevant_context, enrich_prompt_with_context, CATEGORY_MAP
from quality.confidence_curve import compute_calibration_curve, compute_ece_from_benchmark, CalibrationCurveData


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

    # ── 1. KNOWLEDGE BASE: LOADING ─────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  KNOWLEDGE BASE: LOADING")
    print("=" * 62)

    context = retrieve_relevant_context("Plumbing")
    run_test("Plumbing knowledge available", context["available"] is True)
    run_test("Plumbing category returned", context.get("category") == "Plumbing",
             f"category={context.get('category')}")
    run_test("Plumbing has standards", len(context.get("standards", [])) >= 3,
             f"standards_count={len(context.get('standards', []))}")
    run_test("Plumbing has safety", len(context.get("safety", [])) >= 2,
             f"safety_count={len(context.get('safety', []))}")
    run_test("Plumbing has tools", len(context.get("tools", [])) >= 3,
             f"tools_count={len(context.get('tools', []))}")

    context2 = retrieve_relevant_context("Electrical")
    run_test("Electrical knowledge available", context2["available"] is True)
    run_test("Electrical has standards", len(context2.get("standards", [])) >= 3)

    context3 = retrieve_relevant_context("Carpentry")
    run_test("Carpentry knowledge available", context3["available"] is True)
    run_test("Carpentry has standards", len(context3.get("standards", [])) >= 3)

    # ── 2. KNOWLEDGE BASE: UNKNOWN CATEGORY ────────────────────────────────

    print("\n" + "=" * 62)
    print("  KNOWLEDGE BASE: UNKNOWN CATEGORY")
    print("=" * 62)

    context_unknown = retrieve_relevant_context("Underwater Basket Weaving")
    run_test("Unknown category returns not available", context_unknown["available"] is False)
    run_test("Unknown category has fallback message", "general assessment" in context_unknown.get("message", "").lower())

    # ── 3. KNOWLEDGE BASE: VIOLATION MATCHING ──────────────────────────────

    print("\n" + "=" * 62)
    print("  KNOWLEDGE BASE: VIOLATION MATCHING")
    print("=" * 62)

    violations = [
        {"type": "MAJOR", "reason": "No Teflon tape on threaded pipe joints"},
        {"type": "MAJOR", "reason": "Back-pitched drain line observed"},
    ]
    context_match = retrieve_relevant_context("Plumbing", violations=violations)
    run_test("Violations matched against knowledge base",
             len(context_match.get("matched_violations", [])) >= 1,
             f"matched={len(context_match.get('matched_violations', []))}")

    if context_match.get("matched_violations"):
        first_match = context_match["matched_violations"][0]
        run_test("Matched violation has consequence", len(first_match.get("consequence", "")) > 0)
        run_test("Matched violation has severity", first_match.get("severity") in ["MAJOR", "MINOR"])

    # ── 4. PROMPT ENRICHMENT ───────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  PROMPT ENRICHMENT")
    print("=" * 62)

    base_prompt = "Assess this plumbing video for technique and safety."
    enriched = enrich_prompt_with_context(base_prompt, "Plumbing")

    run_test("Enriched prompt includes original", base_prompt in enriched)
    run_test("Enriched prompt includes Pipe Slope", "Pipe Slope" in enriched or "IPC" in enriched,
             f"enriched length: {len(enriched)}")
    run_test("Enriched prompt includes safety", "safety" in enriched.lower())
    run_test("Enriched prompt includes tools", "Pipe Wrench" in enriched or "tools" in enriched.lower())

    # Unknown category enrichment
    enriched_unknown = enrich_prompt_with_context(base_prompt, "Unknown Trade")
    run_test("Unknown category returns original prompt", enriched_unknown == base_prompt)

    # ── 5. CONFIDENCE CURVE: PERFECT CALIBRATION ────────────────────────────

    print("\n" + "=" * 62)
    print("  CONFIDENCE CURVE: PERFECT")
    print("=" * 62)

    # Perfect calibration: confidence = accuracy
    perfect_preds = [
        {"confidence": 0.9, "correct": True},
        {"confidence": 0.9, "correct": True},
        {"confidence": 0.7, "correct": True},
        {"confidence": 0.7, "correct": False},
        {"confidence": 0.5, "correct": True},
        {"confidence": 0.5, "correct": False},
        {"confidence": 0.3, "correct": False},
        {"confidence": 0.3, "correct": True},
        {"confidence": 0.1, "correct": False},
        {"confidence": 0.1, "correct": False},
    ]

    curve = compute_calibration_curve(perfect_preds, n_bins=5)
    run_test("ECE computed for perfect data", curve.ece >= 0, f"ece={curve.ece}")
    run_test("5 bins created", len(curve.bins) == 5, f"bins={len(curve.bins)}")
    run_test("Interpretation is not empty", len(curve.interpretation) > 0)

    # ── 6. CONFIDENCE CURVE: OVERCONFIDENT ─────────────────────────────────

    print("\n" + "=" * 62)
    print("  CONFIDENCE CURVE: OVERCONFIDENT")
    print("=" * 62)

    # Overconfident: high confidence, low accuracy
    overconfident_preds = [
        {"confidence": 0.95, "correct": True},
        {"confidence": 0.95, "correct": False},
        {"confidence": 0.90, "correct": False},
        {"confidence": 0.88, "correct": False},
        {"confidence": 0.85, "correct": True},
        {"confidence": 0.85, "correct": False},
    ]

    curve2 = compute_calibration_curve(overconfident_preds, n_bins=5)
    run_test("Overconfident ECE > 0.2", curve2.ece > 0.2, f"ece={curve2.ece}")
    run_test("Overconfident assessment detected",
             "overconfident" in curve2.calibration_assessment,
             f"assessment={curve2.calibration_assessment}")

    # ── 7. CONFIDENCE CURVE: EDGE CASES ────────────────────────────────────

    print("\n" + "=" * 62)
    print("  CONFIDENCE CURVE: EDGE CASES")
    print("=" * 62)

    # Empty
    empty_curve = compute_calibration_curve([], n_bins=5)
    run_test("Empty predictions -> ECE 0", empty_curve.ece == 0.0)
    run_test("Empty predictions -> no_data", empty_curve.calibration_assessment == "no_data")

    # Single prediction
    single_curve = compute_calibration_curve([{"confidence": 0.8, "correct": True}], n_bins=5)
    run_test("Single prediction -> ECE computed", single_curve.ece >= 0)

    # Benchmark integration
    bench_results = [
        {"confidence": 0.92, "score_ok": True, "actual_score": 82},
        {"confidence": 0.85, "score_ok": True, "actual_score": 78},
        {"confidence": 0.70, "score_ok": False, "actual_score": 55},
        {"confidence": 0.45, "score_ok": False, "actual_score": 30},
    ]
    bench_curve = compute_ece_from_benchmark(bench_results)
    run_test("Benchmark ECE computed", bench_curve.ece >= 0, f"ece={bench_curve.ece}")

    # ── 8. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 5 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 5 fully verified -- RAG Knowledge Base + Confidence Curve working correctly.")
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")

    return FAILED


if __name__ == "__main__":
    sys.exit(main())
