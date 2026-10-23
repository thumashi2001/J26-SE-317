"""Blind marking sheets, a separate answer key, return templates and a pre-marking seal.

Usage (guarded; see below):
  python -m datasets.gold.sheets <dataset dir> --plan plan.json --group final|pilot --origin gold|pilot --rubrics-dir DIR
      --markers A,B --salt-file FILE --sheets-dir DIR --custody-dir DIR

What a marker sheet contains: opaque item ids, the question text, a rubric re-labelled with opaque ids (C1.., C1-L1..), and
the answer text. It does not contain tiers, expected marks, criterion marks, concept lists, splits, sources, or any dataset
id. The mapping back to the dataset lives only in the key file in the custody directory.

Guards (they refuse, they never repair):
  * origin 'gold' needs a lecturer_validated rubric for every question; 'pilot' accepts structurally valid rubrics including
    ai_drafted ones; 'toy_fixture' exists for tests and is not offered on the command line.
  * the sheets directory and the custody directory must be different, neither inside the other, and neither inside a git
    working tree (so the key and the sheets are not committed by accident).
  * the salt must be at least 16 characters; a dataset id, answer id or tier name found in any text shown to a marker stops the
    run.
  * the constant-string IRRELEVANT controls (template_negative_control == 'True') are not put on sheets; they are listed in the
    key as excluded.

Security limits, stated plainly: the opaque ids are a hash of the salt and the answer id, so anyone who holds the salt and the
dataset can recompute the mapping, and a weak or reused salt can be guessed; hashes and the seal give tamper evidence, not
access control; nothing here encrypts, authenticates or logs access. Restricted storage and a real return channel for markers
are arrangements outside this code.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from datasets.gold.common import ORIGINS, GoldToolError, canonical_bytes, sha256_file, sha256_hex
from datasets.gold.rubric_check import check_document, usable_as_gold
from datasets.gold.sampling import validate_plan
from datasets.repair.common import LABELS

GENERATOR = "datasets.gold.sheets/1"
MIN_SALT = 16
PSEUDONYM = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
TIER_WORD = re.compile(r"\b(" + "|".join(LABELS) + r")\b")
GROUP_ORIGINS = {"final": ("gold", "toy_fixture"), "pilot": ("pilot", "toy_fixture")}
INSTRUCTIONS = [
    "Mark each item on its own, using only the rubric shown with it.",
    "For every criterion choose exactly one of the listed levels; do not type marks. The mark is the level's mark.",
    "If you cannot mark an item, set cannot_mark to true and give a reason instead of guessing.",
    "Do not discuss items with other markers until both of you have returned your sheets.",
]


def _opaque(salt: str, kind: str, value: str, n: int) -> str:
    return sha256_hex(f"{salt}|{kind}|{value}".encode())[:n]


def _read(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _blind_rubric(doc: dict) -> tuple[dict, dict]:
    """The rubric as a marker sees it (opaque criterion/level ids) and the mapping back to the document's ids."""
    rubric, shown, back = doc["rubric"], [], {}
    for ci, crit in enumerate(rubric["criteria"], 1):
        cid, levels, level_back = f"C{ci}", [], {}
        for li, lv in enumerate(sorted(crit["scoring_levels"], key=lambda x: x["mark"]), 1):
            lid = f"{cid}-L{li}"
            level_back[lid] = lv["level_id"]
            levels.append({"level": lid, "label": lv["label"], "mark": lv["mark"], "descriptor": lv["descriptor"],
                           "required_concepts": list(lv.get("required_concepts", []))})
        shown.append({"criterion": cid, "description": crit["description"], "max_marks": crit["max_marks"],
                      "required_concepts": list(crit.get("required_concepts", [])), "levels": levels})
        back[cid] = {"criterion_id": crit["criterion_id"], "levels": level_back}
    return {"title": rubric["title"], "criteria": shown}, back


def _texts(obj: object):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texts(v)


