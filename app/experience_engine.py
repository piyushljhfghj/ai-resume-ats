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

# "1-3 years", "2 to 4 yrs" -- in a JD the lower bound is the requirement.
_YEARS_RANGE_PATTERN = re.compile(
    r'(\d{1,2})\s*(?:[-–—]|to)\s*(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)\b'
)


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


def extract_required_years(jd_text):
    """Minimum years a JD asks for. "1-3 years" means at least 1, not 3."""
    text = jd_text.lower()
    minimums = [int(low) for low, _ in _YEARS_RANGE_PATTERN.findall(text)]
    # Blank out the ranges so their upper bound is not re-read as a minimum.
    remainder = _YEARS_RANGE_PATTERN.sub(" ", text)
    minimums += [int(m) for m in _EXPLICIT_PATTERN.findall(remainder)]
    return max(minimums, default=0)


def experience_evidence(resume_text, jd_text):
    """Experience score plus the facts it was computed from.

    Scoring rules (unknown never earns credit):
      * JD minimum N, resume shows >= N years      -> 100
      * JD minimum N, resume shows 0 < y < N years -> y / N * 100
      * resume shows no determinable experience    -> 0
      * JD states no minimum, resume shows > 0     -> 100 (requirement met)
    """
    jd_years = extract_required_years(jd_text)
    resume_years = extract_total_experience(resume_text)

    if resume_years <= 0:
        score = 0.0
        note = (
            "No years of experience could be determined from the resume "
            "(no 'N years' statement or date ranges), so no credit is given."
        )
    elif jd_years == 0:
        score = 100.0
        note = (
            f"The job description states no minimum; the resume shows "
            f"{resume_years} year(s) of experience."
        )
    elif resume_years >= jd_years:
        score = 100.0
        note = f"Resume shows {resume_years} year(s); the role asks for {jd_years}."
    else:
        score = round((resume_years / jd_years) * 100, 1)
        note = (
            f"Resume shows {resume_years} of the {jd_years} year(s) required "
            f"({resume_years}/{jd_years})."
        )

    return {
        "score": score,
        "required_years": jd_years or None,
        "resume_years": resume_years or None,
        "note": note,
    }


def compute_experience_score(resume_text, jd_text):
    return experience_evidence(resume_text, jd_text)["score"]
