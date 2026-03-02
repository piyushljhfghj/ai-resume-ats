# Import required libraries
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# Load pretrained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')


# Step 1: Load Job Description
with open("data/job_description.txt", "r", encoding="utf-8") as file:
    job_description = file.read()


# Step 2: Load All Resumes
resume_folder = "data/resumes"
resumes = []
resume_names = []

for filename in os.listdir(resume_folder):
    if filename.endswith(".txt"):
        file_path = os.path.join(resume_folder, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            resumes.append(file.read())
            resume_names.append(filename)


# Step 3: Generate Embeddings
job_embedding = model.encode([job_description])
resume_embeddings = model.encode(resumes)


# Step 4: Compute Cosine Similarity
similarity_scores = cosine_similarity(job_embedding, resume_embeddings)


# Step 5: Rank Resumes
scores = similarity_scores.flatten()
sorted_indexes = np.argsort(scores)[::-1]


# Step 6: Print Ranking
print("\n🔵 Embedding-Based Resume Ranking:\n")

for index in sorted_indexes:
    print(f"{resume_names[index]}  -->  Score: {scores[index]:.4f}")