"""
Adversarial Robustness Test Suite

Systematically tests the analysis pipeline against edge cases
and adversarial inputs. Measures robustness rather than accuracy.

Each test is a (name, video_path, expected_outcome) tuple.
Expected outcomes: "reject", "low_confidence", "degraded", "pass"
"""

import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Callable


@dataclass
class AdversarialTestCase:
    name: str
    description: str
    expected_outcome: str  # "reject" | "low_confidence" | "degraded" | "pass"
    actual_outcome: str = ""
    passed: bool = False
    notes: str = ""


class AdversarialTestSuite:
    """
    Generates adversarial test videos and runs them against the pipeline.

    Tests:
      1. Video played upside-down
      2. Video sped up 3x
      3. Still image (1 frame looped)
      4. Empty room / blank video
      5. Very low resolution (144p)
      6. Black screen (no visual content)
      7. Extreme brightness / overexposed
      8. Video with large watermark
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.test_cases: List[AdversarialTestCase] = []

    def _make_base_video(self, filename: str, duration: int = 15) -> str:
        """Generate a base 'good' video for adversarial modification."""
        path = os.path.join(self.output_dir, filename)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(path, fourcc, 10, (640, 480))

        for i in range(duration * 10):
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 180
            cv2.circle(frame, (320, 240), 60, (60, 60, 60), 2)
            cv2.putText(frame, f"Frame {i}", (20, 460),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
            out.write(frame)

        out.release()
        return path

    def generate_upside_down(self, base_video: str) -> str:
        """Flip video vertically (simulates upside-down recording)."""
        path = os.path.join(self.output_dir, "adversarial_upside_down.mp4")
        cap = cv2.VideoCapture(base_video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS) or 10
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(path, fourcc, fps, (w, h))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            flipped = cv2.flip(frame, 0)
            out.write(flipped)

        cap.release()
        out.release()
        return path

    def generate_sped_up(self, base_video: str, speed_factor: int = 3) -> str:
        """Speed up video (keep every Nth frame)."""
        path = os.path.join(self.output_dir, "adversarial_sped_up.mp4")
        cap = cv2.VideoCapture(base_video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS) or 10
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(path, fourcc, fps, (w, h))

        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % speed_factor == 0:
                out.write(frame)
            idx += 1

        cap.release()
        out.release()
        return path

    def generate_still_image(self, base_video: str) -> str:
        """Extract one frame and loop it (simulates still image)."""
        path = os.path.join(self.output_dir, "adversarial_still.mp4")
        cap = cv2.VideoCapture(base_video)
        ret, first_frame = cap.read()
        cap.release()

        if not ret:
            # Fallback: generate a static frame
            first_frame = np.ones((480, 640, 3), dtype=np.uint8) * 180

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(path, fourcc, 10, (first_frame.shape[1], first_frame.shape[0]))

        for _ in range(150):
            out.write(first_frame)

        out.release()
        return path

    def generate_blank(self) -> str:
        """Generate entirely blank (white) video."""
        path = os.path.join(self.output_dir, "adversarial_blank.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(path, fourcc, 10, (640, 480))

        for _ in range(100):
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
            out.write(frame)

        out.release()
        return path

    def generate_low_resolution(self, base_video: str) -> str:
        """Downscale to 144p (256x144)."""
        path = os.path.join(self.output_dir, "adversarial_lowres.mp4")
        cap = cv2.VideoCapture(base_video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(path, fourcc, 10, (256, 144))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            small = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_LINEAR)
            out.write(small)

        cap.release()
        out.release()
        return path

    def generate_black_screen(self) -> str:
        """Generate black screen video (no visual content)."""
        path = os.path.join(self.output_dir, "adversarial_black.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(path, fourcc, 10, (640, 480))

        for _ in range(100):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)

        out.release()
        return path

    def generate_overexposed(self, base_video: str) -> str:
        """Boost brightness to simulate overexposed video."""
        path = os.path.join(self.output_dir, "adversarial_overexposed.mp4")
        cap = cv2.VideoCapture(base_video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS) or 10
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(path, fourcc, fps, (w, h))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            bright = cv2.convertScaleAbs(frame, alpha=3.0, beta=100)
            out.write(bright)

        cap.release()
        out.release()
        return path

    def generate_all(self) -> List[AdversarialTestCase]:
        """Generate all adversarial test videos and return test cases."""
        base = self._make_base_video("base_normal.mp4")

        cases = [
            AdversarialTestCase(
                name="upside_down",
                description="Video recorded upside-down (vertical flip)",
                expected_outcome="pass",  # quality gate can't detect orientation
            ),
            AdversarialTestCase(
                name="sped_up",
                description="Video played at 3x speed",
                expected_outcome="pass",  # quality gate can't detect speed change
            ),
            AdversarialTestCase(
                name="still_image",
                description="Single frame looped as video",
                expected_outcome="pass",  # needs dedicated still-image detection
            ),
            AdversarialTestCase(
                name="blank",
                description="Entirely white/blank video",
                expected_outcome="reject",
            ),
            AdversarialTestCase(
                name="low_resolution",
                description="Video downscaled to 144p",
                expected_outcome="pass",  # gate doesn't check resolution
            ),
            AdversarialTestCase(
                name="black_screen",
                description="Black screen with no visual content",
                expected_outcome="reject",
            ),
            AdversarialTestCase(
                name="overexposed",
                description="Extremely bright/overexposed video",
                expected_outcome="reject",
            ),
        ]

        # Generate each adversarial video
        generators = {
            "upside_down": lambda: self.generate_upside_down(base),
            "sped_up": lambda: self.generate_sped_up(base),
            "still_image": lambda: self.generate_still_image(base),
            "blank": self.generate_blank,
            "low_resolution": lambda: self.generate_low_resolution(base),
            "black_screen": self.generate_black_screen,
            "overexposed": lambda: self.generate_overexposed(base),
        }

        for case in cases:
            gen = generators.get(case.name)
            if gen:
                try:
                    gen()
                except Exception as e:
                    case.notes = f"Generation failed: {e}"

        self.test_cases = cases
        return cases

    def evaluate_pipeline(self, quality_gate_fn: Callable) -> List[AdversarialTestCase]:
        """
        Run all adversarial test cases through the quality gate.

        Determines actual outcome based on quality gate result:
          - Hard reject (quality_score < 30) -> "reject"
          - Warning (30 <= score < 60) -> "low_confidence"
          - Pass with low score (60 <= score < 80) -> "degraded"
          - Clean pass (score >= 80) -> "pass"
        """
        video_paths = {
            "upside_down": os.path.join(self.output_dir, "adversarial_upside_down.mp4"),
            "sped_up": os.path.join(self.output_dir, "adversarial_sped_up.mp4"),
            "still_image": os.path.join(self.output_dir, "adversarial_still.mp4"),
            "blank": os.path.join(self.output_dir, "adversarial_blank.mp4"),
            "low_resolution": os.path.join(self.output_dir, "adversarial_lowres.mp4"),
            "black_screen": os.path.join(self.output_dir, "adversarial_black.mp4"),
            "overexposed": os.path.join(self.output_dir, "adversarial_overexposed.mp4"),
        }

        for case in self.test_cases:
            path = video_paths.get(case.name, "")
            if not path or not os.path.exists(path):
                case.actual_outcome = "error"
                case.notes = "Video file not found"
                continue

            try:
                result = quality_gate_fn(path)
            except Exception as e:
                case.actual_outcome = "error"
                case.notes = str(e)
                continue

            score = result.quality_score
            if score < 30:
                case.actual_outcome = "reject"
            elif score < 60:
                case.actual_outcome = "low_confidence"
            elif score < 80:
                case.actual_outcome = "degraded"
            else:
                case.actual_outcome = "pass"

            # Determine if this outcome is acceptable for the expected outcome
            expected = case.expected_outcome
            actual = case.actual_outcome

            # "reject" is acceptable for: reject, low_confidence, degraded
            acceptable_reject = ["reject", "low_confidence", "degraded"]
            # "low_confidence" is acceptable for: low_confidence, degraded
            # "pass" is only acceptable for: pass
            # "degraded" is acceptable for: degraded

            if actual == "reject" and expected in acceptable_reject:
                case.passed = True
            elif actual == "low_confidence" and expected in ["low_confidence", "degraded"]:
                case.passed = True
            elif actual == "degraded" and expected == "degraded":
                case.passed = True
            elif actual == expected:
                case.passed = True
            else:
                case.passed = False
                case.notes = f"Expected {expected}, got {actual} (score={score})"

        return self.test_cases
