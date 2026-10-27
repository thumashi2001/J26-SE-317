"""Concept-level semantic matching experiment for FR-C3-09 (lexical baseline vs local MiniLM embeddings vs hybrid).

Protocol (two separate commands so the held-out split cannot influence any choice):

    python -m experiments.semantic_matching.run_eval select     # reads ONLY the dev + validation splits; writes frozen_config.json
    python -m experiments.semantic_matching.run_eval evaluate   # reads frozen_config.json, then scores the held-out test split once

Ground truth is the per-concept label fixed when each fixture answer was written (see fixtures.json "label_provenance");
it is author-labelled by construction and NOT human-marker validated. No label is derived from any model output.
Nothing here changes the live /assess behaviour: the experiment is offline and reads only local files and the cached
all-MiniLM-L6-v2 weights.

STATUS: exploratory offline experiment (pretrained MiniLM, no training). Running select/evaluate rewrites
frozen_config.json and the results JSON in the repository, so do not run it casually.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from services.preprocessing.text_normalizer import process_text, tokenize  # noqa: E402
from services.rag.embeddings import LocalSentenceTransformerEmbedding  # noqa: E402
from services.semantic.baseline import token_overlap_score  # noqa: E402

FIXTURES = HERE / "fixtures.json"
FROZEN = HERE / "frozen_config.json"
RESULTS = ROOT.parents[1] / "reports" / "c3_remediation" / "experiments" / "semantic_matching_results.json"
DATASET_TEST = ROOT / "datasets" / "c3_phase3_v5_repaired_v2" / "controlled_answers_test.csv"
# Fixed a priori (not tuned): a sentence that negates is not evidence that the concept is demonstrated.
NEGATIONS = {"not", "no", "never", "cannot", "can't", "without", "none", "nothing", "neither", "nor"}
W_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
METHODS = ["M0_lexical_current", "M1_embedding_name", "M2_embedding_description", "M3_hybrid_guarded", "M3b_hybrid_unguarded", "M4_length_only"]
HYBRIDS = ("M3_hybrid_guarded", "M3b_hybrid_unguarded")


def fixtures_hash() -> str:
    """SHA-256 of the fixture file, checked so selection and evaluation use the same data."""
    return hashlib.sha256(FIXTURES.read_bytes()).hexdigest()


def load_items(splits: tuple[str, ...]) -> list[dict]:
    """Fixture items for the requested splits (the test split is never loaded during selection)."""
    doc = json.loads(FIXTURES.read_text(encoding="utf8"))
    return [i for i in doc["items"] if i["split"] in splits]


def mark_from_count(n_demonstrated: int, n_concepts: int) -> int:
    """Toy mark rule for the experiment: 0 / 2 / 4 by how many concepts are demonstrated."""
    return 0 if n_demonstrated == 0 else (4 if n_demonstrated == n_concepts else 2)


def build_rows(items: list[dict], emb: LocalSentenceTransformerEmbedding) -> list[dict]:
    """One row per (answer, concept) with lexical and embedding scores."""
    rows = []
    for item in items:
        for ans in item["answers"]:
            processed = process_text(ans["text"])
            sents = processed.sentences or [ans["text"]]
            tokens = processed.tokens
            sent_vecs = emb.embed(sents, task="document")
            for c in item["concepts"]:
                name_vec = emb.embed([c["name"]], task="query")[0]
                desc_vec = emb.embed([f"{c['name']}: {c['description']}"], task="query")[0]
                sims_name = sent_vecs @ name_vec
                sims_desc = sent_vecs @ desc_vec
                best = int(np.argmax(sims_desc))
                negated = bool(NEGATIONS & {t.lower() for t in tokenize(sents[best])})
                rows.append({
                    "split": item["split"], "item": item["item_id"], "answer_id": ans["answer_id"], "type": ans["type"],
                    "concept": c["id"], "label": int(c["id"] in ans["demonstrated"]), "n_concepts": len(item["concepts"]),
                    "lex": token_overlap_score(c["name"], tokens), "emb_name": float(sims_name.max()),
                    "emb_desc": float(sims_desc.max()), "length": len(tokens), "negated": negated,
                })
    return rows


def score_of(method: str, row: dict, params: dict) -> float:
    """The score a method assigns to a row."""
    if method == "M0_lexical_current":
        return row["lex"]
    if method == "M1_embedding_name":
        return row["emb_name"]
    if method == "M2_embedding_description":
        return row["emb_desc"]
    if method in HYBRIDS:
        s = params["w"] * row["emb_desc"] + (1 - params["w"]) * row["lex"]
        return 0.0 if (method == "M3_hybrid_guarded" and row["negated"]) else s
    if method == "M4_length_only":
        return float(row["length"]) * params.get("direction", 1)
    raise KeyError(method)


def f1_of(pred: np.ndarray, y: np.ndarray) -> float:
    """F1 of binary predictions against labels."""
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    return 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)


def select_threshold(scores: np.ndarray, y: np.ndarray) -> float:
    """Highest validation F1; ties go to the larger (more conservative) threshold. Uses validation rows only."""
    uniq = np.unique(scores)
    cands = list(uniq) + [(a + b) / 2 for a, b in zip(uniq[:-1], uniq[1:])] + [uniq.max() + 1e-6]
    best_t, best_f = None, -1.0
    for t in sorted(cands):
        f = f1_of((scores >= t).astype(int), y)
        if f >= best_f:
            best_t, best_f = float(t), f
    return best_t


def fit_method(method: str, rows: list[dict]) -> dict:
    """Choose a method's threshold (and blend weight) on validation only."""
    y = np.array([r["label"] for r in rows])
    if method == "M0_lexical_current":
        return {"threshold": 1.0, "note": "existing rule: concept 'demonstrated' only when overlap == 1.0 (not tuned)"}
    if method in HYBRIDS:
        best = None
        for w in W_GRID:
            s = np.array([score_of(method, r, {"w": w}) for r in rows])
            t = select_threshold(s, y)
            f = f1_of((s >= t).astype(int), y)
            if best is None or f > best[0] or (f == best[0] and w > best[1]["w"]):
                best = (f, {"w": w, "threshold": t})
        return best[1]
    if method == "M4_length_only":
        best = None
        for d in (1, -1):
            s = np.array([score_of(method, r, {"direction": d}) for r in rows])
            t = select_threshold(s, y)
            f = f1_of((s >= t).astype(int), y)
            if best is None or f > best[0]:
                best = (f, {"direction": d, "threshold": t})
        return best[1]
    s = np.array([score_of(method, r, {}) for r in rows])
    return {"threshold": select_threshold(s, y)}


