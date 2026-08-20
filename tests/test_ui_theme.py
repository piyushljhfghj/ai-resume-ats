import pytest

from app.charts import STRONG_MATCH_THRESHOLD, get_palette
from app.ui_theme import (
    card_accent_css,
    fit_band_colour,
    hero_html,
    page_css,
    rgba,
)


@pytest.fixture(params=["light", "dark"])
def palette(request):
    return get_palette(request.param)


class TestRgba:
    def test_converts_hex(self):
        assert rgba("#4a3aa7", 0.05) == "rgba(74, 58, 167, 0.05)"

    def test_tolerates_missing_hash(self):
        assert rgba("ffffff", 1) == "rgba(255, 255, 255, 1)"


class TestFitBand:
    def test_strong(self, palette):
        colour = fit_band_colour(92.0, palette, STRONG_MATCH_THRESHOLD)
        assert colour == palette["good"]

    def test_possible(self, palette):
        colour = fit_band_colour(60.0, palette, STRONG_MATCH_THRESHOLD)
        assert colour == palette["warning"]

    def test_weak(self, palette):
        colour = fit_band_colour(20.0, palette, STRONG_MATCH_THRESHOLD)
        assert colour == palette["critical"]

    def test_threshold_is_inclusive(self, palette):
        colour = fit_band_colour(
            STRONG_MATCH_THRESHOLD, palette, STRONG_MATCH_THRESHOLD
        )
        assert colour == palette["good"]

    def test_status_colours_are_not_series_colours(self, palette):
        """A status colour must never impersonate a data series."""
        for role in ("good", "warning", "critical"):
            assert palette[role] not in palette["series"]


class TestPageCss:
    def test_builds_for_both_palettes(self, palette):
        css = page_css(palette)
        assert css.strip().startswith("<style>")
        assert css.strip().endswith("</style>")

    def test_uses_the_brand_accent(self, palette):
        assert palette["brand"] in page_css(palette)

    def test_brand_is_not_a_chart_series_hue(self, palette):
        """Chrome and data must not share a hue -- see charts.BRAND_NOTE."""
        assert palette["brand"] not in palette["series"]

    def test_disabled_buttons_are_not_interactive(self, palette):
        css = page_css(palette)
        assert ":disabled" in css
        assert "not-allowed" in css

    def test_keyboard_focus_is_visible(self, palette):
        assert ":focus-visible" in page_css(palette)

    def test_respects_reduced_motion(self, palette):
        assert "prefers-reduced-motion" in page_css(palette)

    def test_texture_is_present_on_chrome(self, palette):
        assert "repeating-linear-gradient" in page_css(palette)

    def test_texture_is_confined_to_chrome(self, palette):
        """Texture belongs on the header band and empty state only -- never
        laid over data, where it reads as noise."""
        css = page_css(palette)
        textured = [
            block for block in css.split("}")
            if "repeating-linear-gradient" in block
        ]
        assert textured
        for block in textured:
            assert (".hero" in block) or (".empty-state" in block)


class TestCardAccents:
    def test_emits_a_rule_per_card(self):
        css = card_accent_css([("cand-1", "#0ca30c"), ("cand-2", "#d03b3b")])
        assert ".st-key-cand-1" in css
        assert ".st-key-cand-2" in css
        assert css.count("border-left") == 2

    def test_accepts_a_generator(self):
        css = card_accent_css((f"cand-{i}", "#0ca30c") for i in range(3))
        assert css.count("border-left") == 3

    def test_empty_is_harmless(self):
        assert card_accent_css([]) == "<style></style>"


class TestHero:
    def test_contains_title_and_subtitle(self):
        out = hero_html("Candidate ranking", "3 screened")
        assert "Candidate ranking" in out
        assert "3 screened" in out

    def test_escapes_the_title(self):
        assert "<script>" not in hero_html("<script>x</script>", "sub")
