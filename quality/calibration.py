"""
Multi-run calibration layer for AI analysis reliability.

Runs analysis multiple times on the same video chunk, measures
output variance, and computes statistical confidence.

Why: A single API call is a point estimate. Three calls with
measured variance tells you how much to trust the result.
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Tuple


@dataclass
class CalibrationResult:
    score: int
    confidence: float           # 0.0 – 1.0  (1/(variance+1))
    reliability: str            # HIGH | MEDIUM | LOW
    variance: float             # raw score variance
    score_range: str            # "lower-upper"  95% CI
    num_runs: int
    individual_scores: List[int]
    recommendation: str


def calibrate(
    analyze_fn: Callable[[str, str], str],
    video_id: str,
    prompt: str,
    parse_fn: Callable[[str], dict],
    num_runs: int = 3,
    run_verification: bool = False,
) -> Tuple[dict, CalibrationResult]:
    """
    Run video analysis multiple times to establish reliability.

    Args:
        analyze_fn:  (video_id, prompt) -> raw text response
        video_id:    Twelve Labs video ID for the chunk
        prompt:      Analysis prompt text
        parse_fn:    (raw_text) -> dict with at least {"score": int}
        num_runs:    Number of repeated analysis calls (default 3)
        run_verification: If True, attach verification filter results

    Returns:
        (best_result, calibration)
        best_result:    parsed dict closest to mean score
        calibration:    CalibrationResult with confidence metrics
    """

    results: List[dict] = []

    for _ in range(num_runs):
        raw_text = analyze_fn(video_id, prompt)
        parsed = parse_fn(raw_text)
        results.append(parsed)

    scores = [int(p.get("score", 0)) for p in results]
    scores_arr = np.array(scores, dtype=float)

    mean_score = float(np.mean(scores_arr))
    std_score = float(np.std(scores_arr, ddof=1))
    variance = float(np.var(scores_arr))

    confidence = 1.0 / (variance + 1.0)

    if std_score > 0:
        margin = 1.96 * (std_score / np.sqrt(num_runs))
    else:
        margin = 0.0

    score_lower = max(0, int(mean_score - margin))
    score_upper = min(100, int(mean_score + margin))

    if variance < 5:
        reliability = "HIGH"
        rec = "All analysis runs agree -- high confidence in this result"
    elif variance < 20:
        reliability = "MEDIUM"
        rec = "Some variation between runs -- result is directionally useful but verify key claims"
    else:
        reliability = "LOW"
        rec = "Runs disagree significantly -- result is unreliable, consider re-recording"

    best_idx = int(np.argmin(np.abs(scores_arr - mean_score)))
    best_result = dict(results[best_idx])
    best_result["score"] = int(round(mean_score))

    calibration = CalibrationResult(
        score=int(round(mean_score)),
        confidence=round(confidence, 3),
        reliability=reliability,
        variance=round(variance, 2),
        score_range=f"{score_lower}-{score_upper}",
        num_runs=num_runs,
        individual_scores=[int(round(s)) for s in scores],
        recommendation=rec,
    )

    if run_verification:
        vf = verification_filter(results, min_occurrence=2)
        best_result["_verification"] = vf

    return best_result, calibration


def verification_filter(
    results_list: List[dict], min_occurrence: int = 2
) -> Dict[str, Any]:
    """
    Cross-run claim verification.

    A violation / strength that only appears in 1 of 3 runs
    is likely a hallucination or noise — flag it separately.

    Args:
        results_list:    Parsed results from each calibration run
        min_occurrence:  Minimum runs a claim must appear in (default 2)

    Returns:
        {
            "verified_violations":   [...],
            "unverified_violations": [...],
            "total_runs": int
        }
    """
    # Count claim frequencies across runs
    violation_freq: Dict[str, int] = {}

    for result in results_list:
        seen_in_this_run = set()
        for v in result.get("violations", []):
            key = v.get("reason", str(v))[:80]
            if key not in seen_in_this_run:
                violation_freq[key] = violation_freq.get(key, 0) + 1
                seen_in_this_run.add(key)

    # Partition
    verified = []
    unverified = []

    for result in results_list:
        for v in result.get("violations", []):
            key = v.get("reason", str(v))[:80]
            freq = violation_freq.get(key, 0)

            v_copy = dict(v)
            v_copy["occurrences"] = freq
            v_copy["verified"] = freq >= min_occurrence

            if freq >= min_occurrence:
                # Deduplicate in verified list
                if not any(x.get("reason") == v.get("reason") for x in verified):
                    verified.append(v_copy)
            else:
                if not any(x.get("reason") == v.get("reason") for x in unverified):
                    unverified.append(v_copy)

    return {
        "verified_violations": verified,
        "unverified_violations": unverified,
        "total_runs": len(results_list),
    }


def aggregate_calibration(
    per_chunk: List[CalibrationResult],
) -> Dict[str, Any]:
    """
    Combine per-chunk calibration into an overall summary.

    Args:
        per_chunk: List of CalibrationResult (one per video chunk)

    Returns:
        Aggregate dict with mean confidence, worst reliability, etc.
    """
    if not per_chunk:
        return {"confidence": 0.0, "reliability": "LOW", "chunks": 0}

    confidences = [c.confidence for c in per_chunk]
    mean_confidence = round(float(np.mean(confidences)), 3)

    reliability_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    worst_reliability = max(per_chunk, key=lambda c: reliability_order.get(c.reliability, 2))

    score_ranges = []
    for c in per_chunk:
        parts = c.score_range.split("-")
        if len(parts) == 2:
            score_ranges.append((int(parts[0]), int(parts[1])))

    if score_ranges:
        agg_lower = max(r[0] for r in score_ranges)
        agg_upper = min(r[1] for r in score_ranges)
        if agg_lower > agg_upper:
            agg_lower, agg_upper = agg_upper, agg_lower
        agg_range = f"{agg_lower}-{agg_upper}"
    else:
        agg_range = "0-100"

    return {
        "mean_confidence": mean_confidence,
        "worst_reliability": worst_reliability.reliability,
        "aggregate_score_range": agg_range,
        "mean_variance": round(float(np.mean([c.variance for c in per_chunk])), 2),
        "total_runs_per_chunk": per_chunk[0].num_runs if per_chunk else 0,
        "chunks": len(per_chunk),
    }
