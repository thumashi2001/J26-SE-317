"""Sampling, blind sheet generation, the separate key and the seal, on toy data and on the real v2 availability.

Sheets built here have origin 'toy_fixture': simulated, never real marking material. Real v2 data is only read.
"""

import hashlib
import json
from pathlib import Path

import pytest
from gold_toy_data import MARKERS, SALT, build_toy_dataset, toy_approvals, toy_rubric, toy_rubrics

from datasets.gold import sampling, sheets
from datasets.gold.common import GoldToolError, canonical_bytes
from datasets.repair.common import LABELS

V2_DIR = Path(__file__).resolve().parents[2] / "datasets" / "c3_phase3_v5_repaired_v2"


@pytest.fixture()
def toy(tmp_path):
    return build_toy_dataset(tmp_path / "data")


def _plan(toy, **kw):
    return sampling.plan(toy, seed="s1", pilot_seed="p1", pilot_size=kw.pop("pilot_size", 4), **kw)


def _build(toy, group="final", origin="toy_fixture", status="ai_drafted", markers=MARKERS, salt=SALT, plan=None, rubrics=None,
           approvals="auto"):
    plan = plan or _plan(toy)
    rubrics = rubrics or toy_rubrics(plan, group, status)
    if approvals == "auto":  # a matching register is supplied automatically, so tests of other guards reach those guards
        approvals = toy_approvals(rubrics) if origin == "gold" else None
    return sheets.build_sheets(toy, plan, group, rubrics, list(markers), salt, origin, approvals)


# ------------------------------------------------------------------------------------------------- sampling
def test_final_set_is_every_eligible_validation_and_test_question(toy):
    p = _plan(toy)
    assert [q["question_id"] for q in p["final"]["questions"]] == ["TQ-T1", "TQ-T2", "TQ-V1", "TQ-V2"]
    assert p["final"]["answers"] == 24 and p["final"]["template_controls_excluded_from_marking"] == 4
    assert p["final"]["answers_to_mark"] == 20


def test_pilot_comes_from_train_only_and_is_disjoint(toy):
    p = _plan(toy)
    final, pilot = {q["question_id"] for q in p["final"]["questions"]}, {q["question_id"] for q in p["pilot"]["questions"]}
    assert pilot and not final & pilot
    assert {q["split"] for q in p["pilot"]["questions"]} == {"train"}
    assert "TQ-X1" not in pilot  # an ineligible question is never selected
    assert p["pilot"]["answers_to_mark"] == 5 * len(pilot)


def test_selection_is_deterministic_and_spreads_over_modules(toy):
    assert _plan(toy) == _plan(toy)
    three = sampling.plan(toy, seed="s", pilot_seed="p", pilot_size=3)["pilot"]["questions"]
    assert sorted(q["module_code"] for q in three) == ["SE1", "SE2", "SE3"]  # round-robin over modules
    picks = {tuple(q["question_id"] for q in sampling.plan(toy, seed="s", pilot_seed=f"p{i}", pilot_size=2)["pilot"]["questions"])
             for i in range(12)}
    assert len(picks) > 1  # the pilot seed matters when the pool is larger than the request


def test_final_size_can_be_smaller_but_never_larger_than_the_pool(toy):
    assert _plan(toy, final_size=2)["final"]["n"] == 2
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in toy.iterdir()}
    with pytest.raises(GoldToolError, match="pool of 4"):
        _plan(toy, final_size=5)
    with pytest.raises(GoldToolError):
        _plan(toy, pilot_size=7)  # six eligible training questions
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in toy.iterdir()} == before


def _edited(toy, edit):
    import copy

    plan = copy.deepcopy(_plan(toy))
    edit(plan)
    return plan


@pytest.mark.parametrize("edit, match", [
    (lambda p: p["final"]["questions"].append(p["pilot"]["questions"][0]), "cannot be in the final group"),
    (lambda p: p["pilot"]["questions"].append(p["final"]["questions"][0]), "must be disjoint"),
    (lambda p: p["pilot"]["questions"].append(p["pilot"]["questions"][0]), "appears more than once"),
    (lambda p: p["final"]["questions"].append({**p["final"]["questions"][0]}), "appears more than once"),
    (lambda p: p["final"]["questions"][0].update(question_id="TQ-X1"), "not an eligible question"),
    (lambda p: p["final"]["questions"][0].update(question_id="TQ-NOPE"), "not an eligible question"),
    (lambda p: p["final"]["questions"][0].update(marks="99"), "differ from the dataset"),
    (lambda p: p["final"]["questions"][0].update(split="train"), "differ from the dataset"),
    (lambda p: p["final"].update(questions=[]), "group is empty"),
    (lambda p: p["dataset"].update(manifest_sha256="0" * 64), "different dataset manifest"),
])
def test_a_hand_edited_plan_is_rejected_before_any_sheet_is_built(toy, edit, match):
    plan = _edited(toy, edit)
    with pytest.raises(GoldToolError, match=match):
        sampling.validate_plan(toy, plan)
    with pytest.raises(GoldToolError, match=match):
        sheets.build_sheets(toy, plan, "final", toy_rubrics(_plan(toy), "final"), MARKERS, SALT, "toy_fixture")


