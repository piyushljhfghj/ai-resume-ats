"""Smoke tests for the Streamlit dashboard.

AppTest runs the real script, so these catch render-time exceptions and
removed/renamed Streamlit APIs -- the failures a unit test never sees.
Session state is seeded directly so no upload or model load is needed.
"""

import pytest
from streamlit.testing.v1 import AppTest

from app.utils import inputs_fingerprint
from tests.test_auth import signed_in  # noqa: F401  (autouse fixture)

RESULTS = [
    {"filename": "alice.pdf", "semantic_score": 80.1, "skill_score": 100.0,
     "experience_score": 100.0, "final_score": 92.0,
     "matched_skills": ["python", "nlp"], "missing_skills": [],
     "explanation": "Overall ATS Score: 92.0%."},
    {"filename": "bob.txt", "semantic_score": 48.9, "skill_score": 25.0,
     "experience_score": 60.0, "final_score": 41.6,
     "matched_skills": ["python"], "missing_skills": ["nlp"],
     "explanation": "Overall ATS Score: 41.6%."},
]


VALID = {"valid": True, "reasons": [], "stats": {}}


def screening(results, jd_validation=VALID, failures=(), fingerprint=None):
    # The app starts with an empty JD and no uploads; a screening only
    # survives while its fingerprint matches the current inputs.
    return {
        "fingerprint": fingerprint or inputs_fingerprint("", None),
        "jd_validation": jd_validation,
        "results": results,
        "failures": list(failures),
    }


def run_app(results=None, **kwargs):
    app = AppTest.from_file("dashboard.py", default_timeout=120)
    if results is not None:
        app.session_state["screening"] = screening(results, **kwargs)
    app.run()
    return app


@pytest.fixture(scope="module")
def app():
    return run_app(RESULTS)


class TestEmptyState:
    def test_renders_without_error(self):
        app = run_app()
        assert not app.exception

    def test_shows_no_charts_before_a_run(self):
        app = run_app()
        assert len(app.get("arrow_vega_lite_chart")) == 0


class TestResultsView:
    def test_renders_without_error(self, app):
        assert not app.exception

    def test_three_charts(self, app):
        assert len(app.get("arrow_vega_lite_chart")) == 3

    def test_tabs(self, app):
        assert [t.label for t in app.tabs] == ["Overview", "Compare", "Candidates"]

    def test_kpi_row(self, app):
        kpis = {m.label: m.value for m in app.metric}
        assert kpis["Candidates"] == "2"
        assert kpis["Top score"] == "92.0%"
        assert kpis["Strong matches"] == "1"

    def test_comparison_table_present(self, app):
        assert len(app.dataframe) == 1

    def test_a_report_download_per_candidate_plus_csv(self, app):
        labels = [d.label for d in app.get("download_button")]
        assert labels.count("Download report (PDF)") == len(RESULTS)
        assert "Export all results (CSV)" in labels

    def test_results_survive_a_rerun(self, app):
        """Downloading a report triggers a rerun; results must not vanish."""
        app.run()
        assert not app.exception
        assert len(app.get("arrow_vega_lite_chart")) == 3


@pytest.fixture(scope="module")
def invalid_app():
    zeroed = [
        {**r, "semantic_score": 0.0, "skill_score": 0.0,
         "experience_score": 0.0, "final_score": 0.0,
         "matched_skills": [], "missing_skills": [], "status": "invalid_jd"}
        for r in RESULTS
    ]
    return run_app(
        zeroed,
        jd_validation={"valid": False, "reasons": ["Mostly random."], "stats": {}},
    )


class TestInvalidJobDescription:
    def test_renders_without_error(self, invalid_app):
        assert not invalid_app.exception

    def test_says_invalid(self, invalid_app):
        text = " ".join(e.value for e in invalid_app.error)
        assert "Invalid Job Description" in text
        assert "meaningful job description" in text

    def test_no_ranking_or_match_badges(self, invalid_app):
        assert len(invalid_app.get("arrow_vega_lite_chart")) == 0
        assert len(invalid_app.tabs) == 0
        assert not [m for m in invalid_app.metric if m.label == "Top score"]


class TestFailedFiles:
    def test_failed_file_named(self):
        app = run_app(
            RESULTS,
            failures=[{"filename": "scan.pdf", "reason": "may be scanned"}],
        )
        assert not app.exception
        text = " ".join(w.value for w in app.warning)
        assert "scan.pdf" in text and "scanned" in text

    def test_all_files_failed_shows_error_not_old_results(self):
        app = run_app(
            [], failures=[{"filename": "scan.pdf", "reason": "may be scanned"}]
        )
        assert not app.exception
        assert len(app.get("arrow_vega_lite_chart")) == 0


class TestStaleResults:
    def test_results_for_other_inputs_are_discarded(self):
        app = run_app(RESULTS, fingerprint="inputs-from-an-earlier-run")
        assert not app.exception
        assert "screening" not in app.session_state
        assert len(app.get("arrow_vega_lite_chart")) == 0

    def test_editing_the_jd_clears_results(self):
        app = run_app(RESULTS)
        assert len(app.get("arrow_vega_lite_chart")) == 3
        app.text_area[0].input("A completely different role").run()
        assert not app.exception
        assert "screening" not in app.session_state
        assert len(app.get("arrow_vega_lite_chart")) == 0
