
import json
from pathlib import Path

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


def main():
    print("\n--- M7.3.5.2.4.4 REVIEW REPORT EXPORT ---")

    print("STEP 1: Processing lecture documents...")
    processed = ModuleLectureProcessor().process()

    print("STEP 2: Extracting candidates...")
    extracted = SyllabusTopicCandidateExtractor().extract_all(processed)

    print("STEP 3: Filtering candidates...")
    filtered = SyllabusTopicCandidateFilter().filter_all(extracted)

    print("STEP 4: Ranking candidates...")
    ranked = SyllabusTopicCandidateRanker().rank_all(filtered)

    print("STEP 5: Building review report...")
    generator = SyllabusTopicReviewReport()
    report = generator.build_all_reports(ranked)

    output_dir = Path(__file__).resolve().parent / "outputs" / "syllabus_reviews"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("STEP 6: Exporting reports...")

    # Export complete report.
    combined_path = output_dir / "all_modules_review_report.json"
    generator.export_json(report, combined_path)

    # Export separate reports for each module.
    for module_key, module_report in report["modules"].items():
        module_path = output_dir / f"{module_key}_review_report.json"
        generator.export_json(module_report, module_path)

        print(
            f"EXPORTED: {module_key} "
            f"({len(module_report['review_candidates'])} candidates)"
        )

    print("\n--- EXPORT SUMMARY ---")
    print("Modules:", report["summary"]["module_count"])
    print(
        "Review candidates:",
        report["summary"]["total_review_candidates"],
    )
    print(
        "Excluded candidates:",
        report["summary"]["total_excluded_candidates"],
    )
    print("Output directory:", output_dir)

    print("\nAll review reports exported successfully.")


if __name__ == "__main__":
    main()
