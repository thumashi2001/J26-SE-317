
"""M11.2.6.4 - Final synthetic pipeline integration tests.

Uses development fixtures only. No authentic data or lecturer
review records are modified.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)
from services.synthetic_pipeline_runner import (
    SyntheticPipelineRunner,
)
from tests.test_synthetic_generation_adapter import (
    adapter,
)
from tests.test_synthetic_pipeline_runner import (
    configs,
)


def make_runner(tmp_path):
    return SyntheticPipelineRunner(
        export_root=tmp_path,
        adapter=adapter(),
    )


def generate_report(tmp_path, count=1, export=False):
    return make_runner(tmp_path).run(
        targets={"database_systems": count},
        module_configs=configs(),
        base_seed=42,
        export=export,
    )


def exported_paper(tmp_path):
    report = generate_report(tmp_path, export=True)

    assert report["generated_papers"] == 1
    assert report["exported_papers"] == 1

    file_path = Path(
        report["modules"][0]["papers"][0]["file_path"]
    )

    assert file_path.exists()

    with file_path.open("r", encoding="utf-8") as file:
        paper = json.load(file)

    return report, paper, file_path


def test_complete_pipeline_exports_valid_paper(tmp_path):
    report, paper, file_path = exported_paper(tmp_path)

    validation = SyntheticDatasetExporter().validate(paper)

    assert validation["valid"] is True
    assert report["failed_attempts"] == 0
    assert paper["total_marks"] == 100
    assert paper["main_question_count"] == 4
    assert file_path.suffix == ".json"


def test_exported_paper_has_exact_question_structure(tmp_path):
    _, paper, _ = exported_paper(tmp_path)

    assert len(paper["questions"]) == 4

    total_marks = 0
    total_subquestions = 0

    for main in paper["questions"]:
        assert main["total_marks"] == 25
        assert len(main["subquestions"]) == 3

        marks = [
            sub["marks"]
            for sub in main["subquestions"]
        ]

        assert marks == [5, 10, 10]

        total_marks += sum(marks)
        total_subquestions += len(marks)

    assert total_marks == 100
    assert total_subquestions == 12


def test_all_questions_have_real_generator_provenance(tmp_path):
    _, paper, _ = exported_paper(tmp_path)

    for main in paper["questions"]:
        for sub in main["subquestions"]:
            question = sub["question"]
            provenance = question["generation_provenance"]

            assert (
                provenance["generator"]
                == "c2_template_generator_v1"
            )
            assert (
                provenance["scenario_enricher"]
                == "c2_scenario_enricher_v1"
            )
            assert provenance["mode"] == "development_fixture"
            assert question["scenario_id"]


def test_exported_paper_is_not_academically_approved(tmp_path):
    _, paper, _ = exported_paper(tmp_path)

    assert paper["source_type"] == "synthetic"
    assert paper["verification_status"] == "unverified"
    assert paper["human_review_status"] == "pending"
    assert paper["release_status"] == "not_approved"

    for main in paper["questions"]:
        for sub in main["subquestions"]:
            question = sub["question"]

            assert question["source_type"] == "synthetic"
            assert question["verification_status"] == "unverified"
            assert question["human_review_status"] == "pending"
            assert question["scenario_review_status"] == "pending"


def test_exported_questions_are_unique_within_paper(tmp_path):
    _, paper, _ = exported_paper(tmp_path)

    ids = []
    texts = []
    scenario_ids = []

    for main in paper["questions"]:
        for sub in main["subquestions"]:
            question = sub["question"]

            ids.append(question["question_id"])
            texts.append(question["question_text"])
            scenario_ids.append(question["scenario_id"])

    assert len(ids) == 12
    assert len(ids) == len(set(ids))
    assert len(texts) == len(set(texts))
    assert len(scenario_ids) == len(set(scenario_ids))


def test_duplicate_export_does_not_overwrite_file(tmp_path):
    first_report, _, file_path = exported_paper(tmp_path)

    original_bytes = file_path.read_bytes()

    second_report = generate_report(
        tmp_path,
        count=1,
        export=True,
    )

    assert first_report["exported_papers"] == 1
    assert second_report["exported_papers"] == 0
    assert second_report["failed_attempts"] == 1
    assert file_path.read_bytes() == original_bytes


def test_cross_paper_repetition_is_reported(tmp_path):
    report = generate_report(
        tmp_path,
        count=2,
        export=False,
    )

    assert report["requested_papers"] == 2
    assert report["generated_papers"] == 1
    assert report["failed_attempts"] == 1

    errors = report["modules"][0]["errors"]

    assert any(
        "Repeated question or scenario" in error["error"]
        for error in errors
    )


def test_invalid_approval_status_is_rejected(tmp_path):
    _, paper, _ = exported_paper(tmp_path)

    altered = deepcopy(paper)
    altered["release_status"] = "approved"

    validation = SyntheticDatasetExporter().validate(
        altered
    )

    assert validation["valid"] is False


def test_dry_run_does_not_create_files(tmp_path):
    report = generate_report(
        tmp_path,
        count=1,
        export=False,
    )

    assert report["generated_papers"] == 1
    assert report["exported_papers"] == 0
    assert list(tmp_path.iterdir()) == []


def test_production_mode_is_blocked(tmp_path):
    with pytest.raises(
        ValueError,
        match="production generation is blocked",
    ):
        make_runner(tmp_path).run(
            targets={"database_systems": 1},
            module_configs=configs(),
            mode="production",
        )


def test_generation_does_not_mutate_configs(tmp_path):
    module_configs = configs()
    original = deepcopy(module_configs)

    make_runner(tmp_path).run(
        targets={"database_systems": 1},
        module_configs=module_configs,
        export=False,
    )

    assert module_configs == original
