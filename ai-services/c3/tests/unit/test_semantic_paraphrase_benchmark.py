"""Benchmark machinery: schema, label provenance, split integrity, metric arithmetic, protocol refusals, reproducibility.

These tests never assert that a model is accurate. Metric tests use hand-computed counts; the runner is a deterministic fake.
"""

import copy
import json

import pytest

from datasets.paraphrase_benchmark import sheets, validate
from experiments import semantic_paraphrase_eval as ev

ITEMS = validate.load_doc()["items"]


def _labelled(items, label_of):
    """Copy of items with two agreeing synthetic annotators; TEST FIXTURE ONLY (not benchmark data)."""
    out = copy.deepcopy(items)
    for item in out:
        label = label_of(item)
        item["annotations"] = [
            {"annotator_id": f"ANN0{n}", "label": label, "rationale": "test fixture"} for n in (1, 2)
        ]
        item["label_status"], item["final_label"] = "human_labelled", label
    return out


# ------------------------------------------------------------------- dataset


def test_shipped_dataset_is_valid_and_has_no_human_labels_yet():
    report = validate.integrity_report(ITEMS)
    assert report["valid"], (report["item_problems"], report["split_problems"])
    assert report["human_labelled_items"] == 0  # honest state: drafts only
    assert all(i["label_status"] == "draft_unreviewed" and i["final_label"] is None for i in ITEMS)


def test_every_category_is_in_both_splits_and_splits_are_group_disjoint():
    for split in validate.SPLITS:
        assert {i["category"] for i in ITEMS if i["split"] == split} == set(validate.CATEGORIES)
    dev = {i["group_id"] for i in ITEMS if i["split"] == "dev"}
    held = {i["group_id"] for i in ITEMS if i["split"] == "heldout"}
    assert dev and held and not dev & held


def test_historical_architecture_case_is_preserved_as_history_only():
    case = next(i for i in ITEMS if i["item_id"] == "PB1-G01-P1")
    assert case["student_answer"].startswith("An architecture describes the overall organisation")
    obs = case["historical_observation"]
    assert (obs["semantic_score"], obs["threshold"]) == (0.3112, 0.5)
    assert case["split"] == "dev"  # an already-observed failure must not sit in the held-out split
    assert case["final_label"] is None  # the observation is not a label


@pytest.mark.parametrize(
    "mutate,fragment",
    [
        (lambda i: i.update(split="test"), "split"),
        (lambda i: i.update(category="other"), "category"),
        (lambda i: i["draft"].update(proposed_label="great"), "proposed_label"),
        (lambda i: i.pop("concept"), "missing field"),
        (lambda i: i.update(student_answer="  "), "student_answer"),
    ],
)
def test_schema_violations_are_reported(mutate, fragment):
    item = copy.deepcopy(ITEMS[0])
    mutate(item)
    assert any(fragment in p for p in validate.item_problems(item))


# ------------------------------------------------------------ label provenance


def _annotation(annotator, label, why="because"):
    return {"annotator_id": annotator, "label": label, "rationale": why}


def test_status_is_derived_from_annotations():
    item = copy.deepcopy(ITEMS[0])
    assert validate.derive_status(item) == "draft_unreviewed"
    item["annotations"] = [_annotation("ANN01", "partial")]
    assert validate.derive_status(item) == "annotated" and validate.derive_final_label(item) is None
    item["annotations"].append(_annotation("ANN02", "missing"))
    assert validate.derive_status(item) == "needs_adjudication" and validate.derive_final_label(item) is None
    item["adjudication"] = {"adjudicator_id": "ADJ01", "label": "partial", "rationale": "x"}
    assert validate.derive_status(item) == "adjudicated" and validate.derive_final_label(item) == "partial"


def test_a_hand_typed_status_or_label_that_contradicts_annotations_is_rejected():
    item = copy.deepcopy(ITEMS[0])
    item["label_status"], item["final_label"] = "human_labelled", "demonstrated"  # no annotations behind it
    assert any("label_status" in p for p in validate.item_problems(item))


@pytest.mark.parametrize(
    "ann",
    [
        {"annotator_id": "Alice", "label": "partial", "rationale": "x"},  # real name, not a pseudonym
        {"annotator_id": "ANN01", "label": "great", "rationale": "x"},
        {"annotator_id": "ANN01", "label": "partial", "rationale": " "},
    ],
)
def test_bad_annotation_records_are_rejected(ann):
    item = copy.deepcopy(ITEMS[0])
    item["annotations"] = [ann]
    assert validate.item_problems(item)


