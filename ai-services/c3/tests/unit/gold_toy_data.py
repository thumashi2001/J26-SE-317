"""Toy material for the gold-tooling tests. Everything here is invented, tiny and simulated.

Nothing built here is a real rubric, a real answer or a human mark; sheets made from it carry origin 'toy_fixture'.
"""

import copy
import csv
import hashlib
import json
from pathlib import Path

from datasets.gold.returns import sheet_sha256

TIERS = ("FULL", "MOSTLY_CORRECT", "PARTIAL", "MISSING_CONCEPT", "MISCONCEPTION")
SALT = "toy-salt-0123456789abcdef"
MARKERS = ["m1", "m2"]
# question id, split, module, marks
QUESTIONS = [("TQ-V1", "validation", "SE1", "10"), ("TQ-V2", "validation", "SE2", "10"), ("TQ-T1", "test", "SE1", "20"),
             ("TQ-T2", "test", "SE3", "10"),
             ("TQ-R1", "train", "SE1", "10"), ("TQ-R2", "train", "SE1", "10"), ("TQ-R3", "train", "SE2", "10"),
             ("TQ-R4", "train", "SE2", "10"), ("TQ-R5", "train", "SE3", "10"), ("TQ-R6", "train", "SE3", "10"),
             ("TQ-X1", "train", "SE3", "10")]  # TQ-X1 is not eligible
WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda sigma omega".split()


def _write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build_toy_dataset(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    bank, answers = [], []
    for n, (qid, split, module, marks) in enumerate(QUESTIONS):
        eligible = qid != "TQ-X1"
        bank.append({"question_id": qid, "module_code": module, "marks": marks, "split": split,
                     "eligibility_status": "eligible" if eligible else "quarantined_v2",
                     "question_text": f"Explain {WORDS[n % 13]} in the setting of {WORDS[(n + 3) % 13]} systems."})
        if not eligible:
            continue
        for t, tier in enumerate((*TIERS, "IRRELEVANT")):
            control = tier == "IRRELEVANT"
            answers.append({"question_id": qid, "answer_id": f"TA-{qid[3:]}-{tier}", "answer_quality": tier, "split": split,
                            "template_negative_control": str(control), "expected_mark": "0" if control else marks, "max_marks": marks,
                            "student_answer": "unrelated constant text" if control else
                            " ".join(WORDS[(n + t + j) % 13] for j in range(6 + 3 * (5 - t))) + f" point {n}{t}"})
    _write(root / "01_question_bank.csv", bank)
    _write(root / "02_controlled_answers_eligible.csv", answers)
    _write(root / "03_rubric_criteria.csv", [{"question_id": q[0], "criterion_id": f"{q[0]}-C01"} for q in QUESTIONS])
    files = {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
             for n in ("01_question_bank.csv", "02_controlled_answers_eligible.csv", "03_rubric_criteria.csv")}
    (root / "manifest.json").write_text(json.dumps({"dataset_version": "toy-v2", "row_dataset_version": "toy-rows",
                                                    "source_dataset_version": "toy-source", "files": files}), encoding="utf-8")
    (root / "validation_report.json").write_text(json.dumps({"overall": "FAIL", "hard_failures": ["ratio_concentration"], "checks": [
        {"name": "ratio_concentration", "status": "fail", "details": {"value": 0.7, "threshold": 0.45}}]}), encoding="utf-8")
    return root


def toy_rubric(qid: str, marks: str, status: str = "ai_drafted") -> dict:
    total = float(marks)
    prov = {"status": status, "drafted_by": "toy-drafter", "drafted_on": "2026-10-01", "validated_by": "", "validated_on": "",
            "validation_notes": ""}
    if status == "lecturer_validated":
        prov.update(validated_by="toy-lecturer", validated_on="2026-10-03")
    levels = [
        {"level_id": "L0", "label": "None", "mark": 0, "descriptor": "The answer shows none of the expected ideas."},
        {"level_id": "L1", "label": "Some", "mark": total / 2, "descriptor": "The answer shows some of the expected ideas.",
         "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 1}},
        {"level_id": "L2", "label": "All", "mark": total, "descriptor": "The answer shows all of the expected ideas clearly.",
         "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 2}}]
    return {"format": "c3-gold-rubric/1", "question_id": qid, "provenance": prov,
            "rubric": {"rubric_id": f"R-{qid}", "title": "Toy rubric", "criteria": [{
                "criterion_id": f"CRIT-{qid}-1", "description": "Toy criterion", "max_marks": total,
                "required_concepts": ["first idea", "second idea"], "scoring_levels": levels}]}}


def toy_rubrics(plan_doc: dict, group: str, status: str = "ai_drafted") -> dict:
    return {q["question_id"]: toy_rubric(q["question_id"], q["marks"], status) for q in plan_doc[group]["questions"]}


def toy_approvals(rubrics: dict, approved_on: str = "2026-10-06") -> dict:
    """A simulated approval register whose entries match the given rubric documents exactly."""
    from datasets.gold.approval import FORMAT, rubric_sha256

    return {"format": FORMAT, "entries": [
        {"question_id": qid, "rubric_sha256": rubric_sha256(doc), "approved_on": approved_on, "approver_role": "lecturer",
         "evidence_ref": f"toy-evidence-{n}", "recorded_by": "toy-custodian"} for n, (qid, doc) in enumerate(sorted(rubrics.items()), 1)]}


def fill_return(sheet: dict, chooser) -> dict:
    """A simulated marker return: chooser(index, item, criterion, level_ids_ascending_by_mark) -> level id."""
    template_levels = {}
    for ref, rubric in sheet["rubrics"].items():
        template_levels[ref] = {c["criterion"]: [lv["level"] for lv in sorted(c["levels"], key=lambda x: x["mark"])]
                                for c in rubric["criteria"]}
    returns = []
    for idx, item in enumerate(sheet["items"]):
        crit = template_levels[item["rubric_ref"]]
        returns.append({"item_id": item["item_id"], "cannot_mark": False, "reason": "", "comment": "",
                        "levels": {c: chooser(idx, item, c, ids) for c, ids in crit.items()}})
    return {"sheet_sha256": sheet_sha256(sheet), "origin": sheet["origin"], "marker": sheet["marker"], "returns": returns}


def by_item_hash(item_id: str, ids: list[str]) -> str:
    """Deterministic pseudo-choice that depends only on the item, so two markers can agree exactly."""
    return ids[int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % len(ids)]


def disagree_on_some(base_return: dict, sheet: dict, every: int = 3) -> dict:
    """A second simulated marker that moves every `every`-th item (in item-id order) to a different level."""
    other = copy.deepcopy(base_return)
    other["marker"] = sheet["marker"]
    other["sheet_sha256"] = sheet_sha256(sheet)
    allowed = {ref: {c["criterion"]: sorted(c["levels"], key=lambda x: x["mark"]) for c in r["criteria"]}
               for ref, r in sheet["rubrics"].items()}
    ref_of = {i["item_id"]: i["rubric_ref"] for i in sheet["items"]}
    for n, e in enumerate(sorted(other["returns"], key=lambda x: x["item_id"])):
        if n % every == 0:
            for crit, level in e["levels"].items():
                ids = [lv["level"] for lv in allowed[ref_of[e["item_id"]]][crit]]
                e["levels"][crit] = ids[(ids.index(level) + 1) % len(ids)]
    return other
