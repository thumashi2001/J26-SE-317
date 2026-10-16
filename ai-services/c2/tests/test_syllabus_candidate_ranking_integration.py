
import sys
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


def run_tests():
    print("\n--- M7.3.5.2.3b REAL-DATA RANKING INTEGRATION TEST ---")

    # STEP 1: Process all lecture documents.
    processed = ModuleLectureProcessor().process()
    print("PASS: lecture documents processed")

    # STEP 2: Extract candidates across eight modules.
    extracted = SyllabusTopicCandidateExtractor().extract_all(processed)

    assert len(extracted["modules"]) == 8
    print("PASS: candidates extracted from eight modules")

    # STEP 3: Filter obvious technical and presentation noise.
    filtered = SyllabusTopicCandidateFilter().filter_all(extracted)

    assert len(filtered["modules"]) == 8
    print("PASS: candidate quality filtering completed")

    # STEP 4: Rank candidates and separate administrative noise.
    ranked = SyllabusTopicCandidateRanker().rank_all(filtered)

    assert len(ranked["modules"]) == 8
    print("PASS: candidates ranked across eight modules")

    # STEP 5: Validate ranking counts.
    filtered_candidate_count = sum(
        len(module_data["candidates"])
        for module_data in filtered["modules"].values()
    )

    summary = ranked["summary"]

    assert summary["module_count"] == 8

    assert (
        summary["input_candidate_count"]
        == filtered_candidate_count
    )

    assert (
        summary["input_candidate_count"]
        == summary["ranked_candidate_count"]
        + summary["excluded_candidate_count"]
        + summary["merged_duplicate_count"]
    )

    assert summary["merged_duplicate_count"] >= 0
    assert summary["excluded_candidate_count"] >= 0

    print("PASS: ranking counts consistent")

    # STEP 6: Validate every module and ranked candidate.
    for module_key, module_data in ranked["modules"].items():
        candidates = module_data["candidates"]
        excluded_candidates = module_data["excluded_candidates"]
        module_summary = module_data["summary"]

        assert module_data["module_key"] == module_key

        assert (
            module_summary["input_candidate_count"]
            == len(filtered["modules"][module_key]["candidates"])
        )

        assert (
            module_summary["ranked_candidate_count"]
            == len(candidates)
        )

        assert (
            module_summary["excluded_candidate_count"]
            == len(excluded_candidates)
        )

        assert (
            module_summary["input_candidate_count"]
            == module_summary["ranked_candidate_count"]
            + module_summary["excluded_candidate_count"]
            + module_summary["merged_duplicate_count"]
        )

        scores = [
            candidate["ranking_score"]
            for candidate in candidates
        ]

        assert scores == sorted(scores, reverse=True)

        for position, candidate in enumerate(candidates, start=1):
            assert candidate["module_key"] == module_key
            assert candidate["verification_status"] == "unverified"
            assert candidate["rank"] == position

            assert 0 <= candidate["ranking_score"] <= 100

            assert (
                candidate["occurrence_count"]
                == len(candidate["sources"])
            )

            assert (
                candidate["document_count"]
                <= candidate["occurrence_count"]
            )

            distinct_documents = {
                source["filename"]
                for source in candidate["sources"]
            }

            assert (
                candidate["document_count"]
                == len(distinct_documents)
            )

            breakdown = candidate["ranking_breakdown"]

            assert (
                candidate["ranking_score"]
                == sum(breakdown.values())
            )

            assert 0 <= breakdown["heading_quality"] <= 40
            assert 0 <= breakdown["occurrence_frequency"] <= 30
            assert 0 <= breakdown["document_coverage"] <= 30

            # Administrative candidates must not enter the ranking.
            assert not SyllabusTopicCandidateRanker().is_administrative_candidate(
                candidate["candidate_name"]
            )

        print(
            f"PASS: {module_key} ranking scores, "
            "ordering and source evidence"
        )

        # STEP 7: Validate excluded administrative candidates.
        for candidate in excluded_candidates:
            assert candidate["module_key"] == module_key
            assert candidate["verification_status"] == "unverified"

            assert (
                SyllabusTopicCandidateRanker().is_administrative_candidate(
                    candidate["candidate_name"]
                )
            )

            assert isinstance(candidate["sources"], list)

    print("PASS: ranking scores and ordering validated")
    print("PASS: administrative candidate exclusion validated")
    print("PASS: verification safeguards preserved")

    # STEP 8: Display overall ranking summary.
    print("\n--- RANKING SUMMARY ---")

    print("Modules:", summary["module_count"])
    print("Input candidates:", summary["input_candidate_count"])
    print("Ranked candidates:", summary["ranked_candidate_count"])
    print("Excluded candidates:", summary["excluded_candidate_count"])
    print("Merged duplicates:", summary["merged_duplicate_count"])

    # STEP 9: Show top-ranked candidates from each module.
    for module_key, module_data in ranked["modules"].items():
        print(f"\n--- {module_key.upper()} ---")

        module_summary = module_data["summary"]

        print("Input:", module_summary["input_candidate_count"])
        print("Ranked:", module_summary["ranked_candidate_count"])
        print("Excluded:", module_summary["excluded_candidate_count"])
        print("Merged:", module_summary["merged_duplicate_count"])

        print("\nTOP 10 RANKED CANDIDATES:")

        for candidate in module_data["candidates"][:10]:
            print(
                f"#{candidate['rank']} "
                f"[{candidate['ranking_score']}/100] "
                f"{candidate['candidate_name']} "
                f"(occurrences={candidate['occurrence_count']}, "
                f"documents={candidate['document_count']})"
            )

        print("\nSAMPLE EXCLUDED CANDIDATES:")

        for candidate in module_data["excluded_candidates"][:5]:
            print(f"- {candidate['candidate_name']}")

    print(
        "\nAll M7.3.5.2.3b real-data ranking "
        "integration tests passed."
    )


if __name__ == "__main__":
    run_tests()