def test_an_untouched_plan_validates(toy):
    sampling.validate_plan(toy, _plan(toy))


def test_plan_holds_ids_and_counts_only(toy):
    text = json.dumps(_plan(toy))
    for forbidden in ("answer_quality", "expected_mark", "student_answer", "FULL", "MISCONCEPTION", "TA-"):
        assert forbidden not in text


@pytest.mark.skipif(not (V2_DIR / "manifest.json").exists(), reason="v2 dataset not present")
def test_real_v2_has_the_26_question_final_set_and_a_disjoint_pilot():
    p = sampling.plan(V2_DIR, seed="availability-check", pilot_seed="availability-check")
    final, pilot = {q["question_id"] for q in p["final"]["questions"]}, {q["question_id"] for q in p["pilot"]["questions"]}
    assert p["final"]["n"] == 26 and {q["split"] for q in p["final"]["questions"]} == {"validation", "test"}
    assert p["final"]["answers_to_mark"] == 5 * 26 and p["final"]["template_controls_excluded_from_marking"] == 26
    assert p["pilot"]["n"] == 4 and {q["split"] for q in p["pilot"]["questions"]} == {"train"} and not final & pilot
    with pytest.raises(GoldToolError):
        sampling.plan(V2_DIR, seed="a", pilot_seed="b", final_size=30)


def test_sampling_cli(toy, capsys):
    assert sampling.main([str(toy), "--seed", "a", "--pilot-seed", "b"]) == 0
    assert json.loads(capsys.readouterr().out)["final"]["n"] == 4
    assert sampling.main([str(toy), "--seed", "a", "--pilot-seed", "b", "--final-size", "9"]) == 1


# ------------------------------------------------------------------------------------------- blind sheets
def test_sheets_hold_only_the_five_marked_answers_per_question_and_exclude_controls(toy):
    r = _build(toy)
    for m in MARKERS:
        assert len(r["sheets"][m]["items"]) == 20
    assert sorted(e["reason"] for e in r["key"]["excluded"]) == ["template_negative_control"] * 4
    assert {a["answer_id"] for a in r["key"]["excluded"]} == {f"TA-{q}-IRRELEVANT" for q in ("T1", "T2", "V1", "V2")}


def test_marker_sheets_hide_tiers_marks_splits_and_dataset_ids(toy):
    r = _build(toy)
    text = "".join(canonical_bytes(r["sheets"][m]).decode() + canonical_bytes(r["return_templates"][m]).decode() for m in MARKERS)
    for token in (*LABELS, "expected_mark", "answer_quality", "criterion_marks", "template_negative_control", "demonstrated",
                  "validation", "TQ-", "TA-", "CRIT-", "R-TQ", "SE1", "SE2"):
        assert token not in text, token
    allowed = {"item_id", "question_text", "rubric_ref", "answer_text"}
    assert all(set(i) == allowed for i in r["sheets"]["m1"]["items"])
    assert set(r["sheets"]["m1"]) == {"sheet_version", "origin", "group", "marker", "instructions", "rubrics", "items", "notice"}


def test_key_is_separate_and_maps_back_without_containing_the_salt(toy):
    r = _build(toy)
    key = r["key"]
    assert len(key["items"]) == 20 and all(v["answer_id"].startswith("TA-") for v in key["items"].values())
    assert SALT not in json.dumps(key) and SALT not in json.dumps(r["seal"]) and key["salt_commitment"] != SALT
    sheet_text = canonical_bytes(r["sheets"]["m1"]).decode()
    assert not any(a["answer_id"] in sheet_text for a in key["items"].values())
    ref = next(iter(key["rubric_refs"]))
    assert key["rubric_refs"][ref]["criteria"]["C1"]["criterion_id"].startswith("CRIT-")
    assert set(key["rubric_refs"][ref]["criteria"]["C1"]["levels"]) == {"C1-L1", "C1-L2", "C1-L3"}


