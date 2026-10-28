"""Deterministic sharding and aggregation for the multi-day RAG vs no-RAG run (no LLM calls, no network)."""

import pandas as pd
import pytest

from experiments import rag_vs_norag as rv
from experiments.model_comparison import load_answers_with_reference


def _test_frame(n=23):
    return pd.DataFrame({"answer_id": [f"A{i:03d}" for i in range(n)], "question_id": "Q"})


def _predictions(ids, failed=()):
    rows = []
    for i in ids:
        for cond in ("A_no_rag", "B_rag"):
            ok = (i, cond) not in failed
            rows.append({"answer_id": i, "question_id": "Q", "tier": "t", "condition": cond, "max_marks": 4.0, "expected_mark": 2.0,
                         "llm_status": "ok" if ok else "error", "predicted_mark": 3.0 if ok else None, "model": "m-1"})
    return pd.DataFrame(rows)


def test_parse_shard_accepts_i_of_k_and_rejects_everything_else():
    assert rv.parse_shard("2/9") == (2, 9) and rv.parse_shard("1/1") == (1, 1)
    for bad in ("0/9", "10/9", "3", "a/b", "1/2/3", "", "-1/3"):
        with pytest.raises(ValueError):
            rv.parse_shard(bad)


@pytest.mark.parametrize("k", [1, 2, 5, 9, 23, 30])
def test_shards_are_disjoint_and_cover_every_answer(k):
    frame = _test_frame()
    slices = [set(rv.select_answers(frame, shard=(i, k))["answer_id"]) for i in range(1, k + 1)]
    assert sum(len(s) for s in slices) == len(frame)  # disjoint
    assert set().union(*slices) == set(frame["answer_id"])  # complete
    assert max(len(s) for s in slices) - min(len(s) for s in slices) <= 1  # balanced


def test_shard_choice_does_not_depend_on_row_order_or_the_day_it_runs():
    frame = _test_frame()
    shuffled = frame.sample(frac=1, random_state=7).reset_index(drop=True)
    for i in range(1, 6):
        assert list(rv.select_answers(frame, shard=(i, 5))["answer_id"]) == list(rv.select_answers(shuffled, shard=(i, 5))["answer_id"])


def test_limit_is_a_fixed_seed_sample_and_cannot_be_combined_with_shard():
    frame = _test_frame()
    assert list(rv.select_answers(frame, limit=6)["answer_id"]) == list(rv.select_answers(frame, limit=6)["answer_id"])
    shuffled = frame.sample(frac=1, random_state=3).reset_index(drop=True)
    # --limit depends on the row order of its input (shards do not; see the order-independence test above)
    assert set(rv.select_answers(frame, limit=6)["answer_id"]) != set(rv.select_answers(shuffled, limit=6)["answer_id"])
    with pytest.raises(ValueError):
        rv.select_answers(frame, limit=5, shard=(1, 3))
    assert rv.main(["--out", "unused", "--limit", "5", "--shard", "1/3"]) == 2


def test_real_test_split_is_partitioned_by_the_shards():
    answers = load_answers_with_reference(rv.DATASET)
    test = answers[answers["split"] == "test"]
    covered = []
    for i in range(1, 10):
        covered += list(rv.select_answers(test, shard=(i, 9))["answer_id"])
    assert sorted(covered) == sorted(test["answer_id"]) and len(set(covered)) == len(test) == 90


def test_summary_counts_failures_and_never_scores_them_as_zero():
    summary = rv.summarise(_predictions(["a", "b"], failed={("a", "B_rag")}), "gemini", {"p": 1})
    assert summary["per_condition"]["B_rag"] == {"n_ok": 1, "n_failed": 1, "nmae": pytest.approx(0.25)}
    assert summary["per_condition"]["A_no_rag"]["n_failed"] == 0 and summary["models"] == ["m-1"] and summary["n_answers"] == 2


def _write_shards(tmp_path, ids, k):
    for i in range(1, k + 1):
        part = [x for n, x in enumerate(sorted(ids)) if n % k == i - 1]
        _predictions(part).to_csv(tmp_path / f"rag_vs_norag_predictions_shard{i}of{k}.csv", index=False)


def test_aggregate_merges_complete_shards(tmp_path):
    ids = [f"A{i:03d}" for i in range(10)]
    _write_shards(tmp_path, ids, 3)
    summary = rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    assert summary["aggregated_from_shards"] == 3 and summary["n_answers"] == 10
    assert (tmp_path / rv.PRED_FILE).exists() and (tmp_path / rv.SUMMARY_FILE).exists()


def test_aggregate_refuses_a_missing_shard_overlap_and_incomplete_cover(tmp_path):
    ids = [f"A{i:03d}" for i in range(10)]
    _write_shards(tmp_path, ids, 3)
    (tmp_path / "rag_vs_norag_predictions_shard2of3.csv").unlink()
    with pytest.raises(FileNotFoundError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    _predictions(["A001"]).to_csv(tmp_path / "rag_vs_norag_predictions_shard2of3.csv", index=False)  # wrong content: overlaps shard 1? no, incomplete cover
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    _write_shards(tmp_path, ids, 3)
    _predictions(["A000"]).to_csv(tmp_path / "rag_vs_norag_predictions_shard3of3.csv", index=False)  # A000 now in two shards
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    assert not (tmp_path / rv.PRED_FILE).exists()  # nothing combined on refusal


def test_aggregate_refuses_an_answer_with_a_single_condition(tmp_path):
    ids = ["A000", "A001"]
    frame = _predictions(ids)
    frame = frame[~((frame["answer_id"] == "A001") & (frame["condition"] == "B_rag"))]
    frame.to_csv(tmp_path / "rag_vs_norag_predictions_shard1of1.csv", index=False)
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 1, set(ids), "gemini", {})
