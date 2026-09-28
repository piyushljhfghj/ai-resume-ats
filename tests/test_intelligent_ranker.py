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

    def seek(self, pos):
        return self._buf.seek(pos)


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

    def test_unrecognised_jd_gives_no_unearned_credit(self):
        # Regression: this used to return a "neutral" 100 with no matched
        # skills -- a perfect skill score backed by no evidence.
        score, matched, missing = compute_skill_score("python", "we want a nice person")
        assert score == 0.0
        assert matched == [] and missing == []


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
        results, failures = rank_resumes(JD, files)
        assert len(results) == 1
        assert results[0]["filename"] == "r1.txt"
        assert failures == []

    def test_non_utf8_bytes_do_not_crash(self):
        # cp1252 smart quote -- a hard utf-8 decode would raise here.
        files = [UploadedFile("r1.txt", b"python \x93developer\x94")]
        results, _ = rank_resumes(JD, files)
        assert len(results) == 1

    def test_unreadable_file_is_reported_not_fatal(self):
        class Exploding:
            name = "bad.txt"

            def read(self):
                raise IOError("disk gone")

        results, failures = rank_resumes(
            JD, [Exploding(), UploadedFile("ok.txt", b"python")]
        )
        assert [r["filename"] for r in results] == ["ok.txt"]
        assert [f["filename"] for f in failures] == ["bad.txt"]

    def test_empty_file_is_reported_not_scored(self):
        results, failures = rank_resumes(JD, [UploadedFile("empty.txt", b"   ")])
        assert results == []
        assert failures[0]["filename"] == "empty.txt"

    def test_same_upload_can_be_screened_twice(self):
        # Streamlit hands back the same file object on a later run; its read
        # pointer is at EOF, which used to make it look empty.
        f = UploadedFile("r1.txt", b"python and docker")
        rank_resumes(JD, [f])
        results, failures = rank_resumes(JD, [f])
        assert len(results) == 1 and failures == []
