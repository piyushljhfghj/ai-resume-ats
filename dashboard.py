"""Streamlit dashboard for the resume screening system."""

import html
import json

import pandas as pd
import streamlit as st

from app.charts import (
    STRONG_MATCH_THRESHOLD,
    breakdown_chart,
    get_palette,
    ranking_chart,
    skill_matrix_chart,
)
from app.config import EXPERIENCE_WEIGHT, SEMANTIC_WEIGHT, SKILL_WEIGHT
from app.intelligent_ranker import rank_resumes
from app.report_generator import generate_pdf_report
from app.ui_theme import card_accent_css, fit_band_colour, hero_html, page_css

st.set_page_config(
    page_title="Resume Screening",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------- theme ----

def active_theme():
    """'dark' or 'light', following the viewer's Streamlit theme."""
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


THEME = active_theme()
PALETTE = get_palette(THEME)

st.markdown(page_css(PALETTE), unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers ---

FIT_BANDS = [
    (STRONG_MATCH_THRESHOLD, "Strong match", "green", ":material/check_circle:"),
    (50, "Possible match", "orange", ":material/help:"),
    (0, "Weak match", "red", ":material/cancel:"),
]


def fit_band(score):
    """(label, badge colour, icon) for a final score. Never colour alone."""
    for floor, label, colour, icon in FIT_BANDS:
        if score >= floor:
            return label, colour, icon
    return FIT_BANDS[-1][1:]


def chip_row(skills, kind):
    """Render a wrapping row of skill chips."""
    if not skills:
        st.markdown(
            '<div class="chip-none">None</div>', unsafe_allow_html=True
        )
        return
    css = "chip-ok" if kind == "matched" else "chip-no"
    chips = "".join(
        f'<span class="chip {css}">{html.escape(str(s))}</span>' for s in skills
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def pdf_for(result_json):
    """Build a candidate PDF once and reuse it across reruns.

    Keyed on the serialised result so Streamlit can hash it -- without the
    cache, every rerun regenerated a PDF for every candidate.
    """
    return generate_pdf_report(json.loads(result_json)).getvalue()


def label_for(key):
    return {
        "semantic_score": "Semantic",
        "skill_score": "Skill",
        "experience_score": "Experience",
    }[key]


# ---------------------------------------------------------------- sidebar ---

with st.sidebar:
    st.markdown('<div class="page-title">Resume Screening</div>', unsafe_allow_html=True)
    st.caption("Rank candidates against a role, with the reasoning shown.")

    st.divider()

    jd_text = st.text_area(
        "Job description",
        height=210,
        placeholder=(
            "Paste the role here.\n\n"
            "Required: Python, machine learning, 5+ years.\n"
            "Preferred: Docker, AWS."
        ),
        help="Skills after the word 'preferred' are weighted at half.",
    )

    uploaded_files = st.file_uploader(
        "Resumes",
        type=["txt", "pdf"],
        accept_multiple_files=True,
        help="PDF or plain text. Upload as many as you like.",
    )

    run = st.button(
        "Run screening",
        type="primary",
        width="stretch",
        icon=":material/play_arrow:",
        disabled=not (jd_text.strip() and uploaded_files),
    )

    if not jd_text.strip() or not uploaded_files:
        st.caption("Add a job description and at least one resume to begin.")

    if st.session_state.get("results"):
        if st.button("Clear results", width="stretch", icon=":material/refresh:"):
            st.session_state.pop("results", None)
            st.rerun()

    st.divider()
    st.markdown('<div class="field-label">Scoring weights</div>', unsafe_allow_html=True)
    st.caption(
        f"Semantic {SEMANTIC_WEIGHT:.0%} · Skill {SKILL_WEIGHT:.0%} · "
        f"Experience {EXPERIENCE_WEIGHT:.0%}"
    )


# ---------------------------------------------------------------- run -------

if run:
    with st.spinner("Reading resumes and scoring against the role..."):
        results = rank_resumes(jd_text, uploaded_files)

    if not results:
        st.error("None of the uploaded files could be read as text.")
    else:
        # Persist, so downloading a report does not wipe the page on rerun.
        st.session_state["results"] = results

results = st.session_state.get("results")


# ---------------------------------------------------------------- header ----

if not results:
    st.markdown(
        hero_html(
            "Candidate ranking",
            "Screen a batch of resumes against one role and see what drove "
            "every score.",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            '<div class="empty-state">'
            "<h3>No screening run yet</h3>"
            "<p>Paste a job description in the sidebar, upload one or more "
            "resumes, then run the screening. Every candidate is scored on "
            "semantic fit, skill coverage, and experience &mdash; and you can "
            "see exactly which skills drove the result.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    st.stop()


df = pd.DataFrame(results).sort_values("final_score", ascending=False)

top = df.iloc[0]
strong = int((df["final_score"] >= STRONG_MATCH_THRESHOLD).sum())

st.markdown(
    hero_html(
        "Candidate ranking",
        f"{len(df)} candidates screened &nbsp;·&nbsp; top match "
        f"<strong>{html.escape(str(top['filename']))}</strong> at "
        f"{top['final_score']:.1f}%",
    ),
    unsafe_allow_html=True,
)

# One coloured left edge per card, keyed to the candidate's fit band.
st.markdown(
    card_accent_css(
        (
            f"cand-{rank}",
            fit_band_colour(row["final_score"], PALETTE, STRONG_MATCH_THRESHOLD),
        )
        for rank, row in enumerate(df.to_dict("records"), start=1)
    ),
    unsafe_allow_html=True,
)

# KPI row -- stat tiles, not a chart.
k1, k2, k3, k4 = st.columns(4)
k1.metric("Candidates", len(df), border=True)
k2.metric("Top score", f"{top['final_score']:.1f}%", border=True)
k3.metric("Average score", f"{df['final_score'].mean():.1f}%", border=True)
k4.metric(
    "Strong matches",
    strong,
    delta=f"{strong / len(df):.0%} of pool",
    delta_color="off",
    border=True,
    help=f"Final score of {STRONG_MATCH_THRESHOLD}% or higher.",
)

st.write("")

overview_tab, compare_tab, candidates_tab = st.tabs(
    ["Overview", "Compare", "Candidates"]
)


# ---------------------------------------------------------------- overview --

with overview_tab:
    left, right = st.columns([3, 2], gap="medium")

    with left:
        with st.container(border=True):
            st.markdown("##### Final score by candidate")
            st.caption(
                f"The vertical rule marks the {STRONG_MATCH_THRESHOLD}% "
                "strong-match threshold."
            )
            st.altair_chart(
                ranking_chart(df, PALETTE), width="stretch", theme=None
            )

    with right:
        with st.container(border=True):
            label, colour, icon = fit_band(top["final_score"])
            st.markdown("##### Top match")
            st.markdown(
                f'<span class="cand-name">{html.escape(str(top["filename"]))}</span>',
                unsafe_allow_html=True,
            )
            st.badge(label, color=colour, icon=icon)
            st.progress(min(float(top["final_score"]) / 100, 1.0))

            a, b, c = st.columns(3)
            a.metric("Semantic", f"{top['semantic_score']:.0f}%")
            b.metric("Skill", f"{top['skill_score']:.0f}%")
            c.metric("Experience", f"{top['experience_score']:.0f}%")

            st.markdown(
                '<div class="field-label">Matched skills</div>',
                unsafe_allow_html=True,
            )
            chip_row(top["matched_skills"], "matched")

            if top["missing_skills"]:
                st.markdown(
                    '<div class="field-label">Gaps</div>', unsafe_allow_html=True
                )
                chip_row(top["missing_skills"], "missing")

        st.download_button(
            "Export all results (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="screening_results.csv",
            mime="text/csv",
            width="stretch",
            icon=":material/download:",
        )


# ---------------------------------------------------------------- compare ---

with compare_tab:
    with st.container(border=True):
        st.markdown("##### Score breakdown")
        st.caption("How each candidate earned their total, dimension by dimension.")
        st.altair_chart(
            breakdown_chart(df, PALETTE), width="stretch", theme=None
        )

    with st.container(border=True):
        st.markdown("##### All scores")
        table = df[
            [
                "filename",
                "semantic_score",
                "skill_score",
                "experience_score",
                "final_score",
            ]
        ].copy()

        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "filename": st.column_config.TextColumn("Candidate", width="medium"),
                "semantic_score": st.column_config.ProgressColumn(
                    "Semantic", format="%.1f%%", min_value=0, max_value=100
                ),
                "skill_score": st.column_config.ProgressColumn(
                    "Skill", format="%.1f%%", min_value=0, max_value=100
                ),
                "experience_score": st.column_config.ProgressColumn(
                    "Experience", format="%.1f%%", min_value=0, max_value=100
                ),
                "final_score": st.column_config.ProgressColumn(
                    "Final", format="%.1f%%", min_value=0, max_value=100
                ),
            },
        )

    matrix = skill_matrix_chart(df, PALETTE)
    with st.container(border=True):
        st.markdown("##### Skill coverage")
        if matrix is None:
            st.caption(
                "The job description named no skills from the known vocabulary, "
                "so there is nothing to match against."
            )
        else:
            st.caption("Which role skills each resume evidences.")
            st.altair_chart(matrix, width="stretch", theme=None)


# ---------------------------------------------------------------- cards -----

with candidates_tab:
    for rank, result in enumerate(df.to_dict("records"), start=1):
        label, colour, icon = fit_band(result["final_score"])

        with st.container(border=True, key=f"cand-{rank}"):
            head, score_col = st.columns([3, 1], vertical_alignment="center")

            with head:
                st.markdown(
                    f'<span class="rank-badge">{rank}</span>'
                    f'<span class="cand-name">'
                    f'{html.escape(str(result["filename"]))}</span>',
                    unsafe_allow_html=True,
                )
                st.badge(label, color=colour, icon=icon)

            with score_col:
                st.metric("Final", f"{result['final_score']:.1f}%")

            st.progress(min(float(result["final_score"]) / 100, 1.0))

            cols = st.columns(3)
            for col, key in zip(
                cols, ("semantic_score", "skill_score", "experience_score")
            ):
                col.metric(label_for(key), f"{result[key]:.0f}%")

            skills_col, gaps_col = st.columns(2)
            with skills_col:
                st.markdown(
                    '<div class="field-label">Matched skills</div>',
                    unsafe_allow_html=True,
                )
                chip_row(result["matched_skills"], "matched")
            with gaps_col:
                st.markdown(
                    '<div class="field-label">Missing skills</div>',
                    unsafe_allow_html=True,
                )
                chip_row(result["missing_skills"], "missing")

            with st.expander("Scoring detail"):
                st.write(result["explanation"])

            st.download_button(
                "Download report (PDF)",
                data=pdf_for(json.dumps(result, sort_keys=True)),
                file_name=f"{result['filename']}_report.pdf",
                mime="application/pdf",
                key=f"pdf-{result['filename']}-{rank}",
                icon=":material/description:",
            )
