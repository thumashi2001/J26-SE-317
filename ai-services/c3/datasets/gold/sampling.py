"""Deterministic selection of the final evaluation questions and a separate pilot, as question ids only.

Usage: python -m datasets.gold.sampling <dataset dir> --seed S --pilot-seed P [--final-size N] [--pilot-size 4]

- Final pool: the eligible questions of the validation and test splits (never the training split).
- Pilot pool: eligible questions of the training split only, so the pilot and the final set are disjoint by construction and the
  pilot never enters the held-out evaluation. Pilot material may be used to refine rubrics and the marking procedure.
- A request larger than the pool is refused; the dataset is never changed to make a sample fit.
- The plan lists question ids, splits, modules and question marks, and counts of answers. It contains no answers, tiers or
  answer marks. Seeds must be chosen and written down before any model output is looked at.
Read-only.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from datasets.gold.common import GoldToolError, sha256_file

FINAL_SPLITS = ("validation", "test")
PILOT_SPLITS = ("train",)
RULE = ("Questions are grouped by module; within a module they are ordered by sha256('<seed>|<question_id>'); modules are "
        "visited alphabetically, one question at a time, until the requested size is reached; the result is sorted by "
        "question_id. When the whole pool is requested the seed does not change the selection.")


def _read(path: Path) -> list[dict[str, str]]:
    """Read a CSV file as a list of dictionaries (one per row, all values text)."""
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def eligible_questions(dataset_dir: Path) -> list[dict]:
    """Eligible questions that have answers, with the fields the plan needs (no answer-level data)."""
    d = Path(dataset_dir)
    with_answers = {r["question_id"] for r in _read(d / "02_controlled_answers_eligible.csv")}
    return [{"question_id": r["question_id"], "split": r["split"], "module_code": r["module_code"], "marks": r["marks"]}
            for r in _read(d / "01_question_bank.csv")
            if r["eligibility_status"] == "eligible" and r["question_id"] in with_answers]


def select(pool: list[dict], size: int, seed: object) -> list[dict]:
    """Deterministic selection of `size` questions from the pool using a seed."""
    if size < 0 or size > len(pool):
        raise GoldToolError(f"cannot select {size} questions from a pool of {len(pool)}; the dataset is not changed to fit a sample")
    by_module: dict[str, list[dict]] = defaultdict(list)
    for q in pool:
        by_module[q["module_code"]].append(q)
    for items in by_module.values():
        items.sort(key=lambda q: hashlib.sha256(f"{seed}|{q['question_id']}".encode()).hexdigest())
    chosen: list[dict] = []
    while len(chosen) < size:
        for module in sorted(by_module):
            if by_module[module] and len(chosen) < size:
                chosen.append(by_module[module].pop(0))
    return sorted(chosen, key=lambda q: q["question_id"])


def _answer_counts(dataset_dir: Path, question_ids: set[str]) -> dict:
    """Answer and control counts for the selected questions."""
    rows = [r for r in _read(Path(dataset_dir) / "02_controlled_answers_eligible.csv") if r["question_id"] in question_ids]
    controls = sum(1 for r in rows if r["template_negative_control"] == "True")
    return {"answers": len(rows), "template_controls_excluded_from_marking": controls, "answers_to_mark": len(rows) - controls}


def plan(dataset_dir: Path, *, seed: object, pilot_seed: object, final_size: int | None = None, pilot_size: int = 4) -> dict:
    """Plan the final and pilot question samples for human marking."""
    d = Path(dataset_dir)
    pool = eligible_questions(d)
    final_pool = [q for q in pool if q["split"] in FINAL_SPLITS]
    pilot_pool = [q for q in pool if q["split"] in PILOT_SPLITS]
    if not final_pool or not pilot_pool:
        raise GoldToolError("the dataset has no eligible questions in the validation/test splits or in the training split")
    final = select(final_pool, len(final_pool) if final_size is None else final_size, seed)
    pilot = select(pilot_pool, pilot_size, pilot_seed)
    if {q["question_id"] for q in final} & {q["question_id"] for q in pilot}:
        raise GoldToolError("pilot and final selections overlap")
    return {
        "plan_version": 1,
        "contains": "question ids, splits, modules, question marks and answer counts only; no answers, tiers or answer marks",
        "dataset": {"name": d.name, "manifest_sha256": sha256_file(d / "manifest.json"),
                    "eligible_questions_in_final_pool": len(final_pool), "eligible_questions_in_pilot_pool": len(pilot_pool)},
        "rule": RULE,
        "seeds": {"final": str(seed), "pilot": str(pilot_seed)},
        "final": {"source_splits": list(FINAL_SPLITS), "n": len(final), "questions": final,
                  **_answer_counts(d, {q["question_id"] for q in final})},
        "pilot": {"source_splits": list(PILOT_SPLITS), "n": len(pilot), "questions": pilot,
                  **_answer_counts(d, {q["question_id"] for q in pilot}),
                  "use": "refining rubrics and the marking procedure; never part of the held-out evaluation"},
        "exclusion_rule": "answers with template_negative_control == 'True' (the constant-string IRRELEVANT controls) are not marked "
                          "by humans; they stay in the dataset and are reported separately",
    }


def validate_plan(dataset_dir: Path, plan_doc: dict) -> None:
    """Re-check a plan file against the dataset, because a plan is a file that anyone could have edited.

    Every question must be an eligible question of this dataset, final questions must be in the validation/test splits and
    pilot questions in the training split, no question may appear twice (so the groups are disjoint), and the recorded splits
    and marks must be the dataset's own. Raises GoldToolError; nothing is repaired.
    """
    d = Path(dataset_dir)
    if plan_doc["dataset"]["manifest_sha256"] != sha256_file(d / "manifest.json"):
        raise GoldToolError("the plan was made for a different dataset manifest")
    pool = {q["question_id"]: q for q in eligible_questions(d)}
    seen: set[str] = set()
    for group, splits in (("final", FINAL_SPLITS), ("pilot", PILOT_SPLITS)):
        questions = plan_doc[group]["questions"]
        if not questions:
            raise GoldToolError(f"the plan's {group} group is empty")
        for q in questions:
            qid, real = q["question_id"], pool.get(q["question_id"])
            if real is None:
                raise GoldToolError(f"{qid} in the plan is not an eligible question of this dataset")
            if qid in seen:
                raise GoldToolError(f"{qid} appears more than once in the plan; the final and pilot groups must be disjoint")
            seen.add(qid)
            if real["split"] not in splits:
                raise GoldToolError(f"{qid} is a {real['split']} question and cannot be in the {group} group")
            if (q.get("split"), str(q.get("marks"))) != (real["split"], real["marks"]):
                raise GoldToolError(f"{qid}: the plan's split or marks differ from the dataset")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Select final and pilot question ids deterministically")
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--pilot-seed", required=True)
    ap.add_argument("--final-size", type=int, default=None, help="default: every eligible validation/test question")
    ap.add_argument("--pilot-size", type=int, default=4)
    args = ap.parse_args(argv)
    try:
        doc = plan(args.dataset, seed=args.seed, pilot_seed=args.pilot_seed, final_size=args.final_size, pilot_size=args.pilot_size)
    except GoldToolError as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 1
    print(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
