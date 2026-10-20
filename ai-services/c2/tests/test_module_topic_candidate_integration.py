
import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.module_lecture_processor import ModuleLectureProcessor
from services.syllabus_topic_candidate_extractor import (
    SyllabusTopicCandidateExtractor,
)


EXPECTED_MODULES = {
    "application_frameworks",
    "case_studies_software_engineering",
    "database_systems",
    "distributed_systems",
    "software_architecture",
    "software_engineering_process_quality_management",
    "software_project_management",
    "user_experience_engineering",
}


def run_tests():
    print("\n--- M7.3.4.2 MULTI-MODULE TOPIC CANDIDATE INTEGRATION TEST ---")

    processor = ModuleLectureProcessor()
    extractor = SyllabusTopicCandidateExtractor()

    processed = processor.process()

    assert processed["schema_version"] == "1.0"
    assert set(processed["modules"]) == EXPECTED_MODULES
    assert processed["summary"]["total_modules"] == 8
    print("PASS: all eight modules recognized")

    assert processed["summary"]["total_files"] == 90
    assert processed["summary"]["successful"] == 90
    assert processed["summary"]["failed"] == 0
    assert processed["summary"]["empty_text"] == 0
    print("PASS: all 90 lecture documents processed")

    original_processed = deepcopy(processed)

    result = extractor.extract_all(processed)

    assert result["schema_version"] == "1.0"
    assert result["summary"]["total_modules"] == 8
    assert set(result["modules"]) == EXPECTED_MODULES
    print("PASS: topic extraction completed for all modules")

    total_candidates = 0

    for module_key, module_result in result["modules"].items():
        assert module_result["module_key"] == module_key

        candidates = module_result["candidates"]

        assert module_result["candidate_count"] == len(candidates)
        assert isinstance(candidates, list)

        total_candidates += len(candidates)

        normalized_names = set()

        source_filenames = {
            document["filename"]
            for document in processed["modules"][module_key]["documents"]
        }

        for candidate in candidates:
            assert candidate["module_key"] == module_key
            assert candidate["verification_status"] == "unverified"
            assert candidate["extraction_method"] == "rule_based"

            name = candidate["candidate_name"]
            assert isinstance(name, str) and name.strip()

            normalized = extractor.normalize(name)
            assert normalized not in normalized_names
            normalized_names.add(normalized)

            assert candidate["sources"]

            for source in candidate["sources"]:
                assert source["filename"] in source_filenames
                assert isinstance(source["line_number"], int)
                assert source["line_number"] > 0

        print(
            f"PASS: {module_key} "
            f"({len(candidates)} candidates)"
        )

    assert result["summary"]["total_candidates"] == total_candidates
    print("PASS: total candidate count consistency")

    assert processed == original_processed
    print("PASS: original lecture processing data unchanged")

    print("\n--- CANDIDATE EXTRACTION SUMMARY ---")
    print("Modules:", result["summary"]["total_modules"])
    print("Lecture files:", processed["summary"]["total_files"])
    print("Total candidates:", total_candidates)

    for module_key, module_result in result["modules"].items():
        print(
            f"  {module_key}: "
            f"{module_result['candidate_count']} candidates"
        )

    print("\nAll M7.3.4.2 integration tests passed.")


if __name__ == "__main__":
    run_tests()
