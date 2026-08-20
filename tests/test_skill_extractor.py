from app.skill_extractor import extract_required_preferred, extract_skills_from_text


class TestSkillExtraction:
    def test_finds_listed_skills(self):
        found = extract_skills_from_text("Strong Python and Docker experience")
        assert "python" in found
        assert "docker" in found

    def test_is_case_insensitive(self):
        assert "python" in extract_skills_from_text("PYTHON")

    def test_multiword_skills(self):
        found = extract_skills_from_text("background in machine learning")
        assert "machine learning" in found

    def test_word_boundaries_prevent_substring_hits(self):
        # "java" must not match inside "javascript"
        found = extract_skills_from_text("experienced in javascript")
        assert "javascript" in found
        assert "java" not in found

    def test_unknown_skill_ignored(self):
        assert extract_skills_from_text("expert in cobol") == []


class TestRequiredPreferredSplit:
    def test_without_preferred_section_all_required(self):
        result = extract_required_preferred("Must know Python and Docker")
        assert "python" in result["required"]
        assert result["preferred"] == []

    def test_splits_on_preferred_keyword(self):
        jd = "Required: Python and Docker. Preferred: AWS and Kubernetes."
        result = extract_required_preferred(jd)
        assert "python" in result["required"]
        assert "aws" in result["preferred"]
        assert "aws" not in result["required"]