def predict(method: str, rows: list[dict], params: dict) -> np.ndarray:
    """Binary decisions: score at or above the fitted threshold."""
    s = np.array([score_of(method, r, params) for r in rows])
    return (s >= params["threshold"]).astype(int)


def answer_marks(rows: list[dict], pred: np.ndarray) -> dict[str, tuple[int, int]]:
    """True and predicted toy marks per answer, derived from concept decisions."""
    by: dict[str, dict] = {}
    for r, p in zip(rows, pred, strict=True):
        a = by.setdefault(r["answer_id"], {"n": r["n_concepts"], "pred": 0, "true": 0, "type": r["type"]})
        a["pred"] += int(p)
        a["true"] += r["label"]
    return {k: (mark_from_count(v["true"], v["n"]), mark_from_count(v["pred"], v["n"])) for k, v in by.items()}


def metrics(method: str, rows: list[dict], params: dict, boot: bool = True) -> dict:
    """Precision, recall, F1 and optional bootstrap interval for a method."""
    y = np.array([r["label"] for r in rows])
    pred = predict(method, rows, params)
    scores = np.array([score_of(method, r, params) for r in rows])
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    marks = answer_marks(rows, pred)
    diffs = [abs(e - a) for e, a in marks.values()]
    by_type = {}
    for t in sorted({r["type"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["type"] == t]
        yt, pt = y[idx], pred[idx]
        by_type[t] = {"n": len(idx), "positives": int(yt.sum()), "recall": float(((pt == 1) & (yt == 1)).sum() / yt.sum()) if yt.sum() else None,
                      "false_positive_rate": float(((pt == 1) & (yt == 0)).sum() / (yt == 0).sum()) if (yt == 0).sum() else None}
    partial_ids = [k for k, v in marks.items() if k.endswith("-PARTIAL")]
    out = {
        "params": params, "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "precision": prec, "recall": rec,
        "f1": f1_of(pred, y), "auc": float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
        "answer_mark_mae_of_4": float(np.mean(diffs)), "answer_mark_exact": float(np.mean([d == 0 for d in diffs])),
        "partial_credit_correct": f"{sum(marks[k][0] == marks[k][1] for k in partial_ids)}/{len(partial_ids)}",
        "by_answer_type": by_type,
        "score_mean_positive": float(scores[y == 1].mean()), "score_mean_negative": float(scores[y == 0].mean()),
    }
    if boot:
        rng = np.random.default_rng(0)
        aids = sorted({r["answer_id"] for r in rows})
        f1s, maes = [], []
        for _ in range(1000):
            sel = rng.choice(len(aids), size=len(aids), replace=True)
            chosen = [aids[i] for i in sel]
            idx = [i for a in chosen for i, r in enumerate(rows) if r["answer_id"] == a]
            f1s.append(f1_of(pred[idx], y[idx]))
            mk = answer_marks([rows[i] for i in idx], pred[idx])
            maes.append(np.mean([abs(e - a) for e, a in mk.values()]))
        out["f1_ci95_answer_bootstrap"] = [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))]
        out["mae_ci95_answer_bootstrap"] = [float(np.percentile(maes, 2.5)), float(np.percentile(maes, 97.5))]
    return out


