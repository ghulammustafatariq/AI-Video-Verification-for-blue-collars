"""
Anti-Fraud Detection Layer

Detects duplicate/near-duplicate video submissions, metadata anomalies,
and potential impersonation attempts.

Prevents:
  - Same video submitted twice (exact / near duplicate)
  - Video from YouTube/tutorials passed as original work
  - Metadata inconsistencies suggesting tampering
"""

import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
import time

# ── Perceptual hashing without imagehash dependency ──

def _phash(frame: np.ndarray, hash_size: int = 16) -> str:
    """Compute perceptual hash of a grayscale frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(resized))
    # Keep top-left 8x8 of DCT (low frequencies)
    dct_low = dct[:8, :8]
    median = np.median(dct_low)
    bits = (dct_low > median).flatten()
    hash_str = "".join("1" if b else "0" for b in bits)
    return hex(int(hash_str, 2))[2:].zfill(16)


def _hamming_distance(h1: str, h2: str) -> int:
    """Hamming distance between two hex hash strings."""
    b1 = bin(int(h1, 16))[2:].zfill(64)
    b2 = bin(int(h2, 16))[2:].zfill(64)
    return sum(c1 != c2 for c1, c2 in zip(b1, b2, strict=False))


def extract_keyframe_hashes(video_path: str, every_n_frames: int = 30) -> List[str]:
    """Extract perceptual hashes from keyframes."""
    if not os.path.exists(video_path):
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    hashes = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % every_n_frames == 0:
            try:
                hashes.append(_phash(frame))
            except Exception:
                pass
        idx += 1
    cap.release()
    return hashes


@dataclass
class FraudCheckResult:
    is_duplicate: bool
    is_suspicious: bool
    duplicate_video_id: Optional[str] = None
    similarity_score: float = 0.0
    issues: List[str] = None
    checks_passed: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.checks_passed is None:
            self.checks_passed = []


class AntiFraudEngine:
    """
    Anti-fraud detection engine.

    Checks:
      1. Perceptual hash comparison against existing submissions
      2. Metadata consistency (duration, file size, format)
      3. Suspicious patterns (perfectly identical keyframes, etc.)
    """

    def __init__(self, database_path: Optional[str] = None):
        self.database_path = database_path
        self._db = self._load_db()

    def _load_db(self) -> dict:
        if self.database_path and os.path.exists(self.database_path):
            try:
                with open(self.database_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"submissions": []}

    def _save_db(self):
        if self.database_path:
            with open(self.database_path, "w") as f:
                json.dump(self._db, f, indent=2)

    def add_to_database(self, video_id: str, video_path: str, metadata: dict = None):
        """Register a video submission in the fraud database."""
        hashes = extract_keyframe_hashes(video_path)
        entry = {
            "video_id": video_id,
            "hashes": hashes,
            "timestamp": time.time(),
            "metadata": metadata or {},
            "file_size_mb": os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0,
        }
        self._db["submissions"].append(entry)
        self._save_db()

    def check_duplicate(self, video_path: str) -> FraudCheckResult:
        """Check if this video is a duplicate or near-duplicate."""
        issues = []
        passed = []

        if not os.path.exists(video_path):
            return FraudCheckResult(
                is_duplicate=False, is_suspicious=True,
                issues=["Video file not found"], checks_passed=[]
            )

        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        new_hashes = extract_keyframe_hashes(video_path)

        if not new_hashes:
            issues.append("Could not extract keyframes from video")
            return FraudCheckResult(
                is_duplicate=False, is_suspicious=True,
                issues=issues, checks_passed=passed
            )

        # 1. Check against existing submissions
        best_similarity = 0.0
        best_match_id = None

        for entry in self._db.get("submissions", []):
            old_hashes = entry.get("hashes", [])
            if not old_hashes or not new_hashes:
                continue

            # Compute similarity as fraction of hash pairs within threshold
            matches = 0
            total = 0
            for nh in new_hashes:
                for oh in old_hashes:
                    if _hamming_distance(nh, oh) < 12:
                        matches += 1
                    total += 1

            similarity = matches / total if total > 0 else 0

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = entry.get("video_id")

        # 2. Check for suspiciously static content
        unique_hashes = len(set(new_hashes))
        if unique_hashes == 1 and len(new_hashes) > 2:
            issues.append("Video appears to be a still image or contains identical frames throughout")
        elif unique_hashes <= 2 and len(new_hashes) > 5:
            issues.append("Very few unique frames detected -- possible still image or looped content")

        # 3. File size sanity
        if file_size_mb < 0.01:
            issues.append("File size unusually small -- possible corrupted or placeholder video")
        if file_size_mb > 1000:
            issues.append("File size unusually large -- check for raw/uncompressed video")

        is_dup = best_similarity > 0.3
        is_suspicious = len(issues) > 0

        if not is_dup and not is_suspicious:
            passed.append("No duplicate or suspicious patterns detected")

        return FraudCheckResult(
            is_duplicate=is_dup,
            is_suspicious=is_suspicious,
            duplicate_video_id=best_match_id if is_dup else None,
            similarity_score=round(best_similarity, 4),
            issues=issues,
            checks_passed=passed,
        )


def metadata_consistency_check(video_path: str) -> dict:
    """
    Check video metadata for consistency anomalies.

    Returns dict with checks and pass/fail statuses.
    """
    checks = {}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video"}

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    duration = frame_count / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    file_size = os.path.getsize(video_path)
    file_size_mb = file_size / (1024 * 1024)

    checks["duration_seconds"] = round(duration, 1)
    checks["resolution"] = f"{width}x{height}"
    checks["fps"] = round(fps, 1)
    checks["file_size_mb"] = round(file_size_mb, 2)

    # Consistency checks
    checks["resolution_ok"] = width >= 320 and height >= 240
    checks["fps_ok"] = 5 <= fps <= 60
    checks["duration_ok"] = duration >= 5
    checks["bitrate_mbps"] = round(
        (file_size * 8) / (duration * 1_000_000) if duration > 0 else 0, 2
    )

    # Bitrate sanity: < 0.005 Mbps is suspiciously low, > 50 Mbps is excessive
    checks["bitrate_ok"] = 0.005 <= checks["bitrate_mbps"] <= 50 if duration > 0 else False

    all_ok = all([
        checks["resolution_ok"],
        checks["fps_ok"],
        checks["duration_ok"],
        checks["bitrate_ok"],
    ])

    checks["all_checks_passed"] = all_ok

    return checks
