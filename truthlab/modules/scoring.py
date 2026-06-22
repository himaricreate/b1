"""Scoring logic for TruthLab.

The score is an educational Digital Literacy Index. It estimates how well a
participant noticed warning signs in the simulator; it is not a real-world truth
or misinformation detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SKILLS = [
    "Source Verification",
    "Emotional Manipulation Detection",
    "AI Content Awareness",
    "Scam Detection",
    "Statistical Reasoning",
]

ANSWER_RATIONALE = {
    "Trust": "You judged the post as generally credible based on the provided evidence.",
    "Doubt": "You noticed warning signs and treated the post as suspicious.",
    "Report": "You identified the post as harmful, deceptive, or likely policy-violating.",
    "Verify First": "You chose to pause and check reliable sources before accepting or sharing.",
}


@dataclass(frozen=True)
class ScoreResult:
    """Computed score fields for one answered scenario."""

    is_correct: bool
    points_awarded: int
    points_possible: int


def score_answer(user_answer: str, correct_answer: str, difficulty: int) -> ScoreResult:
    """Score a single answer with difficulty-weighted points."""
    points_possible = max(1, int(difficulty)) * 10
    is_correct = user_answer == correct_answer
    return ScoreResult(
        is_correct=is_correct,
        points_awarded=points_possible if is_correct else 0,
        points_possible=points_possible,
    )


def digital_literacy_index(results: Iterable[dict]) -> int:
    """Calculate a 0-100 Digital Literacy Index from answer records."""
    results = list(results)
    if not results:
        return 0
    awarded = sum(int(row.get("points_awarded", 0)) for row in results)
    possible = sum(int(row.get("points_possible", 0)) for row in results)
    if possible == 0:
        return 0
    return round((awarded / possible) * 100)


def skill_breakdown(results: Iterable[dict]) -> dict[str, int]:
    """Calculate 0-100 performance by skill focus."""
    totals = {skill: {"awarded": 0, "possible": 0} for skill in SKILLS}
    for row in results:
        skill = row.get("skill_focus")
        if skill not in totals:
            continue
        totals[skill]["awarded"] += int(row.get("points_awarded", 0))
        totals[skill]["possible"] += int(row.get("points_possible", 0))

    return {
        skill: round((values["awarded"] / values["possible"]) * 100)
        if values["possible"]
        else 0
        for skill, values in totals.items()
    }


def performance_band(index: int) -> tuple[str, str]:
    """Convert a numeric index into an interpretable coaching band."""
    if index >= 85:
        return "Advanced analyst", "Excellent pattern recognition and verification habits."
    if index >= 70:
        return "Careful evaluator", "Strong judgment with a few opportunities to slow down."
    if index >= 50:
        return "Developing verifier", "You caught some signals but should practice checking sources."
    return "Needs more practice", "Focus on source checks, emotional wording, and too-good-to-be-true claims."
