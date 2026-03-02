# Import libraries
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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


# Step 3: Combine Job Description and Resumes
documents = [job_description] + resumes


# Step 4: Convert Text into Numbers using TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(documents)


# Step 5: Compute Cosine Similarity
similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])


# Step 6: Rank Resumes
scores = similarity_scores.flatten()
sorted_indexes = np.argsort(scores)[::-1]


# Step 7: Print Ranking
print("\nResume Ranking Results:\n")

for index in sorted_indexes:
    print(f"{resume_names[index]}  -->  Score: {scores[index]:.4f}")
