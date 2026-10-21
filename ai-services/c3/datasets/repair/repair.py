"""Core repair of C3-Phase3-v5-FINAL.

Rules (approved by the user): only repair a value when the data, the rubric or a documented rule proves it;
otherwise quarantine or flag it. Nothing is generated, reworded, moved between splits or re-labelled.
Every record of the original is accounted for exactly once and every change is written to repair_manifest.csv.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from datasets.repair.common import (
    ARCHIVE_DIR,
    DEFAULT_OUT_DIR,
    NAN_WORD,
    NULL_TOKENS,
    ORIGINAL_FILES,
    REPAIR_TOOL_VERSION,
    REPAIRED_VERSION,
    SOURCE_VERSION,
    SPLITS,
    OutputExistsError,
    drop_null_elements,
    fmt_float,
    load_original,
    normalise_text,
    parse_json_list,
    sha256_file,
    truncate_value,
    verify_original,
    write_csv,
    write_json,
)

SCOPE_REVIEW_QUESTIONS = ("PP-SE3040-001", "PP-SE3040-002")
INELIGIBLE_REASON = "question_has_only_one_valid_variant"
FLAT_MARK = "10.0"
TEMPLATE_MIN_QUESTIONS = 10  # an IRRELEVANT/MISCONCEPTION string shared by >= this many questions is a constant template
PLACEHOLDER_PHRASES = (
    "one supporting detail",
    "accurate causal relationship",
    "inverted technical rule",
    "conceptual understanding",
)
LIST_COLUMNS = (
    "demonstrated_concepts",
    "missing_concepts",
    "incorrect_concepts",
    "expected_concepts",
    "expected_relationships",
    "evidence_requirements",
)
QUESTION_LIST_COLUMNS = ("expected_concepts", "expected_relationships", "evidence_requirements")
PLACEHOLDER_ANSWER_COLUMNS = (
    "demonstrated_concepts",
    "missing_concepts",
    "incorrect_concepts",
    "expected_concepts",
    "variant_rationale",
)

ANSWER_NEW_COLS = [
    "max_marks",
    "template_negative_control",
    "placeholder_concepts_flag",
    "scope_review",
    "review_status",
    "source_dataset_version",
    "repair_categories",
    "repair_status",
]
CONTROL_EXTRA_COLS = ["eligibility_reason", "original_marks", "original_expected_mark", "original_criterion_marks"]
QUARANTINE_EXTRA_COLS = [
    "quarantine_reason",
    "max_marks",
    "template_negative_control",
    "placeholder_concepts_flag",
    "source_dataset_version",
]
QUESTION_NEW_COLS = [
    "eligibility_status",
    "eligibility_reason",
    "scope_review",
    "placeholder_concepts_flag",
    "repair_group",
    "source_dataset_version",
    "repair_status",
]
RUBRIC_NEW_COLS = ["repair_status", "source_dataset_version"]
REVIEW_COLS = ["answer_id", "question_id", "split", "answer_quality", "expected_mark", "identical_to",
               "review_status", "reason", "action"]
CRITERION_MAP_COLS = ["answer_criterion_id", "question_id", "rubric_criterion_id", "mapping_status", "rule",
                      "answer_criterion_full_mark", "rubric_criterion_marks", "marks_agree", "question_marks"]
MANIFEST_COLS = [
    "record_id",
    "record_type",
    "question_id",
    "original_file",
    "split",
    "issue_category",
    "field",
    "original_value",
    "repaired_value",
    "reason",
    "evidence",
    "repair_status",
    "validation_result",
]
STATUS_PRIORITY = ("needs_review", "repaired", "flagged", "unchanged")


class Ledger:
    """Collects one manifest row per changed field or per quarantined/flagged record."""

    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []

    def add(self, **kw: str) -> None:
        row = dict.fromkeys(MANIFEST_COLS, "")
        row.update(kw)
        row["original_value"] = truncate_value(row["original_value"])
        row["repaired_value"] = truncate_value(row["repaired_value"])
        self.rows.append(row)


def _has_placeholder(*values: str) -> bool:
    text = " ".join(values).casefold()
    return any(p in text for p in PLACEHOLDER_PHRASES)


def _best_status(statuses: list[str]) -> str:
    for s in STATUS_PRIORITY:
        if s in statuses:
            return s
    return "unchanged"


def _rubric_key(criterion_id: str) -> tuple[str, str] | None:
    """('<qid>', 'C01') from a rubric id such as R-<qid>-v2-C01 or R-<qid>-C01."""
    m = re.fullmatch(r"R-(?P<q>.+?)(?:-v\d+)?-(?P<c>C\d+)", criterion_id)
    return (m.group("q"), m.group("c")) if m else None


def _answer_key(criterion_id: str) -> tuple[str, str] | None:
    m = re.fullmatch(r"(?P<q>.+)-(?P<c>C\d+)", criterion_id)
    return (m.group("q"), m.group("c")) if m else None


def classify_groups(q: pd.DataFrame, audit: pd.DataFrame) -> dict[str, str]:
    """canonical | replacement_block_A (listed in the 63-replacement audit) | replacement_block_B (the rest)."""
    block_a = set(audit["replacement_question_id"])
    groups: dict[str, str] = {}
    for qid, is_rep in zip(q["question_id"], q["is_replacement"], strict=True):
        if is_rep != "True":
            groups[qid] = "canonical"
        elif qid in block_a:
            groups[qid] = "replacement_block_A"
        else:
            groups[qid] = "replacement_block_B"
    return groups


def select_sample(q: pd.DataFrame, groups: dict[str, str]) -> list[str]:
    """3 canonical (first of each split, id order), 2 block-A and 1 block-B question (id order)."""
    chosen: list[str] = []
    for split in SPLITS:
        ids = sorted(qid for qid, s in zip(q["question_id"], q["split"], strict=True)
                     if s == split and groups[qid] == "canonical")
        chosen.append(ids[0])
    chosen += sorted(qid for qid, g in groups.items() if g == "replacement_block_A")[:2]
    chosen += sorted(qid for qid, g in groups.items() if g == "replacement_block_B")[:1]
    return chosen


def _zero_criterion_marks(original: str) -> str:
    parsed = parse_json_list(original)
    if parsed is not None:
        zeroed = [{**e, "mark": 0.0} if isinstance(e, dict) else 0.0 for e in parsed]
        return json.dumps(zeroed, ensure_ascii=False)
    return ",".join("0" for _ in original.split(","))


def _repair_lists(rec: dict[str, str], columns: tuple[str, ...]) -> dict[str, tuple[str, str, int]]:
    """Drop null elements from JSON-list cells in place; return {column: (original, repaired, removed)}."""
    changed: dict[str, tuple[str, str, int]] = {}
    for col in columns:
        new, removed = drop_null_elements(rec[col])
        if removed:
            changed[col] = (rec[col], new, removed)
            rec[col] = new
    return changed


def _list_clean(value: str) -> bool:
    return not any(str(e).strip().lower() in NULL_TOKENS for e in parse_json_list(value) or [])


def build_criterion_map(eligible: list[dict[str, str]], rubric_rows: list[dict[str, str]],
                        question_marks: dict[str, float]) -> list[dict[str, str]]:
    """answer criterion id -> rubric-file criterion id by normalised id; UNRESOLVED otherwise (nothing invented)."""
    rubric_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for r in rubric_rows:
        key = _rubric_key(r["criterion_id"])
        if key and key[0] == r["question_id"]:
            rubric_by_key[key] = r
    full_marks: dict[tuple[str, str], float] = {}
    owner: dict[str, str] = {}
    for a in eligible:
        for entry in parse_json_list(a["criterion_marks"]) or []:
            cid = entry.get("criterion_id", "")
            owner.setdefault(cid, a["question_id"])
            if a["answer_quality"] == "FULL":
                full_marks[(a["question_id"], cid)] = float(entry["mark"])
    rows = []
    for cid in sorted(owner):
        qid = owner[cid]
        key = _answer_key(cid)
        hit = rubric_by_key.get(key) if key and key[0] == qid else None
        rubric_marks = float(hit["criterion_marks"]) if hit else None
        full = full_marks.get((qid, cid))
        agree = "" if hit is None or full is None or rubric_marks is None else str(abs(rubric_marks - full) < 1e-9)
        rows.append({
            "answer_criterion_id": cid,
            "question_id": qid,
            "rubric_criterion_id": hit["criterion_id"] if hit else "",
            "mapping_status": "RESOLVED" if hit else "UNRESOLVED",
            "rule": "normalised id: strip 'R-' prefix and '-vN' infix; same question and Cnn" if hit
                    else "no rubric row with the same normalised (question, Cnn) key",
            "answer_criterion_full_mark": "" if full is None else fmt_float(full),
            "rubric_criterion_marks": "" if rubric_marks is None else fmt_float(rubric_marks),
            "marks_agree": agree,
            "question_marks": fmt_float(question_marks[qid]),
        })
    return rows


def run_repair(
    out_dir: Path | None = None,
    *,
    sample: bool = False,
    archive_dir: Path = ARCHIVE_DIR,
    allow_nonempty: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """Repair the archive into out_dir. Returns {'manifest', 'diff', 'out_dir', 'groups', 'validation'}."""
    out = Path(out_dir) if out_dir else DEFAULT_OUT_DIR
    if out.exists() and any(out.iterdir()) and not allow_nonempty:
        raise OutputExistsError(f"{out} already exists and is not empty (pass --out to overwrite explicitly)")
    archive_dir = Path(archive_dir)
    original_hashes = verify_original(archive_dir)
    data = load_original(archive_dir)
    q_all, a_all, ru_all, audit = data["question_bank"], data["answers"], data["rubric"], data["audit"]
    original_columns = {"question_bank": list(q_all.columns), "answers": list(a_all.columns),
                        "rubric": list(ru_all.columns)}
    groups = classify_groups(q_all, audit)
    qmarks_all = {qid: float(m) for qid, m in zip(q_all["question_id"], q_all["marks"], strict=True)}

    # constant template strings are identified on the FULL original so a sample behaves like the full run
    spread: dict[str, set[str]] = defaultdict(set)
    for r in a_all.to_dict("records"):
        if r["answer_quality"] in ("IRRELEVANT", "MISCONCEPTION"):
            spread[r["student_answer"]].add(r["question_id"])
    template_texts = {t for t, qs in spread.items() if len(qs) >= TEMPLATE_MIN_QUESTIONS}

    source_to_repl = {s: qid for qid, s in zip(q_all["question_id"], q_all["source_replaced_question_id"], strict=True)
                      if s}
    scope_ids = sorted(groups) if not sample else select_sample(q_all, groups)
    scope_set = set(scope_ids)
    questions = [r for r in q_all.to_dict("records") if r["question_id"] in scope_set]
    answers = [r for r in a_all.to_dict("records") if r["question_id"] in scope_set]
    split_of = {r["question_id"]: r["split"] for r in questions}

    rubric_rows: list[dict[str, str]] = []
    for r in ru_all.to_dict("records"):
        orig_qid = r["question_id"]
        if orig_qid not in groups and source_to_repl.get(orig_qid):
            r = {**r, "question_id": source_to_repl[orig_qid], "_orig_question_id": orig_qid}
        if r["question_id"] in scope_set:
            rubric_rows.append(r)

    ledger = Ledger()
    f_ans = ORIGINAL_FILES["answers"]
    eligible: list[dict[str, str]] = []
    quarantine: list[dict[str, str]] = []
    controls: list[dict[str, str]] = []
    meta: dict[str, dict[str, list[str]]] = {}
    diff: list[dict[str, Any]] = []
    by_question: dict[str, list[dict[str, str]]] = defaultdict(list)

    def add_answer_row(orig: dict[str, str], **kw: str) -> None:
        ledger.add(record_id=orig["answer_id"], record_type="answer", question_id=orig["question_id"],
                   original_file=f_ans, split=orig["split"], **kw)

    for orig in answers:
        qid, aid, grp = orig["question_id"], orig["answer_id"], groups[orig["question_id"]]
        tier = orig["answer_quality"]
        is_template = tier in ("IRRELEVANT", "MISCONCEPTION") and orig["student_answer"] in template_texts
        placeholder = _has_placeholder(*(orig[c] for c in PLACEHOLDER_ANSWER_COLUMNS))
        scope = qid in SCOPE_REVIEW_QUESTIONS
        flags = {"max_marks": fmt_float(qmarks_all[qid]), "template_negative_control": str(is_template),
                 "placeholder_concepts_flag": str(placeholder)}
        d: dict[str, Any] = {"answer_id": aid, "question_id": qid, "group": grp, "tier": tier,
                             "split": orig["split"], "orig_mark": orig["expected_mark"],
                             "new_mark": orig["expected_mark"], "orig_criterion_marks": orig["criterion_marks"],
                             "new_criterion_marks": orig["criterion_marks"], "changes": []}

        # ---- quarantine: non-IRRELEVANT replacement answers
        if grp != "canonical" and tier != "IRRELEVANT":
            if grp == "replacement_block_A" and NAN_WORD.search(orig["student_answer"]):
                reason = "unrecoverable_nan"
                why = ("the concept name was lost in the source and the original text exists in no other file; "
                       "reconstructing it would be fabrication")
                field, ov = "student_answer", orig["student_answer"]
                evidence = "student_answer contains the literal token 'nan'"
            else:
                if orig["expected_mark"] != FLAT_MARK:
                    raise AssertionError(f"{aid}: expected the flat mark {FLAT_MARK}, found {orig['expected_mark']}")
                reason = "unsupported_flat_mark"
                why = ("no rubric or answer evidence supports a specific mark; the replacement rubric has two generic "
                       "criteria so the MISCONCEPTION 'affected criterion' rule cannot be applied")
                field, ov = "expected_mark", orig["expected_mark"]
                evidence = f"all six tiers of {qid} carry expected_mark {FLAT_MARK}; tier={tier}"
            quarantine.append({**orig, "quarantine_reason": reason, **flags, "source_dataset_version": SOURCE_VERSION})
            add_answer_row(orig, issue_category=reason, field=field, original_value=ov, repaired_value="",
                           reason=why, evidence=evidence, repair_status="quarantined", validation_result="pass")
            d.update(disposition=f"QUARANTINE:{reason}", new_mark="(removed)", new_criterion_marks="(removed)",
                     status="quarantined")
            diff.append(d)
            continue

        rec = dict(orig)
        statuses: list[str] = []
        cats: list[str] = []
        for col, (ov, nv, removed) in _repair_lists(rec, LIST_COLUMNS).items():
            statuses.append("repaired")
            cats.append("nan_list_element")
            add_answer_row(orig, issue_category="nan_list_element", field=col, original_value=ov, repaired_value=nv,
                           reason="removed empty/'nan' list element (no content lost)",
                           evidence=f"{removed} element(s) equal to a null token in the original JSON list",
                           repair_status="repaired", validation_result="pass" if _list_clean(nv) else "fail")
            d["changes"].append(f"{col}: removed {removed} null element")
        rec["dataset_version"] = REPAIRED_VERSION

        # ---- repaired IRRELEVANT control of a replacement question (ineligible)
        if grp != "canonical":
            new_cm = _zero_criterion_marks(orig["criterion_marks"])
            for col, nv in (("marks", "0.0"), ("expected_mark", "0.0"), ("criterion_marks", new_cm)):
                add_answer_row(orig, issue_category="irrelevant_mark_policy", field=col, original_value=orig[col],
                               repaired_value=nv,
                               reason="IRRELEVANT = 0 marks per datasets/README.md and the dataset card; the answer "
                                      "text itself states it is off-topic",
                               evidence="every canonical IRRELEVANT answer has mark 0.0 (precedent); replacement "
                                        f"text: {orig['student_answer'][:80]}",
                               repair_status="repaired", validation_result="pass")
                rec[col] = nv
            add_answer_row(orig, issue_category="ineligible_control", field="eligibility", original_value="",
                           repaired_value="repaired_ineligible_controls", reason=INELIGIBLE_REASON,
                           evidence="the other five variants are quarantined; the dataset requires 6 variants/question",
                           repair_status="flagged", validation_result="pass")
            for col in LIST_COLUMNS:
                if rec[col].strip().lower() == "nan":
                    add_answer_row(orig, issue_category="unrecoverable_nan_field", field=col, original_value=rec[col],
                                   repaired_value=rec[col],
                                   reason="whole-cell literal nan (the concept names were lost in the source); kept "
                                          "as in the original because no value can be recovered",
                                   evidence="not part of the eligible primary set", repair_status="flagged",
                                   validation_result="pass")
            if is_template:
                add_answer_row(orig, issue_category="template_negative_control", field="template_negative_control",
                               original_value="", repaired_value="True",
                               reason="constant string reused across questions; retained, never moved",
                               evidence=f"text shared by >= {TEMPLATE_MIN_QUESTIONS} questions",
                               repair_status="flagged", validation_result="pass")
            if placeholder:
                add_answer_row(orig, issue_category="placeholder_concepts", field="placeholder_concepts_flag",
                               original_value="", repaired_value="True",
                               reason="placeholder concept annotation; flag only",
                               evidence="matched one of: " + ", ".join(PLACEHOLDER_PHRASES),
                               repair_status="flagged", validation_result="pass")
            controls.append({**rec, **flags, "scope_review": "False", "review_status": "ok",
                             "source_dataset_version": SOURCE_VERSION, "repair_categories": "irrelevant_mark_policy",
                             "repair_status": "repaired", "eligibility_reason": INELIGIBLE_REASON,
                             "original_marks": orig["marks"], "original_expected_mark": orig["expected_mark"],
                             "original_criterion_marks": orig["criterion_marks"]})
            d.update(disposition="REPAIRED_INELIGIBLE_CONTROL", new_mark="0.0", new_criterion_marks=new_cm,
                     status="repaired")
            d["changes"].append("marks 10.0 -> 0.0")
            diff.append(d)
            continue

        # ---- canonical -> eligible
        rules = []
        if is_template:
            rules.append(("template_negative_control", "template_negative_control",
                          f"IRRELEVANT constant string shared by >= {TEMPLATE_MIN_QUESTIONS} questions; retained"))
        if placeholder:
            rules.append(("placeholder_concepts", "placeholder_concepts_flag",
                          "placeholder concept annotation; flag only"))
        if scope:
            rules.append(("scope_review", "scope_review",
                          "question requires code/diagrams (LLM scope probe 2026-10-21: requires_code); kept "
                          "eligible, a human decides exclusion"))
        for cat, fld, why in rules:
            statuses.append("flagged")
            cats.append(cat)
            add_answer_row(orig, issue_category=cat, field=fld, original_value="", repaired_value="True",
                           reason=why, evidence="derived by rule from the original data", repair_status="flagged",
                           validation_result="pass")
        row = {**rec, **flags, "scope_review": str(scope), "review_status": "ok",
               "source_dataset_version": SOURCE_VERSION}
        eligible.append(row)
        by_question[qid].append(row)
        meta[aid] = {"statuses": statuses, "cats": cats}
        d.update(disposition="ELIGIBLE")
        diff.append(d)

    # ---- F6 identical text within a question: keep, flag, queue
    review_queue: list[dict[str, str]] = []
    for qid, rows in by_question.items():
        by_text: dict[str, list[dict[str, str]]] = defaultdict(list)
        for r in rows:
            by_text[normalise_text(r["student_answer"])].append(r)
        for members in by_text.values():
            if len(members) < 2:
                continue
            for m in members:
                peers = [x["answer_id"] for x in members if x is not m]
                m["review_status"] = "needs_review"
                meta[m["answer_id"]]["statuses"].append("needs_review")
                meta[m["answer_id"]]["cats"].append("identical_text_within_question")
                review_queue.append({
                    "answer_id": m["answer_id"], "question_id": qid, "split": m["split"],
                    "answer_quality": m["answer_quality"], "expected_mark": m["expected_mark"],
                    "identical_to": ";".join(peers), "review_status": "needs_review",
                    "reason": "identical student_answer text under different labels within the same question",
                    "action": "kept in the eligible set and flagged; text not rewritten; reviewer decides the label",
                })
                ledger.add(record_id=m["answer_id"], record_type="answer", question_id=qid, original_file=f_ans,
                           split=m["split"], issue_category="identical_text_within_question",
                           field="review_status", original_value="", repaired_value="needs_review",
                           reason="identical text within one question; cannot be repaired without inventing text",
                           evidence=f"identical to {';'.join(peers)}", repair_status="needs_review",
                           validation_result="pass")
    review_queue.sort(key=lambda r: r["answer_id"])
    diff_by_id = {d["answer_id"]: d for d in diff}
    for r in eligible:
        info = meta[r["answer_id"]]
        r["repair_status"] = _best_status(info["statuses"])
        r["repair_categories"] = ";".join(dict.fromkeys(info["cats"]))
        dd = diff_by_id[r["answer_id"]]
        dd["status"] = r["repair_status"]
        dd["changes"] += [c for c in info["cats"] if c != "nan_list_element"]

    # ---------------------------------------------------------------- questions
    f_q = ORIGINAL_FILES["question_bank"]
    q_out: list[dict[str, str]] = []
    for orig in questions:
        qid, grp = orig["question_id"], groups[orig["question_id"]]
        rec = dict(orig)
        statuses, scope = [], qid in SCOPE_REVIEW_QUESTIONS

        def add_q(orig: dict[str, str] = orig, qid: str = qid, **kw: str) -> None:
            ledger.add(record_id=qid, record_type="question", question_id=qid, original_file=f_q,
                       split=orig["split"], **kw)

        for col, (ov, nv, removed) in _repair_lists(rec, QUESTION_LIST_COLUMNS).items():
            statuses.append("repaired")
            add_q(issue_category="nan_list_element", field=col, original_value=ov, repaired_value=nv,
                  reason="removed empty/'nan' list element (no content lost)",
                  evidence=f"{removed} element(s) equal to a null token", repair_status="repaired",
                  validation_result="pass" if _list_clean(nv) else "fail")
        rec["dataset_version"] = REPAIRED_VERSION
        is_eligible = grp == "canonical"
        placeholder = _has_placeholder(orig["expected_concepts"], orig["expected_relationships"])
        if not is_eligible:
            statuses.append("flagged")
            add_q(issue_category="ineligible_question", field="eligibility_status", original_value="",
                  repaired_value="ineligible", reason=INELIGIBLE_REASON,
                  evidence=f"{grp}: 5 of 6 variants quarantined; the dataset requires 6 variants/question",
                  repair_status="flagged", validation_result="pass")
        if scope:
            statuses.append("flagged")
            add_q(issue_category="scope_review", field="scope_review", original_value="", repaired_value="True",
                  reason="question requires code/diagrams; kept eligible, a human decides exclusion",
                  evidence="LLM scope probe 2026-10-21 returned requires_code (100-mark 'develop a web application')",
                  repair_status="flagged", validation_result="pass")
        if placeholder:
            statuses.append("flagged")
            add_q(issue_category="placeholder_concepts", field="placeholder_concepts_flag", original_value="",
                  repaired_value="True", reason="placeholder concept annotation; flag only",
                  evidence="matched one of: " + ", ".join(PLACEHOLDER_PHRASES), repair_status="flagged",
                  validation_result="pass")
        rec.update({
            "eligibility_status": "eligible" if is_eligible else "ineligible",
            "eligibility_reason": "" if is_eligible else INELIGIBLE_REASON,
            "scope_review": str(scope), "placeholder_concepts_flag": str(placeholder), "repair_group": grp,
            "source_dataset_version": SOURCE_VERSION, "repair_status": _best_status(statuses),
        })
        q_out.append(rec)

    # ---------------------------------------------------------------- rubric
    f_r = ORIGINAL_FILES["rubric"]
    r_out: list[dict[str, str]] = []
    rekeyed = 0
    for r in rubric_rows:
        rec = {k: v for k, v in r.items() if k != "_orig_question_id"}
        statuses = []

        def add_r(r: dict[str, str] = r, **kw: str) -> None:
            ledger.add(record_id=r["criterion_id"], record_type="rubric_row", question_id=r["question_id"],
                       original_file=f_r, split=split_of.get(r["question_id"], ""), **kw)

        if "_orig_question_id" in r:
            rekeyed += 1
            statuses.append("repaired")
            add_r(issue_category="rubric_id_mismatch", field="question_id", original_value=r["_orig_question_id"],
                  repaired_value=r["question_id"],
                  reason="re-keyed to the replacement question using its source_replaced_question_id",
                  evidence=f"question_bank[{r['question_id']}].source_replaced_question_id == "
                           f"{r['_orig_question_id']}; repaired: id_mapping_from_source_field",
                  repair_status="repaired", validation_result="pass")
        for col, (ov, nv, removed) in _repair_lists(rec, QUESTION_LIST_COLUMNS).items():
            statuses.append("repaired")
            add_r(issue_category="nan_list_element", field=col, original_value=ov, repaired_value=nv,
                  reason="removed empty/'nan' list element (no content lost)",
                  evidence=f"{removed} element(s) equal to a null token", repair_status="repaired",
                  validation_result="pass" if _list_clean(nv) else "fail")
        rec["dataset_version"] = REPAIRED_VERSION
        rec["repair_status"] = _best_status(statuses)
        rec["source_dataset_version"] = SOURCE_VERSION
        r_out.append(rec)

    # ---------------------------------------------------------------- derived tables / accounting
    crit_map = build_criterion_map(eligible, r_out, qmarks_all)
    accounting = {g: {"original_answers": 0, "eligible": 0, "quarantined": 0, "repaired_ineligible_controls": 0}
                  for g in ("canonical", "replacement_block_A", "replacement_block_B")}
    seen: Counter[str] = Counter()
    for r in answers:
        accounting[groups[r["question_id"]]]["original_answers"] += 1
    for rows, key in ((eligible, "eligible"), (quarantine, "quarantined"), (controls, "repaired_ineligible_controls")):
        for r in rows:
            accounting[groups[r["question_id"]]][key] += 1
            seen[r["answer_id"]] += 1
    original_ids = [r["answer_id"] for r in answers]
    if sorted(seen) != sorted(original_ids) or any(c != 1 for c in seen.values()):
        raise AssertionError("accounting invariant violated: every original answer must appear exactly once")
    if len(original_ids) != len(eligible) + len(quarantine) + len(controls):
        raise AssertionError("accounting invariant violated: counts do not add up")

    for fname, cols in (("02_controlled_answers_eligible.csv", ANSWER_NEW_COLS), ("01_question_bank.csv", QUESTION_NEW_COLS),
                        ("03_rubric_criteria.csv", RUBRIC_NEW_COLS)):
        ledger.add(record_id=fname, record_type="file", original_file=fname, issue_category="schema_addition",
                   field=";".join(cols), reason="derived columns appended after the original columns; no original "
                   "column removed or reordered",
                   evidence="max_marks = question bank marks; marks left untouched" if "max_marks" in cols
                   else "derived by rule", repair_status="flagged", validation_result="pass")
        ledger.add(record_id=fname, record_type="file", original_file=fname, issue_category="version_stamp",
                   field="dataset_version", original_value=SOURCE_VERSION, repaired_value=REPAIRED_VERSION,
                   reason="every retained row is stamped with the repaired version; the original is kept in "
                   "source_dataset_version", evidence="applied to all rows of the file", repair_status="repaired",
                   validation_result="pass")

    # ---------------------------------------------------------------- write
    out.mkdir(parents=True, exist_ok=True)
    ans_cols = original_columns["answers"] + ANSWER_NEW_COLS
    q_cols = original_columns["question_bank"] + QUESTION_NEW_COLS
    ru_cols = original_columns["rubric"] + RUBRIC_NEW_COLS

    def frame(rows: list[dict[str, str]], cols: list[str]) -> pd.DataFrame:
        return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

    eligible_df = frame(eligible, ans_cols)
    q_df = frame(q_out, q_cols)
    write_csv(q_df, out / "01_question_bank.csv")
    write_csv(eligible_df, out / "02_controlled_answers_eligible.csv")
    write_csv(frame(r_out, ru_cols), out / "03_rubric_criteria.csv")
    for split in SPLITS:
        write_csv(eligible_df[eligible_df["split"] == split], out / f"controlled_answers_{split}.csv")
        write_csv(q_df[(q_df["split"] == split) & (q_df["eligibility_status"] == "eligible")],
                  out / f"question_bank_{split}.csv")
    write_csv(frame(quarantine, original_columns["answers"] + QUARANTINE_EXTRA_COLS), out / "quarantine.csv")
    write_csv(frame(controls, ans_cols + CONTROL_EXTRA_COLS), out / "repaired_ineligible_controls.csv")
    write_csv(frame(review_queue, REVIEW_COLS), out / "review_queue.csv")
    write_csv(frame(crit_map, CRITERION_MAP_COLS), out / "criterion_id_map.csv")
    write_csv(pd.DataFrame(ledger.rows, columns=MANIFEST_COLS), out / "repair_manifest.csv")

    split_consistent = True
    for split in SPLITS:
        file_ids = list(pd.read_csv(archive_dir / f"controlled_answers_{split}.csv", dtype=str,
                                    keep_default_na=False)["answer_id"])
        split_consistent &= file_ids == [r["answer_id"] for r in a_all.to_dict("records") if r["split"] == split]

    ledger_counts = {key: dict(sorted(Counter(r[col] for r in ledger.rows).items()))
                     for key, col in (("by_status", "repair_status"), ("by_category", "issue_category"),
                                      ("by_record_type", "record_type"))}
    qgroup = {r["question_id"]: groups[r["question_id"]] for r in q_out}
    by_group: dict[str, dict[str, int]] = {}
    for r in ledger.rows:
        g = qgroup.get(r["question_id"], "file")
        key = f"{r['record_type']}|{r['repair_status']}|{r['issue_category']}"
        by_group.setdefault(g, {})
        by_group[g][key] = by_group[g].get(key, 0) + 1

    elig_q = [r for r in q_out if r["eligibility_status"] == "eligible"]
    counts = {
        "original": {
            "questions": len(questions), "answers": len(answers), "rubric_rows": len(rubric_rows),
            "by_split_answers": dict(Counter(r["split"] for r in answers)),
            "by_split_questions": dict(Counter(r["split"] for r in questions)),
            "label_distribution": dict(Counter(r["answer_quality"] for r in answers)),
        },
        "repaired": {
            "eligible_answers": len(eligible), "eligible_questions": len(elig_q),
            "ineligible_questions": len(q_out) - len(elig_q), "quarantined_answers": len(quarantine),
            "repaired_ineligible_controls": len(controls), "rubric_rows": len(r_out),
            "review_queue": len(review_queue),
            "eligible_by_split": dict(Counter(r["split"] for r in eligible)),
            "eligible_questions_by_split": dict(Counter(r["split"] for r in elig_q)),
            "eligible_label_distribution": dict(Counter(r["answer_quality"] for r in eligible)),
            "quarantine_by_reason": dict(Counter(r["quarantine_reason"] for r in quarantine)),
            "template_negative_controls_eligible": sum(r["template_negative_control"] == "True" for r in eligible),
            "placeholder_flagged_eligible": sum(r["placeholder_concepts_flag"] == "True" for r in eligible),
            "scope_review_questions": sum(r["scope_review"] == "True" for r in q_out),
            "criterion_map_resolved": sum(r["mapping_status"] == "RESOLVED" for r in crit_map),
            "criterion_map_unresolved": sum(r["mapping_status"] == "UNRESOLVED" for r in crit_map),
            "criterion_map_marks_agree_true": sum(r["marks_agree"] == "True" for r in crit_map),
            "criterion_map_marks_agree_false": sum(r["marks_agree"] == "False" for r in crit_map),
            "rubric_rows_rekeyed": rekeyed,
        },
    }
    try:
        orig_manifest = json.loads((archive_dir / "00_MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        orig_manifest = {}
    manifest: dict[str, Any] = {
        "dataset_version": REPAIRED_VERSION,
        "source_dataset_version": SOURCE_VERSION,
        "repair_tool_version": REPAIR_TOOL_VERSION,
        "scope": "sample" if sample else "full",
        "scope_question_ids": scope_ids,
        "original_columns": original_columns,
        "original_manifest_claims": {k: orig_manifest.get(k) for k in ("qa", "questions", "answers", "canonical")},
        "original_sha256": original_hashes,
        "original_split_files_match_master_order": bool(split_consistent),
        "counts": counts,
        "accounting": accounting,
        "ledger": ledger_counts,
        "ledger_by_group": {g: dict(sorted(v.items())) for g, v in sorted(by_group.items())},
        "decisions": {
            "eligible_primary_set": "canonical questions (is_replacement != True); splits exactly as in the original",
            "quarantine": "block-A answers containing the token nan (unrecoverable_nan) and the other non-IRRELEVANT "
                          "replacement answers with the flat 10.0 mark (unsupported_flat_mark)",
            "replacement_irrelevant": "marks set to 0 by documented policy; excluded from the primary set "
                                      "(question_has_only_one_valid_variant)",
            "criterion_marks_format_for_repaired_controls": "positional text '0,0' (same positional format as the "
                                                            "original '5,5')",
            "template_rule": f"IRRELEVANT/MISCONCEPTION text shared by >= {TEMPLATE_MIN_QUESTIONS} questions",
            "placeholder_phrases": list(PLACEHOLDER_PHRASES),
            "scope_review_questions": list(SCOPE_REVIEW_QUESTIONS),
        },
    }
    write_json(manifest, out / "manifest.json")
    result: dict[str, Any] = {"manifest": manifest, "diff": diff, "out_dir": out, "groups": groups}

    if validate:
        from datasets.repair.validate_repaired import validate_dir

        report = validate_dir(out, archive_dir=archive_dir)
        write_json(report, out / "validation_report.json")
        result["validation"] = report
    finalize_outputs(out)
    return result


def finalize_outputs(out: Path) -> None:
    """Record file hashes and the real QA result in manifest.json and (re)generate DATASET_CARD.md."""
    from datasets.repair.card import render_card

    out = Path(out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    report_path = out / "validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    manifest["files"] = {p.name: sha256_file(p) for p in sorted(out.glob("*.csv"))}
    if report is not None:
        failed = [c["name"] for c in report["checks"] if c["hard"] and c["status"] == "fail"]
        manifest["qa"] = {"status": "FAIL" if failed else "PASS", "hard_checks_failed": failed,
                          "source": "validation_report.json (real checks); the original claim 'ALL PASS' is not "
                                    "carried over"}
    write_json(manifest, out / "manifest.json")
    metrics_path = out / "metrics_report.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
    (out / "DATASET_CARD.md").write_text(render_card(manifest, report, metrics), encoding="utf-8", newline="\n")


def diff_table(diff: list[dict[str, Any]]) -> str:
    """Per-record before/after table (markdown) for the sample run."""

    def short(s: str) -> str:
        return s if len(s) <= 36 else s[:33] + "..."

    lines = ["| answer_id | group | tier | split | disposition | status | mark before -> after | "
             "criterion_marks before -> after | other changes |",
             "|---|---|---|---|---|---|---|---|---|"]
    for d in diff:
        lines.append(f"| {d['answer_id']} | {d['group']} | {d['tier']} | {d['split']} | {d['disposition']} | "
                     f"{d.get('status', '')} | {d['orig_mark']} -> {d['new_mark']} | "
                     f"{short(d['orig_criterion_marks'])} -> {short(d['new_criterion_marks'])} | "
                     f"{'; '.join(d['changes']) or '-'} |")
    return "\n".join(lines)