def build_sheets(dataset_dir: Path, plan_doc: dict, group: str, rubrics: dict[str, dict], markers: list[str], salt: str,
                 origin: str) -> dict:
    """Pure construction of sheets, return templates, key and seal; nothing is written."""
    if group not in GROUP_ORIGINS:
        raise GoldToolError("group must be 'final' or 'pilot'")
    if origin not in ORIGINS or origin not in GROUP_ORIGINS[group]:
        raise GoldToolError(f"origin {origin!r} is not allowed for group {group!r} (allowed: {GROUP_ORIGINS[group]})")
    if len(markers) < 2 or len(set(markers)) != len(markers) or not all(PSEUDONYM.match(m) for m in markers):
        raise GoldToolError("need at least two distinct marker pseudonyms made of letters, digits, '_' or '-'")
    if len(salt) < MIN_SALT:
        raise GoldToolError(f"salt must be at least {MIN_SALT} characters and kept secret")
    d = Path(dataset_dir)
    validate_plan(d, plan_doc)  # a plan file may have been edited: eligibility, splits and disjointness are re-checked
    manifest_sha = sha256_file(d / "manifest.json")
    questions = plan_doc[group]["questions"]
    hidden_ids = {q["question_id"] for g in ("final", "pilot") for q in plan_doc[g]["questions"]}
    for m in markers:  # pseudonyms appear in file names and in the sheet's marker field
        if any(h in m for h in hidden_ids) or TIER_WORD.search(m) or m.upper() in LABELS:
            raise GoldToolError(f"marker pseudonym {m!r} contains a dataset id or tier name")

    shown_rubrics, rubric_key, ref_of = {}, {}, {}
    for q in questions:
        qid = q["question_id"]
        doc = rubrics.get(qid)
        if doc is None:
            raise GoldToolError(f"no rubric document for a selected question ({qid})")
        problems = check_document(doc, {"question_id": qid, "marks": q["marks"]})
        if problems:
            raise GoldToolError(f"rubric for {qid} is not acceptable: {problems[0]} (+{len(problems) - 1} more)")
        if origin == "gold" and not usable_as_gold(doc, problems):
            raise GoldToolError(f"origin 'gold' needs a lecturer_validated rubric; {qid} is {doc['provenance']['status']!r}")
        ref = "RB" + _opaque(salt, "rubric", qid, 8)
        ref_of[qid] = ref
        shown_rubrics[ref], back = _blind_rubric(doc)
        rubric_key[ref] = {"question_id": qid, "criteria": back}

    answers = _read(d / "02_controlled_answers_eligible.csv")
    by_q = {q["question_id"]: q for q in _read(d / "01_question_bank.csv")}
    all_answer_ids = {r["answer_id"] for r in answers if r["question_id"] in ref_of}
    items, excluded = [], []
    for row in sorted(answers, key=lambda r: r["answer_id"]):
        if row["question_id"] not in ref_of:
            continue
        if row["template_negative_control"] == "True":
            excluded.append({"answer_id": row["answer_id"], "reason": "template_negative_control"})
            continue
        items.append({"item_id": "I" + _opaque(salt, "item", row["answer_id"], 12), "question_text": by_q[row["question_id"]]["question_text"],
                      "rubric_ref": ref_of[row["question_id"]], "answer_text": row["student_answer"], "_answer_id": row["answer_id"],
                      "_question_id": row["question_id"]})
    if not items:
        raise GoldToolError("no answers left to mark for the selected questions")
    if len({i["item_id"] for i in items}) != len(items):
        raise GoldToolError("opaque item ids collided; choose a different salt")
    # every text a marker will see is scanned for any dataset id (question or answer) and any tier name
    shown_texts = [t for r in shown_rubrics.values() for t in _texts(r)] + [t for i in items for t in (i["question_text"], i["answer_text"])]
    for text in shown_texts:
        leaked = [h for h in hidden_ids | all_answer_ids if h in text] + TIER_WORD.findall(text)
        if leaked:
            raise GoldToolError(f"text shown to a marker contains a dataset id or tier name ({leaked[0]!r}); fix the source, nothing is redacted silently")

    public_items = [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]
    sheets, templates, sheet_hashes = {}, {}, {}
    for marker in markers:
        ordered = sorted(public_items, key=lambda i: sha256_hex(f"{salt}|order|{marker}|{i['item_id']}".encode()))
        sheet = {"sheet_version": 1, "origin": origin, "group": group, "marker": marker, "instructions": INSTRUCTIONS,
                 "rubrics": shown_rubrics, "items": ordered}
        if origin == "toy_fixture":
            sheet["notice"] = "SIMULATED TOY FIXTURE - NOT REAL MARKING MATERIAL"
        sheets[marker] = sheet
        sheet_hashes[marker] = sha256_hex(canonical_bytes(sheet))
        templates[marker] = {
            "sheet_sha256": sheet_hashes[marker], "origin": origin, "marker": marker,
            "returns": [{"item_id": i["item_id"], "levels": {c["criterion"]: None for c in shown_rubrics[i["rubric_ref"]]["criteria"]},
                         "cannot_mark": False, "reason": "", "comment": ""} for i in ordered]}
    key = {"key_version": 1, "generator": GENERATOR, "origin": origin, "group": group,
           "restricted": "this file maps sheet ids back to dataset ids; never give it to a marker",
           "salt_commitment": sha256_hex(f"salt-commitment|{salt}".encode()), "dataset_manifest_sha256": manifest_sha,
           "plan_sha256": sha256_hex(canonical_bytes(plan_doc)), "markers": list(markers),
           "items": {i["item_id"]: {"answer_id": i["_answer_id"], "question_id": i["_question_id"], "rubric_ref": i["rubric_ref"]}
                     for i in items},
           "rubric_refs": rubric_key, "excluded": excluded, "sheet_sha256": sheet_hashes}
    files = {f"sheet_{m}.json": sheet_hashes[m] for m in markers}
    files.update({f"return_template_{m}.json": sha256_hex(canonical_bytes(templates[m])) for m in markers})
    files["answer_key.json"] = sha256_hex(canonical_bytes(key))
    files["plan.json"] = key["plan_sha256"]
    seal = {"seal_version": 1, "stage": "pre_marking", "origin": origin, "group": group, "generator": GENERATOR,
            "dataset_manifest_sha256": manifest_sha, "files": files,
            "seal_sha256": sha256_hex(canonical_bytes(files)),
            "meaning": "tamper evidence only: it shows whether these files changed after sealing, not who may read them"}
    return {"sheets": sheets, "return_templates": templates, "key": key, "seal": seal, "plan": plan_doc}


