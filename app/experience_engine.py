# app/experience_engine.py

import re
from datetime import datetime

CURRENT_YEAR = datetime.now().year


def extract_year_ranges(text):
    """
    Extract year ranges like:
    2021 - 2024
    2020 – Present
    """
    text = text.lower()

    patterns = [
        r'(20\d{2})\s*[-–]\s*(20\d{2})',
        r'(20\d{2})\s*[-–]\s*(present)'
    ]

    total_years = 0

    for pattern in patterns:
        matches = re.findall(pattern, text)

        for start, end in matches:
            start = int(start)

            if end == "present":
                end = CURRENT_YEAR
            else:
                end = int(end)

            if end > start:
                total_years += (end - start)

    return total_years


def extract_explicit_years(text):
    """
    Extract '3 years', '3+ years'
    """
    text = text.lower()
    match = re.search(r'(\d+)\+?\s*(years|year|yrs|yr)', text)
    if match:
        return int(match.group(1))
    return 0


def extract_total_experience(text):
    """
    Combine explicit years + date range calculation
    """
    explicit = extract_explicit_years(text)
    date_based = extract_year_ranges(text)

    return max(explicit, date_based)


def compute_experience_score(resume_text, jd_text):

    jd_years = extract_total_experience(jd_text)
    resume_years = extract_total_experience(resume_text)

    if jd_years == 0:
        return 100.0

    if resume_years == 0:
        return 0.0

    if resume_years >= jd_years:
        return 100.0

    return round((resume_years / jd_years) * 100, 1)