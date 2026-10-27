"""Regression: the answers CSV has an empty reference_answer column; loaders must fill it from the question bank."""

import pandas as pd

from experiments.model_comparison import DATASET, load, load_answers_with_reference


def test_raw_answers_file_has_empty_references_so_the_merge_is_required():
    raw = pd.read_csv(DATASET / "02_controlled_answers_eligible.csv", dtype=str, keep_default_na=False)
    assert (raw["reference_answer"].str.strip() == "").all()


def test_every_loaded_answer_has_a_reference_answer():
    for name, df in load().items():
        assert len(df) and (df["reference_answer"].str.strip() != "").all(), name
    assert (load_answers_with_reference()["reference_answer"].str.len() > 20).all()


def test_answer_only_ablation_reproduces_the_old_empty_reference():
    assert (load(with_reference=False)["train"]["reference_answer"] == "").all()
