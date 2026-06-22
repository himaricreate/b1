"""Report generation for TruthLab results."""

from __future__ import annotations

from datetime import datetime, timezone

from modules.scoring import performance_band


def make_markdown_report(index: int, skill_scores: dict[str, int], results: list[dict]) -> str:
    """Build a downloadable Markdown report from the session results."""
    band, summary = performance_band(index)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    correct = sum(1 for row in results if row.get("is_correct"))
    total = len(results)

    lines = [
        "# TruthLab Digital Literacy Report",
        "",
        f"Generated: {timestamp}",
        "",
        "## Overall Result",
        f"- Digital Literacy Index: **{index}/100**",
        f"- Performance band: **{band}**",
        f"- Summary: {summary}",
        f"- Scenarios completed: {total}",
        f"- Correct answers: {correct}",
        "",
        "## Skill Breakdown",
    ]
    for skill, score in skill_scores.items():
        lines.append(f"- {skill}: {score}/100")

    lines.extend(["", "## Scenario Review"])
    for row in results:
        marker = "Correct" if row.get("is_correct") else "Review"
        lines.extend(
            [
                f"### {row['title']}",
                f"- Result: {marker}",
                f"- Your answer: {row['user_answer']}",
                f"- Recommended answer: {row['correct_answer']}",
                f"- Skill focus: {row['skill_focus']}",
                f"- Key lesson: {row['explanation']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Important Note",
            "TruthLab is an educational simulator. It does not perfectly detect misinformation and should not replace professional fact-checking, medical advice, legal advice, or cybersecurity review.",
        ]
    )
    return "\n".join(lines)
