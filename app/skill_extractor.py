# app/skill_extractor.py

import re

# Central Skill Vocabulary
SKILL_DATABASE = [
    # Programming
    "python", "java", "c++", "javascript", "typescript",

    # AI / ML
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "nlp", "computer vision",
    "llm", "rag", "openai", "sentence transformers", "semantic search",
    "faiss", "vector database",

    # Backend
    "django", "flask", "fastapi", "node.js", "express",

    # Frontend
    "react", "angular", "vue",

    # DevOps
    "docker", "kubernetes", "ci/cd",

    # Cloud
    "aws", "azure", "gcp",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis",

    # Tools
    "git", "linux", "streamlit",

    # Data
    "pandas", "numpy",

    # APIs
    "rest api", "api"
]


def clean_text(text):
    return text.lower()


def extract_skills_from_text(text):
    """
    Extract skills from text using regex matching.
    """
    text = clean_text(text)
    found = []

    for skill in SKILL_DATABASE:
        # Lookarounds rather than \b, which never matches after "c++". An
        # optional plural "s" lets "REST APIs" count as "rest api".
        pattern = r"(?<!\w)" + re.escape(skill) + r"s?(?!\w)"
        if re.search(pattern, text):
            found.append(skill)

    return list(set(found))


def extract_required_preferred(jd_text):
    """
    Split JD into required and preferred sections properly.
    """
    jd_text = clean_text(jd_text)

    required_section = jd_text
    preferred_section = ""

    if "preferred" in jd_text:
        parts = jd_text.split("preferred", 1)
        required_section = parts[0]
        preferred_section = parts[1]

    required_skills = extract_skills_from_text(required_section)
    preferred_skills = extract_skills_from_text(preferred_section)

    return {
        "required": required_skills,
        "preferred": preferred_skills
    }