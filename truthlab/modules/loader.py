"""Data-loading utilities for TruthLab.

This module isolates file access from the Streamlit interface so the app is
simpler to test and maintain. The simulator uses curated educational scenarios,
not live claims or automated misinformation detection.
"""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "id",
    "title",
    "platform",
    "username",
    "post_text",
    "category",
    "correct_answer",
    "difficulty",
    "red_flags",
    "explanation",
    "skill_focus",
    "source_note",
}


def load_scenarios(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate scenario data from a CSV file.

    Args:
        csv_path: Path to the scenario CSV.

    Returns:
        A validated pandas DataFrame sorted by scenario id.

    Raises:
        FileNotFoundError: If the CSV is missing.
        ValueError: If required columns or scenarios are missing.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    scenarios = pd.read_csv(path)
    missing_columns = REQUIRED_COLUMNS.difference(scenarios.columns)
    if missing_columns:
        raise ValueError(f"Scenario CSV is missing columns: {sorted(missing_columns)}")
    if scenarios.empty:
        raise ValueError("Scenario CSV must contain at least one scenario.")

    scenarios = scenarios.copy()
    scenarios["id"] = scenarios["id"].astype(int)
    scenarios["difficulty"] = scenarios["difficulty"].astype(int).clip(1, 5)
    return scenarios.sort_values("id").reset_index(drop=True)


def get_categories(scenarios: pd.DataFrame) -> list[str]:
    """Return category names for filtering controls."""
    return sorted(scenarios["category"].dropna().unique().tolist())
