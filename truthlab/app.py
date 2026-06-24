"""TruthLab: AI-Guided Misinformation Simulator.

Run with:
    streamlit run app.py
"""

from base64 import b64encode
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
ASSET_DIR = APP_DIR / "assets"
ANSWER_CHOICES = ["Trust", "Doubt", "Report", "Verify First"]
ANSWER_STYLES = {
    "Trust": {"icon": "✓", "class": "trust", "caption": "Accept as credible based on the evidence shown"},
    "Doubt": {"icon": "?", "class": "doubt", "caption": "Treat as suspicious, incomplete, or manipulative"},
    "Report": {"icon": "!", "class": "report", "caption": "Flag likely harm, impersonation, scam, or deception"},
    "Verify First": {"icon": "⌕", "class": "verify", "caption": "Pause, investigate, and look for stronger proof"},
}
CATEGORY_IMAGES = {
    "Health misinformation": "health_misinformation.svg",
    "Phishing/scam": "phishing_scam.svg",
    "AI-generated image claim": "ai_image_claim.svg",
    "Misleading statistics": "misleading_statistics.svg",
    "Fake scholarship scam": "fake_scholarship.svg",
    "Trustworthy information": "trustworthy_source.svg",
}
CATEGORY_ICONS = {
    "Health misinformation": "🧬",
    "Phishing/scam": "🛡️",
    "AI-generated image claim": "🖼️",
    "Misleading statistics": "📈",
    "Fake scholarship scam": "🎓",
    "Emotional manipulation": "⚠️",
    "Fake celebrity quote": "🎙️",
    "Trustworthy information": "✅",
}
SKILL_LABELS = {
    "Source Verification": "🔍 Source Verification",
    "Emotional Manipulation Detection": "⚠️ Manipulation Detection",
    "AI Content Awareness": "🖼️ AI Content Awareness",
    "Scam Detection": "🛡️ Scam Detection",
    "Statistical Reasoning": "📈 Statistical Reasoning",
}

