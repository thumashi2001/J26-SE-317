
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.synthetic_rules import SyntheticRules


def test_rules_configuration():
    rules = SyntheticRules()

    assert rules.validate_configuration() is True

    print("PASS: synthetic rules configuration")


def test_module_readiness():
    rules = SyntheticRules()

    result = rules.check_module_readiness(
        "database_systems"
    )

    assert result["ready"] is False
    assert "verified_topics" in result["missing_requirements"]
    assert "verified_exam_structure" in result["missing_requirements"]

    print("PASS: incomplete module readiness detection")


def test_unknown_module():
    rules = SyntheticRules()

    try:
        rules.check_module_readiness("unknown_module")
    except ValueError:
        print("PASS: unknown module rejection")
    else:
        raise AssertionError(
            "Unknown module was accepted"
        )


def test_invalid_generated_question():
    rules = SyntheticRules()

    question = {
        "question_id": "SYN-001",
        "module_key": "database_systems",
        "module_code": "IT3020",
        "question_text": "Explain database normalization.",
        "marks": 5,
        "topic": "Normalization",
        "source_type": "authentic",
        "generation_provenance": None,
    }

    result = rules.validate_generated_question(question)

    assert result["valid"] is False
    assert "Question must have synthetic provenance" in result["errors"]
    assert "Missing generation provenance" in result["errors"]
    assert "Topic is not in verified module topics" in result["errors"]

    print("PASS: invalid synthetic question rejection")


if __name__ == "__main__":
    test_rules_configuration()
    test_module_readiness()
    test_unknown_module()
    test_invalid_generated_question()

    print("\nAll synthetic rules tests passed.")
