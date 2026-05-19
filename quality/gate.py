"""
Pre-analysis video quality assessment.
Uses OpenCV to check blur, brightness, and frame consistency.
Rejects videos that would produce unreliable AI analysis.
"""

import os
import cv2
import numpy as np
from dataclasses import dataclass


@dataclass
class QualityResult:
    passed: bool
    quality_score: int
    usability_ratio: float
    issues: list
    recommendation: str
    metrics: dict


# ── Thresholds (empirically grounded) ──
BLUR_THRESHOLD = 100        # Laplacian variance — below = blurry
BRIGHTNESS_THRESHOLD = 40   # Mean 0-255 — below = too dark
MIN_DURATION_S = 10         # Minimum video length for meaningful analysis
MIN_USABLE_RATIO = 0.6      # Fraction of frames that must be acceptable
MIN_FRAMES = 3              # Minimum sampled frames to analyze


def assess_video_quality(video_path: str) -> QualityResult:
    """
    Analyze video quality for AI analysis readiness.

    Checks performed:
      - File exists and is openable
      - Duration >= MIN_DURATION_S
      - Frame sharpness via Laplacian variance (BLUR_THRESHOLD)
      - Frame brightness via mean pixel intensity (BRIGHTNESS_THRESHOLD)
      - Consistency of focus / lighting across frames

    Returns QualityResult with pass/fail and diagnostic details.
    """

    if not os.path.exists(video_path):
        return QualityResult(
            passed=False,
            quality_score=0,
            usability_ratio=0.0,
            issues=["Video file not found on disk"],
            recommendation="Upload a valid video file",
            metrics={},
        )

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return QualityResult(
            passed=False,
            quality_score=0,
            usability_ratio=0.0,
            issues=["Cannot open video — file may be corrupted or unsupported codec"],
            recommendation="Re-encode video as MP4 (H.264 codec)",
            metrics={"file_size_mb": round(file_size_mb, 1)},
        )

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duration = frame_count / fps if fps > 0 else 0.0

    # Sample 1 frame per second for performance
    sample_interval = max(1, int(fps))
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % sample_interval == 0:
            frames.append(frame)
        idx += 1
    cap.release()

    if len(frames) < MIN_FRAMES:
        return QualityResult(
            passed=False,
            quality_score=0,
            usability_ratio=0.0,
            issues=[
                f"Video too short ({round(duration, 1)}s) — minimum {MIN_DURATION_S}s required",
                f"Only {len(frames)} analyzable frames found (need ≥{MIN_FRAMES})",
            ],
            recommendation="Record a longer video showing the full task from start to finish",
            metrics={
                "duration_seconds": round(duration, 1),
                "frames_analyzed": len(frames),
                "file_size_mb": round(file_size_mb, 1),
            },
        )

    blur_scores = []
    brightness_scores = []
    usable_count = 0
    issues = []

    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Blur detection: Laplacian variance
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Brightness: mean pixel value (0 = black, 255 = white)
        brightness = float(np.mean(gray))

        blur_scores.append(laplacian_var)
        brightness_scores.append(brightness)

        if laplacian_var > BLUR_THRESHOLD and brightness > BRIGHTNESS_THRESHOLD:
            usable_count += 1

    total = len(frames)
    usability_ratio = usable_count / total

    mean_blur = round(float(np.mean(blur_scores)), 1)
    mean_brightness = round(float(np.mean(brightness_scores)), 1)
    blur_std = round(float(np.std(blur_scores)), 1)
    brightness_std = round(float(np.std(brightness_scores)), 1)

    # Diagnose specific issues
    if mean_blur < BLUR_THRESHOLD:
        issues.append(
            f"Video is blurry (sharpness: {mean_blur}, minimum: {BLUR_THRESHOLD})"
        )
    if mean_brightness < BRIGHTNESS_THRESHOLD:
        issues.append(
            f"Video is too dark (brightness: {mean_brightness}, minimum: {BRIGHTNESS_THRESHOLD})"
        )
    if blur_std > 50:
        issues.append("Inconsistent focus across video -- camera may be shaking")
    if brightness_std > 40:
        issues.append(
            "Inconsistent lighting across video -- moving between light/dark areas"
        )
    if duration < MIN_DURATION_S:
        issues.append(
            f"Video too short ({round(duration, 1)}s, minimum: {MIN_DURATION_S}s)"
        )

    quality_score = round(usability_ratio * 100)
    passed = usability_ratio > MIN_USABLE_RATIO and len(issues) == 0

    if passed:
        recommendation = "Video quality acceptable — proceeding with AI analysis"
    elif usability_ratio > 0.3:
        recommendation = (
            "Video has some quality issues — analysis may have reduced confidence"
        )
    else:
        recommendation = (
            "Video quality too low for reliable analysis. "
            "Please re-record with: better lighting, stable camera, clear view of the work"
        )

    return QualityResult(
        passed=passed,
        quality_score=quality_score,
        usability_ratio=round(usability_ratio, 3),
        issues=issues,
        recommendation=recommendation,
        metrics={
            "duration_seconds": round(duration, 1),
            "frames_analyzed": total,
            "usable_frames": usable_count,
            "mean_blur_score": mean_blur,
            "mean_brightness": mean_brightness,
            "blur_std": blur_std,
            "brightness_std": brightness_std,
            "fps": round(fps, 1),
            "file_size_mb": round(file_size_mb, 1),
        },
    )
