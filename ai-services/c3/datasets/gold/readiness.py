"""Human-validation readiness audit: which held-out questions could go to genuine gold-sheet generation, and what is still missing.

Usage: python -m datasets.gold.readiness <dataset dir> [--rubrics-dir DIR] [--approvals FILE] [--json PATH|-] [--markdown PATH|-]

Reads the dataset's manifest, question bank and validation report, a directory of gold-rubric documents (<question_id>.json) and
an optional approval register. Every count comes from those files. It uses rubric_check.check_document and usable_as_gold
unchanged, so "valid" means exactly what the sheet generator accepts. It never modifies a rubric, a dataset file or a result,
holds no timestamps (the same inputs give the same bytes), and names no reviewer: reports state whether a validation claim exists,
not who made it.

It reads no marker returns and no agreement results. It therefore cannot show that human marking or agreement exists, and it does
not claim they do. Lecturer validation is whatever the rubric documents and the register say; the software cannot authenticate it
(see approval.AUTHENTICATION_LIMIT).
"""

import argparse
import json
import sys
from pathlib import Path

from datasets.gold.approval import AUTHENTICATION_LIMIT, approval_state, register_problems
from datasets.gold.common import SIMULATED_NOTICE, GoldToolError, sha256_file
from datasets.gold.rubric_check import check_document, usable_as_gold
from datasets.gold.sampling import FINAL_SPLITS, PILOT_SPLITS, eligible_questions

HUMAN_ACTIONS = [
    "Name the lecturers or other qualified reviewers who may approve rubrics, and record their consent (READINESS_CHECKLIST.md, section 1).",
    "Have each held-out question's rubric drafted and then reviewed by a lecturer other than its drafter (section 2).",
    "Appoint a custodian and set up restricted storage for the salt, key, plan and seals (section 3).",
    "Arrange a private channel for sending sheets to markers and receiving returns, and a pseudonym register (sections 4 to 6).",
    "Recruit two independent markers and an adjudicator, with consent (sections 1 and 7).",
    "Obtain whatever institutional ethics or data-governance confirmation applies, and agree retention rules (section 8).",
    "Fix the agreement acceptance thresholds in the study plan before any marking (section 7).",
    "Produce the post-marking seal and audit record after marking (section 9).",
]


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _question_record(question: dict, rubrics_dir: Path | None, approvals: dict | None) -> dict:
    rec = {"question_id": question["question_id"], "split": question["split"], "module_code": question["module_code"],
           "marks": question["marks"], "rubric_state": "missing", "provenance_status": None, "problems": 0,
           "first_problems": [], "approval_state": None, "ready_for_gold": False}
    path = None if rubrics_dir is None else Path(rubrics_dir) / f"{question['question_id']}.json"
    if path is None or not path.is_file():
        return rec
    try:
        doc = _load_json(path)
    except (OSError, ValueError):
        rec["rubric_state"] = "unreadable"
        return rec
    problems = check_document(doc, {"question_id": question["question_id"], "marks": question["marks"]})
    status = doc.get("provenance", {}).get("status") if isinstance(doc, dict) and isinstance(doc.get("provenance"), dict) else None
    rec.update(provenance_status=status, problems=len(problems), first_problems=problems[:3])
    if problems:
        rec["rubric_state"] = "invalid"
    elif status == "lecturer_validated":
        rec["rubric_state"] = "documented_lecturer_validation"
        rec["approval_state"] = approval_state(approvals, doc)
        rec["ready_for_gold"] = usable_as_gold(doc, problems) and rec["approval_state"] == "matches"
    else:
        rec["rubric_state"] = "structurally_valid_ai_drafted"
    return rec


def _dataset_block(d: Path) -> dict:
    manifest = _load_json(d / "manifest.json")
    report = _load_json(d / "validation_report.json")
    ratio = next((c for c in report["checks"] if c["name"] == "ratio_concentration"), None)
    files = {}
    for name in ("01_question_bank.csv", "02_controlled_answers_eligible.csv", "03_rubric_criteria.csv"):
        files[name] = {"manifest_sha256": manifest["files"].get(name), "recomputed_sha256": sha256_file(d / name),
                       "matches_manifest": manifest["files"].get(name) == sha256_file(d / name)}
    return {"name": d.name, "dataset_version": manifest.get("dataset_version"), "row_dataset_version": manifest.get("row_dataset_version"),
            "source_dataset_version": manifest.get("source_dataset_version"), "manifest_sha256": sha256_file(d / "manifest.json"),
            "files": files, "validation_report_sha256": sha256_file(d / "validation_report.json"),
            "validation_overall": report["overall"], "validation_hard_failures": report["hard_failures"],
            "ratio_concentration": None if ratio is None else {"value": ratio["details"]["value"], "threshold": ratio["details"]["threshold"],
                                                               "status": ratio["status"]}}


