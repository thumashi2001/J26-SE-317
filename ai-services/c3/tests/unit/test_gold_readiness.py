"""Milestone 2d: approval register, post-marking seal and the human-validation readiness audit.

Fixtures are toy and simulated. A passing test shows that the records and guards behave as described; it does not show that any
lecturer approved anything, that anyone marked anything, or that the software is operationally secure.
"""

import copy
import csv
import hashlib
import json
import re
from pathlib import Path

import pytest
from gold_toy_data import (
    MARKERS,
    SALT,
    build_toy_dataset,
    by_item_hash,
    fill_return,
    toy_approvals,
    toy_rubric,
    toy_rubrics,
)

from datasets.gold import approval, readiness, sampling, seal, sheets
from datasets.gold.common import SIMULATED_NOTICE, GoldToolError, canonical_bytes

GOLD = Path(__file__).resolve().parents[2] / "datasets" / "gold"
V2_DIR = Path(__file__).resolve().parents[2] / "datasets" / "c3_phase3_v5_repaired_v2"
REPORT = Path(__file__).resolve().parents[4] / "reports" / "c3_remediation" / "25_human_validation_readiness.md"
HELD_OUT = ["TQ-T1", "TQ-T2", "TQ-V1", "TQ-V2"]  # the toy dataset's eligible validation/test questions


@pytest.fixture()
def toy(tmp_path):
    return build_toy_dataset(tmp_path / "data")


def put(directory: Path, qid: str, doc) -> None:
    directory.mkdir(exist_ok=True)
    (directory / f"{qid}.json").write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")


def marks(toy_dir):
    with open(toy_dir / "01_question_bank.csv", encoding="utf-8", newline="") as f:
        return {r["question_id"]: r["marks"] for r in csv.DictReader(f)}


def digest_tree(*roots: Path) -> dict:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for r in roots if r.exists() for p in sorted(r.rglob("*")) if p.is_file()}


def validated_set(toy_dir, status="lecturer_validated"):
    m = marks(toy_dir)
    return {q: toy_rubric(q, m[q], status) for q in HELD_OUT}


# ------------------------------------------------------------------------------------------ approval register
def test_rubric_hash_covers_marking_content_but_not_the_provenance_block():
    doc = toy_rubric("TQ-V1", "10", "lecturer_validated")
    base = approval.rubric_sha256(doc)
    assert base == approval.rubric_sha256(copy.deepcopy(doc))
    other = copy.deepcopy(doc)
    other["provenance"]["validated_on"] = "2026-12-01"
    assert approval.rubric_sha256(other) == base
    changed = copy.deepcopy(doc)
    changed["rubric"]["criteria"][0]["scoring_levels"][1]["descriptor"] = "A different descriptor that changes what the level means."
    assert approval.rubric_sha256(changed) != base


def _register(**entry_overrides):
    reg = toy_approvals({"TQ-V1": toy_rubric("TQ-V1", "10", "lecturer_validated")})
    reg["entries"][0].update(entry_overrides)
    return reg


def test_a_well_formed_register_has_no_problems():
    assert approval.register_problems(_register()) == []
    assert approval.register_problems({"format": approval.FORMAT, "entries": []}) == []


