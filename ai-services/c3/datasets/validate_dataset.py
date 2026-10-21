# ruff: noqa: E501
"""Release validator for the C3 synthetic dataset (CLI + importable `validate_release`).

python datasets/validate_dataset.py [datasets/c3_synthetic_v6]     # exit 1 on any violation
python datasets/validate_dataset.py <dir> --json [path]            # also write a machine-readable report
                                                                   # (default <dir>/validation_report.json)
python datasets/validate_dataset.py <dir> --source datasets/source/questions_source.csv   # check coverage vs the file
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402

from app.schemas.marking import Rubric, RubricCriterion, ScoringLevel  # noqa: E402
from datasets.generator import C3_ROOT, load_tier_spec, tier_spec_sha256  # noqa: E402
from datasets.generator.checks import (  # noqa: E402
    contains_phrase,
    cue_classifier_accuracy,
    derive_evidence_spans,
    distinct_sentence_ratio,
    in_range,
    normalized_hash,
    pearson,
    ratio_concentration,
    split_sentences,
    tier_order_violations,
)
from datasets.generator.roles import load_env  # noqa: E402
from datasets.generator.splitting import SPLITS, build_parent_docs, max_cross_split_cosine  # noqa: E402
from datasets.generator.writer import OPTIONAL_EMPTY, sha256_file  # noqa: E402
from services.marking.rubric_validator import RubricValidationError, validate_rubric  # noqa: E402

DEFAULT_DIR = C3_ROOT / "datasets" / "c3_synthetic_v6"
EXCLUSION_CLASSES_ALLOWED = {"intentional_scope", "intentional_quality"}  # processing_failure is never a valid row
EXCLUDED_TRACE_COLUMNS = ["parent_question_id", "exclusion_class", "reason", "diagnostic", "source_file", "source_row"]
REPORT_SCHEMA = "c3-validation-report/1"
MAX_REPORT_IDS = 20
ALL_CODES = [
    "FILE_MISSING", "NAN_VALUE", "JSON_INVALID", "VERSION_MISMATCH", "MANIFEST_HASH", "MANIFEST_COUNTS",
    "MANIFEST_SPEC", "MARK_RANGE", "NORMALIZED_MISMATCH", "CRITERION_UNKNOWN", "CRITERION_SUM", "LEVEL_MISMATCH",
    "RUBRIC_NO_ZERO_LEVEL", "RUBRIC_LEVEL_EXCEEDS_MAX", "RUBRIC_LEVELS", "RUBRIC_SUM", "RUBRIC_INVALID",
    "RUBRIC_MISSING", "TIER_MISSING", "TIER_ORDER", "TIER_RANGE", "RATIO_CONCENTRATION", "LENGTH_CORR_OVERALL",
    "LENGTH_CORR_WITHIN", "LOW_SENTENCE_DIVERSITY", "IRRELEVANT_SHARED", "CUE_LEAK", "BANNED_PHRASE",
    "SPLIT_DUP_ANSWER", "SPLIT_NEAR_DUP_ANSWER", "SPLIT_QUESTION_SIMILARITY", "SPLIT_INCONSISTENT",
    "MODULE_SPLIT_COVERAGE", "EVIDENCE_SPAN_RANGE", "EVIDENCE_STALE", "MINDMAP_EDGE", "PLACEHOLDER_CONCEPT",
    "STATUS_UNSET", "EDGE_TIER_MISSING", "EXCLUDED_NO_REASON", "EXCLUDED_ALSO_KEPT", "EXCLUDED_UNTRACEABLE",
    "UNACCOUNTED_SOURCE_QUESTION",
]  # fmt: skip
JSON_COLS = {
    "questions": ["expected_concepts", "concept_graph"],
    "rubrics": ["required_concepts", "scoring_levels"],
    "answers": ["criterion_marks", "concept_status", "incorrect_concepts", "evidence_spans", "gold_mindmap"],
}
EPS = 1e-3


@dataclass
class Violation:
    code: str
    message: str
    ids: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        shown = ", ".join(self.ids[:5]) + (f" (+{len(self.ids) - 5} more)" if len(self.ids) > 5 else "")
        return f"{self.code}: {self.message}" + (f" [{shown}]" if self.ids else "")


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def _json_cols(df: pd.DataFrame, cols: list[str], table: str, out: list[Violation]) -> dict[str, list]:
    parsed: dict[str, list] = {}
    for col in cols:
        vals, bad = [], []
        for i, raw in enumerate(df[col]):
            try:
                vals.append(json.loads(raw))
            except json.JSONDecodeError:
                vals.append(None)
                bad.append(f"{table}[{i}]")
        parsed[col] = vals
        if bad:
            out.append(Violation("JSON_INVALID", f"{table}.{col} is not valid JSON", bad))
    return parsed


def validate_release(
    directory: str | Path, spec: dict | None = None, source_csv: str | Path | None = None
) -> list[Violation]:
    """Return all violations (empty list = release passes). See `validate_with_stats` for the informational data."""
    return validate_with_stats(directory, spec, source_csv)[0]


def validate_with_stats(
    directory: str | Path, spec: dict | None = None, source_csv: str | Path | None = None
) -> tuple[list[Violation], dict]:
    """(violations, stats). stats = informational numbers + warnings for the report; never changes pass/fail."""
    stats: dict = {"warnings": [], "complete": False}
    return _validate(Path(directory), spec or load_tier_spec(), source_csv, stats), stats


def _validate(d: Path, spec: dict, source_csv: str | Path | None, stats: dict) -> list[Violation]:  # noqa: C901
    th = spec["thresholds"]
    out: list[Violation] = []
    warnings: list[str] = stats["warnings"]

    split_files = [f"{k}_{s}.csv" for k in ("questions", "answers") for s in SPLITS]
    required = ["questions.csv", "rubrics.csv", "answers.csv", "excluded_questions.csv", "manifest.json", *split_files]
    missing = [f for f in required if not (d / f).exists()]
    if missing:
        return [Violation("FILE_MISSING", "required files are missing", missing)]

    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    q, r, a, ex = (_read(d / n) for n in ("questions.csv", "rubrics.csv", "answers.csv", "excluded_questions.csv"))
    tables = {"questions": q, "rubrics": r, "answers": a, "excluded_questions": ex}
    for n in split_files:
        tables[n[:-4]] = _read(d / n)

    # nan / empty / unresolved placeholder values --------------------------------------------------------------
    forbidden = {x.casefold() for x in spec["forbidden_text_values"]}
    for name, df in tables.items():
        bad = []
        for col in df.columns:
            stripped = df[col].str.strip()
            blank = (stripped == "").tolist()
            literal = stripped.str.casefold().isin(forbidden).tolist()
            is_empty_tier = (df["tier"] == "EMPTY").tolist() if "tier" in df else [False] * len(df)
            for i in range(len(df)):
                if col == "student_answer":
                    wrong = (not blank[i]) if is_empty_tier[i] else blank[i]
                    if wrong or literal[i]:
                        bad.append(f"{name}[{i}].{col}")
                elif (blank[i] and col not in OPTIONAL_EMPTY) or literal[i]:
                    bad.append(f"{name}[{i}].{col}")
        if bad:
            out.append(Violation("NAN_VALUE", f"{name}: empty / nan / None cells", bad))
    for i, v in enumerate(a["student_answer"]):
        if "<<" in v and ">>" in v:
            out.append(Violation("NAN_VALUE", "unresolved template placeholder in answer", [a["answer_id"].iloc[i]]))

    # versions + manifest ---------------------------------------------------------------------------------------
    versions = {manifest.get("dataset_version")}
    for df in tables.values():
        if "dataset_version" in df:
            versions |= set(df["dataset_version"])
    if len(versions) != 1:
        out.append(Violation("VERSION_MISMATCH", f"multiple dataset_version values: {sorted(map(str, versions))}"))
    for fname, meta in manifest.get("files", {}).items():
        p = d / fname
        if not p.exists() or sha256_file(p) != meta.get("sha256"):
            out.append(Violation("MANIFEST_HASH", f"sha256 mismatch for {fname}", [fname]))
        elif len(_read(p)) != meta.get("rows"):
            out.append(Violation("MANIFEST_COUNTS", f"row count mismatch for {fname}", [fname]))
    for fname in required:
        if fname != "manifest.json" and fname not in manifest.get("files", {}):
            out.append(Violation("MANIFEST_HASH", f"{fname} is not listed in manifest", [fname]))
    counts = manifest.get("counts", {})
    for key, actual in (
        ("questions", len(q)),
        ("answers", len(a)),
        ("rubric_criteria", len(r)),
        ("excluded_questions", len(ex)),
    ):
        if counts.get(key) != actual:
            out.append(Violation("MANIFEST_COUNTS", f"manifest counts.{key}={counts.get(key)} but files hold {actual}"))
    if manifest.get("tier_spec_sha256") != tier_spec_sha256():
        out.append(Violation("MANIFEST_SPEC", "manifest tier_spec_sha256 differs from the current tier_spec.json"))

    qj = _json_cols(q, JSON_COLS["questions"], "questions", out)
    rj = _json_cols(r, JSON_COLS["rubrics"], "rubrics", out)
    aj = _json_cols(a, JSON_COLS["answers"], "answers", out)
    if any(v.code == "JSON_INVALID" for v in out):
        return out

    # statuses ------------------------------------------------------------------------------------------------------
    bad = [x for x, rs, ss in zip(q["question_id"], q["rubric_status"], q["scope_status"], strict=True)
           if rs not in spec["rubric_status_values"] or ss not in spec["scope_status_values"]]  # fmt: skip
    if bad:
        out.append(Violation("STATUS_UNSET", "rubric_status/scope_status missing or unknown", bad))
    noreason = [x for x, rs in zip(ex["question_id"], ex["reason"], strict=True) if not rs.strip()]
    if noreason:
        out.append(Violation("EXCLUDED_NO_REASON", "excluded questions without a reason", noreason))
    kept_parents = set(q["parent_question_id"])
    ex_parent = ex["parent_question_id"] if "parent_question_id" in ex else ex["question_id"]
    both = sorted((set(ex["question_id"]) | set(ex_parent)) & (kept_parents | set(q["question_id"])))
    if both:
        out.append(Violation("EXCLUDED_ALSO_KEPT", "question is both excluded and kept", both))
    _check_exclusion_traceability(ex, ex_parent, q, manifest, source_csv, out, warnings)

    # rubrics -------------------------------------------------------------------------------------------------------------
    qmax = dict(zip(q["question_id"], q["max_marks"].astype(float), strict=True))
    crit_ids: dict[str, set[str]] = defaultdict(set)
    level_marks: dict[tuple[str, str], dict[str, float]] = {}
    by_q: dict[str, list[int]] = defaultdict(list)
    for i, qid in enumerate(r["question_id"]):
        by_q[qid].append(i)
    missing_rub = [x for x in qmax if x not in by_q]
    if missing_rub:
        out.append(Violation("RUBRIC_MISSING", "questions without rubric rows", missing_rub))
    zero_bad, exceed, levels_bad, sum_bad, invalid = [], [], [], [], []
    rubric_id_of = dict(zip(q["question_id"], q["rubric_id"], strict=True))
    for qid, idxs in by_q.items():
        total, criteria = 0.0, []
        for i in idxs:
            cid, cmax = r["criterion_id"].iloc[i], float(r["max_marks"].iloc[i])
            lvls = rj["scoring_levels"][i]
            total += cmax
            crit_ids[qid].add(cid)
            marks = sorted(float(lv["mark"]) for lv in lvls)
            if not marks or marks[0] != 0:
                zero_bad.append(cid)
            if any(m > cmax + 1e-9 for m in marks):
                exceed.append(cid)
            if (
                not th["min_levels"] <= len(marks) <= th["max_levels"]
                or len(set(marks)) != len(marks)
                or (marks and abs(marks[-1] - cmax) > 1e-9)
            ):  # noqa: E501
                levels_bad.append(cid)
            level_marks[(qid, cid)] = {lv["level_id"]: float(lv["mark"]) for lv in lvls}
            try:
                criteria.append(
                    RubricCriterion(
                        criterion_id=cid, description=r["description"].iloc[i], max_marks=cmax,
                        required_concepts=rj["required_concepts"][i],
                        scoring_levels=[ScoringLevel(**lv) for lv in lvls],
                    )
                )  # fmt: skip
            except Exception as exc:  # noqa: BLE001 - report any schema error as a violation
                invalid.append(f"{cid}: {str(exc)[:80]}")
        if qid in qmax and abs(total - qmax[qid]) > EPS:
            sum_bad.append(qid)
        if rubric_id_of.get(qid) != r["rubric_id"].iloc[idxs[0]]:
            invalid.append(f"{qid}: rubric_id differs from questions.csv")
        if criteria and len(criteria) == len(idxs):
            try:
                validate_rubric(Rubric(rubric_id=r["rubric_id"].iloc[idxs[0]], title="validation", criteria=criteria))
            except (RubricValidationError, ValueError) as exc:
                invalid.append(f"{qid}: {str(exc)[:80]}")
    for code, msg, ids in (
        ("RUBRIC_NO_ZERO_LEVEL", "criteria without an explicit mark-0 level", zero_bad),
        ("RUBRIC_LEVEL_EXCEEDS_MAX", "level marks above criterion max", exceed),
        ("RUBRIC_LEVELS", "criteria need 3-5 distinct levels whose top equals max_marks", levels_bad),
        ("RUBRIC_SUM", "criterion maxima do not sum to question max_marks", sum_bad),
        ("RUBRIC_INVALID", "rubric fails schema / validate_rubric", invalid),
    ):
        if ids:
            out.append(Violation(code, msg, ids))

    # placeholder concepts ---------------------------------------------------------------------------------------------------
    deny = {s.casefold() for s in spec["placeholder_concepts"]}
    ph = set()
    for qid, concepts in zip(q["question_id"], qj["expected_concepts"], strict=True):
        ph |= {qid for c in concepts if str(c).strip().casefold() in deny}
    for cid, concepts in zip(r["criterion_id"], rj["required_concepts"], strict=True):
        if any(str(c).strip().casefold() in deny for c in concepts):
            ph.add(cid)
    if ph:
        out.append(Violation("PLACEHOLDER_CONCEPT", "placeholder concept strings", sorted(ph)))

    # answer-level numeric checks ----------------------------------------------------------------------------------------------
    exp, mx, norm = a["expected_mark"].astype(float), a["max_marks"].astype(float), a["normalized_mark"].astype(float)
    ids = list(a["answer_id"])
    rng_bad = [ids[i] for i in range(len(a)) if exp[i] < -1e-9 or exp[i] > mx[i] + 1e-9]
    if rng_bad:
        out.append(Violation("MARK_RANGE", "expected_mark outside [0, max_marks]", rng_bad))
    nm_bad = [ids[i] for i in range(len(a)) if mx[i] <= 0 or abs(norm[i] - exp[i] / mx[i]) > 1e-4]
    if nm_bad:
        out.append(Violation("NORMALIZED_MISMATCH", "normalized_mark != expected_mark / max_marks", nm_bad))
    a_qid, a_tier, a_text = a["question_id"].tolist(), a["tier"].tolist(), a["student_answer"].tolist()
    a_split = a["split"].tolist()
    unknown, sum_mis, lvl_mis, max_mis = [], [], [], []
    for i, aid in enumerate(ids):
        qid = a_qid[i]
        total = 0.0
        for cm in aj["criterion_marks"][i]:
            cid = cm.get("criterion_id")
            if cid not in crit_ids.get(qid, set()):
                unknown.append(aid)
                continue
            lm = level_marks[(qid, cid)]
            if cm.get("level_id") not in lm or abs(lm[cm["level_id"]] - float(cm["mark"])) > EPS:
                lvl_mis.append(aid)
            total += float(cm["mark"])
        if abs(total - exp[i]) > EPS or {c["criterion_id"] for c in aj["criterion_marks"][i]} != crit_ids.get(
            qid, set()
        ):
            sum_mis.append(aid)
        if qid in qmax and abs(qmax[qid] - mx[i]) > EPS:
            max_mis.append(aid)
    if unknown:
        out.append(Violation("CRITERION_UNKNOWN", "criterion ids not present in rubrics.csv", sorted(set(unknown))))
    if sum_mis or max_mis:
        out.append(
            Violation(
                "CRITERION_SUM",
                "criterion_marks do not cover the rubric / sum to expected_mark / match max",
                sorted(set(sum_mis + max_mis)),
            )
        )  # noqa: E501
    if lvl_mis:
        out.append(
            Violation(
                "LEVEL_MISMATCH", "criterion_marks level mark differs from the rubric level", sorted(set(lvl_mis))
            )
        )

    # tiers ---------------------------------------------------------------------------------------------------------------------
    a = a.assign(_exp=exp, _mx=mx, _norm=norm, _wc=a["student_answer"].str.split().str.len())
    core = spec["core_tiers"]
    tier_missing, order_bad, range_bad = [], [], []
    for qid, grp in a.groupby("question_id"):
        means = {t: float(g["_norm"].mean()) for t, g in grp.groupby("tier") if t in core}
        if any(t not in means for t in core):
            tier_missing.append(qid)
            continue
        if tier_order_violations(means, spec):
            order_bad.append(qid)
    for i, aid in enumerate(ids):
        rg = spec["normalized_mark_ranges"].get(a_tier[i])
        if rg is None or not in_range(norm[i], rg):
            range_bad.append(aid)
    if tier_missing:
        out.append(Violation("TIER_MISSING", "questions lacking one of the six core tiers", tier_missing))
    if order_bad:
        out.append(
            Violation(
                "TIER_ORDER",
                "per-question tier means violate FULL>=MOSTLY>PARTIAL>=MISSING>=MISCONCEPTION>=IRRELEVANT=0",
                order_bad,
            )
        )  # noqa: E501
    if range_bad:
        out.append(Violation("TIER_RANGE", "normalized_mark outside the tier's allowed range", range_bad))

    # label / length statistics -----------------------------------------------------------------------------------------------------
    conc = ratio_concentration(list(norm))
    if conc > th["max_share_on_top7_ratios"]:
        out.append(Violation("RATIO_CONCENTRATION", f"top-7 ratio share {conc:.3f} > {th['max_share_on_top7_ratios']}"))
    # informational only: the same metric per split (the enforced check above is dataset-wide)
    per_split_conc = {s: ratio_concentration([float(x) for x in a[a["split"] == s]["_norm"]]) for s in SPLITS}
    stats["ratio_concentration"] = {
        "scope": th.get("ratio_metric_scope", ""),
        "threshold": th["max_share_on_top7_ratios"],
        "dataset_wide": round(conc, 4),
        "enforced": True,
        "per_split_informational": {s: round(v, 4) for s, v in per_split_conc.items()},
    }
    for s, v in per_split_conc.items():
        if v > th["max_share_on_top7_ratios"]:
            warnings.append(
                f"ratio concentration in split '{s}' is {v:.3f} > {th['max_share_on_top7_ratios']} "
                "(informational only; the enforced check is dataset-wide)"
            )
    stats["tier_means"] = {t: round(float(g["_norm"].mean()), 4) for t, g in a.groupby("tier")}
    stats["length_correlation"] = {"overall_pearson": None, "within_question_mean_pearson": None, "n_within": 0}
    sub = a[~a["tier"].isin(th["length_corr_exclude_tiers"])]
    if len(sub) > 3:
        rr = pearson(list(sub["_wc"]), list(sub["_norm"]))
        stats["length_correlation"]["overall_pearson"] = round(rr, 4)
        if abs(rr) > th["max_length_mark_pearson"]:
            out.append(
                Violation(
                    "LENGTH_CORR_OVERALL",
                    f"|pearson(word_count, normalized_mark)|={abs(rr):.3f} > {th['max_length_mark_pearson']}",
                )
            )  # noqa: E501
        within = [pearson(list(g["_wc"]), list(g["_norm"])) for _, g in sub.groupby("question_id") if len(g) >= 6]
        if within:
            stats["length_correlation"]["within_question_mean_pearson"] = round(sum(within) / len(within), 4)
            stats["length_correlation"]["n_within"] = len(within)
        if within and abs(sum(within) / len(within)) > th["max_length_mark_pearson"]:
            out.append(
                Violation(
                    "LENGTH_CORR_WITHIN",
                    f"mean within-question pearson {sum(within) / len(within):.3f} > {th['max_length_mark_pearson']}",
                )
            )  # noqa: E501
    texts = [t for t in a["student_answer"] if t.strip()]
    dr = distinct_sentence_ratio(texts)
    stats["distinct_sentence_ratio"] = round(dr, 4)
    if dr < th["min_distinct_sentence_ratio"]:
        out.append(
            Violation(
                "LOW_SENTENCE_DIVERSITY", f"distinct sentence ratio {dr:.3f} < {th['min_distinct_sentence_ratio']}"
            )
        )
    shared: dict[str, set[str]] = defaultdict(set)
    for t, qid, tx in zip(a["tier"], a["question_id"], a["student_answer"], strict=True):
        if t == "IRRELEVANT":
            shared[normalized_hash(tx)].add(qid)
    multi = sorted(x for s in shared.values() if len(s) > 1 for x in s)
    if multi:
        out.append(Violation("IRRELEVANT_SHARED", "identical IRRELEVANT text used for several questions", multi))
    banned = [
        ids[i]
        for i, tx in enumerate(a["student_answer"])
        if any(contains_phrase(tx, p) for p in spec["banned_cue_phrases"])
    ]
    if banned:
        out.append(Violation("BANNED_PHRASE", "answers contain banned cue phrases", banned))
    sp = a["split"]
    train = a[(sp == "train") & a["tier"].isin(core)]
    test = a[(sp == "test") & a["tier"].isin(core)]
    if len(test) >= th["cue_min_test_samples"] and train["tier"].nunique() > 1:
        acc = cue_classifier_accuracy(
            list(train["student_answer"]), list(train["tier"]), list(test["student_answer"]), list(test["tier"])
        )  # noqa: E501
        stats["cue_classifier_accuracy"] = round(acc, 4)
        if acc > th["max_cue_classifier_accuracy"]:
            out.append(
                Violation(
                    "CUE_LEAK",
                    f"text-only cue classifier reaches {acc:.3f} accuracy on test > {th['max_cue_classifier_accuracy']}",
                )
            )  # noqa: E501

    # splits ---------------------------------------------------------------------------------------------------------------------------
    q_split = dict(zip(q["question_id"], q["split"], strict=True))
    inc = [ids[i] for i in range(len(a)) if q_split.get(a_qid[i]) != a_split[i]]
    parent_split: dict[str, set[str]] = defaultdict(set)
    for pid, s in zip(q["parent_question_id"], q["split"], strict=True):
        parent_split[pid].add(s)
    inc += [p for p, s in parent_split.items() if len(s) > 1]
    for s in SPLITS:
        if set(tables[f"answers_{s}"]["answer_id"]) != set(a[a["split"] == s]["answer_id"]) or set(
            tables[f"questions_{s}"]["question_id"]
        ) != set(q[q["split"] == s]["question_id"]):  # noqa: E501
            inc.append(f"split file {s}")
    if inc:
        out.append(Violation("SPLIT_INCONSISTENT", "split assignment / split files are inconsistent", inc))
    seen: dict[str, str] = {}
    dup = []
    for aid, s, tx in zip(a["answer_id"], a["split"], a["student_answer"], strict=True):
        if tx.strip():
            owner = seen.setdefault(normalized_hash(tx), s)
            if owner != s:
                dup.append(aid)
    if dup:
        out.append(Violation("SPLIT_DUP_ANSWER", "identical answer text appears in several splits", dup))
    longish = a[(a["student_answer"].str.split().str.len() >= 8)].reset_index(drop=True)
    if len(longish) > 1 and longish["split"].nunique() > 1:
        mat = TfidfVectorizer(token_pattern=r"[A-Za-z0-9']+").fit_transform(longish["student_answer"])
        near = set()
        for s in SPLITS:
            mine = (longish["split"] == s).to_numpy()
            if mine.any() and (~mine).any():
                sims = (mat[mine] @ mat[~mine].T).max(axis=1).toarray().ravel()
                near |= {
                    longish["answer_id"][mine].tolist()[j]
                    for j in (sims > th["max_answer_near_duplicate_cosine"]).nonzero()[0]
                }  # noqa: E501
        if near:
            out.append(
                Violation("SPLIT_NEAR_DUP_ANSWER", "near-duplicate answers (TF-IDF cosine) across splits", sorted(near))
            )
    rows = [
        {"parent_question_id": p, "module_code": m, "max_marks": mk, "question_text": t, "expected_concepts": c}
        for p, m, mk, t, c in zip(
            q["parent_question_id"],
            q["module_code"],
            q["max_marks"].astype(float),
            q["question_text"],
            qj["expected_concepts"],
            strict=True,
        )  # noqa: E501
    ]
    docs = build_parent_docs(rows)
    if len(docs) >= 2:
        split_of = {pid: next(iter(s)) for pid, s in parent_split.items()}
        cross, pair = max_cross_split_cosine(docs, split_of)
        if cross >= th["max_cross_split_cosine"]:
            out.append(
                Violation(
                    "SPLIT_QUESTION_SIMILARITY",
                    f"cross-split question cosine {cross:.2f} >= {th['max_cross_split_cosine']}",
                    list(pair or ()),
                )
            )  # noqa: E501
    per_mod: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for m, pid, s in zip(q["module_code"], q["parent_question_id"], q["split"], strict=True):
        per_mod[m][s].add(pid)
    thin = [
        m
        for m, v in per_mod.items()
        if sum(len(x) for x in v.values()) >= th["min_questions_for_module_in_every_split"] and set(v) != set(SPLITS)
    ]  # noqa: E501
    if thin:
        out.append(Violation("MODULE_SPLIT_COVERAGE", "module with >=3 questions missing from a split", thin))
    edge_gap = [
        f"{s}:{t}" for s in SPLITS for t in spec["edge_tiers"] if not ((a["split"] == s) & (a["tier"] == t)).any()
    ]
    if edge_gap:
        out.append(Violation("EDGE_TIER_MISSING", "edge-case tier absent from a split", edge_gap))

    # annotations -------------------------------------------------------------------------------------------------------------------------
    ev_range, ev_stale, mm_bad = [], [], []
    for i, aid in enumerate(ids):
        text = a_text[i]
        n_sent = len(split_sentences(text))
        spans, status = aj["evidence_spans"][i], aj["concept_status"][i]
        if any(not isinstance(k, int) or k < 0 or k >= n_sent for v in spans.values() for k in v):
            ev_range.append(aid)
        elif spans != derive_evidence_spans(text, status):
            ev_stale.append(aid)
        mm = aj["gold_mindmap"][i]
        node_ids = [n["id"] for n in mm.get("nodes", [])]
        if len(set(node_ids)) != len(node_ids) or any(
            e["source"] not in node_ids or e["target"] not in node_ids for e in mm.get("edges", [])
        ):  # noqa: E501
            mm_bad.append(aid)
        if a_tier[i] in ("EMPTY", "IRRELEVANT") and (mm.get("nodes") or mm.get("edges")):
            mm_bad.append(aid)
    if ev_range:
        out.append(Violation("EVIDENCE_SPAN_RANGE", "evidence span index outside the sentence count", ev_range))
    if ev_stale:
        out.append(
            Violation("EVIDENCE_STALE", "evidence spans differ from spans derived from the final text", ev_stale)
        )
    if mm_bad:
        out.append(
            Violation(
                "MINDMAP_EDGE",
                "gold_mindmap edges reference missing nodes / non-empty graph for EMPTY or IRRELEVANT",
                mm_bad,
            )
        )  # noqa: E501
    stats["complete"] = True
    return out


def _check_exclusion_traceability(  # noqa: C901
    ex: pd.DataFrame, ex_parent: pd.Series, q: pd.DataFrame, manifest: dict,
    source_csv: str | Path | None, out: list[Violation], warnings: list[str],
) -> None:  # fmt: skip
    """Every excluded row is classified/traceable and every source question is kept or excluded."""
    missing_cols = [c for c in EXCLUDED_TRACE_COLUMNS if c not in ex.columns]
    if missing_cols:
        out.append(Violation("EXCLUDED_UNTRACEABLE", f"excluded_questions.csv lacks columns {missing_cols}"))
    else:
        bad_class = [x for x, c in zip(ex["question_id"], ex["exclusion_class"], strict=True)
                     if c not in EXCLUSION_CLASSES_ALLOWED]  # fmt: skip
        no_file = [x for x, f in zip(ex["question_id"], ex["source_file"], strict=True) if not f.strip()]
        bad_row = [x for x, r in zip(ex["question_id"], ex["source_row"], strict=True)
                   if not r.strip().isdigit() or int(r) < 1]  # fmt: skip
        for ids, msg in (
            (bad_class, "exclusion_class missing or not intentional_scope/intentional_quality "
                        "(processing failures must never be written as exclusions)"),
            (no_file, "source_file missing"),
            (bad_row, "source_row missing or not a 1-based row index"),
        ):  # fmt: skip
            if ids:
                out.append(Violation("EXCLUDED_UNTRACEABLE", msg, ids))
    source_ids = manifest.get("source_question_ids")
    if source_csv is not None:
        file_ids = pd.read_csv(source_csv, dtype=str, keep_default_na=False)["question_id"].str.strip().tolist()
        n = manifest.get("source_questions")
        source_ids = file_ids[:n] if isinstance(n, int) and n > 0 else file_ids
    if not source_ids:
        warnings.append("source coverage check skipped: manifest has no source_question_ids and no --source given")
        return
    if not missing_cols:
        pos = {sid: i + 1 for i, sid in enumerate(source_ids)}
        wrong = [x for x, p, r in zip(ex["question_id"], ex_parent, ex["source_row"], strict=True)
                 if p in pos and r.strip().isdigit() and int(r) != pos[p]]  # fmt: skip
        if wrong:
            out.append(
                Violation("EXCLUDED_UNTRACEABLE", "source_row does not match the question's position in the source", wrong)
            )
    accounted = set(q["parent_question_id"]) | set(q["question_id"]) | set(ex_parent) | set(ex["question_id"])
    lost = [sid for sid in source_ids if sid not in accounted]
    if lost:
        out.append(Violation("UNACCOUNTED_SOURCE_QUESTION", "source questions neither kept nor excluded", lost))


def print_report(violations: list[Violation], stats: dict | None = None) -> None:
    by_code: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        by_code[v.code].append(v)
    width = max(len(c) for c in ALL_CODES)
    print(f"{'CHECK':<{width}}  RESULT")
    for code in ALL_CODES:
        print(f"{code:<{width}}  {'FAIL (' + str(len(by_code[code])) + ')' if code in by_code else 'ok'}")
    for v in violations:
        print(" -", v)
    summary = Counter(v.code for v in violations)
    print(f"\n{len(violations)} violation(s) across {len(summary)} check(s)" if violations else "\nAll checks passed")
    if stats and "ratio_concentration" in stats:
        rc = stats["ratio_concentration"]
        print(f"\nratio concentration (enforced, dataset-wide): {rc['dataset_wide']} (max {rc['threshold']})")
        print("ratio concentration per split (informational): " + ", ".join(
            f"{s}={v}" for s, v in rc["per_split_informational"].items()))  # fmt: skip
    for w in (stats or {}).get("warnings", []):
        print(f"WARNING: {w}")


def build_report(directory: str | Path, violations: list[Violation], stats: dict, spec: dict | None = None) -> dict:
    """Machine-readable validation report (JSON-serialisable)."""
    d = Path(directory)
    spec = spec or load_tier_spec()
    manifest: dict = {}
    if (d / "manifest.json").exists():
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    files = {}
    if d.is_dir():
        files = {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                 for p in sorted(d.iterdir()) if p.is_file() and p.name != "validation_report.json"}  # fmt: skip
    counts: dict = {}
    if (d / "questions.csv").exists() and (d / "answers.csv").exists():
        q, a = _read(d / "questions.csv"), _read(d / "answers.csv")
        counts = {
            "questions": len(q), "answers": len(a),
            "questions_by_split": dict(sorted(Counter(q["split"]).items())),
            "answers_by_split": dict(sorted(Counter(a["split"]).items())),
        }  # fmt: skip
        if (d / "excluded_questions.csv").exists():
            ex = _read(d / "excluded_questions.csv")
            counts["excluded_questions"] = len(ex)
            by_class = Counter(ex["exclusion_class"]) if "exclusion_class" in ex else Counter()
            counts["excluded_by_class"] = dict(sorted(by_class.items()))
    failed = {v.code for v in violations}
    complete = bool(stats.get("complete"))
    return {
        "report_schema": REPORT_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset_version": manifest.get("dataset_version"),
        "directory": str(d),
        "passed": not violations,
        "counts": counts,
        "files": files,
        "checks": [{"code": c, "passed": c not in failed, "ran": complete or c in failed} for c in ALL_CODES],
        "violations": [
            {"code": v.code, "message": v.message, "n_ids": len(v.ids), "ids": v.ids[:MAX_REPORT_IDS]}
            for v in violations
        ],
        "warnings": stats.get("warnings", []),
        "ratio_concentration": stats.get("ratio_concentration"),
        "tier_means": stats.get("tier_means"),
        "length_correlation": stats.get("length_correlation"),
        "distinct_sentence_ratio": stats.get("distinct_sentence_ratio"),
        "cue_classifier_accuracy": stats.get("cue_classifier_accuracy"),
        "thresholds": {k: v for k, v in spec["thresholds"].items() if not isinstance(v, dict)},
    }


def main(argv: list[str] | None = None) -> int:
    load_env()  # ai-services/c3/.env; real environment variables still win (dotenv override=False)
    ap = argparse.ArgumentParser(description="Validate a C3 dataset release (exit 1 on any violation).")
    ap.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--json", nargs="?", const="", default=None, metavar="PATH",
                    help="write a machine-readable report (default <directory>/validation_report.json)")  # fmt: skip
    ap.add_argument("--source", type=Path, default=None, help="source CSV to check question coverage against")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    violations, stats = validate_with_stats(args.directory, source_csv=args.source)
    print_report(violations, stats)
    if args.json is not None:
        path = Path(args.json) if args.json else args.directory / "validation_report.json"
        path.write_text(json.dumps(build_report(args.directory, violations, stats), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote validation report to {path}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
