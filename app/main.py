"""TF-IDF baseline ranking. Run as a script: python -m app.main"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils import load_job_description, load_resumes


def rank_with_tfidf(job_description, resumes):
    """Return (index, score) pairs, best first."""
    documents = [job_description] + resumes

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)

    scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    return [(i, scores[i]) for i in np.argsort(scores)[::-1]]


def main():
    job_description = load_job_description()
    resumes, resume_names = load_resumes()

    print("\nResume Ranking Results (TF-IDF):\n")
    for index, score in rank_with_tfidf(job_description, resumes):
        print(f"{resume_names[index]}  -->  Score: {score:.4f}")


if __name__ == "__main__":
    main()
