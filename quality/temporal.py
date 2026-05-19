"""
Temporal Consistency Analysis

Tracks score and quality over video duration to detect:
  - Worker fatigue (quality degrades over time)
  - Rushed finish (last segments score lower)
  - Warm-up effect (early segments score lower)
  - Steady performer (consistent across all segments)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TemporalResult:
    segment_scores: List[int]
    segment_labels: List[str]
    trend: str              # "steady" | "improving" | "degrading" | "volatile"
    consistency_index: float  # 0.0-1.0
    first_half_avg: float
    second_half_avg: float
    best_segment_index: int
    worst_segment_index: int
    interpretation: str


def analyze_temporal_consistency(
    segment_scores: List[int],
    segment_labels: List[str] = None,
) -> TemporalResult:
    """
    Analyze score trends across video segments to assess consistency.

    Args:
        segment_scores: Per-segment scores (0-100)
        segment_labels: Optional labels for each segment

    Returns:
        TemporalResult with trend classification and consistency index
    """
    if not segment_scores:
        return TemporalResult(
            segment_scores=[],
            segment_labels=[],
            trend="steady",
            consistency_index=0.0,
            first_half_avg=0.0,
            second_half_avg=0.0,
            best_segment_index=-1,
            worst_segment_index=-1,
            interpretation="No segment data available",
        )

    n = len(segment_scores)
    scores_arr = np.array(segment_scores, dtype=float)

    if segment_labels is None:
        segment_labels = [f"Segment {i+1}" for i in range(n)]

    mean_score = float(np.mean(scores_arr))
    std_score = float(np.std(scores_arr, ddof=1)) if n > 1 else 0.0
    max_possible_std = 28.87  # max std for 0-100 range

    # Consistency index: 1.0 = perfectly consistent, 0.0 = highly volatile
    if max_possible_std > 0:
        consistency_index = 1.0 - min(std_score / max_possible_std, 1.0)
    else:
        consistency_index = 1.0

    # Split into halves
    mid = n // 2
    first_half = scores_arr[:mid] if mid > 0 else scores_arr
    second_half = scores_arr[mid:] if mid > 0 else scores_arr

    first_half_avg = float(np.mean(first_half)) if len(first_half) > 0 else 0
    second_half_avg = float(np.mean(second_half)) if len(second_half) > 0 else 0

    delta = second_half_avg - first_half_avg

    # Trend classification
    if std_score < 5:
        trend = "steady"
    elif delta > 8:
        trend = "improving"
    elif delta < -8:
        trend = "degrading"
    else:
        trend = "volatile"

    best_idx = int(np.argmax(scores_arr))
    worst_idx = int(np.argmin(scores_arr))

    # Interpretation
    interpretations = {
        "steady": "Worker maintains consistent quality throughout the task. Reliable performance.",
        "improving": "Worker improves as the task progresses. May benefit from additional preparation time.",
        "degrading": "Quality drops significantly after the midpoint. Possible fatigue or time pressure.",
        "volatile": "Quality varies unpredictably across segments. Inconsistent methodology.",
    }

    return TemporalResult(
        segment_scores=segment_scores,
        segment_labels=segment_labels,
        trend=trend,
        consistency_index=round(consistency_index, 3),
        first_half_avg=round(first_half_avg, 1),
        second_half_avg=round(second_half_avg, 1),
        best_segment_index=best_idx,
        worst_segment_index=worst_idx,
        interpretation=interpretations.get(trend, "No interpretation available"),
    )


def compute_fatigue_warning(result: TemporalResult) -> Dict[str, Any]:
    """
    Generate a fatigue/sustainability warning if quality degrades significantly.

    Only triggers if:
      - Segments >= 3
      - Consistency index < 0.7 AND trend is "degrading"
    """
    n = len(result.segment_scores)
    if n < 3:
        return {"warning": False, "message": "Too few segments to assess fatigue"}

    if result.trend == "degrading" and result.consistency_index < 0.7:
        return {
            "warning": True,
            "message": (
                f"Performance drops from {result.first_half_avg:.0f} to {result.second_half_avg:.0f} "
                f"in the second half. Recommend shorter tasks or scheduled breaks every "
                f"{n//2} segments."
            ),
            "drop_percentage": round(
                (result.first_half_avg - result.second_half_avg) / result.first_half_avg * 100
                if result.first_half_avg > 0 else 0, 1
            ),
        }

    return {
        "warning": False,
        "message": "No significant fatigue detected — consistent performance throughout",
    }
