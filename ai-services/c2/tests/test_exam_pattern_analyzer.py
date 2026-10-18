
import json

from services.exam_pattern_analyzer import ExamPatternAnalyzer


def make_analyzer(tmp_path, questions, classifications):
    questions_path = tmp_path / "questions.json"
    classifications_path = tmp_path / "classifications.json"
    modules_path = tmp_path / "modules.json"

    questions_path.write_text(
        json.dumps(questions), encoding="utf-8"
    )

    classifications_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "results": classifications,
        }),
        encoding="utf-8",
    )

    modules_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "modules": [
                {
                    "module_key": "database_systems",
                    "module_code": "IT3020",
                    "module_name": "Database Systems",
                }
            ],
        }),
        encoding="utf-8",
    )

    return ExamPatternAnalyzer(
        questions_path=questions_path,
        classifications_path=classifications_path,
        modules_path=modules_path,
    )


def question(
    question_id,
    source_type="authentic",
    marks=5,
    year=2023,
    paper_id="paper-2023",
):
    return {
        "question_id": question_id,
        "paper_id": paper_id,
        "module_code": "IT3020",
        "calendar_year": year,
        "source_type": source_type,
        "marks": marks,
        "marks_status": "extracted",
    }


def classification(question_id, topic_id, status="verified"):
    return {
        "question_id": question_id,
        "valid": True,
        "classification": {
            "question_id": question_id,
            "module_key": "database_systems",
            "topic_id": topic_id,
            "verification_status": status,
        },
    }


def test_excludes_synthetic_questions(tmp_path):
    analyzer = make_analyzer(
        tmp_path,
        [
            question("Q1"),
            question("Q2", source_type="synthetic"),
        ],
        [],
    )

    result = analyzer.analyze("database_systems")

    assert result["total_questions"] == 1
    assert result["excluded"]["synthetic_questions"] == 1
    assert result["distinct_papers"] == 1


def test_counts_verified_topics_only(tmp_path):
    analyzer = make_analyzer(
        tmp_path,
        [question("Q1"), question("Q2")],
        [
            classification("Q1", "sql"),
            classification("Q2", "normalization", "unverified"),
        ],
    )

    result = analyzer.analyze("database_systems")

    assert result["topics"]["verified_classified_questions"] == 1
    assert result["topics"]["without_verified_topic"] == 1
    assert result["topics"]["statistics"][0]["topic_id"] == "sql"


def test_marks_distribution(tmp_path):
    analyzer = make_analyzer(
        tmp_path,
        [
            question("Q1", marks=3),
            question("Q2", marks=5),
            question("Q3", marks=None),
        ],
        [],
    )

    result = analyzer.analyze("database_systems")

    assert result["marks"]["questions_with_extracted_marks"] == 2
    assert result["marks"]["sum_of_extracted_question_marks"] == 8
    assert result["marks"]["distribution"] == {"3": 1, "5": 1}


def test_no_data_is_not_prediction_ready(tmp_path):
    analyzer = make_analyzer(tmp_path, [], [])

    result = analyzer.analyze("database_systems")

    assert result["total_questions"] == 0
    assert result["prediction_ready"] is False
    assert result["limitations"]


def test_duplicate_question_ids_not_double_counted(tmp_path):
    analyzer = make_analyzer(
        tmp_path,
        [question("Q1"), question("Q1")],
        [],
    )

    result = analyzer.analyze("database_systems")

    assert result["total_questions"] == 1


def test_single_year_is_not_prediction_ready(tmp_path):
    analyzer = make_analyzer(
        tmp_path,
        [question("Q1")],
        [classification("Q1", "sql")],
    )

    result = analyzer.analyze("database_systems")

    assert result["distinct_years"] == ["2023"]
    assert result["prediction_ready"] is False
