import pandas as pd
import pytest

from app.charts import (
    DARK,
    LIGHT,
    breakdown_chart,
    get_palette,
    ranking_chart,
    skill_matrix_chart,
)


@pytest.fixture
def df():
    return pd.DataFrame([
        {"filename": "alice.txt", "semantic_score": 80.1, "skill_score": 100.0,
         "experience_score": 100.0, "final_score": 92.0,
         "matched_skills": ["python", "nlp"], "missing_skills": []},
        {"filename": "bob.txt", "semantic_score": 48.9, "skill_score": 25.0,
         "experience_score": 60.0, "final_score": 41.6,
         "matched_skills": ["python"], "missing_skills": ["nlp"]},
    ])


@pytest.fixture(params=["light", "dark"])
def palette(request):
    return get_palette(request.param)


class TestPalette:
    def test_selects_by_theme(self):
        assert get_palette("dark") is DARK
        assert get_palette("light") is LIGHT

    def test_unknown_theme_falls_back_to_light(self):
        assert get_palette(None) is LIGHT

    def test_both_palettes_define_the_same_roles(self):
        assert set(LIGHT) == set(DARK)

    def test_three_categorical_slots(self):
        # The all-pairs CVD gate is only cleared by the first three slots.
        assert len(LIGHT["series"]) == 3
        assert len(DARK["series"]) == 3


class TestCharts:
    def test_ranking_chart_builds(self, df, palette):
        assert ranking_chart(df, palette).to_dict()

    def test_breakdown_chart_builds(self, df, palette):
        assert breakdown_chart(df, palette).to_dict()

    def test_skill_matrix_builds(self, df, palette):
        assert skill_matrix_chart(df, palette).to_dict()

    def test_ranking_uses_one_hue_for_every_bar(self, df, palette):
        """Colouring bars by their own value would double-encode bar length."""
        spec = ranking_chart(df, palette).to_dict()
        bar = next(
            layer for layer in spec["layer"]
            if layer.get("mark", {}).get("type") == "bar"
        )
        assert bar["mark"]["color"] == palette["accent"]
        assert "color" not in bar["encoding"]

    def test_breakdown_uses_the_validated_series_colours(self, df, palette):
        spec = breakdown_chart(df, palette).to_dict()
        assert spec["encoding"]["color"]["scale"]["range"] == palette["series"]

    def test_scores_share_one_axis_domain(self, df, palette):
        """Never a second scale -- every score is a percentage on 0-100."""
        for chart in (ranking_chart(df, palette), breakdown_chart(df, palette)):
            spec = chart.to_dict()
            layers = spec.get("layer", [spec])
            for layer in layers:
                x = layer.get("encoding", {}).get("x", {})
                if "scale" in x:
                    assert x["scale"]["domain"] == [0, 100]

    def test_skill_matrix_is_none_when_no_skills(self, df, palette):
        empty = df.copy()
        empty["matched_skills"] = [[] for _ in range(len(empty))]
        empty["missing_skills"] = [[] for _ in range(len(empty))]
        assert skill_matrix_chart(empty, palette) is None

    def test_skill_matrix_encodes_status_beyond_colour(self, df, palette):
        """Status is carried by a glyph as well as fill, never colour alone."""
        spec = skill_matrix_chart(df, palette).to_dict()
        text_layer = next(
            layer for layer in spec["layer"]
            if layer.get("mark", {}).get("type") == "text"
        )
        assert text_layer["encoding"]["text"]["field"] == "glyph"

    def test_single_candidate_still_renders(self, palette):
        one = pd.DataFrame([{
            "filename": "solo.txt", "semantic_score": 50.0, "skill_score": 50.0,
            "experience_score": 50.0, "final_score": 50.0,
            "matched_skills": ["python"], "missing_skills": [],
        }])
        assert ranking_chart(one, palette).to_dict()
        assert breakdown_chart(one, palette).to_dict()


class TestChrome:
    """The view frame is an ordering trap: .configure() replaces the whole
    config object, so calling it after .configure_view() silently restores
    Vega's default #ddd frame."""

    def test_view_frame_is_disabled(self, df, palette):
        for chart in (
            ranking_chart(df, palette),
            breakdown_chart(df, palette),
            skill_matrix_chart(df, palette),
        ):
            view = chart.to_dict()["config"]["view"]
            assert view["stroke"] is None, "default view frame not suppressed"

    def test_surface_and_font_configured(self, df, palette):
        config = ranking_chart(df, palette).to_dict()["config"]
        assert config["background"] == palette["surface"]
        assert config["view"]["fill"] == palette["surface"]
        assert "system-ui" in config["font"]
