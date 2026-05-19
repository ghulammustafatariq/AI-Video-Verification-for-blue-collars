"""
Skill Gap Roadmap Generator

Translates AI analysis results into actionable improvement steps.
Each step has an impact score and difficulty level.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ImprovementStep:
    action: str
    impact_points: int        # How many score points this action adds
    difficulty: str           # "Easy" | "Medium" | "Hard"
    category: str             # "safety" | "technique" | "professionalism"
    based_on: str             # Which finding this recommendation comes from


@dataclass
class SkillGapRoadmap:
    current_score: int
    current_level: str
    target_level: str
    target_score: int
    steps: List[ImprovementStep]
    potential_score: int       # Score achievable if all steps taken
    estimated_timeline: str


# ── Predefined improvement mappings ──

IMPROVEMENT_MAP = {
    "no gloves": ImprovementStep(
        action="Wear appropriate safety gloves during all tasks",
        impact_points=5,
        difficulty="Easy",
        category="safety",
        based_on="No gloves detected",
    ),
    "no safety glasses": ImprovementStep(
        action="Wear safety glasses consistently throughout the task",
        impact_points=4,
        difficulty="Easy",
        category="safety",
        based_on="No safety glasses detected",
    ),
    "no helmet": ImprovementStep(
        action="Wear a hard hat / helmet on construction sites",
        impact_points=5,
        difficulty="Easy",
        category="safety",
        based_on="No helmet detected",
    ),
    "wrong tool": ImprovementStep(
        action="Use the correct tool for each task (avoid improvised tools)",
        impact_points=7,
        difficulty="Medium",
        category="technique",
        based_on="Wrong tool usage detected",
    ),
    "poor technique": ImprovementStep(
        action="Practice correct technique — consider watching training videos or shadowing a senior technician",
        impact_points=8,
        difficulty="Hard",
        category="technique",
        based_on="Poor technique observed",
    ),
    "messy workspace": ImprovementStep(
        action="Keep workspace clean and organized — clear debris before starting",
        impact_points=3,
        difficulty="Easy",
        category="professionalism",
        based_on="Messy workspace",
    ),
    "no measuring": ImprovementStep(
        action="Always measure before cutting/installing — reduces waste and rework",
        impact_points=4,
        difficulty="Medium",
        category="technique",
        based_on="Missing measurement step",
    ),
    "rushed": ImprovementStep(
        action="Take adequate time per task — rushing leads to mistakes",
        impact_points=6,
        difficulty="Medium",
        category="professionalism",
        based_on="Task appears rushed / hurried",
    ),
    "unsafe position": ImprovementStep(
        action="Maintain proper body position — avoid awkward angles that cause injury",
        impact_points=6,
        difficulty="Medium",
        category="safety",
        based_on="Unsafe body position detected",
    ),
    "no cleanup": ImprovementStep(
        action="Clean the work area after completing the task",
        impact_points=2,
        difficulty="Easy",
        category="professionalism",
        based_on="No cleanup after work",
    ),
}


def generate_roadmap(
    violations: List[dict],
    current_score: int,
    current_level: str,
    target_level: str = None,
) -> SkillGapRoadmap:
    """
    Generate a personalized skill improvement roadmap.

    Args:
        violations: List of violation dicts with 'reason' key
        current_score: Current overall score
        current_level: Current skill level string
        target_level: Desired target level (auto-calculated if None)

    Returns:
        SkillGapRoadmap with prioritized steps
    """
    # Determine target level (one tier above current)
    LEVELS = ["Not Yet Ready", "Developing", "Competent", "Experienced", "Master"]
    LEVEL_MIN_SCORES = {"Not Yet Ready": 0, "Developing": 40, "Competent": 60, "Experienced": 75, "Master": 90}

    if target_level is None:
        try:
            current_idx = LEVELS.index(current_level)
            target_level = LEVELS[min(current_idx + 1, len(LEVELS) - 1)]
        except ValueError:
            target_level = "Experienced"

    target_score = LEVEL_MIN_SCORES.get(target_level, 80)

    # Prevent target <= current
    if target_score <= current_score:
        target_score = min(current_score + 10, 100)
        if target_level == current_level:
            for lvl in reversed(LEVELS):
                if LEVEL_MIN_SCORES[lvl] > current_score:
                    target_level = lvl
                    target_score = LEVEL_MIN_SCORES[lvl]
                    break

    # Match violations to improvement steps
    steps = []
    seen_actions = set()

    for violation in violations:
        reason = violation.get("reason", "").lower()
        for keyword, step in IMPROVEMENT_MAP.items():
            if keyword in reason and step.action not in seen_actions:
                steps.append(ImprovementStep(
                    action=step.action,
                    impact_points=step.impact_points,
                    difficulty=step.difficulty,
                    category=step.category,
                    based_on=step.based_on,
                ))
                seen_actions.add(step.action)

    # Sort by: easy first, then by impact (descending)
    difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    steps.sort(key=lambda s: (difficulty_order[s.difficulty], -s.impact_points))

    # Calculate potential score
    potential = current_score + sum(s.impact_points for s in steps)
    potential = min(potential, 100)

    # Estimate timeline
    easy_count = sum(1 for s in steps if s.difficulty == "Easy")
    medium_count = sum(1 for s in steps if s.difficulty == "Medium")
    hard_count = sum(1 for s in steps if s.difficulty == "Hard")

    total_weeks = easy_count * 0.5 + medium_count * 1 + hard_count * 2

    if total_weeks <= 1:
        timeline = "1 week"
    elif total_weeks <= 4:
        timeline = f"{int(total_weeks)}-{int(total_weeks + 1)} weeks"
    else:
        timeline = f"{int(total_weeks // 4)}-{int(total_weeks // 4 + 1)} months"

    return SkillGapRoadmap(
        current_score=current_score,
        current_level=current_level,
        target_level=target_level,
        target_score=target_score,
        steps=steps[:6],  # Max 6 recommendations
        potential_score=potential,
        estimated_timeline=timeline,
    )
