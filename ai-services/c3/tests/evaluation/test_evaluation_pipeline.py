"""
Unit and regression tests for C3 benchmark evaluation pipeline.
"""

from experiments.run_evaluation import (
    build_synthetic_rubric,
    compute_pearson_r,
    evaluate_test_split,
)


def test_pearson_r_calculation():
    # Perfect positive correlation
    assert round(compute_pearson_r([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]), 2) == 1.0
    # Zero / constant
    assert compute_pearson_r([1.0, 1.0, 1.0], [2.0, 3.0, 4.0]) == 0.0


def test_build_synthetic_rubric():
    rubric = build_synthetic_rubric("PP-SE3040-001", 100.0, ["REST", "UI"])
    assert rubric.rubric_id == "R-PP-SE3040-001"
    assert len(rubric.criteria) >= 1
    total_max = sum(c.max_marks for c in rubric.criteria)
    assert abs(total_max - 100.0) < 0.5


def test_evaluation_pipeline_execution():
    results = evaluate_test_split()
    assert results["dataset_split"] == "test"
    assert results["sample_size"] == 150
    assert "metrics" in results
    assert results["metrics"]["rubric_aware_pipeline"]["mean_absolute_error_mae"] > 0
    assert results["metrics"]["concept_diagnosis"]["f1_score_pct"] > 80.0
    assert results["metrics"]["structural_validity"]["feedback_validity_rate_pct"] == 100.0
