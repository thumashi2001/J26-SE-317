
"""M11.2.6.3 end-to-end pipeline tests."""

from copy import deepcopy

import pytest

from services.synthetic_pipeline_runner import (
    SyntheticPipelineRunner,
)
from tests.test_synthetic_generation_adapter import (
    adapter,
    pool_configs,
)
from tests.test_synthetic_paper_builder import (
    fixture_structure,
)


def configs():
    return {
        "database_systems": {
            "structure": fixture_structure(),
            "pool_configs": pool_configs(),
        }
    }


def runner(tmp_path):
    return SyntheticPipelineRunner(
        export_root=tmp_path,
        adapter=adapter(),
    )


def test_end_to_end_generates_one_paper(tmp_path):
    report = runner(tmp_path).run(
        {"database_systems": 1},
        configs(),
    )

    assert report["generated_papers"] == 1
    assert report["failed_attempts"] == 0
    assert report["exported_papers"] == 0


def test_cross_paper_repetition_is_blocked(tmp_path):
    report = runner(tmp_path).run(
        {"database_systems": 2},
        configs(),
    )

    assert report["generated_papers"] == 1
    assert report["failed_attempts"] == 1
    assert "Repeated question or scenario" in (
        report["modules"][0]["errors"][0]["error"]
    )


def test_end_to_end_export(tmp_path):
    report = runner(tmp_path).run(
        {"database_systems": 1},
        configs(),
        export=True,
    )

    assert report["exported_papers"] == 1

    files = list(
        (tmp_path / "database_systems").glob("*.json")
    )

    assert len(files) == 1


def test_dry_run_writes_nothing(tmp_path):
    runner(tmp_path).run(
        {"database_systems": 1},
        configs(),
        export=False,
    )

    assert list(tmp_path.iterdir()) == []


def test_reproducible_reports(tmp_path):
    service = runner(tmp_path)

    first = service.run(
        {"database_systems": 1},
        configs(),
        base_seed=123,
    )

    second = service.run(
        {"database_systems": 1},
        configs(),
        base_seed=123,
    )

    assert first == second


def test_production_blocked(tmp_path):
    with pytest.raises(
        ValueError,
        match="production generation is blocked",
    ):
        runner(tmp_path).run(
            {"database_systems": 1},
            configs(),
            mode="production",
        )


def test_missing_module_configuration(tmp_path):
    with pytest.raises(
        ValueError,
        match="Missing configuration",
    ):
        runner(tmp_path).run(
            {"database_systems": 1},
            {},
        )


def test_inputs_unchanged(tmp_path):
    original = configs()
    snapshot = deepcopy(original)

    runner(tmp_path).run(
        {"database_systems": 1},
        original,
    )

    assert original == snapshot


def test_report_retains_pending_review(tmp_path):
    report = runner(tmp_path).run(
        {"database_systems": 1},
        configs(),
    )

    assert report["academic_review_status"] == "pending"
    assert report["release_status"] == "not_approved"


def test_invalid_target_rejected(tmp_path):
    with pytest.raises(ValueError):
        runner(tmp_path).run(
            {"database_systems": 0},
            configs(),
        )
