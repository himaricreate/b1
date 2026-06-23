"""TruthLab: AI-Guided Misinformation Simulator.

Run with:
    streamlit run app.py
"""

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.feedback import verification_tip
from modules.loader import get_categories, load_scenarios
from modules.report import make_markdown_report
from modules.scoring import SKILLS, digital_literacy_index, performance_band, score_answer, skill_breakdown

APP_DIR = Path(__file__).parent
DATA_PATH = APP_DIR / "data" / "scenarios.csv"
ANSWER_CHOICES = ["Trust", "Doubt", "Report", "Verify First"]
ANSWER_STYLES = {
    "Trust": {"icon": "✓", "class": "trust", "caption": "Credible enough to accept"},
    "Doubt": {"icon": "?", "class": "doubt", "caption": "Suspicious or incomplete"},
    "Report": {"icon": "!", "class": "report", "caption": "Likely harmful or deceptive"},
    "Verify First": {"icon": "⌕", "class": "verify", "caption": "Pause and check evidence"},
}

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
        "last_answer": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def inject_css() -> None:
    """Apply the TruthLab product theme with Streamlit-safe custom CSS."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        :root {
            --bg: #050816;
            --panel: rgba(15, 23, 42, 0.78);
            --panel-strong: rgba(15, 23, 42, 0.94);
            --line: rgba(148, 163, 184, 0.22);
            --text: #e5f0ff;
            --muted: #9fb1cc;
            --cyan: #22d3ee;
            --blue: #60a5fa;
            --purple: #a78bfa;
            --green: #86efac;
            --red: #fb7185;
            --amber: #fbbf24;
        }

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp {
            color: var(--text);
            background:
                radial-gradient(circle at 15% 10%, rgba(34, 211, 238, 0.19), transparent 28%),
                radial-gradient(circle at 85% 0%, rgba(167, 139, 250, 0.22), transparent 28%),
                radial-gradient(circle at 70% 85%, rgba(96, 165, 250, 0.16), transparent 30%),
                linear-gradient(135deg, #020617 0%, #08111f 48%, #050816 100%);
        }
        section[data-testid="stSidebar"] {
            background: rgba(2, 6, 23, 0.78);
            border-right: 1px solid var(--line);
            backdrop-filter: blur(18px);
        }
        section[data-testid="stSidebar"] * { color: var(--text); }
        h1, h2, h3 { color: #f8fbff; letter-spacing: -0.03em; }
        p, li, label, span { color: inherit; }
        .block-container { padding-top: 2rem; max-width: 1240px; }

        .fade-in { animation: truthlabFade 0.75s ease both; }
        @keyframes truthlabFade {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .glass-card {
            border: 1px solid var(--line);
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.52));
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
            border-radius: 26px;
            padding: 1.35rem;
            backdrop-filter: blur(20px);
            transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
        }
        .glass-card:hover {
            transform: translateY(-3px);
            border-color: rgba(34, 211, 238, 0.45);
            box-shadow: 0 28px 85px rgba(34, 211, 238, 0.12);
        }
        .hero {
            min-height: 560px;
            display: grid;
            grid-template-columns: 1.2fr .8fr;
            gap: 1.5rem;
            align-items: stretch;
        }
        .hero-title {
            font-size: clamp(4rem, 9vw, 8rem);
            line-height: .88;
            margin: .4rem 0;
            background: linear-gradient(90deg, #e0fbff, var(--cyan), var(--purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 42px rgba(34, 211, 238, .18);
        }
        .hero-subtitle { font-size: clamp(1.35rem, 2.5vw, 2.25rem); font-weight: 800; margin: 0; }
        .tagline { color: var(--muted); font-size: 1.15rem; max-width: 720px; }
        .pill-row { display:flex; flex-wrap:wrap; gap:.65rem; margin-top:1rem; }
        .pill {
            border: 1px solid rgba(125, 211, 252, .25);
            color: #dff7ff;
            background: rgba(14, 165, 233, .10);
            border-radius: 999px;
            padding: .42rem .72rem;
            font-size: .84rem;
            font-weight: 700;
        }
        .metric-tile {
            border-radius: 22px;
            border: 1px solid var(--line);
            padding: 1rem;
            background: rgba(2, 6, 23, .44);
        }
        .metric-number { font-size: 2rem; font-weight: 800; color: var(--green); }
        .metric-label { color: var(--muted); font-size: .85rem; }
        .simulation-shell { display:grid; grid-template-columns: 1.18fr .82fr; gap:1.1rem; align-items:start; }
        .feed-card { position:relative; overflow:hidden; }
        .feed-card:before {
            content:""; position:absolute; inset:0 0 auto 0; height:4px;
            background: linear-gradient(90deg, var(--cyan), var(--purple), var(--green));
        }
        .feed-meta { display:flex; align-items:center; justify-content:space-between; gap:.7rem; margin-bottom:.9rem; }
        .platform-label { color: var(--cyan); font-weight:800; text-transform:uppercase; letter-spacing:.12em; font-size:.78rem; }
        .badge { border-radius:999px; padding:.35rem .65rem; font-size:.75rem; font-weight:800; border:1px solid var(--line); }
        .category-badge { background: rgba(167, 139, 250, .14); color:#ddd6fe; }
        .difficulty-badge { background: rgba(251, 191, 36, .12); color:#fde68a; }
        .post-user { color:#c7d2fe; font-weight:800; margin-bottom:.65rem; }
        .post-title { font-size:1.55rem; font-weight:800; margin:.15rem 0 .55rem; color:#f8fbff; }
        .post-text { color:#d9e6ff; font-size:1.12rem; line-height:1.65; }
        .engagement { display:flex; gap:.8rem; flex-wrap:wrap; margin-top:1rem; color:var(--muted); font-size:.86rem; }
        .engagement span { border:1px solid var(--line); padding:.38rem .58rem; border-radius:999px; background:rgba(15, 23, 42, .66); }
        .answer-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:.75rem; margin-top:.8rem; }
        .answer-card {
            min-height: 112px;
            border-radius: 22px;
            padding: 1rem;
            border: 1px solid var(--line);
            background: rgba(15, 23, 42, .67);
            transition: transform .18s ease, border-color .18s ease, background .18s ease;
        }
        .answer-card:hover { transform: translateY(-4px); border-color: rgba(34, 211, 238, .52); background: rgba(30, 41, 59, .72); }
        .answer-icon { font-size: 1.65rem; font-weight: 900; }
        .answer-title { font-weight: 850; color:#f8fbff; margin:.25rem 0; }
        .answer-caption { color:var(--muted); font-size:.82rem; line-height:1.35; }
        .trust .answer-icon { color: var(--green); } .doubt .answer-icon { color: var(--amber); }
        .report .answer-icon { color: var(--red); } .verify .answer-icon { color: var(--cyan); }
        .coach-section { border-left: 3px solid var(--cyan); padding-left:.85rem; margin:.85rem 0; }
        .coach-label { color: var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.1em; font-weight:850; }
        .coach-value { color:#eff6ff; font-weight:650; line-height:1.5; }
        .score-orb {
            width: 210px; height: 210px; border-radius: 50%; margin: 0 auto 1rem;
            display:flex; flex-direction:column; justify-content:center; align-items:center;
            background: conic-gradient(var(--cyan) calc(var(--score) * 1%), rgba(30, 41, 59, .75) 0), radial-gradient(circle, #07111f 60%, transparent 61%);
            box-shadow: 0 0 50px rgba(34, 211, 238, .19), inset 0 0 30px rgba(2, 6, 23, .85);
            border: 1px solid rgba(34, 211, 238, .25);
        }
        .score-number { font-size: 3.3rem; font-weight: 900; color:#f8fbff; line-height:1; }
        .score-label { color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.1em; }
        .skill-card { margin-bottom:.75rem; }
        .skill-top { display:flex; justify-content:space-between; gap:1rem; font-weight:800; margin-bottom:.45rem; }
        .skill-track { height: 11px; border-radius:999px; background: rgba(51, 65, 85, .8); overflow:hidden; }
        .skill-fill { height:100%; border-radius:999px; background: linear-gradient(90deg, var(--cyan), var(--purple)); box-shadow:0 0 16px rgba(34,211,238,.28); }
        .method-grid { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:1rem; }
        div.stButton > button, div.stDownloadButton > button {
            border: 0 !important;
            color: #02111f !important;
            font-weight: 850 !important;
            border-radius: 999px !important;
            background: linear-gradient(90deg, var(--cyan), var(--purple)) !important;
            box-shadow: 0 12px 32px rgba(34, 211, 238, .18) !important;
            transition: transform .18s ease, box-shadow .18s ease !important;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover { transform: translateY(-2px); box-shadow:0 18px 38px rgba(167,139,250,.24) !important; }
        .stProgress > div > div > div > div { background: linear-gradient(90deg, var(--cyan), var(--purple), var(--green)); }
        [data-testid="stMetric"] { background: rgba(15, 23, 42, .55); border:1px solid var(--line); border-radius:18px; padding:1rem; }
        [data-testid="stDataFrame"] { border-radius: 18px; overflow:hidden; }
        @media (max-width: 980px) { .hero, .simulation-shell, .method-grid { grid-template-columns:1fr; } .answer-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 620px) { .answer-grid { grid-template-columns:1fr; } .hero-title { font-size:3.4rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_challenge() -> None:
    """Restart the current training session."""
    st.session_state.started = True
    st.session_state.scenario_index = 0
    st.session_state.results = []
    st.session_state.answered_current = False
    st.session_state.last_answer = ""


def render_product_header() -> None:
    """Render a compact product header used across pages."""
    st.markdown(
        """
        <div class="fade-in" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;gap:1rem;">
            <div>
                <div style="color:#22d3ee;font-weight:900;letter-spacing:.18em;text-transform:uppercase;font-size:.76rem;">TruthLab OS</div>
                <div style="color:#9fb1cc;">Fictional feed. Real verification skills.</div>
            </div>
            <div class="pill">Rule-based AI-style coaching - No paid APIs</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome(scenarios: pd.DataFrame) -> None:
    """Show the cinematic landing page and project framing."""
    st.markdown(
        f"""
        <div class="hero fade-in">
            <div class="glass-card" style="display:flex;flex-direction:column;justify-content:center;">
                <div class="pill" style="width:max-content;">Digital Literacy Training Platform</div>
                <div class="hero-title">TruthLab</div>
                <p class="hero-subtitle">AI-Guided Misinformation Simulator</p>
                <p class="tagline">Train your mind to question what you see online.</p>
                <p class="tagline">Analyze fictional social posts, choose the safest response, and get clear coaching on source checks, emotional manipulation, scam signals, AI-media clues, and statistical reasoning.</p>
                <div class="pill-row">
                    <span class="pill">{len(scenarios)} scenarios</span>
                    <span class="pill">{len(SKILLS)} skill domains</span>
                    <span class="pill">0 paid APIs</span>
                    <span class="pill">Downloadable report</span>
                </div>
            </div>
            <div class="glass-card" style="display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <h3>Mission Brief</h3>
                    <p class="tagline">TruthLab is not a truth machine. It is a practice environment that rewards careful verification behavior.</p>
                </div>
                <div class="metric-tile"><div class="metric-number">100</div><div class="metric-label">Maximum Digital Literacy Index</div></div>
                <div class="metric-tile"><div class="metric-number">4</div><div class="metric-label">Decision paths: Trust, Doubt, Report, Verify First</div></div>
                <div class="metric-tile"><div class="metric-number">∞</div><div class="metric-label">Reason to pause before sharing</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Start Simulation", type="primary", use_container_width=True):
        reset_challenge()
        st.rerun()


def fake_engagement(scenario: pd.Series) -> dict[str, str]:
    """Generate deterministic fictional engagement numbers for a simulated post."""
    base = int(scenario["id"]) * 137 + int(scenario["difficulty"]) * 53
    return {
        "views": f"{base + 1200:,}",
        "shares": f"{(base // 7) + 18:,}",
        "comments": f"{(base // 11) + 9:,}",
    }


def render_feed_card(scenario: pd.Series) -> None:
    """Render one fictional social feed card with rich visual metadata."""
    engagement = fake_engagement(scenario)
    difficulty = "●" * int(scenario["difficulty"]) + "○" * (5 - int(scenario["difficulty"]))
    st.markdown(
        f"""
        <div class="glass-card feed-card fade-in">
            <div class="feed-meta">
                <div class="platform-label">{escape(str(scenario['platform']))} Feed</div>
                <div style="display:flex;gap:.5rem;flex-wrap:wrap;justify-content:flex-end;">
                    <span class="badge category-badge">{escape(str(scenario['category']))}</span>
                    <span class="badge difficulty-badge">Difficulty {difficulty}</span>
                </div>
            </div>
            <div class="post-user">{escape(str(scenario['username']))}</div>
            <div class="post-title">{escape(str(scenario['title']))}</div>
            <div class="post-text">{escape(str(scenario['post_text']))}</div>
            <div class="engagement" aria-label="Fictional engagement indicators">
                <span>{engagement['views']} fictional views</span>
                <span>{engagement['shares']} fictional shares</span>
                <span>{engagement['comments']} fictional comments</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def submit_answer(scenario: pd.Series, user_answer: str) -> None:
    """Score the answer and store all fields needed for dashboards and reports."""
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
    st.session_state.last_answer = user_answer


def render_answer_cards(scenario: pd.Series) -> None:
    """Show visually distinct decision cards and submit immediately on click."""
    st.markdown("<h3>Choose your response</h3>", unsafe_allow_html=True)
    st.markdown('<div class="answer-grid">', unsafe_allow_html=True)
    columns = st.columns(4)
    for column, answer in zip(columns, ANSWER_CHOICES):
        style = ANSWER_STYLES[answer]
        with column:
            st.markdown(
                f"""
                <div class="answer-card {style['class']}">
                    <div class="answer-icon">{style['icon']}</div>
                    <div class="answer-title">{answer}</div>
                    <div class="answer-caption">{style['caption']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(answer, key=f"answer_{scenario['id']}_{answer}", disabled=st.session_state.answered_current, use_container_width=True):
                submit_answer(scenario, answer)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_feedback_card(scenario: pd.Series) -> None:
    """Render the structured AI Coach-style feedback card."""
    user_answer = st.session_state.last_answer
    is_correct = user_answer == scenario["correct_answer"]
    missed_label = "Why this works" if is_correct else "What you missed"
    status_color = "#86efac" if is_correct else "#fbbf24"
    st.markdown(
        f"""
        <div class="glass-card fade-in">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;">
                <div>
                    <div class="platform-label">AI Coach</div>
                    <h3 style="margin:.2rem 0;">{'Correct read' if is_correct else 'Recalibrate your read'}</h3>
                </div>
                <span class="badge" style="color:{status_color};background:rgba(15,23,42,.72);">{'Matched' if is_correct else 'Review'}</span>
            </div>
            <div class="coach-section"><div class="coach-label">Your choice</div><div class="coach-value">{escape(user_answer)}</div></div>
            <div class="coach-section"><div class="coach-label">Correct answer</div><div class="coach-value">{escape(str(scenario['correct_answer']))}</div></div>
            <div class="coach-section"><div class="coach-label">{missed_label}</div><div class="coach-value">{escape(str(scenario['explanation']))}</div></div>
            <div class="coach-section"><div class="coach-label">Red flags</div><div class="coach-value">{escape(str(scenario['red_flags']))}</div></div>
            <div class="coach-section"><div class="coach-label">Learning tip</div><div class="coach-value">{escape(verification_tip(str(scenario['skill_focus'])))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_challenge(scenarios: pd.DataFrame) -> None:
    """Render the interactive challenge workflow."""
    total = len(scenarios)
    index = st.session_state.scenario_index
    if index >= total:
        render_final_report()
        return

    scenario = scenarios.iloc[index]
    st.progress((index + int(st.session_state.answered_current)) / total, text=f"Scenario {index + 1} of {total}")

    st.markdown('<div class="simulation-shell">', unsafe_allow_html=True)
    main, coach = st.columns([1.18, 0.82])
    with main:
        render_feed_card(scenario)
        render_answer_cards(scenario)
    with coach:
        if st.session_state.answered_current:
            render_feedback_card(scenario)
            if st.button("Continue to next post", use_container_width=True):
                st.session_state.scenario_index += 1
                st.session_state.answered_current = False
                st.session_state.last_answer = ""
                st.rerun()
        else:
            st.markdown(
                """
                <div class="glass-card fade-in">
                    <div class="platform-label">Decision Lab</div>
                    <h3>Read before reacting.</h3>
                    <p class="tagline">Your goal is not to guess perfectly. Your goal is to practice the safest reasoning path for the evidence shown.</p>
                    <div class="coach-section"><div class="coach-label">Trust</div><div class="coach-value">Use when the post gives credible, verifiable information.</div></div>
                    <div class="coach-section"><div class="coach-label">Doubt</div><div class="coach-value">Use when the post is suspicious, incomplete, or manipulative.</div></div>
                    <div class="coach-section"><div class="coach-label">Report</div><div class="coach-value">Use for likely scams, harmful deception, impersonation, or credential theft.</div></div>
                    <div class="coach-section"><div class="coach-label">Verify First</div><div class="coach-value">Use when more source, context, or provenance checking is needed.</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)


def render_score_orb(index: int) -> None:
    """Render a circular-looking Digital Literacy Index visualization."""
    st.markdown(
        f"""
        <div class="score-orb" style="--score:{index};">
            <div class="score-number">{index}</div>
            <div class="score-label">Index / 100</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skill_cards(skills: dict[str, int]) -> None:
    """Render skill progress cards with custom progress bars."""
    for skill, score in skills.items():
        st.markdown(
            f"""
            <div class="glass-card skill-card">
                <div class="skill-top"><span>{escape(skill)}</span><span>{score}/100</span></div>
                <div class="skill-track"><div class="skill-fill" style="width:{score}%;"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_final_report() -> None:
    """Render summary analytics and a downloadable report."""
    results = st.session_state.results
    index = digital_literacy_index(results)
    skills = skill_breakdown(results)
    band, summary = performance_band(index)
    report = make_markdown_report(index, skills, results)

    st.markdown('<div class="fade-in"><h1>Mission Debrief</h1></div>', unsafe_allow_html=True)
    left, right = st.columns([0.85, 1.15])
    with left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        render_score_orb(index)
        st.markdown(
            f"<h3 style='text-align:center;'>{escape(band)}</h3><p class='tagline' style='text-align:center;'>{escape(summary)}</p>",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        render_skill_cards(skills)

    st.markdown("### Scenario Review")
    display = pd.DataFrame(results)[["title", "category", "user_answer", "correct_answer", "is_correct", "skill_focus"]]
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.download_button(
        "Download Markdown Report",
        data=report,
        file_name="truthlab_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    if st.button("Restart Simulation", use_container_width=True):
        reset_challenge()
        st.rerun()


def render_about() -> None:
    """Explain the scholarship project and product purpose."""
    st.markdown(
        """
        <div class="glass-card fade-in">
            <div class="platform-label">About</div>
            <h1>TruthLab turns misinformation awareness into practice.</h1>
            <p class="tagline">The product simulates a fictional social feed where learners make decisions under uncertainty. Each decision creates a teachable moment: the app explains why a post should be trusted, doubted, reported, or verified first.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="method-grid fade-in">', unsafe_allow_html=True)
    for title, text in [
        ("Why it matters", "Online misinformation can spread through urgency, emotion, fake authority, weak statistics, manipulated media, and scams. TruthLab trains users to slow down and inspect those signals."),
        ("Software logic", "The app loads scenario data, validates records, scores decisions with difficulty weighting, aggregates skill performance, and generates a downloadable report."),
        ("Original work", "The scenarios, scoring model, interface language, and report structure were written for this project as a scholarship-ready software application."),
        ("Clear limitation", "TruthLab is not an automated fact-checker. It is a controlled simulator for learning verification habits."),
    ]:
        st.markdown(f"<div class='glass-card'><h3>{title}</h3><p class='tagline'>{text}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_methodology() -> None:
    """Describe scoring, feedback, and educational methodology."""
    st.markdown(
        """
        <div class="glass-card fade-in">
            <div class="platform-label">Methodology</div>
            <h1>Transparent scoring. Explainable coaching.</h1>
            <p class="tagline">TruthLab uses rule-based AI-style feedback. It does not call a paid model or make hidden truth judgments. Each scenario contains a correct educational response, red flags, explanation, skill focus, and source note.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="method-grid fade-in">', unsafe_allow_html=True)
    methodology = [
        ("Digital Literacy Index", "Correct answers earn difficulty-weighted points. The total is normalized to a 0-100 score."),
        ("Skill analytics", "Each scenario maps to one core skill: source verification, emotional manipulation detection, AI content awareness, scam detection, or statistical reasoning."),
        ("Coach feedback", "After each answer, a structured feedback card shows the user choice, correct answer, missed reasoning, red flags, and a learning tip."),
        ("Fictional safety", "Platforms, usernames, engagement numbers, and posts are fictional to avoid copying real social media content or using copyrighted branding."),
    ]
    for title, text in methodology:
        st.markdown(f"<div class='glass-card'><h3>{title}</h3><p class='tagline'>{text}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_sources() -> None:
    """Show concise credits in-app."""
    st.markdown(
        """
        <div class="glass-card fade-in">
            <div class="platform-label">Sources</div>
            <h1>Credits and reference foundation</h1>
            <p class="tagline">TruthLab is built with Python, Streamlit, Pandas, Pillow, and Matplotlib-compatible dependencies. Scenario patterns are original educational simulations informed by general media literacy, cybersecurity, phishing prevention, AI-media verification, and statistical reasoning concepts.</p>
            <p class="tagline">See <code>sources.md</code> for detailed attribution categories. All app text is in English, and all scenarios are fictional.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(scenarios: pd.DataFrame) -> str:
    """Render navigation and quick statistics."""
    st.sidebar.markdown("## 🧪 TruthLab")
    st.sidebar.caption("AI-Guided Misinformation Simulator")
    page = st.sidebar.radio("Navigate", ["Simulation", "About", "Methodology", "Sources"])
    st.sidebar.divider()
    st.sidebar.metric("Scenario library", len(scenarios))
    st.sidebar.metric("Skill domains", len(SKILLS))
    st.sidebar.caption("Fictional scenario categories")
    for category in get_categories(scenarios):
        st.sidebar.caption(f"• {category}")
    if st.sidebar.button("Reset simulation", use_container_width=True):
        reset_challenge()
        st.rerun()
    return page


def main() -> None:
    """Main Streamlit entry point."""
    initialize_state()
    inject_css()
    scenarios = cached_scenarios()
    render_product_header()
    page = render_sidebar(scenarios)

    if page == "About":
        render_about()
    elif page == "Methodology":
        render_methodology()
    elif page == "Sources":
        render_sources()
    elif not st.session_state.started:
        render_welcome(scenarios)
    else:
        render_challenge(scenarios)


if __name__ == "__main__":
    main()
