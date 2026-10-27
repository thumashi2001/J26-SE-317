"""Phase-1/phase-2 model comparison plumbing that needs no network or GPU."""

import pytest

from experiments import model_comparison_extra as mx


def test_every_embedding_spec_label_rebuilds_a_model():
    """The final-test script rebuilds the validation-selected model from its label alone."""
    for name, (_, labels, make, _) in mx.EMBED_SPECS.items():
        assert labels, name
        for label in labels:
            assert hasattr(make(label), "fit"), (name, label)


def test_forest_depth_none_label_round_trips():
    assert mx._forest("depth=None").max_depth is None
    assert mx._forest("depth=6").max_depth == 6


def test_phase1_drops_the_held_out_split():
    import pandas as pd

    d = {s: pd.DataFrame({"x": [1]}) for s in ("train", "validation", "test")}
    assert set(mx._val_only(d)) == {"train", "validation"}


def test_checkpoint_key_is_filesystem_safe():
    assert mx._key("microsoft/deberta-v3-base") == "D_deberta-v3-base"
    assert "/" not in mx._key("cross-encoder/ms-marco-MiniLM-L-6-v2")


def test_final_test_refuses_smoke_phase1(tmp_path):
    import json

    from experiments import final_test_extra as ft

    p1 = tmp_path / "p.json"
    p1.write_text(json.dumps({"meta": {"smoke": True, "dataset_sha256": {}}, "results": {}}), encoding="utf-8")
    with pytest.raises(SystemExit, match="smoke"):
        ft.main(["--phase1", str(p1), "--ckpt", str(tmp_path), "--out", str(tmp_path / "o")])