def test_nothing_in_the_marker_directory_exposes_ids_tiers_scores_the_key_or_the_salt(toy, tmp_path):
    import csv
    import re

    r = _build(toy)
    out, custody = tmp_path / "marker_dir", tmp_path / "custody_dir"
    sheets.write_outputs(r, out, custody)
    names = sorted(p.name for p in out.rglob("*"))
    assert all(re.fullmatch(r"(sheet|return_template)_(m1|m2)\.json", n) for n in names)  # file names carry only the pseudonym
    ids = {row["question_id"] for row in csv.DictReader(open(toy / "01_question_bank.csv", encoding="utf-8", newline=""))}
    ids |= {row["answer_id"] for row in csv.DictReader(open(toy / "02_controlled_answers_eligible.csv", encoding="utf-8", newline=""))}
    secrets_ = [SALT, r["key"]["salt_commitment"], r["seal"]["seal_sha256"], r["seal"]["files"]["answer_key.json"],
                r["key"]["plan_sha256"], r["key"]["dataset_manifest_sha256"],
                *ids, *LABELS, "expected_mark", "answer_quality", "template_negative_control", "answer_key", "salt", "restricted"]
    blob = "".join(p.read_text(encoding="utf-8") for p in out.rglob("*.json")) + "".join(names)
    assert [s for s in secrets_ if s and s in blob] == []
    assert not (out / "answer_key.json").exists() and not list(out.rglob("*key*")) and not list(out.rglob("*seal*"))
    assert (custody / "answer_key.json").exists()


def test_each_marker_gets_an_independent_order_that_is_not_grouped_by_question(toy):
    r = _build(toy)
    order = {m: [i["item_id"] for i in r["sheets"][m]["items"]] for m in MARKERS}
    assert sorted(order["m1"]) == sorted(order["m2"]) and order["m1"] != order["m2"]
    refs = [i["rubric_ref"] for i in r["sheets"]["m1"]["items"]]
    runs = 1 + sum(a != b for a, b in zip(refs, refs[1:], strict=False))
    assert runs > len(set(refs))  # at least one question appears in more than one block


def test_generation_is_deterministic_and_the_salt_changes_every_opaque_id(toy):
    a, b = _build(toy), _build(toy)
    assert canonical_bytes(a["key"]) == canonical_bytes(b["key"]) and a["seal"]["seal_sha256"] == b["seal"]["seal_sha256"]
    c = _build(toy, salt="another-salt-0123456789")
    assert not set(a["key"]["items"]) & set(c["key"]["items"])


@pytest.mark.parametrize("kwargs, match", [
    ({"salt": "short"}, "salt must be"),
    ({"markers": ["only-one"]}, "at least two"),
    ({"markers": ["m1", "m1"]}, "at least two"),
    ({"markers": ["m1", "bad name"]}, "at least two"),
    ({"group": "pilot", "origin": "gold"}, "not allowed for group"),
    ({"origin": "pilot"}, "not allowed for group"),
    ({"origin": "other"}, "not allowed for group"),
])
def test_argument_guards(toy, kwargs, match):
    with pytest.raises(GoldToolError, match=match):
        _build(toy, **kwargs)


def test_gold_needs_lecturer_validated_rubrics_but_pilot_accepts_ai_drafts(toy):
    with pytest.raises(GoldToolError, match="lecturer_validated"):
        _build(toy, origin="gold", status="ai_drafted")
    assert _build(toy, origin="gold", status="lecturer_validated")["sheets"]["m1"]["origin"] == "gold"
    assert _build(toy, group="pilot", origin="pilot", status="ai_drafted")["sheets"]["m1"]["group"] == "pilot"


def test_a_rubric_filed_under_the_wrong_question_is_refused(toy):
    plan = _plan(toy)
    rubrics = toy_rubrics(plan, "final", "lecturer_validated")
    rubrics["TQ-V1"], rubrics["TQ-V2"] = rubrics["TQ-V2"], rubrics["TQ-V1"]
    with pytest.raises(GoldToolError, match="not acceptable"):
        _build(toy, origin="gold", plan=plan, rubrics=rubrics)