@pytest.mark.parametrize("edit, fragment", [
    (lambda r: r.update(format="other"), "format must be"),
    (lambda r: r.update(entries="nope"), "entries must be a list"),
    (lambda r: r["entries"].append("x"), "must be an object"),
    (lambda r: r["entries"][0].update(approver_name="A Person"), "unexpected field"),
    (lambda r: r["entries"][0].update(email="a@b.c"), "no names or other personal data"),
    (lambda r: r["entries"].append(copy.deepcopy(r["entries"][0])), "more than one entry"),
    (lambda r: r["entries"][0].update(question_id=" "), "question_id is required"),
    (lambda r: r["entries"][0].update(rubric_sha256="abc"), "64 lowercase hex"),
    (lambda r: r["entries"][0].update(rubric_sha256="A" * 64), "64 lowercase hex"),
    (lambda r: r["entries"][0].update(approved_on="06/10/2026"), "approved_on must be an ISO date"),
    (lambda r: r["entries"][0].update(approver_role="student"), "approver_role must be"),
    (lambda r: r["entries"][0].update(evidence_ref=""), "evidence_ref is required"),
    (lambda r: r["entries"][0].update(evidence_ref="<FILL IN: ticket>"), "evidence_ref is required"),
    (lambda r: r["entries"][0].pop("recorded_by"), "recorded_by is required"),
])
def test_malformed_registers_are_reported(edit, fragment):
    reg = _register()
    edit(reg)
    assert any(fragment in p for p in approval.register_problems(reg))
    assert approval.register_problems([]) == ["register must be a JSON object"]


def test_approval_states_cover_every_way_the_record_can_fail():
    doc = toy_rubric("TQ-V1", "10", "lecturer_validated")
    reg = toy_approvals({"TQ-V1": doc})
    assert approval.approval_state(None, doc) == "no_register"
    assert approval.approval_state({"format": "x", "entries": []}, doc) == "register_invalid"
    assert approval.approval_state({"format": approval.FORMAT, "entries": []}, doc) == "no_entry"
    assert approval.approval_state(reg, doc) == "matches"
    edited = copy.deepcopy(doc)
    edited["rubric"]["title"] = "Edited after approval"
    assert approval.approval_state(reg, edited) == "stale"
    early = toy_approvals({"TQ-V1": doc}, approved_on="2026-09-01")  # before the document was drafted and validated
    assert approval.approval_state(early, doc) == "date_inconsistent"
    before_validation = toy_approvals({"TQ-V1": doc}, approved_on="2026-10-02")  # after drafting, before validated_on (2026-10-03)
    assert approval.approval_state(before_validation, doc) == "date_inconsistent"


def test_the_authentication_limit_is_stated_in_the_module_and_not_hidden():
    assert "cannot authenticate" in approval.AUTHENTICATION_LIMIT and "not a proof" in approval.AUTHENTICATION_LIMIT


# --------------------------------------------------------------------- gold gate with the approval register
def _gold(toy_dir, rubrics, approvals):
    plan = sampling.plan(toy_dir, seed="s", pilot_seed="p")
    return sheets.build_sheets(toy_dir, plan, "final", rubrics, MARKERS, SALT, "gold", approvals)


@pytest.mark.parametrize("make_approvals, state", [
    (lambda rubrics: None, "no_register"),
    (lambda rubrics: {"format": "bad", "entries": []}, "register_invalid"),
    (lambda rubrics: {"format": approval.FORMAT, "entries": toy_approvals(rubrics)["entries"][1:]}, "no_entry"),
    (lambda rubrics: toy_approvals(rubrics, approved_on="2026-09-01"), "date_inconsistent"),
])
def test_gold_sheets_are_refused_without_a_matching_approval_record(toy, make_approvals, state):
    rubrics = validated_set(toy)
    with pytest.raises(GoldToolError, match=f"approval-register entry.*{state}"):
        _gold(toy, rubrics, make_approvals(rubrics))


def test_a_rubric_edited_after_approval_is_refused_for_gold(toy):
    rubrics = validated_set(toy)
    reg = toy_approvals(rubrics)
    rubrics["TQ-V2"]["rubric"]["criteria"][0]["scoring_levels"][1]["descriptor"] = "Edited later so the approved text no longer applies."
    with pytest.raises(GoldToolError, match="TQ-V2: stale"):
        _gold(toy, rubrics, reg)


