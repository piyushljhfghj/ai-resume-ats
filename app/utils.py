


# app/utils.py

import hashlib
import os
import re
import string


def inputs_fingerprint(jd_text, uploaded_files):
    """Stable id for one set of screening inputs (JD + uploaded files).

    The dashboard stores it next to its results; when the JD is edited or a
    file is added/removed the fingerprint changes and the old results are
    discarded instead of being shown against the new inputs.
    """
    h = hashlib.sha256((jd_text or "").strip().encode("utf-8"))
    for f in uploaded_files or []:
        ident = (
            getattr(f, "file_id", None),
            getattr(f, "name", str(f)),
            getattr(f, "size", None),
        )
        h.update(repr(ident).encode("utf-8"))
    return h.hexdigest()


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