def test_a_validation_claim_with_missing_details_is_refused_even_for_gold(toy):
    plan = _plan(toy)
    for edit in (lambda p: p.update(validated_by=""), lambda p: p.update(validated_by="toy-drafter"),
                 lambda p: p.update(validated_on="2026-09-01")):
        rubrics = toy_rubrics(plan, "final", "lecturer_validated")
        edit(rubrics["TQ-T2"]["provenance"])
        with pytest.raises(GoldToolError, match="not acceptable"):
            _build(toy, origin="gold", plan=plan, rubrics=rubrics)


def test_missing_or_unacceptable_rubrics_are_refused(toy):
    plan = _plan(toy)
    rubrics = toy_rubrics(plan, "final")
    del rubrics["TQ-V1"]
    with pytest.raises(GoldToolError, match="no rubric document"):
        _build(toy, plan=plan, rubrics=rubrics)
    rubrics = toy_rubrics(plan, "final")
    rubrics["TQ-V1"] = toy_rubric("TQ-V1", "12")  # marks do not match the question
    with pytest.raises(GoldToolError, match="not acceptable"):
        _build(toy, plan=plan, rubrics=rubrics)


def test_leaking_text_stops_the_run_instead_of_being_redacted(toy):
    plan = _plan(toy)
    rubrics = toy_rubrics(plan, "final")
    rubrics["TQ-V1"]["rubric"]["title"] = "Rubric for TQ-V1"
    with pytest.raises(GoldToolError, match="dataset id or tier name"):
        _build(toy, plan=plan, rubrics=rubrics)
    leaky = build_toy_dataset(toy.parent / "leaky")
    text = (leaky / "02_controlled_answers_eligible.csv").read_text(encoding="utf-8").replace("point 00", "this is a MISCONCEPTION", 1)
    (leaky / "02_controlled_answers_eligible.csv").write_text(text, encoding="utf-8")
    p2 = sampling.plan(leaky, seed="s", pilot_seed="p")
    with pytest.raises(GoldToolError, match="dataset id or tier name"):
        sheets.build_sheets(leaky, p2, "final", toy_rubrics(p2, "final"), MARKERS, SALT, "toy_fixture")


@pytest.mark.parametrize("pseudonym", ["TQ-V1", "marker-TA-V1-FULL", "FULL", "full", "MISCONCEPTION", "TQ-R1"])
def test_marker_pseudonyms_cannot_carry_a_dataset_id_or_tier_name(toy, pseudonym):
    with pytest.raises(GoldToolError, match="pseudonym"):
        _build(toy, markers=["m1", pseudonym])


def test_another_answers_id_inside_an_answer_text_is_caught(toy):
    # an answer id without any tier word in it, so that only the answer-id scan can catch it
    text = (toy / "02_controlled_answers_eligible.csv").read_text(encoding="utf-8").replace("TA-V2-FULL", "TA-V2-X1")
    text = text.replace("point 00", "see TA-V2-X1", 1)
    (toy / "02_controlled_answers_eligible.csv").write_text(text, encoding="utf-8")
    plan = sampling.plan(toy, seed="s", pilot_seed="p")
    with pytest.raises(GoldToolError, match="dataset id or tier name"):
        sheets.build_sheets(toy, plan, "final", toy_rubrics(plan, "final"), MARKERS, SALT, "toy_fixture")


def test_a_leak_in_a_rubric_text_is_caught_in_any_field(toy):
    plan = _plan(toy)
    for edit in (lambda r: r["rubric"]["criteria"][0]["scoring_levels"][1].update(descriptor="Shows some of TQ-T1's ideas clearly."),
                 lambda r: r["rubric"]["criteria"][0].update(required_concepts=["PARTIAL idea", "second idea"]),
                 lambda r: r["rubric"]["criteria"][0]["scoring_levels"][0].update(label="Nothing (TA-V1-FULL)")):
        rubrics = toy_rubrics(plan, "final")
        edit(rubrics["TQ-V2"])
        with pytest.raises(GoldToolError, match="dataset id or tier name"):
            _build(toy, plan=plan, rubrics=rubrics)


def test_no_items_means_no_sheet(toy):
    import csv

    path = toy / "02_controlled_answers_eligible.csv"
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8", newline="")) if r["template_negative_control"] == "True"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    plan = sampling.plan(toy, seed="s", pilot_seed="p")
    with pytest.raises(GoldToolError, match="no answers left"):
        sheets.build_sheets(toy, plan, "final", toy_rubrics(plan, "final"), MARKERS, SALT, "toy_fixture")