def test_matching_records_allow_gold_and_the_key_records_the_rubric_versions(toy):
    rubrics = validated_set(toy)
    built = _gold(toy, rubrics, toy_approvals(rubrics))
    refs = built["key"]["rubric_refs"]
    assert len(refs) == 4
    for entry in refs.values():
        doc = rubrics[entry["question_id"]]
        assert entry["rubric_sha256"] == approval.rubric_sha256(doc)
        assert entry["document_sha256"] == hashlib.sha256(canonical_bytes(doc)).hexdigest() and entry["approval_state"] == "matches"
    assert built["seal"]["files"]["answer_key.json"] == hashlib.sha256(canonical_bytes(built["key"])).hexdigest()


def test_pilot_sheets_record_the_state_but_do_not_need_an_approval(toy):
    plan = sampling.plan(toy, seed="s", pilot_seed="p")
    built = sheets.build_sheets(toy, plan, "pilot", toy_rubrics(plan, "pilot", "ai_drafted"), MARKERS, SALT, "pilot")
    assert {e["approval_state"] for e in built["key"]["rubric_refs"].values()} == {"no_register"}


# --------------------------------------------------------------------------------------- post-marking seal
@pytest.fixture()
def marked(toy):
    plan = sampling.plan(toy, seed="s", pilot_seed="p")
    built = sheets.build_sheets(toy, plan, "final", toy_rubrics(plan, "final"), MARKERS, SALT, "toy_fixture")
    rets = {m: fill_return(built["sheets"][m], lambda i, item, c, ids: by_item_hash(item["item_id"], ids)) for m in MARKERS}
    files = {f"return_{m}.json": canonical_bytes(rets[m]) for m in MARKERS}
    files["adjudication.json"] = canonical_bytes({"adjudicator": "adj1", "decisions": []})
    files["final_labels.json"] = canonical_bytes({"simulated": True, "labels": {}})
    return {"built": built, "rets": rets, "files": files}


def test_post_marking_seal_chains_to_the_pre_marking_seal_and_detects_tampering(marked, tmp_path):
    post = seal.post_marking_seal(marked["built"]["seal"], marked["files"])
    assert post["stage"] == "post_marking" and post["pre_marking_seal_sha256"] == marked["built"]["seal"]["seal_sha256"]
    assert post["notice"] == SIMULATED_NOTICE and post["origin"] == "toy_fixture"
    folder = tmp_path / "sealed"
    folder.mkdir()
    for name, data in marked["files"].items():
        (folder / name).write_bytes(data)
    assert seal.verify_post_marking_seal(post, folder, marked["built"]["seal"]) == []
    (folder / "final_labels.json").write_bytes(marked["files"]["final_labels.json"] + b" ")
    assert seal.verify_post_marking_seal(post, folder) == ["final_labels.json"]
    (folder / "adjudication.json").unlink()
    assert "adjudication.json" in seal.verify_post_marking_seal(post, folder)
    other_pre = {**marked["built"]["seal"], "seal_sha256": "0" * 64}
    assert "pre_marking_seal_sha256" in seal.verify_post_marking_seal(post, folder, other_pre)


def test_post_marking_seal_refuses_returns_that_do_not_belong_to_the_sealed_sheets(marked):
    pre = marked["built"]["seal"]

    def attempt(edit):
        files = dict(marked["files"])
        ret = copy.deepcopy(marked["rets"]["m1"])
        edit(ret)
        files["return_m1.json"] = canonical_bytes(ret)
        return seal.post_marking_seal(pre, files)

    for edit in (lambda r: r.update(sheet_sha256="0" * 64), lambda r: r.update(marker="m2"), lambda r: r.update(origin="gold")):
        with pytest.raises(GoldToolError, match="does not belong to the sealed sheet"):
            attempt(edit)
    files = dict(marked["files"])
    files["return_m1.json"] = b"{broken"
    with pytest.raises(GoldToolError, match="not valid JSON"):
        seal.post_marking_seal(pre, files)


