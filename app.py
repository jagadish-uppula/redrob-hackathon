"""
Redrob Candidate Ranker — Streamlit Demo App

A web-based interface for ranking candidates against any job description.
Supports:
- Upload custom JD (text file or paste)
- Upload candidate JSONL files up to 500 MB
- Load local candidates.jsonl from disk
- Dynamic scoring based on the uploaded JD

Run with:
    streamlit run app.py
"""

import csv
import io
import json
import sys
import time
from pathlib import Path

import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.features import extract_features
from src.scorer import compute_score
from src.reasoning import generate_reasoning
from src.honeypot import detect_honeypot
from src.jd_parser import (
    JDRequirements,
    build_senior_ai_engineer_jd,
    parse_jd_text,
)


# =============================================================================
# Page Config
# =============================================================================

st.set_page_config(
    page_title="Redrob Candidate Ranker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Custom CSS
# =============================================================================

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
    }
    .sub-header {
        text-align: center;
        color: #a0a0b0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .rank-badge-1 {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #000;
        padding: 2px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .rank-badge-2 {
        background: linear-gradient(135deg, #C0C0C0, #A9A9A9);
        color: #000;
        padding: 2px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .rank-badge-3 {
        background: linear-gradient(135deg, #CD7F32, #B87333);
        color: #fff;
        padding: 2px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .jd-info {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Header
# =============================================================================

st.markdown('<div class="main-header">🎯 Redrob Candidate Ranker</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Intelligent Candidate Discovery & Ranking System — '
    'Pure Python, No LLMs, CPU Only</div>',
    unsafe_allow_html=True,
)

# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    # -----------------------------------------------------------------
    # Section 1: Job Description
    # -----------------------------------------------------------------
    st.header("📋 Job Description")

    jd_source = st.radio(
        "Choose JD source:",
        [
            "Default JD (Senior AI Engineer)",
            "Upload JD file (.txt)",
            "Paste JD text",
        ],
        index=0,
    )

    jd_requirements = None
    custom_jd_text = None

    if jd_source == "Default JD (Senior AI Engineer)":
        jd_requirements = build_senior_ai_engineer_jd()
        st.success(f"Using: {jd_requirements.role_title}")

    elif jd_source == "Upload JD file (.txt)":
        jd_file = st.file_uploader(
            "Upload job description (.txt)",
            type=["txt"],
            help="Upload a plain text file containing the job description.",
        )
        if jd_file:
            custom_jd_text = jd_file.read().decode("utf-8")
            jd_requirements = parse_jd_text(custom_jd_text)
            st.success(f"Parsed: {jd_requirements.role_title}")
            st.caption(
                f"Category: **{jd_requirements.role_category}** | "
                f"Experience: **{jd_requirements.min_years:.0f}–{jd_requirements.max_years:.0f}y** | "
                f"Skills detected: **{len(jd_requirements.must_have_skills) + len(jd_requirements.nice_to_have_skills)}**"
            )
        else:
            st.info("Upload a .txt file with the job description.")

    elif jd_source == "Paste JD text":
        custom_jd_text = st.text_area(
            "Paste job description here:",
            height=200,
            placeholder="Paste the full job description text here...",
        )
        if custom_jd_text and len(custom_jd_text.strip()) > 50:
            jd_requirements = parse_jd_text(custom_jd_text)
            st.success(f"Parsed: {jd_requirements.role_title}")
            st.caption(
                f"Category: **{jd_requirements.role_category}** | "
                f"Experience: **{jd_requirements.min_years:.0f}–{jd_requirements.max_years:.0f}y** | "
                f"Skills detected: **{len(jd_requirements.must_have_skills) + len(jd_requirements.nice_to_have_skills)}**"
            )
        elif custom_jd_text:
            st.warning("Please paste at least 50 characters of JD text.")

    st.divider()

    # -----------------------------------------------------------------
    # Section 2: Candidate Data
    # -----------------------------------------------------------------
    st.header("📁 Candidate Data")

    data_source = st.radio(
        "Choose data source:",
        ["Load local candidates.jsonl (Fastest)", "Upload JSONL file", "Use sample data (50 candidates)"],
        index=0,
    )

    candidates = []

    if data_source == "Upload JSONL file":
        uploaded_file = st.file_uploader(
            "Upload candidates.jsonl (up to 500 MB)",
            type=["jsonl", "json"],
            help="Upload a JSONL file with candidate profiles. Supports the full 100K dataset.",
        )
        if uploaded_file:
            with st.spinner("Parsing uploaded file..."):
                for line in uploaded_file:
                    line_str = line.decode("utf-8").strip()
                    if line_str:
                        try:
                            candidates.append(json.loads(line_str))
                        except json.JSONDecodeError:
                            pass
            st.success(f"Loaded {len(candidates)} candidates")

    elif data_source == "Use sample data (50 candidates)":
        sample_path = Path(__file__).parent / "sample_candidates.json"
        if sample_path.exists():
            with open(sample_path, "r", encoding="utf-8") as f:
                candidates = json.load(f)
            st.success(f"Loaded {len(candidates)} sample candidates")
        else:
            st.error("sample_candidates.json not found!")

    elif data_source == "Load local candidates.jsonl (Fastest)":
        local_path = Path(__file__).parent / "candidates.jsonl"
        if local_path.exists():
            with st.spinner("Loading candidates from local disk..."):
                with open(local_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                candidates.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            st.success(f"Loaded {len(candidates)} candidates from local file")
        else:
            st.error("candidates.jsonl not found in the project directory!")

    st.divider()

    # -----------------------------------------------------------------
    # Section 3: Configuration
    # -----------------------------------------------------------------
    st.header("⚙️ Configuration")
    num_cands = len(candidates)
    max_slider = min(100, max(num_cands, 2))
    top_n = st.slider("Top N to rank", 1, max_slider, min(50, max_slider))
    show_details = st.checkbox("Show detailed breakdown", value=True)
    show_honeypots = st.checkbox("Highlight honeypot detections", value=True)

# =============================================================================
# Main Content
# =============================================================================

if candidates and jd_requirements:
    # Show JD info banner
    st.markdown(
        f'<div class="jd-info">'
        f'<strong>📋 Ranking for:</strong> {jd_requirements.role_title} | '
        f'<strong>Category:</strong> {jd_requirements.role_category} | '
        f'<strong>Experience:</strong> {jd_requirements.min_years:.0f}–{jd_requirements.max_years:.0f} years | '
        f'<strong>Skills:</strong> {len(jd_requirements.must_have_skills)} required, '
        f'{len(jd_requirements.nice_to_have_skills)} nice-to-have'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("🚀 Run Ranking", type="primary", use_container_width=True):

        # Progress bar
        progress = st.progress(0, text="Scoring candidates...")
        t0 = time.time()

        scored = []
        for i, candidate in enumerate(candidates):
            features = extract_features(candidate, jd_requirements=jd_requirements)
            score_result = compute_score(candidate, features, jd_requirements=jd_requirements)
            scored.append((candidate, features, score_result))
            if (i + 1) % max(1, len(candidates) // 100) == 0:
                progress.progress(
                    (i + 1) / len(candidates),
                    text=f"Scoring {i+1}/{len(candidates)}...",
                )

        # Sort by score
        scored.sort(key=lambda x: x[2]["final_score"], reverse=True)

        elapsed = time.time() - t0
        progress.progress(1.0, text=f"✅ Scored {len(candidates)} candidates in {elapsed:.2f}s")

        # --- Metrics row ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Candidates Scored", len(candidates))
        with col2:
            st.metric("Time Elapsed", f"{elapsed:.2f}s")
        with col3:
            top_score = scored[0][2]["final_score"] if scored else 0
            st.metric("Top Score", f"{top_score:.4f}")
        with col4:
            honeypot_count = sum(1 for _, _, sr in scored if sr.get("penalties") and any("HONEYPOT" in p for p in sr["penalties"]))
            st.metric("Honeypots Detected", honeypot_count)

        st.divider()

        # --- Ranking Results ---
        st.header("📊 Ranking Results")

        for rank, (candidate, features, score_result) in enumerate(scored[:top_n], 1):
            profile = candidate["profile"]
            signals = candidate["redrob_signals"]
            title = profile["current_title"]
            score = score_result["final_score"]

            # Rank badge
            if rank == 1:
                badge = "🥇"
            elif rank == 2:
                badge = "🥈"
            elif rank == 3:
                badge = "🥉"
            else:
                badge = f"#{rank}"

            # Honeypot warning
            is_hp = any("HONEYPOT" in p for p in score_result.get("penalties", []))
            hp_icon = " ⚠️ HONEYPOT" if is_hp and show_honeypots else ""

            with st.expander(
                f"{badge} {profile['anonymized_name']} — {title} | "
                f"{profile['years_of_experience']}y | "
                f"Score: {score:.4f}{hp_icon}",
                expanded=(rank <= 3),
            ):
                col_a, col_b = st.columns([2, 1])

                with col_a:
                    st.markdown(f"**Company:** {profile['current_company']} ({profile['current_industry']})")
                    st.markdown(f"**Location:** {profile['location']}, {profile['country']}")
                    st.markdown(f"**Headline:** {profile['headline']}")

                    reasoning = generate_reasoning(candidate, features, score_result, rank)
                    st.info(f"**Reasoning:** {reasoning}")

                with col_b:
                    st.markdown(f"**Response Rate:** {signals['recruiter_response_rate']:.0%}")
                    st.markdown(f"**Notice Period:** {signals['notice_period_days']} days")
                    st.markdown(f"**Open to Work:** {'✅' if signals['open_to_work_flag'] else '❌'}")
                    st.markdown(f"**GitHub Score:** {signals['github_activity_score']}")

                if show_details:
                    st.markdown("---")
                    st.markdown("**Score Breakdown:**")
                    breakdown = score_result.get("breakdown", {})
                    cols = st.columns(len(breakdown))
                    for col, (key, val) in zip(cols, breakdown.items()):
                        with col:
                            st.metric(key.replace("_", " ").title(), f"{val:.3f}")

                    if score_result.get("penalties"):
                        st.warning("**Penalties:** " + "; ".join(score_result["penalties"]))

        # --- Download CSV ---
        st.divider()
        st.header("📥 Download Submission")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, (candidate, features, score_result) in enumerate(scored[:top_n], 1):
            reasoning = generate_reasoning(candidate, features, score_result, rank)
            writer.writerow([
                candidate["candidate_id"],
                rank,
                f"{score_result['final_score']:.4f}",
                reasoning,
            ])

        csv_content = output.getvalue()
        st.download_button(
            label="⬇️ Download submission.csv",
            data=csv_content,
            file_name="submission.csv",
            mime="text/csv",
            use_container_width=True,
        )

elif not jd_requirements:
    st.warning("👈 Please select or upload a Job Description in the sidebar first.")
else:
    st.info("👈 Upload a JSONL file or select sample data from the sidebar, then click **Run Ranking**.")

# =============================================================================
# Footer
# =============================================================================

st.divider()
st.markdown(
    "<div style='text-align:center; color:#666; font-size:0.85rem;'>"
    "Redrob Candidate Ranker — Built by U Jagadish | "
    "Pure Python, No LLMs, CPU Only | "
    "Hackathon Submission 2026"
    "</div>",
    unsafe_allow_html=True,
)
