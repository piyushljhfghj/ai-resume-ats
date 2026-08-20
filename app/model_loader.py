# app/model_loader.py

from sentence_transformers import SentenceTransformer

from app.config import MODEL_NAME

_model = None


def get_model():
    """Return the shared embedding model, loading it on first use.

    Every module must go through this function -- instantiating
    SentenceTransformer directly loads a second copy of the same
    ~420MB model into memory.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model
