"""
Day 1 Verification Script -- Quality Gate + Calibration Layer

Generates synthetic test videos and validates:
  1. Quality gate correctly passes well-lit/sharp video
  2. Quality gate correctly rejects blurry/dark/short video
  3. Quality gate returns all required metric fields
  4. Calibration computes correct mean, variance, confidence
  5. Calibration assigns correct reliability tier
  6. Verification filter correctly isolates unverified claims

Usage:
    python scripts/verify_day1.py

Output: PASSED / FAILED with diagnostic table
"""

import sys
import os
import json

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from quality.gate import assess_video_quality
from quality.calibration import calibrate, verification_filter, CalibrationResult

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work")
os.makedirs(TEST_DIR, exist_ok=True)

# ── Test helpers ────────────────────────────────────────────────────────────

def _make_video(filename, w=640, h=480, fps=10, duration=15, blur=False, dark=False):
    """Generate a synthetic MP4 for testing."""

    path = os.path.join(TEST_DIR, filename)
    if os.path.exists(path):
        return path  # reuse cached

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))

    for frame_idx in range(int(fps * duration)):
        # Solid uniform background for consistent Laplacian scores
        frame = np.ones((h, w, 3), dtype=np.uint8) * 180  # light gray

        # Static structured content (no position shift -- consistent across frames)
        cv2.circle(frame, (w // 2, h // 2), 70, (60, 60, 60), 2)
        cv2.circle(frame, (w // 2 - 80, h // 2), 40, (80, 80, 80), 2)
        cv2.rectangle(frame, (w // 2 + 30, h // 2 - 30), (w // 2 + 100, h // 2 + 30), (100, 100, 100), 2)

        # Text with frame number
        cv2.putText(
            frame, f"Frame {frame_idx}", (30, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1,
        )

        if blur:
            frame = cv2.GaussianBlur(frame, (15, 15), 0)

        if dark:
            frame = (frame * 0.15).astype(np.uint8)

        out.write(frame)

    out.release()
    return path


def _parse_mock(text: str) -> dict:
    """Mock parser that actually parses JSON from the analyzer."""
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return {"score": 50, "skill_level": "Developing", "strengths": [], "violations": [], "segments": []}


def _analyze_mock_stable(video_id: str, prompt: str) -> str:
    """Mock analyzer -- stable (low variance)"""
    import hashlib
    # Deterministic variation: score oscillates 74-76 around 75
    h = int(hashlib.md5(video_id.encode()).hexdigest()[:4], 16)
    offset = (h % 3) - 1  # -1, 0, or 1
    return f'{{"score": {75 + offset}, "skill_level": "Experienced"}}'


def _analyze_mock_unstable(video_id: str, prompt: str) -> str:
    """Mock analyzer -- unstable (high variance), different output each call."""
    # Use a global counter so each call produces a different score
    if not hasattr(_analyze_mock_unstable, "_counter"):
        _analyze_mock_unstable._counter = 0
    _analyze_mock_unstable._counter += 1
    seed = _analyze_mock_unstable._counter * 31
    offset = (seed % 55) - 27  # -27 to +27
    return f'{{"score": {50 + offset}, "skill_level": "Developing"}}'


def main():
    PASSED = 0
    FAILED = 0
    DETAILS = []

    def run_test(name: str, check: bool, detail: str = ""):
        nonlocal PASSED, FAILED
        if check:
            PASSED += 1
            DETAILS.append(f"  PASS  {name}")
        else:
            FAILED += 1
            DETAILS.append(f"  FAIL  {name}  -- {detail}")

    # ── 1. QUALITY GATE TESTS ─────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  QUALITY GATE TESTS")
    print("=" * 62)

    # 1a -- Good video passes
    good_video = _make_video("test_good.mp4", blur=False, dark=False, duration=15)
    result = assess_video_quality(good_video)
    run_test("Good video passes", result.passed,
             f"passed={result.passed}, ratio={result.usability_ratio}, issues={result.issues}")
    run_test("Good video quality_score >= 80", result.quality_score >= 80,
             f"score={result.quality_score}")
    run_test("Good video has no issues", len(result.issues) == 0,
             f"issues={result.issues}")
    run_test("Good video has all metrics", all(k in result.metrics for k in [
        "duration_seconds", "frames_analyzed", "usable_frames",
        "mean_blur_score", "mean_brightness", "blur_std", "brightness_std", "fps", "file_size_mb"
    ]), f"keys={list(result.metrics.keys())}")
    run_test("Good video recommendation is positive",
             "acceptable" in result.recommendation.lower(),
             f"rec={result.recommendation}")

    # 1b -- Blurry video rejected
    blurry_video = _make_video("test_blurry.mp4", blur=True, dark=False, duration=15)
    result = assess_video_quality(blurry_video)
    run_test("Blurry video fails", not result.passed,
             f"passed={result.passed}, ratio={result.usability_ratio}")
    run_test("Blurry video has blur issue", any("blur" in i.lower() for i in result.issues),
             f"issues={result.issues}")
    run_test("Blurry video quality_score < 60", result.quality_score < 60,
             f"score={result.quality_score}")

    # 1c -- Dark video rejected
    dark_video = _make_video("test_dark.mp4", blur=False, dark=True, duration=15)
    result = assess_video_quality(dark_video)
    run_test("Dark video fails", not result.passed,
             f"passed={result.passed}, ratio={result.usability_ratio}")
    run_test("Dark video has light/dark issue", any(
        "dark" in i.lower() or "light" in i.lower() or "bright" in i.lower()
        for i in result.issues), f"issues={result.issues}")

    # 1d -- Short video rejected
    short_video = _make_video("test_short.mp4", blur=False, dark=False, duration=3)
    result = assess_video_quality(short_video)
    run_test("Short video fails", not result.passed,
             f"passed={result.passed}, duration={result.metrics.get('duration_seconds')}")
    run_test("Short video mentions duration", any("short" in i.lower() for i in result.issues),
             f"issues={result.issues}")

    # 1e -- Nonexistent file
    result = assess_video_quality("/nonexistent/path/video.mp4")
    run_test("Missing file fails", not result.passed)

    # ── 2. CALIBRATION LAYER TESTS ─────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  CALIBRATION LAYER TESTS")
    print("=" * 62)

    # 2a -- Stable analysis -> HIGH reliability
    best, cal = calibrate(
        analyze_fn=_analyze_mock_stable,
        video_id="stable_test_vid_001",
        prompt="test prompt",
        parse_fn=_parse_mock,
        num_runs=3,
    )
    run_test("Stable -> reliability HIGH", cal.reliability == "HIGH",
             f"reliability={cal.reliability}, variance={cal.variance}, scores={cal.individual_scores}")
    run_test("Stable -> confidence > 0.8", cal.confidence > 0.8,
             f"confidence={cal.confidence}")
    run_test("Stable -> variance < 5", cal.variance < 5,
             f"variance={cal.variance}")
    run_test("Stable -> num_runs == 3", cal.num_runs == 3)
    run_test("Stable -> individual_scores has 3 entries", len(cal.individual_scores) == 3)
    run_test("Stable -> score_range is valid format",
             "-" in cal.score_range and len(cal.score_range.split("-")) == 2,
             f"score_range={cal.score_range}")

    # 2b -- Unstable analysis -> LOW reliability
    best2, cal2 = calibrate(
        analyze_fn=_analyze_mock_unstable,
        video_id="unstable_test_vid_002",
        prompt="test prompt",
        parse_fn=_parse_mock,
        num_runs=3,
    )
    run_test("Unstable -> reliability LOW", cal2.reliability == "LOW",
             f"reliability={cal2.reliability}, variance={cal2.variance}, scores={cal2.individual_scores}")
    run_test("Unstable -> confidence < 0.3", cal2.confidence < 0.3,
             f"confidence={cal2.confidence}")
    run_test("Unstable -> variance >= 20", cal2.variance >= 20,
             f"variance={cal2.variance}")

    # 2c -- Calibration result dataclass fields
    run_test("CalibrationResult has score field", hasattr(cal, "score"))
    run_test("CalibrationResult has confidence field", hasattr(cal, "confidence"))
    run_test("CalibrationResult has reliability field", hasattr(cal, "reliability"))
    run_test("CalibrationResult has variance field", hasattr(cal, "variance"))
    run_test("CalibrationResult has score_range field", hasattr(cal, "score_range"))

    # ── 3. VERIFICATION FILTER TESTS ────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  VERIFICATION FILTER TESTS")
    print("=" * 62)

    # 3a -- Claim appearing in all 3 runs -> verified
    all_agree = [
        {"violations": [{"type": "MAJOR", "reason": "No safety glasses"}]},
        {"violations": [{"type": "MAJOR", "reason": "No safety glasses"}]},
        {"violations": [{"type": "MAJOR", "reason": "No safety glasses"}]},
    ]
    vf = verification_filter(all_agree, min_occurrence=2)
    run_test("Claim in 3/3 runs -> verified", len(vf["verified_violations"]) == 1,
             f"verified={len(vf['verified_violations'])}")
    run_test("Claim in 3/3 runs -> no unverified", len(vf["unverified_violations"]) == 0,
             f"unverified={len(vf['unverified_violations'])}")

    # 3b -- Claim in only 1 run -> unverified
    one_off = [
        {"violations": [{"type": "MAJOR", "reason": "Gas leak detected"}]},
        {"violations": []},
        {"violations": []},
    ]
    vf2 = verification_filter(one_off, min_occurrence=2)
    run_test("Claim in 1/3 runs -> unverified", len(vf2["unverified_violations"]) == 1,
             f"unverified={len(vf2['unverified_violations'])}")
    run_test("Claim in 1/3 runs -> no verified", len(vf2["verified_violations"]) == 0,
             f"verified={len(vf2['verified_violations'])}")

    # 3c -- Mixed claims
    mixed = [
        {"violations": [
            {"type": "MAJOR", "reason": "No gloves"},
            {"type": "MINOR", "reason": "Messy workspace"},
        ]},
        {"violations": [
            {"type": "MAJOR", "reason": "No gloves"},
        ]},
        {"violations": [
            {"type": "MAJOR", "reason": "No gloves"},
            {"type": "MAJOR", "reason": "Wrong tool used"},
        ]},
    ]
    vf3 = verification_filter(mixed, min_occurrence=2)
    run_test("Mixed: 'No gloves' verified (3x)", len(vf3["verified_violations"]) == 1,
             f"verified={[v['reason'] for v in vf3['verified_violations']]}")
    run_test("Mixed: other claims unverified", len(vf3["unverified_violations"]) >= 2,
             f"unverified={[v['reason'] for v in vf3['unverified_violations']]}")

    # ── 4. SUMMARY ─────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("  DAY 1 VERIFICATION SUMMARY")
    print("=" * 62)

    for d in DETAILS:
        print(d)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    print(f"  Failed: {FAILED}/{total}")

    if FAILED == 0:
        print("\n  [SUCCESS] Day 1 fully verified -- Quality Gate + Calibration Layer working correctly.")
        sys.exit(0)
    else:
        print(f"\n  [FAILURE] {FAILED} test(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
