import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client():
    return TestClient(api.app)


class TestHealth:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()


class TestRank:
    def test_rank_returns_ranking(self, client):
        """Regression: /rank used to call rank_resumes() with a mismatched
        signature and always returned 500."""
        response = client.post("/rank", json={
            "job_description": "Required: Python and machine learning.",
            "resumes": ["cobol developer", "python and machine learning expert"],
            "resume_names": ["weak.txt", "strong.txt"],
        })

        assert response.status_code == 200
        body = response.json()
        assert body["total_candidates"] == 2
        assert body["ranking"][0]["filename"] == "strong.txt"

    def test_mismatched_lengths_rejected(self, client):
        response = client.post("/rank", json={
            "job_description": "Python",
            "resumes": ["a", "b"],
            "resume_names": ["only-one.txt"],
        })
        assert response.status_code == 422

    def test_empty_job_description_rejected(self, client):
        response = client.post("/rank", json={
            "job_description": "",
            "resumes": ["a"],
            "resume_names": ["a.txt"],
        })
        assert response.status_code == 422

    def test_no_resumes_is_empty_ranking(self, client):
        response = client.post("/rank", json={
            "job_description": "Python",
            "resumes": [],
            "resume_names": [],
        })
        assert response.status_code == 200
        assert response.json()["total_candidates"] == 0

    def test_internal_errors_do_not_leak_detail(self, client, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("secret internal path /srv/models/key.bin")

        monkeypatch.setattr(api, "rank_texts", boom)

        response = client.post("/rank", json={
            "job_description": "Python",
            "resumes": ["a"],
            "resume_names": ["a.txt"],
        })
        assert response.status_code == 500
        assert "secret internal path" not in response.text