def test_post_marking_seal_needs_every_required_file_and_a_pre_marking_seal(marked):
    pre = marked["built"]["seal"]
    for name in ("adjudication.json", "final_labels.json"):
        files = {k: v for k, v in marked["files"].items() if k != name}
        with pytest.raises(GoldToolError, match="missing file"):
            seal.post_marking_seal(pre, files)
    with pytest.raises(GoldToolError, match="at least two marker return files"):
        seal.post_marking_seal(pre, {k: v for k, v in marked["files"].items() if k != "return_m2.json"})
    with pytest.raises(GoldToolError, match="on a pre-marking seal"):
        seal.post_marking_seal({**pre, "stage": "post_marking"}, marked["files"])


# ------------------------------------------------------------------------------------------ readiness audit
def test_with_no_rubric_directory_every_question_is_missing_and_nothing_is_ready(toy):
    a = readiness.audit(toy)
    assert a["questions"]["held_out_pool"] == 4 and a["questions"]["pilot_pool_training_split"] == 6
    assert a["rubrics"]["missing"] == 4 and a["readiness"] == {**a["readiness"], "ready_for_gold_sheets": 0, "of": 4, "all_ready": False}
    assert a["inputs"]["rubric_directory_found"] is False
    assert any("No rubric directory" in b for b in a["blockers"]) and "No lecturer validation is documented" in a["human_validation"]["statement"]
    assert a["human_validation"]["marker_returns_read"] is False and a["human_validation"]["agreement_results_read"] is False


def _mixed(toy_dir, rdir):
    put(rdir, "TQ-T1", toy_rubric("TQ-T1", "12", "ai_drafted"))  # marks do not match the question (20)
    put(rdir, "TQ-T2", "{not json")
    put(rdir, "TQ-V1", toy_rubric("TQ-V1", "10", "ai_drafted"))
    v2 = toy_rubric("TQ-V2", "10", "lecturer_validated")
    put(rdir, "TQ-V2", v2)
    return v2


def test_each_rubric_state_is_counted_separately(toy, tmp_path):
    rdir, reg = tmp_path / "rubrics", tmp_path / "approvals.json"
    v2 = _mixed(toy, rdir)
    reg.write_text(json.dumps(toy_approvals({"TQ-V2": v2})), encoding="utf-8")
    a = readiness.audit(toy, rdir, reg)
    assert (a["rubrics"]["missing"], a["rubrics"]["unreadable"], a["rubrics"]["invalid"]) == (0, 1, 1)
    assert (a["rubrics"]["structurally_valid"], a["rubrics"]["structurally_valid_ai_drafted"]) == (2, 1)
    assert (a["rubrics"]["documented_lecturer_validation"], a["rubrics"]["with_matching_approval_record"]) == (1, 1)
    assert a["readiness"]["ready_for_gold_sheets"] == 1 and a["readiness"]["proportion"] == 0.25 and not a["readiness"]["all_ready"]
    statement = a["human_validation"]["statement"]  # with one claim present the statement must say so, and must not call it proven
    assert "1 held-out rubric(s) carry a lecturer-validation claim" in statement and "none is authenticated" in statement
    assert "No lecturer validation is documented" not in statement
    assert "no genuine human marking" in a["human_validation"]["scope"]
    by_q = {r["question_id"]: r for r in a["per_question"]}
    assert by_q["TQ-T1"]["rubric_state"] == "invalid" and by_q["TQ-T1"]["first_problems"] and not by_q["TQ-T1"]["ready_for_gold"]
    assert by_q["TQ-T2"]["rubric_state"] == "unreadable"
    assert by_q["TQ-V1"]["rubric_state"] == "structurally_valid_ai_drafted" and not by_q["TQ-V1"]["ready_for_gold"]
    assert by_q["TQ-V2"]["ready_for_gold"] and by_q["TQ-V2"]["approval_state"] == "matches"
    assert any("AI-drafted rubric that still needs lecturer review" in b for b in a["blockers"])


