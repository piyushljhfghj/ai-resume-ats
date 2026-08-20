import io

import pytest

from app.intelligent_ranker import (
    compute_final_score,
    compute_skill_score,
    rank_resumes,
    rank_texts,
)


class UploadedFile:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name, data):
        self.name = name
        self._buf = io.BytesIO(data)

    def read(self):
        return self._buf.read()


JD = "Required: Python and machine learning. Must have Docker."


class TestSkillScore:
    def test_full_match(self):
        score, matched, missing = compute_skill_score(
            "python, machine learning, docker", JD
        )
        assert score == 100.0
        assert missing == []

    def test_partial_match(self):
        score, matched, missing = compute_skill_score("python only", JD)
        assert 0 < score < 100
        assert "python" in matched
        assert "docker" in missing

    def test_no_match(self):
        score, matched, missing = compute_skill_score("cobol", JD)
        assert score == 0.0
        assert matched == []

    def test_skill_never_both_matched_and_missing(self):
        jd = "Required: Python. Preferred: Python and AWS."
        _, matched, missing = compute_skill_score("python developer", jd)
        assert not (set(matched) & set(missing))

    def test_unrecognised_jd_is_neutral_not_zero(self):
        # A JD naming no known skill cannot discriminate; scoring everyone 0
        # would silently cap all final scores at 60.
        score, matched, missing = compute_skill_score("python", "we want a nice person")
        assert score == 100.0


class TestFinalScore:
    def test_weighting(self):
        assert compute_final_score(100, 100, 100) == 100.0
        assert compute_final_score(0, 0, 0) == 0.0

    def test_is_weighted_average(self):
        # 0.4*100 + 0.4*50 + 0.2*0
        assert compute_final_score(100, 50, 0) == 60.0


class TestRankTexts:
    def test_empty_input(self):
        assert rank_texts(JD, []) == []

    def test_sorted_best_first(self):
        results = rank_texts(JD, [
            ("weak.txt", "cobol developer"),
            ("strong.txt", "python, machine learning, docker"),
        ])
        assert [r["filename"] for r in results] == ["strong.txt", "weak.txt"]
        assert results[0]["final_score"] >= results[1]["final_score"]

    def test_result_shape(self):
        result = rank_texts(JD, [("a.txt", "python")])[0]
        for key in (
            "filename", "semantic_score", "skill_score", "experience_score",
            "final_score", "matched_skills", "missing_skills", "explanation",
        ):
            assert key in result

    def test_accepts_a_generator(self):
        # The API passes zip(...), not a list.
        results = rank_texts(JD, zip(["a.txt"], ["python"]))
        assert len(results) == 1


class TestRankResumes:
    def test_reads_txt_uploads(self):
        files = [UploadedFile("r1.txt", b"python and docker")]
        results = rank_resumes(JD, files)
        assert len(results) == 1
        assert results[0]["filename"] == "r1.txt"

    def test_non_utf8_bytes_do_not_crash(self):
        # cp1252 smart quote -- a hard utf-8 decode would raise here.
        files = [UploadedFile("r1.txt", b"python \x93developer\x94")]
        results = rank_resumes(JD, files)
        assert len(results) == 1

    def test_unreadable_file_is_skipped_not_fatal(self):
        class Exploding:
            name = "bad.txt"

            def read(self):
                raise IOError("disk gone")

        results = rank_resumes(JD, [Exploding(), UploadedFile("ok.txt", b"python")])
        assert [r["filename"] for r in results] == ["ok.txt"]

    def test_empty_file_is_skipped(self):
        results = rank_resumes(JD, [UploadedFile("empty.txt", b"   ")])
        assert results == []
