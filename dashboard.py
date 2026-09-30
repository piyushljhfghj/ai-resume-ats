"""Streamlit dashboard for the resume screening system."""

import html
import json

import pandas as pd
import streamlit as st

from app import auth
from app.charts import (
    STRONG_MATCH_THRESHOLD,
    breakdown_chart,
    get_palette,
    ranking_chart,
    skill_matrix_chart,
)
from app.config import EXPERIENCE_WEIGHT, SEMANTIC_WEIGHT, SKILL_WEIGHT
from app.intelligent_ranker import rank_resumes
from app.jd_validator import INVALID_JD_MESSAGE, validate_job_description
from app.report_generator import generate_pdf_report
from app.ui_theme import card_accent_css, fit_band_colour, hero_html, page_css
from app.utils import inputs_fingerprint

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

# Nothing below runs until an allowed Google user is signed in.
USER = auth.require_login()


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


def _skills_text(skills):
    return ", ".join(skills) if skills else "none"


def render_evidence(result):
    """The exact facts each component score was computed from."""
    evidence = result.get("evidence") or {}
    semantic = evidence.get("semantic", {})
    skill = evidence.get("skill")
    experience = evidence.get("experience")

    st.markdown(f"**Semantic — {result['semantic_score']:.1f}%**")
    st.caption(semantic.get("note", "Embedding similarity between resume and JD."))

    st.markdown(f"**Skill — {result['skill_score']:.1f}%**")
    if skill:
        st.markdown(
            f"- Required in JD: {_skills_text(skill['required'])}\n"
            f"- Preferred in JD: {_skills_text(skill['preferred'])}\n"
            f"- Matched required: {_skills_text(skill['matched_required'])}\n"
            f"- Matched preferred: {_skills_text(skill['matched_preferred'])}"
        )
        st.caption(skill["note"])

    st.markdown(f"**Experience — {result['experience_score']:.1f}%**")
    if experience:
        required = experience["required_years"]
        found = experience["resume_years"]
        st.markdown(
            f"- Required by JD: {f'{required} year(s)' if required else 'not stated'}\n"
            f"- Found in resume: {f'{found} year(s)' if found else 'not determinable'}"
        )
        st.caption(experience["note"])

    formula = evidence.get("final", {}).get("formula")
    st.markdown(f"**Final — {result['final_score']:.1f}%**")
    st.caption(formula or result["explanation"])


def render_failures(failures):
    """Files that could not be read are named, not silently dropped."""
    if not failures:
        return
    lines = "\n".join(
        f"- `{f['filename']}` — {f['reason']}" for f in failures
    )
    st.warning(
        f"{len(failures)} file(s) could not be screened and were not scored:\n\n"
        + lines,
        icon=":material/error:",
    )


# ---------------------------------------------------------------- sidebar ---

with st.sidebar:
    st.markdown('<div class="page-title">Resume Screening</div>', unsafe_allow_html=True)
    st.caption("Rank candidates against a role, with the reasoning shown.")

    st.caption(f":material/account_circle: Signed in as **{USER['email']}**")
    st.button(
        "Sign out",
        icon=":material/logout:",
        on_click=auth.sign_out,
        key="sign-out",
    )

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

    if st.session_state.get("screening"):
        if st.button("Clear results", width="stretch", icon=":material/refresh:"):
            st.session_state.pop("screening", None)
            st.rerun()

    st.divider()
    st.markdown('<div class="field-label">Scoring weights</div>', unsafe_allow_html=True)
    st.caption(
        f"Semantic {SEMANTIC_WEIGHT:.0%} · Skill {SKILL_WEIGHT:.0%} · "
        f"Experience {EXPERIENCE_WEIGHT:.0%}"
    )


# ---------------------------------------------------------------- run -------

fingerprint = inputs_fingerprint(jd_text, uploaded_files)

if run:
    with st.spinner("Reading resumes and scoring against the role..."):
        run_results, run_failures = rank_resumes(jd_text, uploaded_files)

    # Always replace the whole screening -- even when nothing could be scored
    # -- so no result from a previous run survives into this one. Persisted
    # so downloading a report (which reruns the script) keeps the page.
    st.session_state["screening"] = {
        "fingerprint": fingerprint,
        "jd_validation": validate_job_description(jd_text),
        "results": run_results,
        "failures": run_failures,
    }

screening = st.session_state.get("screening")

if screening is not None and screening.get("fingerprint") != fingerprint:
    # The JD or the uploaded files changed since this screening ran; its
    # results describe inputs that no longer exist.
    st.session_state.pop("screening", None)
    screening = None
    st.toast("Inputs changed — previous results cleared. Run the screening again.")


# ---------------------------------------------------------------- header ----

if screening is None:
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


results = screening["results"]
jd_validation = screening["jd_validation"]

if not jd_validation["valid"]:
    st.markdown(
        hero_html("Candidate ranking", "The screening could not be run."),
        unsafe_allow_html=True,
    )
    reasons = "\n".join(f"- {r}" for r in jd_validation["reasons"])
    st.error(
        f"**Invalid Job Description**\n\n{INVALID_JD_MESSAGE}\n\n{reasons}",
        icon=":material/block:",
    )
    render_failures(screening["failures"])
    if results:
        st.caption(
            "No candidate was scored against this job description; every "
            "score is 0 and none of these is a match."
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "Candidate": [r["filename"] for r in results],
                    "Status": "Not scored — invalid job description",
                    "Final": [f"{r['final_score']:.0f}%" for r in results],
                }
            ),
            hide_index=True,
            width="stretch",
        )
    st.stop()

render_failures(screening["failures"])

if not results:
    st.error("None of the uploaded files could be read as text.")
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
            data=df.drop(columns=["evidence"], errors="ignore")
            .to_csv(index=False)
            .encode("utf-8"),
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

            with st.expander("Scoring evidence"):
                render_evidence(result)

            st.download_button(
                "Download report (PDF)",
                data=pdf_for(json.dumps(result, sort_keys=True)),
                file_name=f"{result['filename']}_report.pdf",
                mime="application/pdf",
                key=f"pdf-{result['filename']}-{rank}",
                icon=":material/description:",
            )