st.set_page_config(page_title="TruthLab", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")


def asset_uri(filename: str) -> str:
    """Return a data URI for local SVG assets so Streamlit Cloud paths stay reliable."""
    path = ASSET_DIR / filename
    encoded = b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


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
        "page": "Simulation",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def inject_css() -> None:
    """Apply an Apple-inspired premium dark product theme with Streamlit-safe CSS."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        :root {
            --bg: #030712; --panel: rgba(15, 23, 42, 0.72); --panel-strong: rgba(8, 13, 27, 0.92);
            --line: rgba(148, 163, 184, 0.20); --text: #f8fbff; --muted: #9fb1cc;
            --cyan: #22d3ee; --blue: #60a5fa; --violet: #a78bfa; --green: #86efac;
            --red: #fb7185; --amber: #fbbf24;
        }
        html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .stApp {
            color: var(--text);
            background:
                radial-gradient(circle at 50% -10%, rgba(96,165,250,.24), transparent 32%),
                radial-gradient(circle at 12% 18%, rgba(34,211,238,.16), transparent 30%),
                radial-gradient(circle at 90% 12%, rgba(167,139,250,.18), transparent 28%),
                linear-gradient(180deg, #020617 0%, #050816 48%, #020617 100%);
        }
        section[data-testid="stSidebar"] { background: rgba(2, 6, 23, .78); border-right: 1px solid var(--line); backdrop-filter: blur(22px); }
        section[data-testid="stSidebar"] * { color: var(--text); }
        .block-container { padding-top: 1.65rem; max-width: 1240px; }
        h1, h2, h3 { color: var(--text); letter-spacing: -0.045em; }
        p, li, label, span { color: inherit; }
        .fade-in { animation: truthlabFade .75s ease both; }
        @keyframes truthlabFade { from { opacity:0; transform: translateY(16px); } to { opacity:1; transform: translateY(0); } }
        .glass-card {
            border: 1px solid var(--line); border-radius: 30px; padding: 1.35rem;
            background: linear-gradient(145deg, rgba(15,23,42,.84), rgba(15,23,42,.44));
            box-shadow: 0 28px 90px rgba(0,0,0,.36); backdrop-filter: blur(24px);
            transition: transform .24s ease, border-color .24s ease, box-shadow .24s ease;
        }
        .glass-card:hover { transform: translateY(-3px); border-color: rgba(34,211,238,.42); box-shadow: 0 34px 100px rgba(34,211,238,.11); }
        .topbar { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1rem; }
        .brand-dot { width:42px; height:42px; border-radius:16px; background:linear-gradient(135deg,var(--cyan),var(--violet)); box-shadow:0 0 34px rgba(34,211,238,.28); display:flex; align-items:center; justify-content:center; font-weight:900; color:#020617; }
        .platform-label { color: var(--cyan); font-weight:850; text-transform:uppercase; letter-spacing:.13em; font-size:.76rem; }
        .tagline { color: var(--muted); font-size:1.09rem; line-height:1.65; }
        .pill-row { display:flex; flex-wrap:wrap; gap:.7rem; margin-top:1.2rem; }
        .pill { border:1px solid rgba(125,211,252,.24); color:#dff7ff; background:rgba(14,165,233,.10); border-radius:999px; padding:.46rem .78rem; font-size:.84rem; font-weight:750; }
        .hero { min-height:640px; display:grid; grid-template-columns:1.12fr .88fr; gap:1.2rem; align-items:stretch; }
        .hero-copy { display:flex; flex-direction:column; justify-content:center; padding:2rem; }
        .hero-title { font-size:clamp(4.8rem, 11vw, 9rem); line-height:.84; margin:.55rem 0; background:linear-gradient(92deg,#fff,#dff7ff 34%,var(--cyan),var(--violet)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-shadow:0 0 55px rgba(34,211,238,.12); }
        .hero-subtitle { font-size:clamp(1.55rem,2.8vw,2.55rem); font-weight:850; margin:0; }
        .hero-device { position:relative; overflow:hidden; display:flex; flex-direction:column; justify-content:space-between; }
        .phone-frame { margin:auto; width:min(360px,100%); border-radius:42px; padding:1rem; background:linear-gradient(145deg,rgba(226,232,240,.20),rgba(15,23,42,.80)); border:1px solid rgba(226,232,240,.18); box-shadow: inset 0 0 0 1px rgba(255,255,255,.04), 0 35px 90px rgba(0,0,0,.42); }
        .phone-screen { border-radius:34px; overflow:hidden; background:#050816; border:1px solid rgba(148,163,184,.22); }
        .phone-screen img { display:block; width:100%; }
        .product-stats { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.9rem; margin:1.1rem 0; }
        .stat-card { border:1px solid var(--line); border-radius:24px; padding:1rem; background:rgba(2,6,23,.45); }
        .stat-number { font-size:1.8rem; font-weight:900; color:#f8fbff; }
        .stat-label { color:var(--muted); font-size:.84rem; }
        .mission-grid, .method-grid, .diagnostic-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; margin-top:1rem; }
        .method-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .diagnostic-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .simulation-shell { display:grid; grid-template-columns:minmax(0, .98fr) minmax(320px, .62fr); gap:1rem; align-items:start; }
        .feed-card { max-width:650px; margin:0 auto; padding:0; overflow:hidden; border-radius:34px; }
        .feed-header { display:flex; justify-content:space-between; align-items:center; padding:1rem 1.1rem .8rem; }
        .avatar { width:50px; height:50px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:950; color:#020617; background:linear-gradient(135deg,var(--cyan),var(--violet)); box-shadow:0 0 24px rgba(34,211,238,.22); }
        .post-user { color:#f8fbff; font-weight:850; }
        .topic-label { color:var(--muted); font-size:.82rem; }
        .menu-dots { color:#cbd5e1; letter-spacing:.08em; font-weight:900; }
        .post-image { width:100%; display:block; border-top:1px solid var(--line); border-bottom:1px solid var(--line); background:#020617; }
        .feed-body { padding:1rem 1.1rem 1.2rem; }
        .action-row { display:flex; justify-content:space-between; font-size:1.32rem; margin-bottom:.65rem; }
        .action-row span { display:inline-flex; gap:.65rem; }
        .post-title { font-size:1.15rem; font-weight:850; color:#f8fbff; margin:.35rem 0; }
        .post-text { color:#dbeafe; line-height:1.62; font-size:1rem; }
        .comment-preview { color:var(--muted); margin-top:.8rem; font-size:.9rem; }
        .badge { border-radius:999px; padding:.35rem .65rem; font-size:.75rem; font-weight:850; border:1px solid var(--line); }
        .category-badge { background:rgba(167,139,250,.14); color:#ddd6fe; }
        .difficulty-badge { background:rgba(251,191,36,.12); color:#fde68a; }
        .engagement { display:flex; flex-wrap:wrap; gap:.55rem; margin:.85rem 0; color:var(--muted); font-size:.84rem; }
        .engagement span { border:1px solid var(--line); border-radius:999px; padding:.32rem .54rem; background:rgba(15,23,42,.62); }
        .answer-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin-top:.8rem; }
        .answer-card { min-height:122px; border-radius:24px; padding:1rem; border:1px solid var(--line); background:rgba(15,23,42,.66); transition:transform .18s ease,border-color .18s ease,background .18s ease; }
        .answer-card:hover { transform:translateY(-4px); border-color:rgba(34,211,238,.55); background:rgba(30,41,59,.74); }
        .answer-icon { font-size:1.8rem; font-weight:950; }
        .answer-title { font-weight:850; color:#f8fbff; margin:.25rem 0; }
        .answer-caption { color:var(--muted); font-size:.82rem; line-height:1.35; }
        .trust .answer-icon { color:var(--green); } .doubt .answer-icon { color:var(--amber); } .report .answer-icon { color:var(--red); } .verify .answer-icon { color:var(--cyan); }
        .coach-section { border-left:3px solid var(--cyan); padding-left:.85rem; margin:.85rem 0; }
        .coach-label { color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.1em; font-weight:850; }
        .coach-value { color:#eff6ff; font-weight:620; line-height:1.5; }
        .score-orb { width:220px; height:220px; border-radius:50%; margin:0 auto 1rem; display:flex; flex-direction:column; justify-content:center; align-items:center; background:conic-gradient(var(--cyan) calc(var(--score) * 1%), rgba(30,41,59,.75) 0), radial-gradient(circle,#07111f 61%,transparent 62%); box-shadow:0 0 60px rgba(34,211,238,.20), inset 0 0 32px rgba(2,6,23,.86); border:1px solid rgba(34,211,238,.26); }
        .score-number { font-size:3.5rem; font-weight:950; color:#f8fbff; line-height:1; }
        .score-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.11em; }
        .skill-card { margin-bottom:.75rem; }
        .skill-top { display:flex; justify-content:space-between; gap:1rem; font-weight:850; margin-bottom:.45rem; }
        .skill-track { height:12px; border-radius:999px; background:rgba(51,65,85,.78); overflow:hidden; }
        .skill-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,var(--cyan),var(--violet),var(--green)); box-shadow:0 0 18px rgba(34,211,238,.30); }
        .next-step { border-left:3px solid var(--green); padding:.75rem .9rem; background:rgba(134,239,172,.08); border-radius:15px; margin:.55rem 0; color:#dff7ea; }
        div.stButton > button, div.stDownloadButton > button { border:0!important; color:#02111f!important; font-weight:850!important; border-radius:999px!important; background:linear-gradient(90deg,var(--cyan),var(--violet))!important; box-shadow:0 14px 34px rgba(34,211,238,.18)!important; transition:transform .18s ease, box-shadow .18s ease!important; }
        div.stButton > button:hover, div.stDownloadButton > button:hover { transform:translateY(-2px); box-shadow:0 19px 42px rgba(167,139,250,.25)!important; }
        .stProgress > div > div > div > div { background:linear-gradient(90deg,var(--cyan),var(--violet),var(--green)); }
        [data-testid="stMetric"] { background:rgba(15,23,42,.55); border:1px solid var(--line); border-radius:18px; padding:1rem; }
        [data-testid="stDataFrame"] { border-radius:18px; overflow:hidden; }
        @media (max-width: 980px) { .hero, .simulation-shell, .product-stats, .mission-grid, .method-grid, .diagnostic-grid { grid-template-columns:1fr; } .answer-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
        @media (max-width: 620px) { .answer-grid { grid-template-columns:1fr; } .hero-title { font-size:3.8rem; } .hero-copy { padding:1.2rem; } }
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
        <div class="topbar fade-in">
            <div style="display:flex;align-items:center;gap:.8rem;">
                <div class="brand-dot">TL</div>
                <div><div class="platform-label">TruthLab</div><div style="color:#9fb1cc;">Premium digital literacy simulation</div></div>
            </div>
            <div class="pill">Rule-based AI-style coaching - No paid APIs</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def initials_from_username(username: str) -> str:
    """Create fictional avatar initials from a scenario username."""
    clean = username.replace("@", "").replace("_", " ").strip()
    parts = [part for part in clean.split() if part]
    return "".join(part[0].upper() for part in parts[:2]) if parts else "TL"


def scenario_image(scenario: pd.Series) -> str:
    """Choose an original local SVG illustration for the post category."""
    filename = CATEGORY_IMAGES.get(str(scenario["category"]), "trustworthy_source.svg")
    return asset_uri(filename)


def fake_engagement(scenario: pd.Series) -> dict[str, str]:
    """Generate deterministic fictional engagement numbers for a simulated post."""
    base = int(scenario["id"]) * 137 + int(scenario["difficulty"]) * 53
    return {"likes": f"{base + 420:,}", "comments": f"{(base // 11) + 9:,}", "shares": f"{(base // 7) + 18:,}", "saves": f"{(base // 13) + 6:,}"}


def render_mission_strip() -> None:
    """Show product storytelling cards below the hero."""
    cards = [
        ("Simulate", "Misleading content", "Practice against fictional posts that mirror real misinformation patterns without copying real users or brands."),
        ("Analyze", "User decisions", "Every response is scored with transparent Python logic and connected to one literacy skill."),
        ("Build", "Digital resilience", "The final dashboard turns practice into a profile with strengths, gaps, and next steps."),
    ]
    st.markdown('<div class="mission-grid fade-in">', unsafe_allow_html=True)
    for eyebrow, title, text in cards:
        st.markdown(f"<div class='glass-card'><div class='platform-label'>{eyebrow}</div><h3>{title}</h3><p class='tagline'>{text}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_welcome(scenarios: pd.DataFrame) -> None:
    """Show the cinematic landing page and project framing."""
    preview = asset_uri("ai_image_claim.svg")
    st.markdown(
        f"""
        <div class="hero fade-in">
            <div class="glass-card hero-copy">
                <div class="pill" style="width:max-content;">Digital Literacy Training Platform</div>
                <div class="hero-title">TruthLab</div>
                <p class="hero-subtitle">AI-Guided Misinformation Simulator</p>
                <p class="tagline">Train your mind to question what you see online.</p>
                <p class="tagline">TruthLab simulates a fictional social media environment where users practice identifying misinformation, scams, AI-generated content, and manipulative posts through interactive challenges and intelligent feedback.</p>
                <div class="pill-row">
                    <span class="pill">15+ simulated scenarios</span><span class="pill">5 digital literacy skills</span><span class="pill">AI Coach feedback</span><span class="pill">Educational simulation</span>
                </div>
            </div>
            <div class="glass-card hero-device">
                <div><div class="platform-label">SignalSpace preview</div><h3 style="margin-top:.35rem;">A safer place to practice online judgment.</h3></div>
                <div class="phone-frame"><div class="phone-screen"><img src="{preview}" alt="Original TruthLab AI media illustration" /></div></div>
                <p class="tagline">Premium interface. Transparent scoring. No paid APIs. No real social media branding.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="product-stats fade-in">
            <div class="stat-card"><div class="stat-number">{len(scenarios)}+</div><div class="stat-label">simulated scenarios</div></div>
            <div class="stat-card"><div class="stat-number">{len(SKILLS)}</div><div class="stat-label">digital literacy skills</div></div>
            <div class="stat-card"><div class="stat-number">AI</div><div class="stat-label">Coach-style feedback</div></div>
            <div class="stat-card"><div class="stat-number">100</div><div class="stat-label">point Literacy Index</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cta1, cta2 = st.columns(2)
    with cta1:
        if st.button("Start Simulation", type="primary", use_container_width=True):
            reset_challenge()
            st.rerun()
    with cta2:
        if st.button("View Methodology", use_container_width=True):
            st.session_state.page = "Methodology"
            st.rerun()
    render_mission_strip()


def render_feed_card(scenario: pd.Series) -> None:
    """Render one fictional SignalSpace social feed post with original image art."""
    engagement = fake_engagement(scenario)
    difficulty = "●" * int(scenario["difficulty"]) + "○" * (5 - int(scenario["difficulty"]))
    category = str(scenario["category"])
    icon = CATEGORY_ICONS.get(category, "🧪")
    username = escape(str(scenario["username"]))
    st.markdown(
        f"""
        <div class="glass-card feed-card fade-in">
            <div class="feed-header">
                <div style="display:flex;align-items:center;gap:.75rem;">
                    <div class="avatar">{escape(initials_from_username(str(scenario['username'])))}</div>
                    <div><div class="post-user">{username}</div><div class="topic-label">SignalSpace - {escape(str(scenario['skill_focus']))}</div></div>
                </div>
                <div class="menu-dots">•••</div>
            </div>
            <img class="post-image" src="{scenario_image(scenario)}" alt="Original educational illustration for {escape(category)}" />
            <div class="feed-body">
                <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.8rem;"><span class="badge category-badge">{icon} {escape(category)}</span><span class="badge difficulty-badge">Difficulty {difficulty}</span></div>
                <div class="action-row"><span>♡ 💬 ↗</span><span>▢</span></div>
                <div class="engagement"><span>{engagement['likes']} fictional likes</span><span>{engagement['comments']} comments</span><span>{engagement['shares']} shares</span><span>{engagement['saves']} saves</span></div>
                <div class="post-title">{escape(str(scenario['title']))}</div>
                <div class="post-text"><strong>{username}</strong> {escape(str(scenario['post_text']))}</div>
                <div class="comment-preview">Preview comment: "Can anyone verify the original source before this spreads?"</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def submit_answer(scenario: pd.Series, user_answer: str) -> None:
    """Score the answer and store all fields needed for dashboards and reports."""
    score = score_answer(user_answer, scenario["correct_answer"], int(scenario["difficulty"]))
    st.session_state.results.append({
        "id": int(scenario["id"]), "title": scenario["title"], "category": scenario["category"],
        "user_answer": user_answer, "correct_answer": scenario["correct_answer"], "difficulty": int(scenario["difficulty"]),
        "is_correct": score.is_correct, "points_awarded": score.points_awarded, "points_possible": score.points_possible,
        "skill_focus": scenario["skill_focus"], "explanation": scenario["explanation"],
    })
    st.session_state.answered_current = True
    st.session_state.last_answer = user_answer


def render_answer_cards(scenario: pd.Series) -> None:
    """Show visually distinct decision cards and submit immediately on click."""
    st.markdown("<h3>Make your call</h3>", unsafe_allow_html=True)
    columns = st.columns(4)
    for column, answer in zip(columns, ANSWER_CHOICES):
        style = ANSWER_STYLES[answer]
        with column:
            st.markdown(f"<div class='answer-card {style['class']}'><div class='answer-icon'>{style['icon']}</div><div class='answer-title'>{answer}</div><div class='answer-caption'>{style['caption']}</div></div>", unsafe_allow_html=True)
            if st.button(answer, key=f"answer_{scenario['id']}_{answer}", disabled=st.session_state.answered_current, use_container_width=True):
                submit_answer(scenario, answer)
                st.rerun()


def render_feedback_card(scenario: pd.Series) -> None:
    """Render premium AI Coach-style feedback with score and skill context."""
    user_answer = st.session_state.last_answer
    score = score_answer(user_answer, scenario["correct_answer"], int(scenario["difficulty"]))
    is_correct = score.is_correct
    status_color = "#86efac" if is_correct else "#fbbf24"
    score_impact = f"+{score.points_awarded} of {score.points_possible} possible points"
    decision_signal = "You chose the safest action for the evidence shown." if is_correct else "Your choice missed a signal that should change the response strategy."
    st.markdown(
        f"""
        <div class="glass-card fade-in">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;"><div><div class="platform-label">🧠 AI Coach</div><h3 style="margin:.2rem 0;">{'Strong verification move' if is_correct else 'Coach recalibration'}</h3></div><span class="badge" style="color:{status_color};background:rgba(15,23,42,.72);">{score_impact}</span></div>
            <div class="coach-section"><div class="coach-label">Your choice</div><div class="coach-value">{escape(user_answer)}</div></div>
            <div class="coach-section"><div class="coach-label">Correct answer</div><div class="coach-value">{escape(str(scenario['correct_answer']))}</div></div>
            <div class="coach-section"><div class="coach-label">Score impact</div><div class="coach-value">{score_impact}. {decision_signal}</div></div>
            <div class="coach-section"><div class="coach-label">Why this matters</div><div class="coach-value">{escape(str(scenario['explanation']))}</div></div>
            <div class="coach-section"><div class="coach-label">Red flags</div><div class="coach-value">{escape(str(scenario['red_flags']))}</div></div>
            <div class="coach-section"><div class="coach-label">Learning tip</div><div class="coach-value">{escape(verification_tip(str(scenario['skill_focus'])))}</div></div>
            <div class="coach-section"><div class="coach-label">Skill affected</div><div class="coach-value">{escape(SKILL_LABELS.get(str(scenario['skill_focus']), str(scenario['skill_focus'])))}</div></div>
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
    main, coach = st.columns([1.05, .75])
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
            st.markdown("""
                <div class="glass-card fade-in"><div class="platform-label">Decision Lab</div><h3>Read like an analyst.</h3><p class="tagline">Do not react to the style of the post alone. Inspect source, evidence, urgency, provenance, and possible harm.</p>
                <div class="coach-section"><div class="coach-label">Trust</div><div class="coach-value">Use only when the post gives credible, verifiable information.</div></div>
                <div class="coach-section"><div class="coach-label">Doubt</div><div class="coach-value">Use when the post is suspicious, incomplete, or manipulative.</div></div>
                <div class="coach-section"><div class="coach-label">Report</div><div class="coach-value">Use for likely scams, harmful deception, impersonation, or credential theft.</div></div>
                <div class="coach-section"><div class="coach-label">Verify First</div><div class="coach-value">Use when more source, context, or provenance checking is needed.</div></div></div>
            """, unsafe_allow_html=True)


def render_score_orb(index: int) -> None:
    """Render a circular Digital Literacy Index visualization."""
    st.markdown(f"<div class='score-orb' style='--score:{index};'><div class='score-number'>{index}</div><div class='score-label'>Index / 100</div></div>", unsafe_allow_html=True)


def render_skill_cards(skills: dict[str, int]) -> None:
    """Render skill progress cards with custom progress bars."""
    for skill, score in skills.items():
        label = SKILL_LABELS.get(skill, skill)
        st.markdown(f"<div class='glass-card skill-card'><div class='skill-top'><span>{escape(label)}</span><span>{score}/100</span></div><div class='skill-track'><div class='skill-fill' style='width:{score}%;'></div></div></div>", unsafe_allow_html=True)


def render_final_report() -> None:
    """Render diagnostic analytics and a downloadable report."""
    results = st.session_state.results
    index = digital_literacy_index(results)
    skills = skill_breakdown(results)
    band, summary = performance_band(index)
    report = make_markdown_report(index, skills, results)
    strongest = max(skills, key=skills.get) if skills else "Not enough data"
    weakest = min(skills, key=skills.get) if skills else "Not enough data"
    st.markdown('<div class="fade-in"><h1>Digital Literacy Diagnostic</h1></div>', unsafe_allow_html=True)
    left, right = st.columns([.82, 1.18])
    with left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        render_score_orb(index)
        st.markdown(f"<h3 style='text-align:center;'>{escape(band)}</h3><p class='tagline' style='text-align:center;'>{escape(summary)}</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        render_skill_cards(skills)
    st.markdown(f"""
        <div class="diagnostic-grid fade-in">
            <div class="glass-card"><div class="platform-label">Strongest skill</div><h3>{escape(SKILL_LABELS.get(strongest, strongest))}</h3><p class="tagline">This was your most consistent verification behavior during the simulation.</p></div>
            <div class="glass-card"><div class="platform-label">Weakest skill</div><h3>{escape(SKILL_LABELS.get(weakest, weakest))}</h3><p class="tagline">Improve this area to raise your future Digital Literacy Index.</p></div>
        </div>
        <div class="glass-card fade-in" style="margin-top:1rem;"><div class="platform-label">Personalized next steps</div><div class="next-step">Run a lateral source check before trusting screenshots, celebrity quotes, or unnamed experts.</div><div class="next-step">Slow down when posts use urgency, fear, guaranteed rewards, or identity-data requests.</div><div class="next-step">For images and statistics, verify provenance, labels, sample size, and context before sharing.</div></div>
    """, unsafe_allow_html=True)
    st.markdown("### Scenario Review")
    display = pd.DataFrame(results)[["title", "category", "user_answer", "correct_answer", "is_correct", "skill_focus"]]
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("Download Markdown Report", data=report, file_name="truthlab_report.md", mime="text/markdown", use_container_width=True)
    if st.button("Restart Simulation", use_container_width=True):
        reset_challenge()
        st.rerun()


def render_about() -> None:
    """Explain the scholarship project, product purpose, and original contribution."""
    st.markdown("""
        <div class="glass-card fade-in"><div class="platform-label">About TruthLab</div><h1>A premium simulator for digital judgment.</h1><p class="tagline">TruthLab turns misinformation awareness into active practice. Learners enter a fictional feed, make decisions under uncertainty, and receive transparent coaching about safer online behavior.</p></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="method-grid fade-in">', unsafe_allow_html=True)
    for title, text in [
        ("Why misinformation matters", "Students encounter viral claims, fake scholarships, AI media, emotional manipulation, misleading statistics, and phishing attempts in ordinary online spaces."),
        ("Software logic", "The app loads and validates scenario data, scores difficulty-weighted decisions, aggregates skill analytics, and generates a downloadable Markdown report."),
        ("Original contributions", "Created for this project: custom scenario dataset, scoring logic, feedback framework, Digital Literacy Index, fictional feed interface, and simulation flow."),
        ("Clear limitation", "TruthLab is an educational simulation. It does not perfectly detect misinformation and should not replace professional fact-checking or cybersecurity review."),
    ]:
        st.markdown(f"<div class='glass-card'><h3>{title}</h3><p class='tagline'>{text}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_methodology() -> None:
    """Describe scoring, feedback, and educational methodology."""
    st.markdown("""
        <div class="glass-card fade-in"><div class="platform-label">Methodology</div><h1>Transparent scoring. Explainable coaching.</h1><p class="tagline">TruthLab uses scenario-based learning and rule-based AI-style feedback. It does not call a paid model or make hidden truth judgments.</p></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="method-grid fade-in">', unsafe_allow_html=True)
    methodology = [
        ("Scenario-based learning", "Each fictional post places the learner in a realistic decision moment with limited evidence and social pressure."),
        ("Rule-based AI-style feedback", "Feedback is generated from scenario fields, answer choices, red flags, explanations, and skill-specific learning tips."),
        ("Skill-weighted scoring", "Correct answers earn difficulty-weighted points, then performance is grouped by literacy skill."),
        ("Digital Literacy Index", "The total score is normalized to a 0-100 diagnostic profile with strongest and weakest skill insights."),
        ("Educational simulation", "TruthLab trains verification habits. It is not a perfect automated misinformation detector."),
        ("Fictional safety", "Platform names, usernames, images, engagement, and comments are fictional and avoid real social media branding."),
    ]
    for title, text in methodology:
        st.markdown(f"<div class='glass-card'><h3>{title}</h3><p class='tagline'>{text}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_sources() -> None:
    """Show concise credits in-app."""
    st.markdown("""
        <div class="glass-card fade-in"><div class="platform-label">Sources and Credits</div><h1>Transparent by design.</h1><p class="tagline">TruthLab is built with Python, Streamlit, Pandas, Pillow, Matplotlib-compatible dependencies, custom CSS, and original local SVG illustrations. Scenario patterns are original educational simulations informed by general media literacy, cybersecurity, phishing prevention, AI-media verification, and statistical reasoning concepts.</p><p class="tagline">See <code>sources.md</code> for detailed attribution categories. All app text is in English, all posts are fictional, and no copyrighted platform branding is used.</p></div>
    """, unsafe_allow_html=True)


def render_sidebar(scenarios: pd.DataFrame) -> str:
    """Render navigation and quick statistics."""
    st.sidebar.markdown("## 🧪 TruthLab")
    st.sidebar.caption("AI-Guided Misinformation Simulator")
    page = st.sidebar.radio("Navigate", ["Simulation", "About", "Methodology", "Sources"], key="page")
    st.sidebar.divider()
    st.sidebar.metric("Scenario library", len(scenarios))
    st.sidebar.metric("Skill domains", len(SKILLS))
    st.sidebar.caption("Fictional scenario categories")
    for category in get_categories(scenarios):
        st.sidebar.caption(f"- {category}")
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
