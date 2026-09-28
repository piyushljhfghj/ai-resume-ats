"""Regression tests: invalid JDs are never scored, valid JDs are scored on
evidence, and unreadable PDFs are reported rather than scored."""

import io

import fitz
import pytest

import app.intelligent_ranker as ranker
from app.intelligent_ranker import (
    STATUS_INVALID_JD,
    STATUS_SCORED,
    compute_final_score,
    rank_resumes,
    rank_texts,
    skill_evidence,
)
from app.jd_validator import validate_job_description
from app.skill_extractor import extract_skills_from_text

VALID_JD = """AI/ML Backend Engineer

We are looking for an AI/ML Backend Engineer with 1–3 years of experience.

Required Skills:
Python, FastAPI or Flask, REST APIs, PostgreSQL, Git,
Machine Learning, NLP, Sentence Transformers, text embeddings,
semantic search, data processing and model integration.

Preferred Skills:
FAISS, vector databases, RAG, OpenAI APIs, Docker,
AWS, Streamlit, CI/CD.

Responsibilities:
Develop Python backend services and REST APIs.
Build NLP and machine learning features.
Implement semantic search and embedding-based retrieval.
Integrate ML models and LLM APIs.
Work with PostgreSQL and cloud platforms.
Write tests and maintain documented code.

Education:
Bachelor's or Master's degree in Computer Science,
AI/ML, Data Science, or related field.
"""

STRONG_RESUME = (
    "Backend engineer, 2021 - 2024. Python, FastAPI, REST APIs, PostgreSQL, "
    "Git, machine learning, NLP, sentence transformers, semantic search, "
    "FAISS, Docker, AWS."
)

GIBBERISH_JDS = [
    "gdssgd dsfefds gdgd gdg gdfgfdgd vbtsgdsfdad",
    "xnsldln enwlkdns dnsjnd fdsnl 525256525",
    "asdf qwerty zxcv",
    "python python python python python",
    "123 456 789 000",
    "lorem ipsum dolor sit amet consectetur",
    "",
]

SHORT_LEGIT_JDS = [
    "Python developer",
    "Data Analyst",
    "Kubernetes SRE",
    "Barista wanted",
    "Registered nurse for night shifts",
    "Plumber needed, 3 years experience",
    "Looking for a Terraform and Ansible specialist",
    "Sales executive with strong communication skills",
    "We need someone to manage our Instagram and TikTok accounts",
]


class TestValidator:
    @pytest.mark.parametrize("jd", GIBBERISH_JDS)
    def test_gibberish_is_invalid(self, jd):
        result = validate_job_description(jd)
        assert result["valid"] is False
        assert result["reasons"]

    @pytest.mark.parametrize("jd", SHORT_LEGIT_JDS)
    def test_short_legitimate_jd_is_valid(self, jd):
        # Few or no recognised skills must not by itself mean invalid.
        result = validate_job_description(jd)
        assert result["valid"], result["reasons"]

    def test_full_jd_is_valid(self):
        assert validate_job_description(VALID_JD)["valid"]

    def test_jd_with_no_vocabulary_skills_is_still_valid(self):
        jd = (
            "We are hiring a warehouse supervisor to lead a team of ten, "
            "plan shifts and ensure safety standards are met."
        )
        assert extract_skills_from_text(jd) == []
        assert validate_job_description(jd)["valid"]

    def test_gibberish_mixed_with_a_couple_of_real_words_is_invalid(self):
        assert not validate_job_description("hiring qwpo zxcv mnbv lkjh poiu")["valid"]


class TestInvalidJdIsNotScored:
    @pytest.mark.parametrize("jd", GIBBERISH_JDS[:2])
    def test_all_scores_zero(self, jd):
        results = rank_texts(jd, [("cand.txt", STRONG_RESUME)])
        r = results[0]
        assert r["status"] == STATUS_INVALID_JD
        assert r["semantic_score"] == 0
        assert r["skill_score"] == 0
        assert r["experience_score"] == 0
        assert r["final_score"] == 0
        assert r["matched_skills"] == []
        assert "invalid job description" in r["explanation"].lower()

    def test_model_is_never_called(self, monkeypatch):
        def boom():
            raise AssertionError("model must not run for an invalid JD")

        monkeypatch.setattr(ranker, "get_model", boom)
        rank_texts(GIBBERISH_JDS[0], [("a.txt", STRONG_RESUME), ("b.txt", "x")])

    def test_every_candidate_is_zeroed(self):
        results = rank_texts(
            GIBBERISH_JDS[1], [("a.txt", STRONG_RESUME), ("b.txt", "cobol")]
        )
        assert {r["final_score"] for r in results} == {0}


