# app/skill_engine.py

from sentence_transformers import util
from app.utils import clean_text
from app.model_loader import get_model
import re


# INDUSTRY SKILL DATABASE

SKILL_DATABASE = [
    # Programming
    "python", "java", "c++", "javascript", "typescript",

    # AI / ML
    "machine learning", "deep learning", "tensorflow",
    "pytorch", "scikit-learn", "nlp", "computer vision",

    # Backend
    "django", "flask", "fastapi", "node.js", "express",

    # DevOps
    "docker", "kubernetes", "ci/cd",

    # Cloud
    "aws", "azure", "gcp",

    # Databases
    "mysql", "postgresql", "mongodb", "redis",

    # Data
    "numpy", "pandas", "data analysis",

    # APIs
    "api", "rest api",
]

# Core skill weights
SKILL_WEIGHTS = {
    "python": 3,
    "machine learning": 3,
    "deep learning": 3,
    "tensorflow": 2,
    "pytorch": 2,
    "docker": 2,
    "aws": 2,
}


# PRECOMPUTE SKILL EMBEDDINGS 

_model = get_model()
_skill_embeddings = _model.encode(
    SKILL_DATABASE,
    convert_to_tensor=True
)


def extract_skills_semantic(text, threshold=0.55):
    """
    Detect relevant skills using semantic similarity.
    Optimized with precomputed skill embeddings.
    """

    text = clean_text(text)
    model = get_model()

    text_embedding = model.encode(text, convert_to_tensor=True)

    similarities = util.cos_sim(_skill_embeddings, text_embedding)

    detected_skills = []

    for i, score in enumerate(similarities):
        if float(score) >= threshold:
            detected_skills.append(SKILL_DATABASE[i])

    return list(set(detected_skills))


def classify_required_preferred(jd_text, skills):
    """
    Sentence-level required/preferred classification.
    """

    jd_text_lower = jd_text.lower()
    sentences = re.split(r'[.\n]', jd_text_lower)

    required = set()
    preferred = set()

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        for skill in skills:
            if skill in sentence:

                if any(word in sentence for word in ["required", "must", "mandatory"]):
                    required.add(skill)

                elif any(word in sentence for word in ["preferred", "nice to have", "plus"]):
                    preferred.add(skill)

                else:
                    required.add(skill)

    return list(required), list(preferred)


def compute_weighted_skill_score(resume_text, jd_text):

    resume_text = clean_text(resume_text)
    jd_text = clean_text(jd_text)

    jd_skills = extract_skills_semantic(jd_text)
    required_skills, preferred_skills = classify_required_preferred(jd_text, jd_skills)

    resume_skills = extract_skills_semantic(resume_text)

    total_weight = 0
    matched_weight = 0

    matched = []
    missing = []

    # Required (full weight)
    for skill in required_skills:
        weight = SKILL_WEIGHTS.get(skill, 1)
        total_weight += weight

        if skill in resume_skills:
            matched_weight += weight
            matched.append(skill)
        else:
            missing.append(skill)

    # Preferred (half weight)
    for skill in preferred_skills:
        weight = SKILL_WEIGHTS.get(skill, 1) * 0.5
        total_weight += weight

        if skill in resume_skills:
            matched_weight += weight
            matched.append(skill)
        else:
            missing.append(skill)

    if total_weight == 0:
        return 0, matched, missing

    score = matched_weight / total_weight
    return score, list(set(matched)), list(set(missing))