def calibration(method: str, params: dict, val_rows: list[dict], test_rows: list[dict]) -> dict:
    """Platt scaling fitted on validation, then checked on test."""
    sv = np.array([[score_of(method, r, params)] for r in val_rows]); yv = np.array([r["label"] for r in val_rows])
    st = np.array([[score_of(method, r, params)] for r in test_rows]); yt = np.array([r["label"] for r in test_rows])
    lr = LogisticRegression().fit(sv, yv)  # Platt scaling fitted on validation only
    p = lr.predict_proba(st)[:, 1]
    bins = np.linspace(0, 1, 6)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            ece += m.mean() * abs(p[m].mean() - yt[m].mean())
    return {"brier": float(np.mean((p - yt) ** 2)), "ece_5bins": float(ece), "note": "Platt scaling fitted on validation, applied to test; n is small so ECE is coarse"}


def dataset_secondary(emb, frozen: dict) -> dict:
    """Templated synthetic dataset (repaired v2 test split): concept labels from its own annotation. Cannot test paraphrase."""
    rows = []
    for rec in csv.DictReader(open(DATASET_TEST, encoding="utf8")):
        sents = process_text(rec["student_answer"]).sentences or [rec["student_answer"]]
        toks = tokenize(rec["student_answer"])
        sv = emb.embed(sents, task="document")
        for names, label in ((json.loads(rec["demonstrated_concepts"] or "[]"), 1), (json.loads(rec["missing_concepts"] or "[]"), 0)):
            for name in names:
                cv = emb.embed([name], task="query")[0]
                rows.append({"label": label, "lex": token_overlap_score(name, toks), "emb_name": float((sv @ cv).max()), "length": len(toks)})
    y = np.array([r["label"] for r in rows])
    out = {"n_concept_judgements": len(rows), "positives": int(y.sum())}
    for m, key, p in (("M0_lexical_current", "lex", frozen["methods"]["M0_lexical_current"]), ("M1_embedding_name", "emb_name", frozen["methods"]["M1_embedding_name"])):
        pred = np.array([r[key] >= p["threshold"] for r in rows]).astype(int)
        out[m] = {"precision": float(((pred == 1) & (y == 1)).sum() / max(1, (pred == 1).sum())), "recall": float(((pred == 1) & (y == 1)).sum() / max(1, y.sum())), "f1": f1_of(pred, y)}
    p4 = frozen["methods"]["M4_length_only"]
    pred = np.array([r["length"] * p4["direction"] >= p4["threshold"] for r in rows]).astype(int)
    out["M4_length_only"] = {"f1": f1_of(pred, y)}
    out["caveat"] = "answers are template sentences that quote the concept verbatim; lexical matching is expected to saturate and this set cannot show paraphrase handling"
    return out