def _inside_git_worktree(path: Path) -> bool:
    return any((p / ".git").exists() for p in [path.resolve(), *path.resolve().parents])


def write_outputs(result: dict, sheets_dir: Path, custody_dir: Path, allow_inside_git: bool = False) -> dict:
    sheets_dir, custody_dir = Path(sheets_dir).resolve(), Path(custody_dir).resolve()
    if sheets_dir == custody_dir or sheets_dir in custody_dir.parents or custody_dir in sheets_dir.parents:
        raise GoldToolError("the sheets directory and the custody directory must be separate and not nested")
    if not allow_inside_git and (_inside_git_worktree(sheets_dir) or _inside_git_worktree(custody_dir)):
        raise GoldToolError("refusing to write sheets or the key inside a git working tree; use restricted storage outside it")
    for d in (sheets_dir, custody_dir):  # check both before creating either, so a refusal leaves nothing behind
        if d.exists() and (not d.is_dir() or any(d.iterdir())):
            raise GoldToolError(f"{d} is not an empty directory; nothing is overwritten")
    for d in (sheets_dir, custody_dir):
        d.mkdir(parents=True, exist_ok=True)
    for m, sheet in result["sheets"].items():
        (sheets_dir / f"sheet_{m}.json").write_bytes(canonical_bytes(sheet))
        (sheets_dir / f"return_template_{m}.json").write_bytes(canonical_bytes(result["return_templates"][m]))
    (custody_dir / "answer_key.json").write_bytes(canonical_bytes(result["key"]))
    (custody_dir / "plan.json").write_bytes(canonical_bytes(result["plan"]))
    (custody_dir / "seal_pre_marking.json").write_bytes(canonical_bytes(result["seal"]))
    return result["seal"]


def verify_seal(seal: dict, sheets_dir: Path, custody_dir: Path) -> list[str]:
    """Names of sealed files that are missing or whose bytes changed (an empty list means unchanged)."""
    bad = []
    for name, digest in seal["files"].items():
        folder = Path(custody_dir) if name in ("answer_key.json", "plan.json") else Path(sheets_dir)
        path = folder / name
        if not path.exists() or sha256_file(path) != digest:
            bad.append(name)
    if sha256_hex(canonical_bytes(seal["files"])) != seal["seal_sha256"]:
        bad.append("seal_sha256")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate blind marking sheets and a separate key (guarded)")
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--group", choices=sorted(GROUP_ORIGINS), required=True)
    ap.add_argument("--origin", choices=["pilot", "gold"], required=True)
    ap.add_argument("--rubrics-dir", type=Path, required=True, help="one <question_id>.json gold-rubric document per selected question")
    ap.add_argument("--markers", required=True, help="comma-separated pseudonyms, at least two")
    ap.add_argument("--salt-file", type=Path, required=True)
    ap.add_argument("--sheets-dir", type=Path, required=True)
    ap.add_argument("--custody-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        plan_doc = json.loads(args.plan.read_text(encoding="utf-8"))
        rubrics = {}
        for q in plan_doc[args.group]["questions"]:
            path = args.rubrics_dir / f"{q['question_id']}.json"
            if not path.exists():
                raise GoldToolError(f"missing rubric document {path.name}")
            rubrics[q["question_id"]] = json.loads(path.read_text(encoding="utf-8"))
        salt = args.salt_file.read_text(encoding="utf-8").strip()
        result = build_sheets(args.dataset, plan_doc, args.group, rubrics, args.markers.split(","), salt, args.origin)
        seal = write_outputs(result, args.sheets_dir, args.custody_dir)
    except (GoldToolError, OSError, ValueError, KeyError) as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 1
    print(f"wrote {len(result['key']['items'])} items per sheet; seal {seal['seal_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
