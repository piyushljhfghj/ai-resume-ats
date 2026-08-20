from app.experience_engine import (
    compute_experience_score,
    extract_explicit_years,
    extract_total_experience,
    extract_year_ranges,
)


class TestExplicitYears:
    def test_plain(self):
        assert extract_explicit_years("3 years of python") == 3

    def test_plus_notation(self):
        assert extract_explicit_years("5+ years required") == 5

    def test_takes_the_maximum_not_the_first(self):
        text = "3 years of python, and 8 years in software overall"
        assert extract_explicit_years(text) == 8

    def test_abbreviations(self):
        assert extract_explicit_years("7 yrs experience") == 7

    def test_none_present(self):
        assert extract_explicit_years("no duration here") == 0


class TestYearRanges:
    def test_simple_range(self):
        assert extract_year_ranges("2019 - 2023") == 4

    def test_present(self, monkeypatch):
        import app.experience_engine as ee
        monkeypatch.setattr(ee, "_current_year", lambda: 2026)
        assert ee.extract_year_ranges("2020 - Present") == 6

    def test_currently_is_understood(self, monkeypatch):
        import app.experience_engine as ee
        monkeypatch.setattr(ee, "_current_year", lambda: 2026)
        assert ee.extract_year_ranges("2020 to currently") == 6

    def test_sequential_ranges_add_up(self):
        assert extract_year_ranges("2015-2018 and 2019-2022") == 6

    def test_overlapping_ranges_are_merged(self):
        # Two concurrent roles over the same period is 4 years, not 6.
        assert extract_year_ranges("2020-2024 and 2021-2023") == 4

    def test_partial_overlap(self):
        assert extract_year_ranges("2018-2022 and 2020-2024") == 6

    def test_reversed_range_ignored(self):
        assert extract_year_ranges("2024 - 2020") == 0


class TestExperienceScore:
    def test_no_requirement_is_neutral(self):
        assert compute_experience_score("2019-2023", "no years mentioned") == 100.0

    def test_meets_requirement(self):
        assert compute_experience_score("8 years", "5+ years required") == 100.0

    def test_exceeds_requirement(self):
        assert compute_experience_score("10 years", "3 years required") == 100.0

    def test_falls_short_is_proportional(self):
        assert compute_experience_score("2 years", "4 years required") == 50.0

    def test_no_experience_scores_zero(self):
        assert compute_experience_score("no dates at all", "5 years required") == 0.0

    def test_combines_explicit_and_ranges(self):
        assert extract_total_experience("2010-2020, also 3 years of python") == 10
