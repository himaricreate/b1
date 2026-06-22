"""AI Coach-style feedback templates for TruthLab."""

from modules.scoring import ANSWER_RATIONALE


def build_feedback(scenario: dict, user_answer: str, is_correct: bool) -> str:
    """Create concise coaching feedback after a user answers a scenario."""
    status = "Correct" if is_correct else "Not quite"
    opening = (
        "You matched the safest interpretation of this scenario."
        if is_correct
        else "This answer misses at least one important warning sign or credibility cue."
    )
    rationale = ANSWER_RATIONALE.get(user_answer, "You made a judgment about the post.")

    return (
        f"**{status}.** {opening}\n\n"
        f"**Your choice:** {user_answer}. {rationale}\n\n"
        f"**Recommended choice:** {scenario['correct_answer']}\n\n"
        f"**Why:** {scenario['explanation']}\n\n"
        f"**Red flags or credibility cues:** {scenario['red_flags']}\n\n"
        f"**Skill focus:** {scenario['skill_focus']}"
    )


def verification_tip(skill_focus: str) -> str:
    """Return one practical next step based on the scenario skill."""
    tips = {
        "Source Verification": "Open the original source, check the author or organization, and compare with another reputable source.",
        "Emotional Manipulation Detection": "Pause when a post demands outrage, fear, or immediate sharing before evidence is shown.",
        "AI Content Awareness": "Look for provenance, image context, reverse-image results, and whether trusted outlets confirm the media.",
        "Scam Detection": "Never enter personal data through unsolicited links; verify opportunities on official domains.",
        "Statistical Reasoning": "Ask what is being measured, sample size, baseline rates, and whether the graph scale is misleading.",
    }
    return tips.get(skill_focus, "Verify claims with reliable independent sources before sharing.")