class TestValidJdIsScored:
    def test_goes_through_normal_pipeline(self):
        r = rank_texts(VALID_JD, [("cand.txt", STRONG_RESUME)])[0]
        assert r["status"] == STATUS_SCORED
        assert r["skill_score"] > 0
        assert r["final_score"] > 0

    def test_valid_jd_skills_are_parsed(self):
        ev = skill_evidence(STRONG_RESUME, VALID_JD)
        for skill in ("python", "fastapi", "rest api", "postgresql", "nlp"):
            assert skill in ev["required"]
        for skill in ("faiss", "docker", "aws"):
            assert skill in ev["preferred"]

    def test_jd_experience_range_is_a_minimum(self):
        r = rank_texts(VALID_JD, [("cand.txt", "Python engineer, 2 years")])[0]
        assert r["evidence"]["experience"]["required_years"] == 1
        assert r["experience_score"] == 100.0

    def test_short_jd_still_scored(self):
        r = rank_texts("Python developer", [("a.txt", "python")])[0]
        assert r["status"] == STATUS_SCORED


RESUMES = [
    ("strong.txt", STRONG_RESUME),
    ("no_skills.txt", "Warehouse supervisor. Led a team. Forklift certified."),
    ("no_dates.txt", "Python and machine learning enthusiast."),
    ("partial.txt", "Java developer 2018 - 2020, some Docker."),
]


class TestScoringConsistency:
    @pytest.mark.parametrize(
        "jd", [VALID_JD, "Python developer", "We are hiring a friendly team lead."]
    )
    def test_invariants(self, jd):
        for r in rank_texts(jd, RESUMES):
            # 5. Final is exactly the weighted sum of the displayed parts.
            assert r["final_score"] == compute_final_score(
                r["semantic_score"], r["skill_score"], r["experience_score"]
            )
            # 1/4. No matched skills -> no skill credit.
            if not r["matched_skills"]:
                assert r["skill_score"] == 0
            # 3. A perfect skill score is backed by matched skills.
            if r["skill_score"] == 100:
                assert r["matched_skills"]
            # 2. Undeterminable experience never earns credit.
            if r["evidence"]["experience"]["resume_years"] is None:
                assert r["experience_score"] == 0
            # 6. The evidence and the displayed lists agree.
            ev = r["evidence"]["skill"]
            assert sorted(ev["matched_required"] + ev["matched_preferred"]) == r[
                "matched_skills"
            ]
            assert r["evidence"]["final"]["formula"].endswith(str(r["final_score"]))

    def test_jd_without_vocabulary_skills_scores_skill_zero(self):
        r = rank_texts("We are hiring a friendly team lead.", RESUMES[:1])[0]
        assert r["skill_score"] == 0
        assert r["matched_skills"] == []
        assert "could not be assessed" in r["evidence"]["skill"]["note"]


class TestSkillExtraction:
    def test_plural_matches(self):
        assert "rest api" in extract_skills_from_text("Built REST APIs")

    def test_cpp_matches(self):
        assert "c++" in extract_skills_from_text("Strong C++ skills")

    def test_java_still_not_inside_javascript(self):
        assert "java" not in extract_skills_from_text("javascript")


# ------------------------------------------------------------ PDF parsing --

class Upload:
    def __init__(self, name, data):
        self.name = name
        self._buf = io.BytesIO(data)

    def read(self):
        return self._buf.read()

    def seek(self, pos):
        return self._buf.seek(pos)


def _pdf(text=None):
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    else:
        # Image-only page: a drawn shape, no text layer -- like a scan.
        page.draw_rect(fitz.Rect(50, 50, 200, 200), fill=(0, 0, 0))
    data = doc.tobytes()
    doc.close()
    return data


class TestPdfFailures:
    def test_text_pdf_is_scored(self):
        results, failures = rank_resumes(
            "Python developer", [Upload("ok.pdf", _pdf("Python developer 3 years"))]
        )
        assert failures == []
        assert results[0]["filename"] == "ok.pdf"

    def test_image_only_pdf_is_reported_not_scored(self):
        results, failures = rank_resumes(
            "Python developer",
            [Upload("scan.pdf", _pdf()), Upload("ok.txt", b"python")],
        )
        assert [r["filename"] for r in results] == ["ok.txt"]
        assert failures[0]["filename"] == "scan.pdf"
        assert "scanned" in failures[0]["reason"]

    def test_corrupted_pdf_is_reported_not_scored(self):
        results, failures = rank_resumes(
            "Python developer", [Upload("broken.pdf", b"%PDF-1.4 garbage")]
        )
        assert results == []
        assert failures[0]["filename"] == "broken.pdf"
        assert "could not be opened" in failures[0]["reason"]
