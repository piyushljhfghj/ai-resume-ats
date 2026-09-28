# app/intelligent_ranker.py

from sentence_transformers import util

from app.config import (
    EXPERIENCE_WEIGHT,
    PREFERRED_SKILL_WEIGHT,
    REQUIRED_SKILL_WEIGHT,
    SEMANTIC_WEIGHT,
    SKILL_WEIGHT,
)
from app.experience_engine import experience_evidence
from app.jd_validator import INVALID_JD_MESSAGE, validate_job_description
from app.logger import logger
from app.model_loader import get_model
from app.skill_extractor import extract_required_preferred, extract_skills_from_text

STATUS_SCORED = "scored"
STATUS_INVALID_JD = "invalid_jd"


def compute_semantic_score(resume_text, jd_text):
    """Cosine similarity between a single resume and the JD, as a percentage."""
    model = get_model()
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    return _similarity_percent(resume_embedding, jd_embedding)


def _similarity_percent(resume_embedding, jd_embedding):
    score = float(util.cos_sim(resume_embedding, jd_embedding))
    # Cosine can dip below zero; a negative percentage is meaningless here.
    return round(max(score, 0.0) * 100, 1)


def skill_evidence(resume_text, jd_text):
    """Weighted required/preferred skill match, with the skills behind it.

    A skill named in both the required and preferred halves of the JD is
    counted once, as required. If the JD names no skill we recognise there
    is no evidence to award, so the score is 0 -- never a default 100 with
    an empty matched list.
    """
    jd_skills = extract_required_preferred(jd_text)
    resume_skills = set(extract_skills_from_text(resume_text))

    required = sorted(set(jd_skills["required"]))
    # A skill can appear on both sides of the JD split; required wins, so it
    # is not weighted twice.
    preferred = sorted(set(jd_skills["preferred"]) - set(required))

    matched_required = [s for s in required if s in resume_skills]
    matched_preferred = [s for s in preferred if s in resume_skills]

    total_weight = (
        len(required) * REQUIRED_SKILL_WEIGHT
        + len(preferred) * PREFERRED_SKILL_WEIGHT
    )
    matched_weight = (
        len(matched_required) * REQUIRED_SKILL_WEIGHT
        + len(matched_preferred) * PREFERRED_SKILL_WEIGHT
    )

    if total_weight == 0:
        score = 0.0
        note = (
            "The job description names no skill from the recognised "
            "vocabulary, so skill coverage could not be assessed; no credit "
            "is given."
        )
    else:
        score = round(matched_weight / total_weight * 100, 1)
        note = (
            f"Matched weight {matched_weight} of {total_weight} "
            f"(required skills x{REQUIRED_SKILL_WEIGHT}, "
            f"preferred x{PREFERRED_SKILL_WEIGHT})."
        )

    return {
        "score": score,
        "required": required,
        "preferred": preferred,
        "matched_required": matched_required,
        "matched_preferred": matched_preferred,
        "missing_required": [s for s in required if s not in resume_skills],
        "missing_preferred": [s for s in preferred if s not in resume_skills],
        "matched_weight": matched_weight,
        "total_weight": total_weight,
        "note": note,
    }


def compute_skill_score(resume_text, jd_text):
    """Returns (score, matched, missing)."""
    ev = skill_evidence(resume_text, jd_text)
    matched = sorted(ev["matched_required"] + ev["matched_preferred"])
    missing = sorted(ev["missing_required"] + ev["missing_preferred"])
    return ev["score"], matched, missing


def compute_final_score(semantic, skill, experience):
    """Weighted final ATS score."""
    final = (
        SEMANTIC_WEIGHT * semantic
        + SKILL_WEIGHT * skill
        + EXPERIENCE_WEIGHT * experience
    )
    return round(final, 1)


def _final_formula(semantic, skill, experience, final):
    return (
        f"{SEMANTIC_WEIGHT} x {semantic} + {SKILL_WEIGHT} x {skill} + "
        f"{EXPERIENCE_WEIGHT} x {experience} = {final}"
    )


