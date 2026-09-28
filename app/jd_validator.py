# app/jd_validator.py
"""Decide whether a job description is meaningful enough to score against.

Without this gate, a gibberish JD still produced a confident-looking score:
the embedding model returns *some* cosine similarity for any two strings,
and the skill/experience dimensions fell back to their neutral values.

The check is about text quality, not skill count -- a legitimate JD may name
no skill from our vocabulary. It combines four signals:

1. Enough meaningful words (at least MIN_MEANINGFUL_WORDS).
2. Few gibberish tokens: words that are neither known vocabulary nor
   pronounceable (no vowels, long consonant runs, e.g. "gdfgfdgd").
3. No single token dominating the text ("python python python python").
4. At least one piece of job content: a known skill, a role noun, a
   responsibility verb or a qualification/hiring term.

Short but real JDs ("Python developer", "Registered nurse, night shifts")
pass: the thresholds are ratios, and there is no minimum word count beyond
two meaningful words.
"""

import re
from collections import Counter

from app.skill_extractor import extract_skills_from_text

INVALID_JD_MESSAGE = (
    "Please provide a meaningful job description containing "
    "role/responsibility/skill information."
)

MIN_MEANINGFUL_WORDS = 2
# Share of words that may look like random keystrokes before we give up.
MAX_GIBBERISH_RATIO = 0.35
# Share of the text a single repeated word may take (only checked from
# MIN_TOKENS_FOR_REPETITION words up, so "Python developer" is unaffected).
MAX_TOP_TOKEN_SHARE = 0.5
MIN_TOKENS_FOR_REPETITION = 4
# Share of all tokens that may be bare numbers ("525256525").
MAX_NUMERIC_RATIO = 0.5

_VOWELS = set("aeiouy")

# Everyday English: function words and common verbs/nouns that appear in any
# natural-language JD. Recognising these is what separates prose from noise.
_COMMON_WORDS = set("""
a about above across after all also an and any are as at be been being both
but by can could do does each either etc every for from good great has have
he help high highly how i if in including into is it its just like looking
make may more most must new no not of on one or other our out over own per
plus preferably preferred related required requirements same she should so
some strong such than that the their them then there these they this those
through to under up us using very we well what when where which
while who will with within without work working would year years you your
able ability across day days week weeks month months time full part hours
based level least minimum maximum good excellent solid proven hands on
knowledge understanding familiarity familiar exposure proficiency proficient
""".split())

# Job content: roles, responsibilities, qualifications, hiring language.
_JOB_WORDS = set("""
job role position opening vacancy hiring hire seeking candidate candidates
want wanted need needed required
applicant join company team teams organisation organization client clients
customer customers business department office remote hybrid onsite site
salary compensation benefits shift shifts contract permanent intern
internship junior senior lead principal staff head chief associate trainee
engineer engineering developer development programmer architect analyst
scientist researcher designer manager management director administrator
consultant specialist technician coordinator officer executive assistant
accountant nurse doctor teacher tutor driver sales marketing support
operator supervisor representative agent writer editor recruiter
responsibilities responsibility duties duty tasks task requirement
qualifications qualification skills skill experience experienced expertise
education degree bachelor bachelors master masters phd diploma certification
certified license licensed graduate background field science computer
develop build design implement maintain manage lead create write test
deploy integrate analyse analyze support collaborate communicate deliver
own review improve optimize optimise monitor document report research
coordinate plan train mentor ensure provide handle operate troubleshoot
backend frontend fullstack software hardware data cloud web mobile systems
system services service application applications product products platform
platforms model models code api apis database databases infrastructure
security network pipeline pipelines tools tool technical technology
communication problem solving detail oriented
""".split())

_KNOWN_WORDS = _COMMON_WORDS | _JOB_WORDS

# Cheap stemming so "developing", "responsibilities", "engineers" all hit.
_SUFFIXES = ("ities", "ies", "ing", "ers", "ed", "es", "er", "s", "ly")

