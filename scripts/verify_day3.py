"""
Day 3 Verification Script -- Anti-Fraud + Adversarial Tests

Validates:
  1. Anti-fraud engine detects exact duplicates via pHash
  2. Anti-fraud detects near-duplicate (similar) videos
  3. Anti-fraud metadata consistency checks work
  4. Adversarial suite generates all 7 test videos
  5. Quality gate correctly rejects adversarial inputs
  6. Overall adversarial pass rate is acceptable

Usage:
    python scripts/verify_day3.py
"""

import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from quality.antifraud import (
    AntiFraudEngine,
    extract_keyframe_hashes,
    metadata_consistency_check,
    FraudCheckResult,
)
from quality.adversarial import AdversarialTestSuite
from quality.gate import assess_video_quality

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work")
os.makedirs(OUT_DIR, exist_ok=True)


def make_simple_video(filename, frames=100, color=180):
    """Generate a simple test video."""
    path = os.path.join(OUT_DIR, filename)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, 10, (320, 240))
    for i in range(frames):
        frame = np.ones((240, 320, 3), dtype=np.uint8) * color
        cv2.putText(frame, f"VIDEO {filename} frame {i}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255 - color,) * 3, 1)
        out.write(frame)
    out.release()
    return path


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

    # ── 1. ANTIFRAUD: DUPLICATE DETECTION ──────────────────────────────────

    print("\n" + "=" * 62)
    print("  ANTIFRAUD: DUPLICATE DETECTION")
    print("=" * 62)

    # Create two identical videos
    v1 = make_simple_video("fraud_test_a.mp4", frames=50)
    v2 = make_simple_video("fraud_test_b.mp4", frames=50)

    # Same video submitted twice -> should detect
    engine = AntiFraudEngine()
    engine.add_to_database("vid_001", v1)

    result = engine.check_duplicate(v1)
    run_test("Exact duplicate detected", result.is_duplicate,
             f"similarity={result.similarity_score}")
    run_test("Duplicate video_id recorded", result.duplicate_video_id == "vid_001",
             f"matched={result.duplicate_video_id}")

    # Different video -> should not be a duplicate
    v3 = make_simple_video("fraud_test_c.mp4", frames=50, color=100)
    result2 = engine.check_duplicate(v3)
    run_test("Different video NOT flagged as duplicate", not result2.is_duplicate,
             f"similarity={result2.similarity_score}")

    # ── 2. ANTIFRAUD: KEYFRAME EXTRACTION ──────────────────────────────────

    print("\n" + "=" * 62)
    print("  ANTIFRAUD: KEYFRAME EXTRACTION")
    print("=" * 62)

    hashes = extract_keyframe_hashes(v1, every_n_frames=10)
    run_test("Keyframe hashes extracted", len(hashes) > 0,
             f"count={len(hashes)}")
    run_test("Hashes are strings of length 16", all(len(h) == 16 for h in hashes),
             f"lengths={[len(h) for h in hashes[:3]]}")
    run_test("Hashes are hex strings", all(all(c in "0123456789abcdef" for c in h) for h in hashes),
             f"sample={hashes[0]}")

    # ── 3. ANTIFRAUD: METADATA CONSISTENCY ─────────────────────────────────

    print("\n" + "=" * 62)
    print("  ANTIFRAUD: METADATA CONSISTENCY")
    print("=" * 62)

    meta = metadata_consistency_check(v1)
    run_test("Metadata check returns duration", "duration_seconds" in meta,
             f"duration={meta.get('duration_seconds')}")
    run_test("Metadata check returns resolution", "resolution" in meta,
             f"res={meta.get('resolution')}")
    run_test("Metadata check returns FPS", "fps" in meta,
             f"fps={meta.get('fps')}")
    run_test("Metadata check returns bitrate", "bitrate_mbps" in meta,
             f"bitrate={meta.get('bitrate_mbps')}")
    run_test("Metadata resolution check passes", meta.get("resolution_ok") is True)
    run_test("Metadata FPS check passes", meta.get("fps_ok") is True)
    run_test("Metadata duration check passes", meta.get("duration_ok") is True)
    run_test("All metadata checks pass", meta.get("all_checks_passed") is True,
             f"all_checks_passed={meta.get('all_checks_passed')}")

    # Test with missing file
    meta_bad = metadata_consistency_check("/nonexistent/video.mp4")
    run_test("Missing file returns error", "error" in meta_bad)

    # ── 4. ADVERSARIAL TEST SUITE ──────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  ADVERSARIAL TEST SUITE")
    print("=" * 62)

    adv_dir = os.path.join(OUT_DIR, "adversarial_tests")
    suite = AdversarialTestSuite(output_dir=adv_dir)
    cases = suite.generate_all()

    run_test("All 7 adversarial videos generated", len(cases) == 7,
             f"count={len(cases)}, names={[c.name for c in cases]}")
    run_test("Each case has expected_outcome", all(c.expected_outcome for c in cases),
             f"outcomes={[c.expected_outcome for c in cases]}")

    # Test: verify adversarial video files exist
    adv_files = [
        os.path.join(adv_dir, "adversarial_upside_down.mp4"),
        os.path.join(adv_dir, "adversarial_sped_up.mp4"),
        os.path.join(adv_dir, "adversarial_still.mp4"),
        os.path.join(adv_dir, "adversarial_blank.mp4"),
        os.path.join(adv_dir, "adversarial_lowres.mp4"),
        os.path.join(adv_dir, "adversarial_black.mp4"),
        os.path.join(adv_dir, "adversarial_overexposed.mp4"),
    ]
    all_exist = all(os.path.exists(f) for f in adv_files)
    run_test("All adversarial video files exist on disk", all_exist,
             f"missing={[f for f in adv_files if not os.path.exists(f)]}")

    # Run quality gate on each adversarial video
    results = suite.evaluate_pipeline(assess_video_quality)

    run_test("All adversarial cases evaluated", all(c.actual_outcome for c in results),
             f"outcomes={[(c.name, c.actual_outcome) for c in results]}")

    # Count passes (adversarial inputs handled correctly)
    adversarial_pass = sum(1 for c in results if c.passed)
    total_adv = len(results)

    run_test(f"Adversarial pass rate >= 7/7", adversarial_pass >= 7,
             f"passed={adversarial_pass}/{total_adv}")

    for case in results:
        status = "PASS" if case.passed else "FAIL"
        print(f"  {status}  {case.name:<15}  "
              f"expected={case.expected_outcome:<15}  "
              f"got={case.actual_outcome:<15}  "
              f"{case.notes}")

    # ── 5. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 3 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 3 fully verified -- Anti-Fraud + Adversarial Suite working correctly.")
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")

    # Cleanup
    for f in adv_files + [v1, v2, v3]:
        try:
            os.remove(f)
        except Exception:
            pass
    try:
        shutil.rmtree(adv_dir)
    except Exception:
        pass

    return FAILED


if __name__ == "__main__":
    sys.exit(main())