def _invalid_jd_result(name, reasons):
    """A candidate row for a JD that cannot be scored against: all zeros."""
    detail = " ".join(reasons)
    return {
        "filename": name,
        "status": STATUS_INVALID_JD,
        "semantic_score": 0.0,
        "skill_score": 0.0,
        "experience_score": 0.0,
        "final_score": 0.0,
        "matched_skills": [],
        "missing_skills": [],
        "explanation": (
            f"Not scored: invalid job description. {detail} {INVALID_JD_MESSAGE}"
        ),
        "evidence": {"job_description": {"valid": False, "reasons": reasons}},
    }


def rank_texts(jd_text, documents):
    """Rank already-extracted resume text against a job description.

    documents: iterable of (name, resume_text) pairs.
    Returns a list of result dicts, best final_score first. Each carries a
    "status": "scored", or "invalid_jd" when the JD fails validation -- in
    which case no model is run and every score is 0.

    This is the core entry point -- it takes plain strings so it can be
    driven from the API, a test, or a batch job. Use rank_resumes() when
    you have uploaded file objects instead.
    """
    documents = [(name, text) for name, text in documents]
    if not documents:
        return []

    validation = validate_job_description(jd_text)
    if not validation["valid"]:
        logger.warning("Invalid job description: %s", validation["reasons"])
        return [_invalid_jd_result(name, validation["reasons"]) for name, _ in documents]

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
        skills = skill_evidence(resume_text, jd_text)
        experience = experience_evidence(resume_text, jd_text)
        skill_score = skills["score"]
        experience_score = round(experience["score"], 1)

        # Computed from the same rounded values that are displayed, so the
        # shown components always reproduce the shown final score.
        final_score = compute_final_score(semantic_score, skill_score, experience_score)
        formula = _final_formula(semantic_score, skill_score, experience_score, final_score)

        explanation = (
            f"Skill Match: {skill_score}%, "
            f"Semantic Similarity: {semantic_score}%, "
            f"Experience Match: {experience_score}%. "
            f"Overall ATS Score: {final_score}% ({formula})."
        )

        results.append({
            "filename": name,
            "status": STATUS_SCORED,
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "experience_score": experience_score,
            "final_score": final_score,
            "matched_skills": sorted(
                skills["matched_required"] + skills["matched_preferred"]
            ),
            "missing_skills": sorted(
                skills["missing_required"] + skills["missing_preferred"]
            ),
            "explanation": explanation,
            "evidence": {
                "semantic": {
                    "note": (
                        "Cosine similarity between the whole resume and the "
                        "whole job description embeddings (negative clipped to 0)."
                    ),
                },
                "skill": skills,
                "experience": experience,
                "final": {"formula": formula},
            },
        })

    return sorted(results, key=lambda x: x["final_score"], reverse=True)


NO_TEXT_PDF_REASON = (
    "The PDF contains no extractable text -- it may be scanned or image-based. "
    "Upload a text-based PDF or a .txt file."
)


def extract_uploaded_text(file):
    """Read text out of an uploaded .pdf or .txt file object."""
    # A Streamlit UploadedFile may already have been read by an earlier run;
    # rewind so a re-run does not see an "empty" file.
    if hasattr(file, "seek"):
        file.seek(0)

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


def read_uploads(uploaded_files):
    """Extract text from uploads. Returns (documents, failures).

    documents: [(name, text)]. failures: [{"filename", "reason"}] for files
    that could not be read or held no text. A failed file is reported, never
    scored -- an unreadable PDF is not a weak candidate -- and one bad file
    does not take down the batch.
    """
    documents, failures = [], []

    for file in uploaded_files:
        name = getattr(file, "name", str(file))
        is_pdf = name.lower().endswith(".pdf")
        try:
            text = extract_uploaded_text(file)
        except Exception:
            logger.exception("Could not read resume %s", name)
            failures.append({
                "filename": name,
                "reason": (
                    "The file could not be opened -- it may be corrupted, "
                    "password-protected, or not a valid PDF."
                    if is_pdf else "The file could not be read."
                ),
            })
            continue

        if not text or not text.strip():
            logger.warning("No text extracted from %s", name)
            failures.append({
                "filename": name,
                "reason": NO_TEXT_PDF_REASON if is_pdf else "The file is empty.",
            })
            continue

        documents.append((name, text))

    return documents, failures


def rank_resumes(jd_text, uploaded_files):
    """Rank uploaded resume files against a job description.

    Returns (results, failures) -- see read_uploads() for failures.
    """
    documents, failures = read_uploads(uploaded_files)
    return rank_texts(jd_text, documents), failures