def audit(dataset_dir: Path, rubrics_dir: Path | None = None, approvals_path: Path | None = None, simulated: bool = False) -> dict:
    d = Path(dataset_dir)
    pool = eligible_questions(d)
    held_out = sorted((q for q in pool if q["split"] in FINAL_SPLITS), key=lambda q: q["question_id"])
    pilot_pool = [q for q in pool if q["split"] in PILOT_SPLITS]
    if not held_out:
        raise GoldToolError("the dataset has no eligible validation/test questions")
    rubrics_present = rubrics_dir is not None and Path(rubrics_dir).is_dir()
    approvals, approvals_info = None, {"provided": approvals_path is not None, "readable": False, "problems": []}
    if approvals_path is not None and Path(approvals_path).is_file():
        try:
            approvals = _load_json(approvals_path)
            approvals_info.update(readable=True, problems=register_problems(approvals))
        except (OSError, ValueError):
            approvals_info["problems"] = ["register is not readable JSON"]
    records = [_question_record(q, Path(rubrics_dir) if rubrics_present else None, approvals) for q in held_out]
    count = lambda state: sum(1 for r in records if r["rubric_state"] == state)  # noqa: E731
    n = len(records)
    valid_ai, claims = count("structurally_valid_ai_drafted"), count("documented_lecturer_validation")
    matching = sum(1 for r in records if r["approval_state"] == "matches")
    ready = sum(1 for r in records if r["ready_for_gold"])
    unbacked = {s: sum(1 for r in records if r["approval_state"] == s)
                for s in ("no_register", "register_invalid", "no_entry", "stale", "date_inconsistent")}
    dataset = _dataset_block(d)

    blockers = []
    if not rubrics_present:
        blockers.append("No rubric directory was supplied or found, so no rubric document is available for any question.")
    for state, label in (("missing", "have no rubric document"), ("unreadable", "have an unreadable rubric document"),
                         ("invalid", "have a rubric document that fails the checker"),
                         ("structurally_valid_ai_drafted", "have a structurally valid AI-drafted rubric that still needs lecturer review")):
        if count(state):
            blockers.append(f"{count(state)} of {n} held-out questions {label}.")
    for state, number in unbacked.items():
        if number:
            blockers.append(f"{number} of {n} lecturer-validation claims have no usable approval record ({state}).")
    if approvals_info["problems"]:
        blockers.append(f"The approval register has {len(approvals_info['problems'])} problem(s).")
    if ready < n:
        blockers.append(f"Genuine gold-sheet generation needs all {n} held-out questions ready; {ready} are.")
    ratio = dataset["ratio_concentration"]
    if ratio and ratio["status"] == "fail":
        blockers.append(f"The dataset's own validation still fails ratio concentration ({ratio['value']} against {ratio['threshold']}); "
                        "human validation of marks does not remove that finding.")
    if not all(f["matches_manifest"] for f in dataset["files"].values()):
        blockers.append("A dataset CSV no longer matches the hash recorded in the manifest.")

    statement = ("No lecturer validation is documented for any held-out question." if claims == 0 else
                 f"{claims} held-out rubric(s) carry a lecturer-validation claim; none is authenticated by this software.")
    return {
        "report_version": 1, "simulated": simulated, "notice": SIMULATED_NOTICE if simulated else None,
        "dataset": dataset,
        "questions": {"eligible_total": len(pool), "eligible_by_split": {s: sum(1 for q in pool if q["split"] == s)
                                                                      for s in sorted({q["split"] for q in pool})},
                      "held_out_pool": n, "held_out_splits": list(FINAL_SPLITS), "pilot_pool_training_split": len(pilot_pool),
                      "pilot_note": "the pilot is drawn from the training split and is never part of the held-out evaluation; "
                                    "pilot rubrics are assessed once the team has fixed the pilot seed"},
        "inputs": {"rubric_directory_found": rubrics_present, "approval_register": approvals_info},
        "rubrics": {"missing": count("missing"), "unreadable": count("unreadable"), "invalid": count("invalid"),
                    "structurally_valid": valid_ai + claims, "structurally_valid_ai_drafted": valid_ai,
                    "documented_lecturer_validation": claims, "with_matching_approval_record": matching,
                    "approval_not_backed_by_a_record": unbacked},
        "readiness": {"ready_for_gold_sheets": ready, "of": n, "proportion": round(ready / n, 4), "all_ready": ready == n,
                      "definition": "lecturer_validated provenance, no checker problems (including marks that match the dataset "
                                    "question) and an approval-register entry whose hash matches the current rubric"},
        "human_validation": {"statement": statement,
                             "marker_returns_read": False, "agreement_results_read": False,
                             "scope": "This audit has no input for marker returns or agreement results, so it establishes no genuine human "
                                      "marking and no inter-marker agreement; the project's milestone records (GOLD_PROTOCOL.md) state "
                                      "that none has taken place."},
        "blockers": blockers, "human_actions_required": HUMAN_ACTIONS,
        "per_question": records, "limits": [AUTHENTICATION_LIMIT,
                                            "A passing audit shows that records are complete and consistent. It is not research validity "
                                            "and not operational security."],
    }


