# app/experience_engine.py

import re
from datetime import datetime

# Words a resume uses to mean "still working here".
_PRESENT_WORDS = ("present", "current", "currently", "now", "today", "date")

_RANGE_PATTERN = re.compile(
    r'(19\d{2}|20\d{2})\s*(?:[-–—]|to)\s*'
    r'(19\d{2}|20\d{2}|' + "|".join(_PRESENT_WORDS) + r')'
)

_EXPLICIT_PATTERN = re.compile(r'(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)\b')


def _current_year():
    return datetime.now().year


def extract_year_ranges(text):
    """Total years covered by date ranges like '2021 - 2024' or '2020 - Present'.

    Overlapping ranges are merged rather than added up, so concurrent roles
    (e.g. a job and a side project over the same years) count once.
    """
    text = text.lower()

    intervals = []
    for start, end in _RANGE_PATTERN.findall(text):
        start = int(start)
        end = _current_year() if end in _PRESENT_WORDS else int(end)

        if end > start:
            intervals.append((start, end))

    return _merged_span(intervals)


def _merged_span(intervals):
    """Sum the length of a set of intervals after merging any overlaps."""
    if not intervals:
        return 0

    total = 0
    current_start, current_end = None, None

    for start, end in sorted(intervals):
        if current_end is None:
            current_start, current_end = start, end
        elif start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end

    return total + (current_end - current_start)


def extract_explicit_years(text):
    """Largest explicitly stated duration, e.g. '3 years', '5+ years'.

    Takes the maximum across the whole document -- a resume that opens with
    "3 years of Python" and later says "8 years in software" has 8.
    """
    matches = _EXPLICIT_PATTERN.findall(text.lower())
    return max((int(m) for m in matches), default=0)


def extract_total_experience(text):
    """Combine explicit years and date-range calculation."""
    return max(extract_explicit_years(text), extract_year_ranges(text))


def compute_experience_score(resume_text, jd_text):
    jd_years = extract_total_experience(jd_text)
    resume_years = extract_total_experience(resume_text)

    # The JD states no requirement, so this dimension cannot discriminate.
    if jd_years == 0:
        return 100.0

    if resume_years <= 0:
        return 0.0

    if resume_years >= jd_years:
        return 100.0

    return round((resume_years / jd_years) * 100, 1)
