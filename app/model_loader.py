# app/model_loader.py

from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-mpnet-base-v2")
    return _model