def test_adjudicator_cannot_be_an_annotator_or_adjudicate_agreement():
    item = copy.deepcopy(ITEMS[0])
    item["annotations"] = [_annotation("ANN01", "partial"), _annotation("ANN02", "missing")]
    item["adjudication"] = {"adjudicator_id": "ADJ01", "label": "partial", "rationale": "x"}
    item["label_status"], item["final_label"] = "adjudicated", "partial"
    assert validate.item_problems(item) == []
    item["annotations"][1]["label"] = "partial"
    assert any("did not disagree" in p for p in validate.item_problems(item))


def test_ingest_never_invents_labels_and_rejects_bad_returns():
    assert all(i["final_label"] is None for i in sheets.ingest_returns(ITEMS, "ANN01", []))
    first = ITEMS[0]["item_id"]
    with pytest.raises(ValueError):
        sheets.ingest_returns(ITEMS, "ANN01", [{"item_id": first, "label": "yes", "rationale": "x"}])
    with pytest.raises(ValueError):
        sheets.ingest_returns(ITEMS, "ANN01", [{"item_id": first, "label": "partial", "rationale": ""}])
    once = sheets.ingest_returns(ITEMS, "ANN01", [{"item_id": first, "label": "partial", "rationale": "r"}])
    with pytest.raises(ValueError):
        sheets.ingest_returns(once, "ANN01", [{"item_id": first, "label": "partial", "rationale": "r"}])


def test_two_agreeing_returns_make_an_item_scorable_and_disagreement_waits_for_adjudication():
    a, b = ITEMS[0]["item_id"], ITEMS[1]["item_id"]
    step = sheets.ingest_returns(
        ITEMS,
        "ANN01",
        [
            {"item_id": a, "label": "demonstrated", "rationale": "r"},
            {"item_id": b, "label": "partial", "rationale": "r"},
        ],
    )
    step = sheets.ingest_returns(
        step,
        "ANN02",
        [
            {"item_id": a, "label": "demonstrated", "rationale": "r"},
            {"item_id": b, "label": "missing", "rationale": "r"},
        ],
    )
    by = {i["item_id"]: i for i in step}
    assert by[a]["label_status"] == "human_labelled" and by[a]["final_label"] == "demonstrated"
    assert by[b]["label_status"] == "needs_adjudication" and [d["item_id"] for d in sheets.disagreements(step)] == [b]
    done = sheets.ingest_adjudication(step, "ADJ01", [{"item_id": b, "label": "partial", "rationale": "r"}])
    assert {i["item_id"]: i for i in done}[b]["final_label"] == "partial" and validate.validate_items(done)["ok"]


def test_blind_sheet_hides_draft_label_category_and_split():
    row = sheets.blind_rows(ITEMS)[0]
    assert set(row) == set(sheets.SHEET_COLUMNS) and row["label"] == "" and row["rationale"] == ""
    text = json.dumps(sheets.blind_rows(ITEMS))
    assert "proposed" not in text and "keyword_trap" not in text


def test_sheets_refuse_to_overwrite(tmp_path):
    path = tmp_path / "s.csv"
    sheets.write_sheet(sheets.blind_rows(ITEMS)[:2], path)
    with pytest.raises(FileExistsError):
        sheets.write_sheet([], path)


# ----------------------------------------------------------- split integrity


def test_group_straddling_splits_and_cross_split_near_duplicates_are_detected():
    items = copy.deepcopy(ITEMS)
    items[0]["split"] = "heldout"  # G01 now in both splits
    assert any("more than one split" in p for p in validate.split_problems(items))
    items = copy.deepcopy(ITEMS)
    dev = next(i for i in items if i["split"] == "dev")
    held = next(i for i in items if i["split"] == "heldout")
    held["student_answer"] = dev["student_answer"] + " Indeed."
    assert any("near-duplicate" in p for p in validate.split_problems(items))


def test_duplicate_ids_and_exact_duplicates_are_detected():
    items = copy.deepcopy(ITEMS)
    items.append(copy.deepcopy(items[0]))
    problems = validate.split_problems(items)
    assert any("duplicate item_id" in p for p in problems) and any("exact duplicate" in p for p in problems)


def test_content_hash_ignores_key_order_but_not_content():
    shuffled = [dict(reversed(list(i.items()))) for i in ITEMS]
    assert validate.content_hash(shuffled) == validate.content_hash(ITEMS)
    changed = copy.deepcopy(ITEMS)
    changed[0]["student_answer"] += "!"
    assert validate.content_hash(changed) != validate.content_hash(ITEMS)


