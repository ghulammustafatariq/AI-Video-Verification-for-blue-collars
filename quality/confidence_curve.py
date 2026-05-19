"""
Confidence Calibration Curve

Measures how honest the system's confidence scores are.

ECE (Expected Calibration Error):
  - Split predictions into confidence bins
  - For each bin: |mean_confidence - accuracy|
  - Weight by bin size
  - Lower ECE = more honest confidence scores

A well-calibrated system:
  - When it says "90% confident" -> correct ~90% of the time
  - When it says "50% confident" -> correct ~50% of the time

Overconfident = confidence > accuracy (typical for LLM-based systems)
Underconfident = confidence < accuracy
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CalibrationCurveData:
    ece: float                      # Expected Calibration Error (0-1)
    mce: float                      # Maximum Calibration Error
    bins: List[dict]                # Per-bin: {confidence_range, count, mean_confidence, accuracy, error}
    calibration_assessment: str     # "well_calibrated" / "overconfident" / "underconfident"
    interpretation: str


def compute_calibration_curve(
    predictions: List[dict],
    n_bins: int = 5,
) -> CalibrationCurveData:
    """
    Compute calibration curve from list of predictions.

    Each prediction must have:
      - "confidence": float 0-1
      - "correct": bool (was the prediction correct?)

    Args:
        predictions: List of {"confidence": float, "correct": bool}
        n_bins: Number of confidence bins

    Returns:
        CalibrationCurveData with ECE and per-bin metrics
    """
    if not predictions:
        return CalibrationCurveData(
            ece=0.0,
            mce=0.0,
            bins=[],
            calibration_assessment="no_data",
            interpretation="No calibration data available",
        )

    confidences = np.array([p["confidence"] for p in predictions])
    corrects = np.array([1.0 if p["correct"] else 0.0 for p in predictions])

    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    max_error = 0.0
    bins = []

    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]

        # Find predictions in this bin
        mask = (confidences >= lower) & (confidences < upper)
        if i == n_bins - 1:
            mask = (confidences >= lower) & (confidences <= upper)

        bin_count = int(np.sum(mask))

        if bin_count == 0:
            bins.append({
                "confidence_range": f"{lower:.1f}-{upper:.1f}",
                "count": 0,
                "mean_confidence": 0.0,
                "accuracy": 0.0,
                "error": 0.0,
            })
            continue

        bin_conf = confidences[mask]
        bin_corr = corrects[mask]

        mean_conf = float(np.mean(bin_conf))
        accuracy = float(np.mean(bin_corr))
        error = abs(mean_conf - accuracy)

        ece += (bin_count / len(predictions)) * error
        max_error = max(max_error, error)

        bins.append({
            "confidence_range": f"{lower:.1f}-{upper:.1f}",
            "count": bin_count,
            "mean_confidence": round(mean_conf, 3),
            "accuracy": round(accuracy, 3),
            "error": round(error, 3),
        })

    ece = round(ece, 4)
    max_error = round(max_error, 4)

    # Assess calibration
    if ece < 0.1:
        assessment = "well_calibrated"
        interp = f"Confidence scores are honest (ECE={ece:.3f}). When the system says it's X% confident, it is correct approximately X% of the time."
    elif ece < 0.2:
        assessment = "slightly_overconfident"
        interp = f"System is slightly overconfident (ECE={ece:.3f}). Reported confidence is typically higher than actual accuracy."
    elif ece < 0.3:
        assessment = "overconfident"
        interp = f"System is overconfident (ECE={ece:.3f}). Confidence scores should be discounted by approximately {int((1 - (1-ece)) * 100)}%."
    else:
        assessment = "severely_overconfident"
        interp = f"Confidence scores are unreliable (ECE={ece:.3f}). Do not trust the reported confidence — the system is severely miscalibrated."

    return CalibrationCurveData(
        ece=ece,
        mce=max_error,
        bins=bins,
        calibration_assessment=assessment,
        interpretation=interp,
    )


def compute_ece_from_benchmark(benchmark_results: List[dict]) -> CalibrationCurveData:
    """
    Convert benchmark results into calibration curve data.

    Args:
        benchmark_results: List of {"confidence": float, "score_ok": bool} from benchmark

    Returns:
        CalibrationCurveData
    """
    predictions = [
        {"confidence": r["confidence"], "correct": r["score_ok"]}
        for r in benchmark_results
        if "confidence" in r and "score_ok" in r
    ]
    return compute_calibration_curve(predictions)