def test_a_validation_claim_without_a_usable_approval_record_is_not_ready(toy, tmp_path):
    rdir = tmp_path / "rubrics"
    v2 = _mixed(toy, rdir)
    for register, state in ((None, "no_register"), ({"format": "bad", "entries": []}, "register_invalid"),
                            ({"format": approval.FORMAT, "entries": []}, "no_entry")):
        path = None
        if register is not None:
            path = tmp_path / "reg.json"
            path.write_text(json.dumps(register), encoding="utf-8")
        a = readiness.audit(toy, rdir, path)
        row = next(r for r in a["per_question"] if r["question_id"] == "TQ-V2")
        assert row["approval_state"] == state and not row["ready_for_gold"] and a["readiness"]["ready_for_gold_sheets"] == 0
        assert a["rubrics"]["approval_not_backed_by_a_record"][state] == 1
    stale = toy_approvals({"TQ-V2": v2})
    stale["entries"][0]["rubric_sha256"] = "0" * 64
    (tmp_path / "reg.json").write_text(json.dumps(stale), encoding="utf-8")
    a = readiness.audit(toy, rdir, tmp_path / "reg.json")
    assert next(r for r in a["per_question"] if r["question_id"] == "TQ-V2")["approval_state"] == "stale"
    (tmp_path / "reg.json").write_text("{broken", encoding="utf-8")
    assert readiness.audit(toy, rdir, tmp_path / "reg.json")["inputs"]["approval_register"] == {
        "provided": True, "readable": False, "problems": ["register is not readable JSON"]}


def test_a_malformed_register_is_reported_as_a_blocker(toy, tmp_path):
    rdir = tmp_path / "rubrics"
    v2 = _mixed(toy, rdir)
    reg = toy_approvals({"TQ-V2": v2})
    reg["entries"][0]["approver_name"] = "A Person"
    (tmp_path / "reg.json").write_text(json.dumps(reg), encoding="utf-8")
    a = readiness.audit(toy, rdir, tmp_path / "reg.json")
    assert a["inputs"]["approval_register"]["problems"] and any("approval register has" in b for b in a["blockers"])
    assert a["readiness"]["ready_for_gold_sheets"] == 0


def test_readiness_agrees_with_what_the_sheet_generator_accepts(toy, tmp_path):
    plan = sampling.plan(toy, seed="s", pilot_seed="p")
    rdir = tmp_path / "rubrics"
    rubrics = validated_set(toy)
    for q, doc in rubrics.items():
        put(rdir, q, doc)
    (tmp_path / "reg.json").write_text(json.dumps(toy_approvals(rubrics)), encoding="utf-8")
    a = readiness.audit(toy, rdir, tmp_path / "reg.json")
    assert a["readiness"]["all_ready"] and a["readiness"]["ready_for_gold_sheets"] == 4
    assert sheets.build_sheets(toy, plan, "final", rubrics, MARKERS, SALT, "gold", toy_approvals(rubrics))["key"]["origin"] == "gold"
    # make one rubric stale: the audit stops reporting it ready, and the generator stops accepting it
    rubrics["TQ-T1"]["rubric"]["title"] = "Changed after approval"
    put(rdir, "TQ-T1", rubrics["TQ-T1"])
    a2 = readiness.audit(toy, rdir, tmp_path / "reg.json")
    assert a2["readiness"]["ready_for_gold_sheets"] == 3 and not a2["readiness"]["all_ready"]
    with pytest.raises(GoldToolError, match="TQ-T1: stale"):
        sheets.build_sheets(toy, plan, "final", rubrics, MARKERS, SALT, "gold", toy_approvals(validated_set(toy)))


def test_reports_name_no_reviewer_and_no_local_path(toy, tmp_path):
    rdir = tmp_path / "rubrics"
    v2 = _mixed(toy, rdir)
    (tmp_path / "reg.json").write_text(json.dumps(toy_approvals({"TQ-V2": v2})), encoding="utf-8")
    a = readiness.audit(toy, rdir, tmp_path / "reg.json")
    text = json.dumps(a) + readiness.render_markdown(a)
    for private in ("toy-lecturer", "toy-drafter", "toy-custodian", "toy-evidence", str(tmp_path), str(tmp_path).replace("\\", "/")):
        assert private not in text


