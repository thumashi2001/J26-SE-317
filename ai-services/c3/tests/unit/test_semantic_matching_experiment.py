"""Integrity and protocol tests for the FR-C3-09 semantic-matching experiment (offline: no embedding model is loaded)."""
import json

import numpy as np
import pytest

from experiments.semantic_matching import run_eval
from services.preprocessing.text_normalizer import tokenize
from services.semantic.baseline import token_overlap_score

DOC = json.loads(run_eval.FIXTURES.read_text(encoding="utf8"))
ITEMS = DOC["items"]
TYPES = set(DOC["answer_types"])


def test_splits_are_disjoint_by_item_and_by_concept():
    seen: dict[str, str] = {}
    for item in ITEMS:
        for c in item["concepts"]:
            assert seen.setdefault(c["name"], item["split"]) == item["split"], f"concept '{c['name']}' appears in two splits"
    assert {i["split"] for i in ITEMS} == {"dev", "validation", "test"}
    assert len({i["item_id"] for i in ITEMS}) == len(ITEMS)


def test_every_item_has_each_answer_type_once_and_labels_follow_the_construction_rule():
    for item in ITEMS:
        by_type = {a["type"]: a for a in item["answers"]}
        assert set(by_type) == TYPES and len(item["answers"]) == len(TYPES)
        n = len(item["concepts"])
        for t in ("EXACT", "PARAPHRASE", "CONCISE_CORRECT"):
            assert len(by_type[t]["demonstrated"]) == n
        assert len(by_type["PARTIAL"]["demonstrated"]) == 1
        for t in ("LEXICAL_WRONG", "IRRELEVANT", "KEYWORD_STUFFED"):
            assert by_type[t]["demonstrated"] == []
        assert len({a["text"] for a in item["answers"]}) == len(item["answers"])


def test_paraphrases_really_avoid_the_concept_wording_and_exact_answers_contain_it():
    for item in ITEMS:
        names = {c["id"]: c["name"] for c in item["concepts"]}
        by_type = {a["type"]: a for a in item["answers"]}
        for cid, name in names.items():
            assert token_overlap_score(name, tokenize(by_type["PARAPHRASE"]["text"])) < 1.0, (item["item_id"], name)
            assert token_overlap_score(name, tokenize(by_type["EXACT"]["text"])) == 1.0, (item["item_id"], name)
            # distractors reuse the wording, so a pure keyword rule cannot tell them apart from correct answers
            for t in ("LEXICAL_WRONG", "KEYWORD_STUFFED"):
                assert token_overlap_score(name, tokenize(by_type[t]["text"])) == 1.0, (item["item_id"], t, name)


def test_length_is_not_a_trivial_giveaway_between_correct_and_stuffed_answers():
    for item in ITEMS:
        by_type = {a["type"]: len(tokenize(a["text"])) for a in item["answers"]}
        assert by_type["KEYWORD_STUFFED"] > by_type["CONCISE_CORRECT"]
        assert by_type["PARAPHRASE"] >= by_type["EXACT"] - 10


def test_mark_rule_matches_the_rubric_levels():
    assert [run_eval.mark_from_count(k, 3) for k in range(4)] == [0, 2, 2, 4]


def test_threshold_selection_uses_only_the_scores_it_is_given_and_prefers_the_conservative_tie():
    scores = np.array([0.1, 0.2, 0.8, 0.9])
    y = np.array([0, 0, 1, 1])
    t = run_eval.select_threshold(scores, y)
    assert 0.2 < t <= 0.8
    # identical F1 for several thresholds -> the larger one is returned
    t2 = run_eval.select_threshold(np.array([0.5, 0.5, 0.9]), np.array([1, 1, 1]))
    # perfect F1 is reached for every threshold <= 0.5; the largest such threshold is chosen
    assert t2 == pytest.approx(0.5)


def test_select_never_loads_the_test_split(monkeypatch, tmp_path):
    loaded = []
    real_load = run_eval.load_items
    monkeypatch.setattr(run_eval, "FROZEN", tmp_path / "frozen.json")
    monkeypatch.setattr(run_eval, "LocalSentenceTransformerEmbedding", lambda *a, **k: object())

    def fake_load(splits):
        loaded.append(tuple(splits))
        return real_load(splits)

    def fake_rows(items, emb):
        assert all(i["split"] != "test" for i in items)
        rng = np.random.default_rng(1)
        return [
            {"split": i["split"], "item": i["item_id"], "answer_id": a["answer_id"], "type": a["type"], "concept": c["id"],
             "label": int(c["id"] in a["demonstrated"]), "n_concepts": len(i["concepts"]), "lex": float(rng.random()),
             "emb_name": float(rng.random()), "emb_desc": float(rng.random()), "length": 20, "negated": False}
            for i in items for a in i["answers"] for c in i["concepts"]
        ]

    monkeypatch.setattr(run_eval, "load_items", fake_load)
    monkeypatch.setattr(run_eval, "build_rows", fake_rows)
    run_eval.cmd_select()
    assert loaded == [("dev", "validation")]
    frozen = json.loads((tmp_path / "frozen.json").read_text())
    assert frozen["selection_split"] == "validation"
    assert set(frozen["methods"]) == set(run_eval.METHODS)


def test_committed_frozen_config_matches_the_current_fixtures():
    if not run_eval.FROZEN.exists():
        pytest.skip("select has not been run")
    frozen = json.loads(run_eval.FROZEN.read_text())
    assert frozen["fixtures_sha256"] == run_eval.fixtures_hash(), "fixtures changed after freezing: re-run select, then evaluate"