# ------------------------------------------------------------------- metrics


def _row(truth, lexical, score, category="paraphrase", concept="c"):
    return {
        "item_id": f"{truth}{lexical}{score}",
        "group_id": "g",
        "concept": concept,
        "category": category,
        "truth": truth,
        "lexical_status": lexical,
        "semantic_score": score,
    }


ROWS = [  # hand-countable
    _row("demonstrated", "demonstrated", 0.9),  # lexical TP
    _row("demonstrated", "not_demonstrated", 0.6),  # semantic rescues at t<=0.6
    _row("demonstrated", "not_demonstrated", 0.2),  # always missed
    _row("contradicted", "demonstrated", 0.8, "negation"),  # lexical false positive, never removed
    _row("missing", "not_demonstrated", 0.55, "keyword_trap"),  # semantic false positive at t<=0.55
    _row("missing", "partial", 0.1, "missing"),
]


def test_binary_counts_and_prf_by_hand():
    lexical = ev.binary_counts(ROWS, None)
    assert lexical == {"tp": 1, "fp": 1, "fn": 2, "tn": 2}
    report = ev.prf_report(lexical)
    assert report["positive"] == {"precision": 0.5, "recall": 0.3333, "f1": 0.4}
    assert report["negative"]["recall"] == 0.6667 and report["accuracy"] == 0.5
    assert ev.binary_counts(ROWS, 0.5) == {"tp": 2, "fp": 2, "fn": 1, "tn": 1}
    assert ev.binary_counts(ROWS, 0.7) == {"tp": 1, "fp": 1, "fn": 2, "tn": 2}  # high threshold == lexical only


def test_macro_f1_is_the_mean_of_both_classes():
    r = ev.prf_report(ev.binary_counts(ROWS, None))
    assert r["macro_f1"] == round((r["positive"]["f1"] + r["negative"]["f1"]) / 2, 4)


def test_system_status_follows_the_analyzer_rule():
    assert ev.system_status(_row("demonstrated", "partial", 0.6), 0.5) == "demonstrated"
    assert ev.system_status(_row("demonstrated", "partial", 0.4), 0.5) == "partial"
    assert ev.system_status(_row("demonstrated", "demonstrated", None), 0.5) == "demonstrated"
    assert (
        ev.system_status(_row("demonstrated", "not_demonstrated", None), 0.1) == "not_demonstrated"
    )  # layer unavailable
    assert ev.system_status(_row("demonstrated", "partial", 0.9), None) == "partial"  # layer off


def test_rule_matches_the_real_analyzer_on_a_fake_matcher(monkeypatch):
    import numpy as np

    from app.schemas.analysis import AnswerAnalysisRequest
    from services.semantic import analyzer

    class Fake:
        def similarities(self, concepts, sentences):
            return np.full((len(concepts), len(sentences)), 0.6)

    monkeypatch.setattr(analyzer, "get_matcher", lambda: Fake())
    monkeypatch.setenv("C3_SEMANTIC_THRESHOLD", "0.5")
    request = AnswerAnalysisRequest(
        question_id="q",
        question_text="q",
        student_answer="Some unrelated words here.",
        expected_concepts=["alpha"],
        answer_type="short",
    )
    match = analyzer.analyze_answer(request).concept_matches[0]
    row = _row("demonstrated", "not_demonstrated", match.semantic_score)
    assert match.status == ev.system_status(row, 0.5) == "demonstrated"


def test_label_by_status_matrix_by_category_and_errors():
    matrix = ev.label_by_status_matrix(ROWS, 0.5)
    assert matrix["demonstrated"] == {"demonstrated": 2, "not_demonstrated": 1}
    assert matrix["missing"] == {"demonstrated": 1, "partial": 1}
    cats = ev.by_group_key(ROWS, 0.5, "category")
    assert cats["keyword_trap"]["fp"] == 1 and cats["negation"]["fp"] == 1 and cats["paraphrase"]["n"] == 3
    errs = ev.errors(ROWS, 0.5)
    assert len(errs["false_positives"]) == 2 and [e["semantic_score"] for e in errs["false_negatives"]] == [0.2]


