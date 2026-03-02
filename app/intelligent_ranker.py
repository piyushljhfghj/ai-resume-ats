# app/intelligent_ranker.py

from sentence_transformers import SentenceTransformer, util
from app.skill_extractor import extract_required_preferred, extract_skills_from_text
from app.experience_engine import compute_experience_score

model = SentenceTransformer("all-mpnet-base-v2")


def compute_semantic_score(resume_text, jd_text):
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    score = float(util.cos_sim(resume_embedding, jd_embedding))
    return round(score * 100, 1)


def compute_skill_score(resume_text, jd_text):

    jd_skills = extract_required_preferred(jd_text)
    resume_skills = extract_skills_from_text(resume_text)

    required = jd_skills["required"]
    preferred = jd_skills["preferred"]

    matched = []
    missing = []

    total_weight = 0
    matched_weight = 0

    # Required skills weight = 2
    for skill in required:
        total_weight += 2
        if skill in resume_skills:
            matched.append(skill)
            matched_weight += 2
        else:
            missing.append(skill)

    # Preferred skills weight = 1
    for skill in preferred:
        total_weight += 1
        if skill in resume_skills:
            matched.append(skill)
            matched_weight += 1
        else:
            missing.append(skill)

    if total_weight == 0:
        return 0, [], []

    score = (matched_weight / total_weight) * 100

    return round(score, 1), list(set(matched)), list(set(missing))


def compute_final_score(semantic, skill, experience):
    """
    Weighted final ATS score
    """
    final = (0.4 * semantic) + (0.4 * skill) + (0.2 * experience)
    return round(final, 1)


def rank_resumes(jd_text, uploaded_files):

    results = []

    for file in uploaded_files:

        if file.name.endswith(".pdf"):
            from app.pdf_parser import extract_text_from_pdf
            resume_text = extract_text_from_pdf(file)
        else:
            resume_text = file.read().decode("utf-8")

        semantic_score = compute_semantic_score(resume_text, jd_text)

        skill_score, matched, missing = compute_skill_score(
            resume_text,
            jd_text
        )

        experience_score = compute_experience_score(
            resume_text,
            jd_text
        ) 

        final_score = compute_final_score(
            semantic_score,
            skill_score,
            experience_score
        )

        explanation = (
            f"Skill Match: {skill_score}%, "
            f"Semantic Similarity: {semantic_score}%, "
            f"Experience Match: {round(experience_score,1)}%. "
            f"Overall ATS Score: {final_score}%."
        )

        results.append({
            "filename": file.name,
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "experience_score": round(experience_score, 1),
            "final_score": final_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "cluster":0,
            "explanation": explanation
        })

    results = sorted(results, key=lambda x: x["final_score"], reverse=True)

    return results