def cmd_select() -> None:
    """Select thresholds on validation and freeze them in a file."""
    emb = LocalSentenceTransformerEmbedding()
    items = load_items(("dev", "validation"))  # the held-out test split is never loaded here
    rows = build_rows(items, emb)
    val = [r for r in rows if r["split"] == "validation"]
    frozen = {"fixtures_sha256": fixtures_hash(), "selection_split": "validation", "methods": {}, "validation_metrics": {}}
    for m in METHODS:
        frozen["methods"][m] = fit_method(m, val)
        frozen["validation_metrics"][m] = metrics(m, val, frozen["methods"][m], boot=False)
    cand = ["M1_embedding_name", "M2_embedding_description", "M3_hybrid_guarded", "M3b_hybrid_unguarded"]
    frozen["primary_candidate"] = max(cand, key=lambda m: (frozen["validation_metrics"][m]["f1"], m))
    frozen["design_note"] = "M3 (lexical negation guard, fixed a priori) turned out harmful on validation (flags legitimate phrases such as 'keeps no client session'); M3b (same hybrid without the guard) was added after seeing VALIDATION results only; the test split had not been loaded"
    frozen["dev_split_use"] = "inspection only (sentence splitting, label sanity); no parameter was fitted on it"
    FROZEN.write_text(json.dumps(frozen, indent=1), encoding="utf8")
    print(json.dumps({m: (frozen["methods"][m], round(frozen["validation_metrics"][m]["f1"], 3)) for m in METHODS}, indent=1))
    print("primary candidate (validation F1):", frozen["primary_candidate"])


def cmd_evaluate() -> None:
    """Score the test split once with the frozen configuration; refuses if the fixtures changed."""
    frozen = json.loads(FROZEN.read_text(encoding="utf8"))
    if frozen["fixtures_sha256"] != fixtures_hash():
        raise SystemExit("fixtures changed after the configuration was frozen: re-run `select`")
    emb = LocalSentenceTransformerEmbedding()
    t_load = time.perf_counter(); emb.embed(["warm up"], task="query"); load_s = time.perf_counter() - t_load
    t0 = time.perf_counter()
    test_rows = build_rows(load_items(("test",)), emb)
    embed_s = time.perf_counter() - t0
    val_rows = build_rows(load_items(("validation",)), emb)
    res = {"fixtures_sha256": frozen["fixtures_sha256"], "frozen_config": frozen["methods"], "primary_candidate": frozen["primary_candidate"],
           "n_test_answers": len({r["answer_id"] for r in test_rows}), "n_test_concept_judgements": len(test_rows),
           "label_provenance": "author-labelled by construction; not human-marker validated; synthetic text", "test": {}}
    for m in METHODS:
        res["test"][m] = metrics(m, test_rows, frozen["methods"][m])
        res["test"][m]["validation_f1_at_freeze"] = frozen["validation_metrics"][m]["f1"]
    res["calibration_primary"] = calibration(frozen["primary_candidate"], frozen["methods"][frozen["primary_candidate"]], val_rows, test_rows)
    res["runtime"] = {"model": "sentence-transformers/all-MiniLM-L6-v2 (local, CPU)", "model_first_call_s": round(load_s, 2),
                      "test_split_embedding_and_scoring_s": round(embed_s, 2), "per_answer_ms": round(1000 * embed_s / res["n_test_answers"], 1),
                      "lexical_baseline": "microseconds per concept (token set overlap)"}
    res["secondary_templated_dataset"] = dataset_secondary(emb, frozen)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, indent=1), encoding="utf8")
    for m in METHODS:
        t = res["test"][m]
        print(f"{m:26s} F1={t['f1']:.3f} P={t['precision']:.3f} R={t['recall']:.3f} AUC={t['auc']:.3f} markMAE={t['answer_mark_mae_of_4']:.2f} partial={t['partial_credit_correct']} CM={t['confusion']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["select", "evaluate"])
    {"select": cmd_select, "evaluate": cmd_evaluate}[ap.parse_args().command]()
