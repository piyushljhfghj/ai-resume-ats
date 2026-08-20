"""Embedding baseline ranking. Run as a script: python -m app.embedding_ranker"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.model_loader import get_model
from app.utils import load_job_description, load_resumes


def rank_with_embeddings(job_description, resumes):
    """Return (index, score) pairs, best first."""
    model = get_model()

    job_embedding = model.encode([job_description])
    resume_embeddings = model.encode(resumes)

    scores = cosine_similarity(job_embedding, resume_embeddings).flatten()

    return [(i, scores[i]) for i in np.argsort(scores)[::-1]]


def main():
    job_description = load_job_description()
    resumes, resume_names = load_resumes()

    print("\nEmbedding-Based Resume Ranking:\n")
    for index, score in rank_with_embeddings(job_description, resumes):
        print(f"{resume_names[index]}  -->  Score: {score:.4f}")


if __name__ == "__main__":
    main()