_TOKEN = re.compile(r"[A-Za-z]+|\d+")


def _stems(word):
    yield word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[: -len(suffix)]
            yield stem
            yield stem + "e"   # "managing" -> "manag" -> "manage"
            yield stem + "y"   # "responsibilities" -> "responsibil" ... "duties" -> "duty"


def _is_known(word, skill_words):
    return any(s in _KNOWN_WORDS or s in skill_words for s in _stems(word))


def _is_job_word(word, skill_words):
    return any(s in _JOB_WORDS or s in skill_words for s in _stems(word))


def _longest_consonant_run(word):
    return max((len(run) for run in re.findall(r"[^aeiouy]+", word)), default=0)


def _looks_pronounceable(word):
    """Heuristic: real (including unknown) words have vowels and no long
    consonant pile-ups. "terraform", "grafana" pass; "gdfgfdgd" does not."""
    vowels = sum(ch in _VOWELS for ch in word)
    if vowels == 0:
        return False
    if _longest_consonant_run(word) >= 5:
        return False
    return vowels / len(word) >= 0.2


def _is_acronym(original):
    # "AWS", "SQL", "NLP", "CI" -- vowel-less but legitimate. Neutral: they
    # count neither for nor against the text.
    return original.isupper() and 2 <= len(original) <= 5


def validate_job_description(text):
    """Return {"valid": bool, "reasons": [str], "stats": {...}}.

    reasons is empty for a valid JD and lists every failed check otherwise,
    so the UI can say *why* a JD was rejected.
    """
    text = text or ""
    tokens = _TOKEN.findall(text)

    skills = extract_skills_from_text(text)
    skill_words = {part for skill in skills for part in re.findall(r"[a-z]+", skill)}

    numeric = [t for t in tokens if t.isdigit()]
    words = [t for t in tokens if not t.isdigit()]

    known, gibberish = [], []
    judged = meaningful = 0
    for original in words:
        word = original.lower()
        if _is_known(word, skill_words):
            known.append(word)
            meaningful += 1
            judged += 1
            continue
        # Unknown one/two-letter fragments ("js", "ml") carry no signal.
        if len(word) <= 2:
            continue
        # Acronyms ("SRE", "SQL") are meaningful but never judged gibberish.
        if _is_acronym(original):
            meaningful += 1
            continue
        judged += 1
        if _looks_pronounceable(word):
            meaningful += 1
        else:
            gibberish.append(word)

    job_signals = sorted({w for w in known if _is_job_word(w, skill_words)} | set(skills))

    lowered = [w.lower() for w in words]
    top_word, top_count = Counter(lowered).most_common(1)[0] if lowered else ("", 0)

    stats = {
        "tokens": len(tokens),
        "words": len(words),
        "known_words": len(known),
        "gibberish_words": len(gibberish),
        "numeric_tokens": len(numeric),
        "recognised_skills": sorted(skills),
        "job_signals": job_signals[:15],
    }

    reasons = []
    if not words:
        reasons.append("The text contains no words.")
    else:
        if judged and len(gibberish) / judged > MAX_GIBBERISH_RATIO:
            reasons.append(
                f"{len(gibberish)} of {judged} words look like random "
                f"characters (e.g. {', '.join(repr(g) for g in gibberish[:3])})."
            )
        if meaningful < MIN_MEANINGFUL_WORDS or not known:
            reasons.append("Too little meaningful text to describe a role.")
        if (
            len(words) >= MIN_TOKENS_FOR_REPETITION
            and top_count / len(words) > MAX_TOP_TOKEN_SHARE
        ):
            reasons.append(f"The word {top_word!r} is repeated excessively.")
        if not job_signals:
            reasons.append(
                "No role, responsibility, qualification or skill information found."
            )
    if tokens and len(numeric) / len(tokens) > MAX_NUMERIC_RATIO:
        reasons.append("The text is mostly numbers.")

    return {"valid": not reasons, "reasons": reasons, "stats": stats}
