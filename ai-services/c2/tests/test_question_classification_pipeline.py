
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.question_classification_pipeline import (
    QuestionClassificationPipeline,
)


def run_tests():
    print("\n--- M6.4.2 QUESTION REPOSITORY INTEGRATION TEST ---")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        modules_path = root / "modules.json"
        questions_path = root / "questions.json"
        output_path = root / "topic_classifications.json"

        
        modules = {
            "modules": [
                {
                    "module_key": "database_systems",
                    "module_code": "IT3020",
                },
                {
                    "module_key": "case_studies_in_software_engineering",
                    "module_code": None,
                },
            ]
        }           


        questions = [
            {
                "question_id": "TEST-Q1(a)",
                "module_code": "IT3020",
                "question_text": "Write an SQL query to retrieve records.",
                "marks": 5,
                "source_type": "authentic",
            },
            {
                "question_id": "TEST-Q1(b)",
                "module_code": "UNKNOWN",
                "question_text": "Explain database normalization.",
                "marks": 5,
                "source_type": "authentic",
            },
        ]

        modules_path.write_text(
            json.dumps(modules), encoding="utf-8"
        )

        questions_path.write_text(
            json.dumps(questions), encoding="utf-8"
        )

        pipeline = QuestionClassificationPipeline(
            modules_path=modules_path
        )
        
        mapping = pipeline.load_module_mapping()

        assert mapping == {
            "IT3020": "database_systems"
        }

        print("PASS: null module codes safely skipped")


        loaded = pipeline.load_questions(questions_path)
        assert len(loaded) == 2
        print("PASS: question repository loading")

        prepared = pipeline.prepare_questions(loaded)

        assert prepared[0]["module_key"] == "database_systems"
        print("PASS: module code mapping")

        assert prepared[1]["module_key"] is None
        print("PASS: unknown module handling")

        result = pipeline.run(
            questions_path=questions_path,
            output_path=output_path,
        )

        assert result["summary"]["total_questions"] == 2
        print("PASS: batch classification integration")

        assert len(result["results"]) == 2
        print("PASS: classification result preservation")

        assert output_path.exists()
        print("PASS: classification output saved")

        original = json.loads(
            questions_path.read_text(encoding="utf-8")
        )

        assert original == questions
        print("PASS: original question repository unchanged")

        assert result["summary"]["invalid"] >= 1
        print("PASS: invalid module classification detected")

    print("\nAll M6.4.2 integration tests passed.")


if __name__ == "__main__":
    run_tests()
