
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.module_lecture_processor import ModuleLectureProcessor
from services.syllabus_topic_candidate_extractor import (
    SyllabusTopicCandidateExtractor,
)
from services.syllabus_topic_candidate_filter import (
    SyllabusTopicCandidateFilter,
)


def run_tests():
    print("\n--- M7.3.5.1 REAL-DATA FILTERING INTEGRATION TEST ---")

    processed = ModuleLectureProcessor().process()

    assert processed["summary"]["total_modules"] == 8
    assert processed["summary"]["failed"] == 0
    print("PASS: lecture documents processed")

    extracted = SyllabusTopicCandidateExtractor().extract_all(processed)

    assert extracted["summary"]["total_modules"] == 8
    print("PASS: candidates extracted from eight modules")

    filtered = SyllabusTopicCandidateFilter().filter_all(extracted)

    summary = filtered["summary"]

    assert summary["total_modules"] == 8
    assert summary["total_candidates"] == (
        summary["kept"] + summary["rejected"]
    )
    assert summary["total_candidates"] == extracted["summary"]["total_candidates"]

    print("PASS: candidate filtering counts consistent")

    for module_key, module_result in filtered["modules"].items():
        counts = module_result["summary"]

        assert counts["total_candidates"] == (
            counts["kept"] + counts["rejected"]
        )

        assert all(
            candidate["verification_status"] == "unverified"
            for candidate in module_result["candidates"]
        )

        assert all(
            item["candidate"]["verification_status"] == "unverified"
            for item in module_result["rejected_candidates"]
        )

    print("PASS: verification safeguards preserved")

    print("\n--- FILTERING SUMMARY ---")
    print("Total candidates:", summary["total_candidates"])
    print("Kept:", summary["kept"])
    print("Rejected:", summary["rejected"])

    percentage = (
        summary["rejected"] / summary["total_candidates"] * 100
        if summary["total_candidates"] else 0
    )

    print(f"Rejection percentage: {percentage:.2f}%")

    print("\n--- MODULE RESULTS ---")

    rejection_reasons = Counter()

    for module_key, module_result in filtered["modules"].items():
        counts = module_result["summary"]

        print(
            f"{module_key}: "
            f"kept={counts['kept']}, "
            f"rejected={counts['rejected']}"
        )

        for item in module_result["rejected_candidates"]:
            rejection_reasons[item["rejection_reason"]] += 1

    print("\n--- REJECTION REASONS ---")

    for reason, count in rejection_reasons.most_common():
        print(f"{reason}: {count}")

    print("\n--- SAMPLE REJECTED CANDIDATES ---")

    shown = 0

    for module_result in filtered["modules"].values():
        for item in module_result["rejected_candidates"]:
            print(
                f"- {item['candidate']['candidate_name']} "
                f"[{item['rejection_reason']}]"
            )
            shown += 1

            if shown >= 15:
                break

        if shown >= 15:
            break

    print("\nAll M7.3.5.1 real-data integration tests passed.")


if __name__ == "__main__":
    run_tests()
