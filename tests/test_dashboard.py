"""Smoke tests for the Streamlit dashboard.

AppTest runs the real script, so these catch render-time exceptions and
removed/renamed Streamlit APIs -- the failures a unit test never sees.
Session state is seeded directly so no upload or model load is needed.
"""

import pytest
from streamlit.testing.v1 import AppTest

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


def run_app(results=None):
    app = AppTest.from_file("dashboard.py", default_timeout=120)
    if results is not None:
        app.session_state["results"] = results
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
