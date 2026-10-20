
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.module_lecture_processor import ModuleLectureProcessor
from services.syllabus_topic_candidate_extractor import (
    SyllabusTopicCandidateExtractor,
)
from services.syllabus_topic_candidate_filter import (
    SyllabusTopicCandidateFilter,
)
from services.syllabus_topic_candidate_ranker import (
    SyllabusTopicCandidateRanker,
)
from services.syllabus_topic_review_report import (
    SyllabusTopicReviewReport,
)


def run_tests():
    print("\n--- M7.3.5.2.4.3 REVIEW REPORT INTEGRATION ---")

    processed = ModuleLectureProcessor().process()
    print("PASS: lecture processing")

    extracted = SyllabusTopicCandidateExtractor().extract_all(processed)
    print("PASS: candidate extraction")

    filtered = SyllabusTopicCandidateFilter().filter_all(extracted)
    print("PASS: candidate filtering")

    ranked = SyllabusTopicCandidateRanker().rank_all(filtered)
    print("PASS: candidate ranking")

    generator = SyllabusTopicReviewReport()
    report = generator.build_all_reports(ranked)

    assert report["summary"]["module_count"] == 8

    assert (
        report["summary"]["total_review_candidates"]
        == ranked["summary"]["ranked_candidate_count"]
    )

    assert (
        report["summary"]["total_excluded_candidates"]
        == ranked["summary"]["excluded_candidate_count"]
    )

    print("PASS: report candidate counts")

    for module_key, module_report in report["modules"].items():
        ranked_candidates = ranked["modules"][module_key]["candidates"]
        review_candidates = module_report["review_candidates"]

        assert len(review_candidates) == len(ranked_candidates)

        for ranked_candidate, review_candidate in zip(
            ranked_candidates,
            review_candidates,
        ):
            assert (
                review_candidate["candidate_name"]
                == ranked_candidate["candidate_name"]
            )

            assert (
                review_candidate["sources"]
                == ranked_candidate["sources"]
            )

            assert review_candidate["review_decision"] == "pending"
            assert review_candidate["verification_status"] == "unverified"

    print("PASS: review fields and source evidence")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "review_report.json"

        generator.export_json(report, output_path)

        with output_path.open("r", encoding="utf-8") as file:
            exported = json.load(file)

        assert exported == report

    print("PASS: JSON export integrity")

    print("\n--- REVIEW REPORT SUMMARY ---")
    print("Modules:", report["summary"]["module_count"])
    print(
        "Review candidates:",
        report["summary"]["total_review_candidates"],
    )
    print(
        "Excluded candidates:",
        report["summary"]["total_excluded_candidates"],
    )

    print(
        "\nAll M7.3.5.2.4.3 real-data review report "
        "integration tests passed."
    )


if __name__ == "__main__":
    run_tests()