def test_a_plan_for_another_manifest_is_refused(toy):
    plan = _plan(toy)
    plan["dataset"]["manifest_sha256"] = "0" * 64
    with pytest.raises(GoldToolError, match="different dataset manifest"):
        _build(toy, plan=plan)


# ---------------------------------------------------------------------------------- writing and the seal
def test_outputs_are_written_separately_and_the_seal_detects_tampering(toy, tmp_path):
    r = _build(toy)
    out, custody = tmp_path / "out" / "sheets", tmp_path / "out_custody"
    seal = sheets.write_outputs(r, out, custody)
    assert sorted(p.name for p in out.iterdir()) == sorted(
        [f"sheet_{m}.json" for m in MARKERS] + [f"return_template_{m}.json" for m in MARKERS])
    assert sorted(p.name for p in custody.iterdir()) == ["answer_key.json", "plan.json", "seal_pre_marking.json"]
    assert sheets.verify_seal(seal, out, custody) == []
    (out / "sheet_m1.json").write_bytes((out / "sheet_m1.json").read_bytes() + b" ")
    assert sheets.verify_seal(seal, out, custody) == ["sheet_m1.json"]
    (custody / "answer_key.json").unlink()
    assert "answer_key.json" in sheets.verify_seal(seal, out, custody)


def test_unsafe_output_locations_are_refused(toy, tmp_path):
    r = _build(toy)
    same = tmp_path / "same"
    for a, b in ((same, same), (tmp_path / "a", tmp_path / "a" / "b"), (tmp_path / "c" / "d", tmp_path / "c")):
        with pytest.raises(GoldToolError, match="separate and not nested"):
            sheets.write_outputs(r, a, b)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "existing.txt").write_text("keep me", encoding="utf-8")
    for first, second in ((busy, tmp_path / "fresh"), (tmp_path / "fresh2", busy)):
        with pytest.raises(GoldToolError, match="not an empty directory"):
            sheets.write_outputs(r, first, second)
        assert not (tmp_path / "fresh").exists() and not (tmp_path / "fresh2").exists()  # a refusal leaves nothing behind
    assert (busy / "existing.txt").read_text(encoding="utf-8") == "keep me"
    a_file = tmp_path / "a_file"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(GoldToolError, match="not an empty directory"):
        sheets.write_outputs(r, a_file, tmp_path / "fresh3")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    with pytest.raises(GoldToolError, match="git working tree"):
        sheets.write_outputs(r, repo / "sheets", tmp_path / "elsewhere")
    assert not (repo / "sheets").exists()


def test_the_command_line_cannot_make_real_sheets_without_validated_rubrics(toy, tmp_path, capsys):
    plan_path, salt_path = tmp_path / "plan.json", tmp_path / "salt.txt"
    plan_path.write_text(json.dumps(_plan(toy)), encoding="utf-8")
    salt_path.write_text(SALT, encoding="utf-8")
    rubrics = tmp_path / "rubrics"
    rubrics.mkdir()
    base = [str(toy), "--plan", str(plan_path), "--group", "final", "--origin", "gold", "--rubrics-dir", str(rubrics), "--markers", "m1,m2",
            "--salt-file", str(salt_path), "--sheets-dir", str(tmp_path / "s"), "--custody-dir", str(tmp_path / "c")]
    assert sheets.main(base) == 1 and "missing rubric document" in capsys.readouterr().err
    for q in _plan(toy)["final"]["questions"]:
        (rubrics / f"{q['question_id']}.json").write_text(json.dumps(toy_rubric(q["question_id"], q["marks"], "ai_drafted")), encoding="utf-8")
    assert sheets.main(base) == 1 and "lecturer_validated" in capsys.readouterr().err
    assert not (tmp_path / "s").exists() and not (tmp_path / "c").exists()
    validated = {}
    for q in _plan(toy)["final"]["questions"]:
        validated[q["question_id"]] = toy_rubric(q["question_id"], q["marks"], "lecturer_validated")
        (rubrics / f"{q['question_id']}.json").write_text(json.dumps(validated[q["question_id"]]), encoding="utf-8")
    assert sheets.main(base) == 1 and "approval-register entry" in capsys.readouterr().err  # validated, but no approval record
    assert not (tmp_path / "s").exists()
    approvals = tmp_path / "approvals.json"
    approvals.write_text(json.dumps(toy_approvals(validated)), encoding="utf-8")
    assert sheets.main([*base, "--approvals", str(approvals)]) == 0 and (tmp_path / "c" / "answer_key.json").exists()