def test_the_audit_is_deterministic_and_does_not_change_its_inputs(toy, tmp_path):
    rdir = tmp_path / "rubrics"
    _mixed(toy, rdir)
    before = digest_tree(toy, rdir)
    first, second = readiness.audit(toy, rdir), readiness.audit(toy, rdir)
    assert first == second and readiness.render_markdown(first) == readiness.render_markdown(second)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert digest_tree(toy, rdir) == before


def test_dataset_version_and_hashes_are_traceable_and_a_changed_file_is_flagged(toy):
    a = readiness.audit(toy)
    ds = a["dataset"]
    assert (ds["dataset_version"], ds["row_dataset_version"], ds["source_dataset_version"]) == ("toy-v2", "toy-rows", "toy-source")
    assert ds["manifest_sha256"] == hashlib.sha256((toy / "manifest.json").read_bytes()).hexdigest()
    assert ds["validation_report_sha256"] == hashlib.sha256((toy / "validation_report.json").read_bytes()).hexdigest()
    assert all(f["matches_manifest"] for f in ds["files"].values())
    assert ds["ratio_concentration"] == {"value": 0.7, "threshold": 0.45, "status": "fail"}
    assert any("ratio concentration" in b for b in a["blockers"])
    (toy / "03_rubric_criteria.csv").write_text("question_id,criterion_id\nX,Y\n", encoding="utf-8")
    changed = readiness.audit(toy)
    assert changed["dataset"]["files"]["03_rubric_criteria.csv"]["matches_manifest"] is False
    assert any("no longer matches the hash" in b for b in changed["blockers"])


def test_simulated_inputs_are_marked_and_real_runs_are_not(toy):
    sim = readiness.audit(toy, simulated=True)
    assert sim["simulated"] is True and sim["notice"] == SIMULATED_NOTICE
    assert SIMULATED_NOTICE in readiness.render_markdown(sim)
    real = readiness.audit(toy)
    assert real["simulated"] is False and real["notice"] is None and SIMULATED_NOTICE not in readiness.render_markdown(real)