def test_threshold_curve_shows_the_trade_off_and_selection_prefers_higher_on_ties():
    curve = {c["threshold"]: c for c in ev.threshold_curve(ROWS)}
    assert (curve[0.5]["missed"], curve[0.5]["wrongly_detected"]) == (1, 2)
    assert (curve[0.7]["missed"], curve[0.7]["wrongly_detected"]) == (2, 1)
    tie = [
        _row("demonstrated", "demonstrated", 0.9),
        _row("missing", "not_demonstrated", 0.1),
    ]  # every threshold is perfect
    selection = ev.select_threshold(tie)
    assert selection["threshold"] == ev.THRESHOLD_GRID[-1] and selection["dev_gain_over_lexical"] == 0.0


def test_selection_uses_only_the_rows_it_is_given():
    held_out_leak = ROWS + [_row("missing", "not_demonstrated", 0.99)]
    assert ev.select_threshold(ROWS) == ev.select_threshold(list(ROWS))
    assert ev.select_threshold(held_out_leak) != {}  # it can differ, which is why run_dev passes DEV rows only


# ------------------------------------------------------------------ protocol


def fake_runner(item, semantic):
    """Deterministic stand-in for the analyzer: score from answer length, lexical status from a word check."""
    lexical = (
        "demonstrated" if item["concept"].split()[0].lower() in item["student_answer"].lower() else "not_demonstrated"
    )
    return {
        "status": lexical,
        "semantic_score": round((len(item["student_answer"]) % 50) / 50, 4) if semantic else None,
    }


def test_dev_phase_refuses_draft_items(tmp_path):
    with pytest.raises(PermissionError):
        ev.run_dev(ITEMS, tmp_path, fake_runner)
    assert not (tmp_path / "frozen_config.json").exists()


def test_cli_exits_3_without_human_labels(tmp_path):
    assert ev.main(["dev", "--out", str(tmp_path)]) == ev.EXIT_NO_LABELS
    assert ev.main(["heldout", "--out", str(tmp_path)]) in (ev.EXIT_NO_LABELS, ev.EXIT_REFUSED)


def test_protocol_end_to_end_with_fixture_labels_and_single_heldout_scoring(tmp_path):
    items = _labelled(ITEMS, lambda i: i["draft"]["proposed_label"])  # fixture labels, test only
    frozen = ev.run_dev(items, tmp_path, fake_runner)
    assert frozen["dataset_sha256"] == validate.content_hash(items) and frozen["split_used"] == "dev"
    result = ev.run_heldout(items, tmp_path, fake_runner)
    assert result["n_items"] == 32 and result["frozen_config"] == frozen
    assert {r["group_id"] for r in result["rows"]} == {"G07", "G08", "G09", "G10"}
    with pytest.raises(FileExistsError):
        ev.run_heldout(items, tmp_path, fake_runner)  # second scoring of the held-out split is refused


def test_heldout_refuses_a_changed_dataset_and_unlabelled_heldout(tmp_path):
    items = _labelled([i for i in ITEMS if i["split"] == "dev"], lambda i: i["draft"]["proposed_label"]) + [
        i for i in ITEMS if i["split"] == "heldout"
    ]
    ev.run_dev(items, tmp_path, fake_runner)
    with pytest.raises(PermissionError):
        ev.run_heldout(items, tmp_path, fake_runner)  # held-out items still unlabelled
    edited = copy.deepcopy(items)
    edited[0]["student_answer"] += " edited"
    with pytest.raises(ValueError):
        ev.run_heldout(edited, tmp_path, fake_runner)  # dataset changed after freezing


def test_benchmark_run_is_reproducible(tmp_path):
    items = _labelled(ITEMS, lambda i: i["draft"]["proposed_label"])
    outputs = []
    for name in ("a", "b"):
        out = tmp_path / name
        ev.run_dev(items, out, fake_runner)
        ev.run_heldout(items, out, fake_runner)
        outputs.append(
            {f: (out / f).read_bytes() for f in ("frozen_config.json", "dev_report.json", "heldout_final.json")}
        )
    assert outputs[0] == outputs[1]


def test_pipeline_check_is_stamped_not_evidence_and_freezes_nothing(tmp_path):
    result = ev.run_pipeline_check(ITEMS, tmp_path, fake_runner)
    assert result["STAMP"].startswith("NOT EVIDENCE") and result["label_source"] == "draft.proposed_label"
    assert [p.name for p in tmp_path.iterdir()] == ["DRAFT_NOT_EVIDENCE_pipeline_check.json"]


def test_score_only_run_that_changes_status_is_caught():
    def broken(item, semantic):
        return {"status": "demonstrated" if semantic else "not_demonstrated", "semantic_score": 0.9}

    with pytest.raises(RuntimeError):
        ev.collect_rows(ITEMS[:1], lambda i: "missing", broken)
