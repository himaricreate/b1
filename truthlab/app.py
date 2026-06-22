"""TruthLab: AI-Guided Misinformation Simulator.

Run with:
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from modules.feedback import build_feedback, verification_tip
from modules.loader import get_categories, load_scenarios
from modules.report import make_markdown_report
from modules.scoring import SKILLS, digital_literacy_index, performance_band, score_answer, skill_breakdown

APP_DIR = Path(__file__).parent
DATA_PATH = APP_DIR / "data" / "scenarios.csv"
ANSWER_CHOICES = ["Trust", "Doubt", "Report", "Verify First"]

st.set_page_config(
    page_title="TruthLab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def cached_scenarios() -> pd.DataFrame:
    """Cache scenario data so the app remains responsive."""
    return load_scenarios(DATA_PATH)


def initialize_state() -> None:
    """Create Streamlit session state keys used by the simulator."""
    defaults = {
        "started": False,
        "scenario_index": 0,
        "results": [],
        "answered_current": False,
        "last_feedback": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_challenge() -> None:
    """Restart the current training session."""
    st.session_state.started = True
    st.session_state.scenario_index = 0
    st.session_state.results = []
    st.session_state.answered_current = False
    st.session_state.last_feedback = ""


def render_header() -> None:
    """Render the app masthead."""
    st.title("TruthLab: AI-Guided Misinformation Simulator")
    st.caption(
        "An educational digital literacy platform for practicing source checks, scam detection, "
        "statistical reasoning, and AI-content awareness."
    )
    st.info(
        "TruthLab is a simulator. It trains recognition of warning signs; it does not perfectly detect misinformation."
    )


def render_welcome(scenarios: pd.DataFrame) -> None:
    """Show the landing page and project framing."""
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Welcome to TruthLab")
        st.write(
            "You will review simulated social media posts and decide whether each one should be trusted, doubted, "
            "reported, or verified first. After each choice, an AI Coach-style explanation highlights the reasoning."
        )
        st.markdown(
            """
            **Training goals**
            - Slow down before sharing emotional or urgent claims.
            - Verify sources, images, statistics, and scholarship offers.
            - Recognize scams, impersonation, and AI-generated media risks.
            - Build a personalized Digital Literacy Index from 0 to 100.
            """
        )
        if st.button("Start Challenge", type="primary", use_container_width=True):
            reset_challenge()
            st.rerun()
    with right:
        st.metric("Scenarios", len(scenarios))
        st.metric("Skill areas", len(SKILLS))
        st.metric("Cost", "No paid APIs")


def render_feed_card(scenario: pd.Series) -> None:
    """Render one simulated social media post."""
    st.markdown(
        f"""
        <div style="border:1px solid #d9dee7;border-radius:16px;padding:1.2rem;background:#ffffff;box-shadow:0 2px 10px rgba(15,23,42,0.06);">
            <div style="font-size:0.85rem;color:#64748b;">{scenario['platform']} · {scenario['category']}</div>
            <h3 style="margin:0.2rem 0 0.4rem 0;color:#0f172a;">{scenario['title']}</h3>
            <div style="font-weight:700;color:#334155;">{scenario['username']}</div>
            <p style="font-size:1.05rem;line-height:1.55;color:#111827;">{scenario['post_text']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def submit_answer(scenario: pd.Series, user_answer: str) -> None:
    """Score the answer, store the result, and prepare coach feedback."""
    score = score_answer(user_answer, scenario["correct_answer"], int(scenario["difficulty"]))
    result = {
        "id": int(scenario["id"]),
        "title": scenario["title"],
        "category": scenario["category"],
        "user_answer": user_answer,
        "correct_answer": scenario["correct_answer"],
        "difficulty": int(scenario["difficulty"]),
        "is_correct": score.is_correct,
        "points_awarded": score.points_awarded,
        "points_possible": score.points_possible,
        "skill_focus": scenario["skill_focus"],
        "explanation": scenario["explanation"],
    }
    st.session_state.results.append(result)
    st.session_state.answered_current = True
    st.session_state.last_feedback = build_feedback(scenario.to_dict(), user_answer, score.is_correct)


def render_challenge(scenarios: pd.DataFrame) -> None:
    """Render the interactive challenge workflow."""
    total = len(scenarios)
    index = st.session_state.scenario_index
    if index >= total:
        render_final_report()
        return

    scenario = scenarios.iloc[index]
    st.progress(index / total, text=f"Scenario {index + 1} of {total}")

    main, coach = st.columns([1.35, 1])
    with main:
        render_feed_card(scenario)
        st.write("")
        choice = st.radio("What is the best response?", ANSWER_CHOICES, horizontal=True)
        if st.button("Submit answer", type="primary", disabled=st.session_state.answered_current):
            submit_answer(scenario, choice)
            st.rerun()

    with coach:
        st.subheader("AI Coach")
        if st.session_state.answered_current:
            st.markdown(st.session_state.last_feedback)
            st.success("Next step: " + verification_tip(scenario["skill_focus"]))
            if st.button("Next scenario", use_container_width=True):
                st.session_state.scenario_index += 1
                st.session_state.answered_current = False
                st.session_state.last_feedback = ""
                st.rerun()
        else:
            st.write("Submit an answer to receive coaching feedback.")
            st.markdown(
                "**Answer guide:** Trust means credible; Doubt means suspicious; Report means likely harmful or deceptive; Verify First means more evidence is needed."
            )


def render_final_report() -> None:
    """Render summary analytics and a downloadable report."""
    results = st.session_state.results
    index = digital_literacy_index(results)
    skills = skill_breakdown(results)
    band, summary = performance_band(index)
    report = make_markdown_report(index, skills, results)

    st.subheader("Final Personalized Report")
    cols = st.columns(3)
    cols[0].metric("Digital Literacy Index", f"{index}/100")
    cols[1].metric("Performance band", band)
    cols[2].metric("Completed", len(results))
    st.write(summary)

    st.markdown("### Skill Breakdown")
    chart_data = pd.DataFrame({"Skill": list(skills.keys()), "Score": list(skills.values())}).set_index("Skill")
    st.bar_chart(chart_data)

    with st.expander("Review scenario results", expanded=True):
        display = pd.DataFrame(results)[["title", "category", "user_answer", "correct_answer", "is_correct", "skill_focus"]]
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.download_button(
        "Download Markdown Report",
        data=report,
        file_name="truthlab_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    if st.button("Restart Challenge", use_container_width=True):
        reset_challenge()
        st.rerun()


def render_about() -> None:
    """Explain the scholarship project and limitations."""
    st.header("About TruthLab")
    st.write(
        "TruthLab is a Computer Science scholarship project that demonstrates modular Python programming, "
        "data-driven scenario design, user interaction, scoring algorithms, and clear educational feedback."
    )
    st.write(
        "The app intentionally avoids paid APIs. Its 'AI Coach' is a transparent rule-based feedback system that explains "
        "the reasoning stored in each educational scenario."
    )
    st.warning(
        "Limitation: TruthLab does not certify whether a real post is true or false. It teaches habits for verification and critical thinking."
    )


def render_sources() -> None:
    """Show concise credits in-app."""
    st.header("Sources and Credits")
    st.markdown(
        """
        - Built with Python, Streamlit, Pandas, Pillow, and Matplotlib-compatible dependencies.
        - Scenario patterns are original educational simulations inspired by general media literacy, phishing prevention, and AI-content verification guidance.
        - See `sources.md` for detailed attribution and reference categories.
        """
    )


def render_sidebar(scenarios: pd.DataFrame) -> None:
    """Render navigation and quick statistics."""
    st.sidebar.header("TruthLab Navigation")
    page = st.sidebar.radio("Go to", ["Simulator", "About", "Sources/Credits"])
    st.sidebar.divider()
    st.sidebar.write("Scenario categories")
    for category in get_categories(scenarios):
        st.sidebar.caption(f"• {category}")
    if st.sidebar.button("Reset session"):
        reset_challenge()
        st.rerun()
    return page


def main() -> None:
    """Main Streamlit entry point."""
    initialize_state()
    scenarios = cached_scenarios()
    render_header()
    page = render_sidebar(scenarios)

    if page == "About":
        render_about()
    elif page == "Sources/Credits":
        render_sources()
    elif not st.session_state.started:
        render_welcome(scenarios)
    else:
        render_challenge(scenarios)


if __name__ == "__main__":
    main()
