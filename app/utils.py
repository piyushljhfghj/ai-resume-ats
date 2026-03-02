


# app/utils.py

import os
import re
import string


# Text Cleaning 
def clean_text(text):
    text = text.lower()
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.strip()



# Load job description
def load_job_description(path="data/job_description.txt"):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()



# load resumes from folder
def load_resumes(folder_path="data/resumes"):
    resumes = []
    resume_names = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)

            with open(file_path, "r", encoding="utf-8") as file:
                resumes.append(file.read())
                resume_names.append(filename)

    return resumes, resume_names