import pytest
import torch

import app.intelligent_ranker as ranker


class FakeModel:
    """Deterministic stand-in for the embedding model.

    Encodes text into a 3-dim keyword-presence vector so ranking logic can be
    tested without loading a ~420MB transformer.
    """

    def encode(self, text, convert_to_tensor=False):
        if isinstance(text, (list, tuple)):
            return torch.stack([self._vec(t) for t in text])
        return self._vec(text)

    @staticmethod
    def _vec(text):
        text = text.lower()
        return torch.tensor([
            1.0 if "python" in text else 0.0,
            1.0 if "machine learning" in text else 0.0,
            1.0 if "docker" in text else 0.0,
        ])


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    """Applied to every test, so the suite never downloads or loads the model."""
    monkeypatch.setattr(ranker, "get_model", lambda: FakeModel())
    return FakeModel()