def render_markdown(a: dict) -> str:
    ds, q, ru, rd, hv = a["dataset"], a["questions"], a["rubrics"], a["readiness"], a["human_validation"]
    ratio = ds["ratio_concentration"]
    lines = ["# Human-validation readiness", ""]
    if a["simulated"]:
        lines += [f"> **{a['notice']}** - this report was built from toy fixtures, not from the project dataset.", ""]
    lines += [
        f"> **{hv['statement']}** {hv['scope']}", "",
        "Generated by `python -m datasets.gold.readiness` from the files on disk; every number below is computed, none is typed in.", "",
        "## Dataset and traceability", "",
        f"- Dataset: `{ds['name']}`, version `{ds['dataset_version']}` (rows stamped `{ds['row_dataset_version']}`, source `{ds['source_dataset_version']}`)",
        f"- `manifest.json` sha256: `{ds['manifest_sha256']}`",
        f"- `validation_report.json` sha256: `{ds['validation_report_sha256']}`; overall {ds['validation_overall']}, hard failures {ds['validation_hard_failures']}",
    ]
    if ratio:
        lines.append(f"- Ratio concentration: {ratio['value']} against {ratio['threshold']} ({ratio['status']})")
    for name, info in ds["files"].items():
        lines.append(f"- `{name}` sha256 `{info['recomputed_sha256']}` (matches manifest: {info['matches_manifest']})")
    lines += ["", "## Counts", "", "| item | count |", "|---|---|",
              f"| eligible questions (all splits) | {q['eligible_total']} |",
              *[f"| eligible, {s} split | {n} |" for s, n in q["eligible_by_split"].items()],
              f"| held-out pool (validation + test) | {q['held_out_pool']} |",
              f"| rubric document missing | {ru['missing']} |", f"| rubric document unreadable | {ru['unreadable']} |",
              f"| rubric document fails the checker | {ru['invalid']} |",
              f"| structurally valid rubrics | {ru['structurally_valid']} |",
              f"| of which AI-drafted, not lecturer-validated | {ru['structurally_valid_ai_drafted']} |",
              f"| documented lecturer validation (claimed, unauthenticated) | {ru['documented_lecturer_validation']} |",
              f"| with a matching approval-register entry | {ru['with_matching_approval_record']} |",
              f"| **ready for genuine gold-sheet generation** | **{rd['ready_for_gold_sheets']} of {rd['of']} ({rd['proportion']:.1%})** |", "",
              f"Ready means: {rd['definition']}. Gold sheets can only be generated when all {rd['of']} are ready: "
              f"**{'yes' if rd['all_ready'] else 'no'}**.", "",
              f"The pilot ({q['pilot_pool_training_split']} eligible training-split questions in the pool) is separate: {q['pilot_note']}.", "",
              "## Remaining blockers", ""]
    lines += [f"- {b}" for b in a["blockers"]] or ["- none found by the software"]
    lines += ["", "## Actions that need real people or institutional approval", ""] + [f"{i}. {t}" for i, t in enumerate(a["human_actions_required"], 1)]
    lines += ["", "## Held-out questions", "", "| question | split | module | marks | rubric | provenance claim | approval record | ready |", "|---|---|---|---|---|---|---|---|"]
    for r in a["per_question"]:
        lines.append(f"| {r['question_id']} | {r['split']} | {r['module_code']} | {r['marks']} | {r['rubric_state']} | "
                     f"{r['provenance_status'] or '-'} | {r['approval_state'] or '-'} | {'yes' if r['ready_for_gold'] else 'no'} |")
    lines += ["", "## Limits", ""] + [f"- {t}" for t in a["limits"]]
    lines += ["", "## Reproduce", "",
              "From `ai-services/c3`: `python -m datasets.gold.readiness datasets/c3_phase3_v5_repaired_v2 --rubrics-dir <dir> "
              "--approvals <register> --markdown -` (with no rubric directory every question is reported missing).", ""]
    return "\n".join(lines)


def _write_new(path: Path, text: str, dataset_dir: Path) -> None:
    path = Path(path).resolve()
    if path.exists():
        raise GoldToolError(f"{path.name} already exists; nothing is overwritten")
    if Path(dataset_dir).resolve() in path.parents:
        raise GoldToolError("refusing to write a report inside the dataset directory")
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Human-validation readiness audit (read-only)")
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--rubrics-dir", type=Path, default=None)
    ap.add_argument("--approvals", type=Path, default=None)
    ap.add_argument("--json", default=None, help="write the JSON report to PATH, or '-' for stdout")
    ap.add_argument("--markdown", default=None, help="write the Markdown report to PATH, or '-' for stdout")
    args = ap.parse_args(argv)
    try:
        report = audit(args.dataset, args.rubrics_dir, args.approvals)
        outputs = [("json", args.json, json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"),
                   ("markdown", args.markdown, render_markdown(report))]
        if args.json is None and args.markdown is None:
            outputs[0] = ("json", "-", outputs[0][2])
        for _, target, text in outputs:
            if target == "-":
                sys.stdout.write(text)
            elif target is not None:
                _write_new(Path(target), text, args.dataset)
    except (GoldToolError, OSError, ValueError, KeyError) as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