def test_an_empty_held_out_pool_is_refused(toy):
    with open(toy / "01_question_bank.csv", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "train"]
    with open(toy / "01_question_bank.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(GoldToolError, match="no eligible validation/test questions"):
        readiness.audit(toy)


def test_readiness_cli(toy, tmp_path, capsys):
    assert readiness.main([str(toy)]) == 0
    assert json.loads(capsys.readouterr().out)["readiness"]["of"] == 4
    out = tmp_path / "out.md"
    assert readiness.main([str(toy), "--markdown", str(out)]) == 0 and out.read_text(encoding="utf-8").startswith("# Human-validation readiness")
    assert readiness.main([str(toy), "--markdown", str(out)]) == 1 and "already exists" in capsys.readouterr().err
    assert readiness.main([str(toy), "--json", str(toy / "report.json")]) == 1  # not inside the dataset directory
    assert not (toy / "report.json").exists()
    assert readiness.main([str(toy), "--json", str(tmp_path / "out.json"), "--markdown", "-"]) == 0
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["human_validation"]["marker_returns_read"] is False


# --------------------------------------------------------------------------- the project dataset and report
@pytest.mark.skipif(not (V2_DIR / "manifest.json").exists(), reason="v2 dataset not present")
def test_real_v2_counts_match_the_csv_and_nothing_is_ready():
    a = readiness.audit(V2_DIR)
    with open(V2_DIR / "01_question_bank.csv", encoding="utf-8", newline="") as f:
        bank = [r for r in csv.DictReader(f) if r["eligibility_status"] == "eligible"]
    held_out = [r for r in bank if r["split"] in ("validation", "test")]
    assert a["questions"]["eligible_total"] == len(bank) and a["questions"]["held_out_pool"] == len(held_out)
    assert a["questions"]["pilot_pool_training_split"] == len(bank) - len(held_out)
    report = json.loads((V2_DIR / "validation_report.json").read_text(encoding="utf-8"))
    ratio = next(c for c in report["checks"] if c["name"] == "ratio_concentration")["details"]
    assert a["dataset"]["ratio_concentration"]["value"] == ratio["value"] and a["dataset"]["ratio_concentration"]["status"] == "fail"
    assert a["readiness"]["ready_for_gold_sheets"] == 0 and a["rubrics"]["documented_lecturer_validation"] == 0
    assert "No lecturer validation is documented" in a["human_validation"]["statement"]
    assert all(f["matches_manifest"] for f in a["dataset"]["files"].values()) and a["simulated"] is False


@pytest.mark.skipif(not (V2_DIR / "manifest.json").exists(), reason="v2 dataset not present")
def test_committed_readiness_report_is_what_the_audit_produces_now():
    expected = readiness.render_markdown(readiness.audit(V2_DIR))
    assert REPORT.read_text(encoding="utf-8").replace("\r\n", "\n") == expected


@pytest.mark.skipif(not (V2_DIR / "manifest.json").exists(), reason="v2 dataset not present")
def test_no_gold_sheet_can_be_built_for_the_real_dataset_without_validated_and_approved_rubrics():
    plan = sampling.plan(V2_DIR, seed="readiness-check", pilot_seed="readiness-check")
    drafts = {q["question_id"]: toy_rubric(q["question_id"], q["marks"], "ai_drafted") for q in plan["final"]["questions"]}
    with pytest.raises(GoldToolError):
        sheets.build_sheets(V2_DIR, plan, "final", drafts, MARKERS, SALT, "gold", None)
    with pytest.raises(GoldToolError, match="lecturer_validated"):
        sheets.build_sheets(V2_DIR, plan, "final", drafts, MARKERS, SALT, "gold", toy_approvals(drafts))
    with pytest.raises(GoldToolError, match="no rubric document"):
        sheets.build_sheets(V2_DIR, plan, "final", {}, MARKERS, SALT, "gold", None)


# ----------------------------------------------------------------------------------- checklist and protocol
def test_checklist_covers_every_required_topic_and_claims_nothing_is_done():
    text = (GOLD / "READINESS_CHECKLIST.md").read_text(encoding="utf-8")
    topics = ["Reviewers, markers and adjudicator: qualifications and consent", "Rubric review and approval",
              "Restricted storage and a named custodian", "Distribution of blind marking sheets",
              "Return collection and integrity checks", "Pseudonym management and separation of identifying information",
              "Marking, thresholds, adjudication and unresolved scores", "Ethics, data retention and participant privacy",
              "Post-marking sealing and audit records"]
    for n, topic in enumerate(topics, 1):
        assert f"\n## {n}. {topic}\n" in text, topic
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines()
            if line.startswith("| ") and not re.match(r"^\|[- |]+\|$", line) and "Software safeguard" not in line]
    assert len(rows) >= 25 and all(len(r) == 5 for r in rows)
    assert {r[4] for r in rows} == {"Open"}  # nothing is recorded as done
    assert "Every item is Open" in text and "Not possible in software" in text and "Nothing**: no encryption" in text


def test_protocol_explains_approval_binding_and_what_cannot_be_verified():
    text = (GOLD / "GOLD_PROTOCOL.md").read_text(encoding="utf-8")
    assert "\n## Approval, version binding and evidence\n" in text
    for phrase in ("How a rubric becomes `lecturer_validated`", "Who may approve", "How approval evidence is recorded",
                   "Not verified, and not verifiable by software", "Version binding", "Keeping simulated results",
                   "READINESS_CHECKLIST.md", "`seal.py`", "approval-register entry"):
        assert phrase in text, phrase
    assert "None of these exists yet" in text and "has not been operationally validated" in text
