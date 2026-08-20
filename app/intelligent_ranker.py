# app/intelligent_ranker.py

from sentence_transformers import util

from app.config import (
    EXPERIENCE_WEIGHT,
    PREFERRED_SKILL_WEIGHT,
    REQUIRED_SKILL_WEIGHT,
    SEMANTIC_WEIGHT,
    SKILL_WEIGHT,
)
from app.experience_engine import compute_experience_score
from app.logger import logger
from app.model_loader import get_model
from app.skill_extractor import extract_required_preferred, extract_skills_from_text


def compute_semantic_score(resume_text, jd_text):
    """Cosine similarity between a single resume and the JD, as a percentage."""
    model = get_model()
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    return _similarity_percent(resume_embedding, jd_embedding)


def _similarity_percent(resume_embedding, jd_embedding):
    score = float(util.cos_sim(resume_embedding, jd_embedding))
    return round(score * 100, 1)


def compute_skill_score(resume_text, jd_text):
    """Weighted required/preferred skill match.

    Returns (score, matched, missing). A skill named in both the required
    and preferred halves of the JD is counted once, as required.
    """
    jd_skills = extract_required_preferred(jd_text)
    resume_skills = set(extract_skills_from_text(resume_text))

    required = list(jd_skills["required"])
    # A skill can appear on both sides of the JD split; required wins, so it
    # is not weighted twice.
    preferred = [s for s in jd_skills["preferred"] if s not in set(required)]

    matched = []
    missing = []

    total_weight = 0
    matched_weight = 0

    for skill_list, weight in (
        (required, REQUIRED_SKILL_WEIGHT),
        (preferred, PREFERRED_SKILL_WEIGHT),
    ):
        for skill in skill_list:
            total_weight += weight
            if skill in resume_skills:
                matched.append(skill)
                matched_weight += weight
            else:
                missing.append(skill)

    if total_weight == 0:
        # The JD names no skill we recognise, so this dimension cannot
        # discriminate between candidates. Score it neutral rather than 0,
        # which would silently cap everyone's final score at 60.
        return 100.0, [], []

    score = (matched_weight / total_weight) * 100

    return round(score, 1), sorted(set(matched)), sorted(set(missing))


def compute_final_score(semantic, skill, experience):
    """Weighted final ATS score."""
    final = (
        SEMANTIC_WEIGHT * semantic
        + SKILL_WEIGHT * skill
        + EXPERIENCE_WEIGHT * experience
    )
    return round(final, 1)


def rank_texts(jd_text, documents):
    """Rank already-extracted resume text against a job description.

    documents: iterable of (name, resume_text) pairs.
    Returns a list of result dicts, best final_score first.

    This is the core entry point -- it takes plain strings so it can be
    driven from the API, a test, or a batch job. Use rank_resumes() when
    you have uploaded file objects instead.
    """
    documents = [(name, text) for name, text in documents]
    if not documents:
        return []

    model = get_model()

    # Encode the JD once for the whole batch, and batch the resumes into a
    # single encode call, instead of re-encoding the JD for every resume.
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    resume_embeddings = model.encode(
        [text for _, text in documents], convert_to_tensor=True
    )

    results = []

    for (name, resume_text), resume_embedding in zip(documents, resume_embeddings):

        semantic_score = _similarity_percent(resume_embedding, jd_embedding)
        skill_score, matched, missing = compute_skill_score(resume_text, jd_text)
        experience_score = compute_experience_score(resume_text, jd_text)

        final_score = compute_final_score(semantic_score, skill_score, experience_score)

        explanation = (
            f"Skill Match: {skill_score}%, "
            f"Semantic Similarity: {semantic_score}%, "
            f"Experience Match: {round(experience_score, 1)}%. "
            f"Overall ATS Score: {final_score}%."
        )

        results.append({
            "filename": name,
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "experience_score": round(experience_score, 1),
            "final_score": final_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "explanation": explanation,
        })

    return sorted(results, key=lambda x: x["final_score"], reverse=True)


def extract_uploaded_text(file):
    """Read text out of an uploaded .pdf or .txt file object."""
    name = getattr(file, "name", "")

    if name.lower().endswith(".pdf"):
        from app.pdf_parser import extract_text_from_pdf

        return extract_text_from_pdf(file)

    raw = file.read()
    if isinstance(raw, bytes):
        # Resumes are routinely exported as cp1252 or latin-1; a hard utf-8
        # decode turns one such file into a failed batch.
        return raw.decode("utf-8", errors="replace")
    return raw


def rank_resumes(jd_text, uploaded_files):
    """Rank uploaded resume files against a job description.

    A file that cannot be read is skipped and logged -- one unreadable
    PDF must not take down the whole batch.
    """
    documents = []

    for file in uploaded_files:
        name = getattr(file, "name", str(file))
        try:
            text = extract_uploaded_text(file)
        except Exception:
            logger.exception("Could not read resume %s -- skipping", name)
            continue

        if not text or not text.strip():
            logger.warning("No text extracted from %s -- skipping", name)
            continue

        documents.append((name, text))

    return rank_texts(jd_text, documents)
