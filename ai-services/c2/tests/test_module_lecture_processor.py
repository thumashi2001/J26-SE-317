
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.module_lecture_processor import ModuleLectureProcessor


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
    print("--- M7.3.3 MODULE LECTURE PROCESSING TEST ---")

    processor = ModuleLectureProcessor()
    result = processor.process()

    assert result["schema_version"] == "1.0"
    print("PASS: schema version")

    summary = result["summary"]
    modules = result["modules"]

    assert set(modules) == EXPECTED_MODULES
    assert summary["total_modules"] == 8
    print("PASS: eight module directories recognized")

    assert summary["total_files"] == 90
    print("PASS: all 90 lecture files discovered")

    assert summary["successful"] == 90
    assert summary["failed"] == 0
    print("PASS: lecture file processing")

    assert summary["empty_text"] == 0
    print("PASS: all lecture files contain extractable text")

    for module_key, module in modules.items():
        assert module["module_key"] == module_key
        assert module["document_count"] > 0
        assert not module["errors"]

        for document in module["documents"]:
            assert document["filename"]
            assert document["relative_path"]
            assert document["file_type"] in {"pdf", "pptx"}
            assert document["unit_count"] > 0
            assert document["character_count"] > 0
            assert document["text"].strip()

        print(
            f"PASS: {module_key} "
            f"({module['document_count']} documents)"
        )

    print("\n--- MODULE PROCESSING SUMMARY ---")
    for module_key, module in modules.items():
        print(f"{module_key}: {module['document_count']} files")

    print(f"\nTotal modules: {summary['total_modules']}")
    print(f"Total files: {summary['total_files']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Empty text: {summary['empty_text']}")

    print("\nAll M7.3.3 module processing tests passed.")


if __name__ == "__main__":
    run_tests()
