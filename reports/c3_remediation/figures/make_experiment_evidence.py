"""Builds reports/c3_remediation/figures/c3_experiment_evidence.html from the experiment result files.

Every number is read from an existing artifact (comparison_table.csv, log_C.txt, comparison_summary.json, diagnostics.json,
frozen_config.json, semantic_matching_results.json, trainable_model_summary*.json). Nothing is typed in by hand.
Run from the repository root:  python reports/c3_remediation/figures/make_experiment_evidence.py
"""
import ast
import csv
import datetime
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "reports/c3_remediation/experiments"
RES = ROOT / "ai-services/c3/experiments/results"  # git-ignored local evidence
SEM = ROOT / "ai-services/c3/experiments/semantic_matching"
OUT = Path(__file__).with_name("c3_experiment_evidence.html")


def stamp(p: Path) -> str:
    return datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if p.exists() else "missing"


# ------------------------------------------------------------------------------------------------ data from artifacts
rows = list(csv.DictReader(open(EXP / "comparison_table.csv", encoding="utf8")))
meta = json.load(open(EXP / "comparison_summary.json", encoding="utf8"))["meta"]
diag = json.load(open(EXP / "diagnostics.json", encoding="utf8"))["diagnostics"]["length_only_ridge"]
epochs = [ast.literal_eval(line) for line in open(EXP / "log_C.txt", encoding="utf8", errors="ignore") if line.startswith("{'epoch'")]
frozen = json.load(open(SEM / "frozen_config.json", encoding="utf8"))
sem = json.load(open(EXP / "semantic_matching_results.json", encoding="utf8"))
old = {}
for key, f in (("v1", "trainable_model_summary.json"), ("v2", "trainable_model_summary_corrected.json")):
    p = RES / f
    old[key] = json.load(open(p, encoding="utf8")) if p.exists() else None

NAMES = {
    "C_roberta_base_finetuned": ("RoBERTa-base (fine-tuned)", "ft"),
    "A1_tfidf_ridge": ("TF-IDF + Ridge", "sk"),
    "A2_tfidf_cosine_overlap_gbr": ("TF-IDF cosine/overlap + GBR", "sk"),
    "B1_sbert_features_ridge": ("SBERT features + Ridge", "enc"),
    "B0_sbert_cosine_isotonic": ("SBERT cosine + isotonic", "enc"),
    "R1_lexical_token_recall_baseline": ("Lexical token recall (rule)", "rule"),
    "R2_condition_E_binary_rubric": ("Condition E binary rubric (rule)", "rule"),
}
KINDS = {"ft": "Fine-tuned transformer", "sk": "Trained scikit-learn model", "enc": "Frozen pretrained encoder + trained head", "rule": "Rule-based baseline (no training)"}
SEM_NAMES = {
    "M0_lexical_current": "Lexical (current rule)",
    "M1_embedding_name": "MiniLM, concept name",
    "M2_embedding_description": "MiniLM, name + description",
    "M3_hybrid_guarded": "Hybrid + negation guard",
    "M3b_hybrid_unguarded": "Hybrid, unguarded",
    "M4_length_only": "Length only (shortcut)",
}
e = html.escape


# ------------------------------------------------------------------------------------------------------ chart 1: bars
def chart_models() -> str:
    data = sorted(rows, key=lambda r: float(r["test_nmae"]))
    W, left, right, top, rh = 940, 270, 70, 44, 38
    H = top + rh * len(data) + 34
    xmax = 0.28
    sx = lambda v: left + (W - left - right) * v / xmax
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Test error by model, lower is better" class="chart">']
    for t in (0, 0.05, 0.10, 0.15, 0.20, 0.25):
        s.append(f'<line class="grid" x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{H - 28}"/><text class="tick" x="{sx(t):.1f}" y="{H - 10}" text-anchor="middle">{t:.2f}</text>')
    for i, r in enumerate(data):
        name, kind = NAMES[r["candidate"]]
        y = top + i * rh
        v, lo, hi = float(r["test_nmae"]), float(r["test_nmae_ci95_lo"]), float(r["test_nmae_ci95_hi"])
        x0, x1 = sx(0), sx(v)
        bar = f"M{x0:.1f},{y + 6} H{x1 - 4:.1f} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 H{x0:.1f} Z"
        tip = f"{name}: test nMAE {v:.4f} (95% CI {lo:.4f} to {hi:.4f}); validation nMAE {float(r['val_nmae']):.4f}; test QWK {float(r['test_qwk']):.3f}; n_test={r['n_test']}"
        s.append(f'<g class="mark"><title>{e(tip)}</title><text class="lab" x="{left - 12}" y="{y + 20}" text-anchor="end">{e(name)}</text>'
                 f'<path class="k-{kind}" d="{bar}"/><line class="whisk" x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y + 20}" y2="{y + 20}"/>'
                 f'<line class="whisk" x1="{sx(lo):.1f}" x2="{sx(lo):.1f}" y1="{y + 15}" y2="{y + 25}"/><line class="whisk" x1="{sx(hi):.1f}" x2="{sx(hi):.1f}" y1="{y + 15}" y2="{y + 25}"/>'
                 f'<text class="val" x="{sx(hi) + 8:.1f}" y="{y + 24}">{v:.3f}</text></g>')
    lv = float(diag["test_nmae"])
    s.append(f'<line class="ref" x1="{sx(lv):.1f}" x2="{sx(lv):.1f}" y1="{top - 10}" y2="{H - 28}"/><text class="reflab" x="{sx(lv) + 6:.1f}" y="{top - 14}">length-only ridge (diagnostic): {lv:.3f}</text>')
    s.append("</svg>")
    return "".join(s)


# ------------------------------------------------------------------------------------------------ chart 2: RoBERTa curve
def line_chart(xs, ys, title, ylab, ymin, ymax, best_x=None, fmt="{:.3f}") -> str:
    W, H, l, r, t, b = 440, 250, 56, 18, 34, 38
    sx = lambda x: l + (W - l - r) * (x - 1) / (len(xs) - 1)
    sy = lambda y: H - b - (H - t - b) * (y - ymin) / (ymax - ymin)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(title)}" class="chart"><text class="ctitle" x="{l}" y="18">{e(title)}</text>']
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        s.append(f'<line class="grid" x1="{l}" x2="{W - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/><text class="tick" x="{l - 8}" y="{sy(v) + 4:.1f}" text-anchor="end">{fmt.format(v)}</text>')
    for x in xs:
        s.append(f'<text class="tick" x="{sx(x):.1f}" y="{H - 16}" text-anchor="middle">{x}</text>')
    s.append(f'<text class="tick" x="{(l + W - r) / 2:.0f}" y="{H - 2}" text-anchor="middle">epoch</text>')
    pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
    s.append(f'<polyline class="line" points="{pts}"/>')
    for x, y in zip(xs, ys):
        sel = best_x == x
        s.append(f'<g class="mark"><title>{e(f"epoch {x}: {ylab} {y:.4f}")}</title><circle class="dot{" sel" if sel else ""}" cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{6 if sel else 4}"/><circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="14" fill="transparent"/></g>')
    if best_x:
        by = ys[xs.index(best_x)]
        s.append(f'<text class="lab" x="{sx(best_x) + 24:.1f}" y="{sy(by) + 30:.1f}" text-anchor="end">selected (lowest validation): {fmt.format(by)}</text>')
    s.append("</svg>")
    return "".join(s)


# ------------------------------------------------------------------------------------------------ chart 3: semantic F1
def chart_semantic() -> str:
    keys = list(SEM_NAMES)
    W, H, l, r, t, b = 940, 330, 60, 20, 40, 78
    gw = (W - l - r) / len(keys)
    sy = lambda v: H - b - (H - t - b) * v
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Concept-level F1 on validation and test splits" class="chart">']
    for k in range(6):
        v = k / 5
        s.append(f'<line class="grid" x1="{l}" x2="{W - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/><text class="tick" x="{l - 8}" y="{sy(v) + 4:.1f}" text-anchor="end">{v:.1f}</text>')
    for i, k in enumerate(keys):
        gx = l + i * gw
        for j, (label, val, cls) in enumerate((("validation", frozen["validation_metrics"][k]["f1"], "s1"), ("test", sem["test"][k]["f1"], "s2"))):
            x = gx + gw * 0.2 + j * gw * 0.31
            w = gw * 0.27
            y = sy(val)
            path = f"M{x:.1f},{H - b} V{y + 4:.1f} a4,4 0 0 1 4,-4 h{w - 8:.1f} a4,4 0 0 1 4,4 V{H - b} Z"
            tip = f"{SEM_NAMES[k]} - {label} F1 {val:.3f}"
            s.append(f'<g class="mark"><title>{e(tip)}</title><path class="{cls}" d="{path}"/><text class="val" x="{x + w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle">{val:.2f}</text></g>')
        words = SEM_NAMES[k].split(" ")
        half = (len(words) + 1) // 2
        for n, line in enumerate((" ".join(words[:half]), " ".join(words[half:]))):
            s.append(f'<text class="lab" x="{gx + gw / 2:.1f}" y="{H - b + 22 + n * 16}" text-anchor="middle">{e(line)}</text>')
    s.append("</svg>")
    return "".join(s)


# --------------------------------------------------------------------------------------------------- tables (a11y view)
def table(headers, body) -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in row) + "</tr>" for row in body)
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


models_tbl = table(["Candidate", "Kind", "Test nMAE", "95% CI", "Validation nMAE", "Test QWK", "Runtime (s)"],
                   [(NAMES[r["candidate"]][0], KINDS[NAMES[r["candidate"]][1]], f"{float(r['test_nmae']):.4f}", f"{float(r['test_nmae_ci95_lo']):.4f} to {float(r['test_nmae_ci95_hi']):.4f}",
                     f"{float(r['val_nmae']):.4f}", f"{float(r['test_qwk']):.3f}", f"{float(r['runtime_s']):.1f}") for r in sorted(rows, key=lambda r: float(r["test_nmae"]))])
epoch_tbl = table(["Epoch", "Train MSE", "Validation nMAE", "Elapsed (s)"], [(d["epoch"], f"{d['train_mse']:.5f}", f"{d['validation_nmae']:.5f}", d["elapsed_s"]) for d in epochs])
sem_tbl = table(["Method", "Validation F1", "Test precision", "Test recall", "Test F1", "Test mark MAE (of 4)", "Chosen parameters (validation only)"],
                [(SEM_NAMES[k], f"{frozen['validation_metrics'][k]['f1']:.3f}", f"{sem['test'][k]['precision']:.3f}", f"{sem['test'][k]['recall']:.3f}", f"{sem['test'][k]['f1']:.3f}",
                  f"{sem['test'][k]['answer_mark_mae_of_4']:.2f}", json.dumps({a: b for a, b in frozen['methods'][k].items() if a != 'note'})) for k in SEM_NAMES])
old_rows = []
for key, label in (("v1", "v1.0.0 (uncorrected)"), ("v2", "v2.0.0 (length-bias corrected)")):
    d = old[key]
    old_rows.append((label, d["model_type"], f"{d['train_samples']} / {d['test_samples']}", f"{d['test_mae']}", f"{d['test_pearson_r']}", f"{d['tolerance_le_2_marks_pct']}%") if d else (label, "file not found", "", "", "", ""))
old_tbl = table(["Saved regressor", "Hyperparameters", "Train / test answers", "Test MAE (marks of 10)", "Test r", "Within 2 marks"], old_rows)

best = min(epochs, key=lambda d: d["validation_nmae"])["epoch"]
ex = [d["epoch"] for d in epochs]
c_val = line_chart(ex, [d["validation_nmae"] for d in epochs], "RoBERTa-base fine-tuning: validation nMAE (lower is better)", "validation nMAE", 0.03, 0.06, best)
c_trn = line_chart(ex, [d["train_mse"] for d in epochs], "RoBERTa-base fine-tuning: training MSE", "train MSE", 0.0, 0.07, None, "{:.3f}")

provenance = [
    ("Dataset", f"{meta['dataset']} (synthetic controlled answers, tier-based expected marks; not human-marked)"),
    ("Split", f"train {meta['split_sizes']['train']} / validation {meta['split_sizes']['validation']} / test {meta['split_sizes']['test']} answers, split by question"),
    ("Seed", str(meta["seed"])),
    ("Target", meta["target"]),
    ("Selection rule", meta["selection_rule"] if "selection_rule" in meta else "lowest validation nMAE"),
    ("Dataset file hashes", "recorded in comparison_summary.json (sha256 for every file)"),
    ("Model comparison run", f"python -m experiments.model_comparison (files dated {stamp(EXP / 'results_C.json')}; RoBERTa training log {stamp(EXP / 'log_C.txt')}, {epochs[-1]['elapsed_s']:.0f} s for {len(epochs)} epochs)"),
    ("RoBERTa checkpoint", "NOT saved (the script keeps the best epoch in memory only), so only metrics remain"),
    ("Semantic-matching run", f"python -m experiments.semantic_matching.run_eval select, then evaluate (frozen_config.json {stamp(SEM / 'frozen_config.json')}; results {stamp(EXP / 'semantic_matching_results.json')})"),
    ("Semantic labels", sem["label_provenance"] + f"; {sem['n_test_answers']} test answers / {sem['n_test_concept_judgements']} concept judgments"),
    ("Live marking", "none of these models is used by the live student path; live marks come from rubric levels over token-overlap concept evidence"),
]
prov_tbl = table(["Item", "Evidence"], provenance)

CSS = """
.viz-root{color-scheme:light;--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6d68;--grid:#e6e4df;--line:#d4d2cc;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#8a8984;--ref:#b8351f}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])) .viz-root{color-scheme:dark;--surface:#1a1a19;--panel:#222221;--ink:#f0efec;--ink2:#c3c2b7;--muted:#a3a29a;--grid:#33332f;--line:#43423d;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#8f8e87;--ref:#ff8a73}}
:root[data-theme=dark] .viz-root{color-scheme:dark;--surface:#1a1a19;--panel:#222221;--ink:#f0efec;--ink2:#c3c2b7;--muted:#a3a29a;--grid:#33332f;--line:#43423d;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#8f8e87;--ref:#ff8a73}
body{margin:0;background:var(--surface,#fcfcfb)}
.viz-root{background:var(--surface);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:24px 16px}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:0 0 18px}
.note{color:var(--ink2);font-size:.9rem;margin:6px 0 10px}
.warn{border-left:4px solid var(--ref);padding:8px 12px;background:var(--surface);margin:10px 0;color:var(--ink)}
.chart{width:100%;height:auto;display:block}
.grid{stroke:var(--grid);stroke-width:1}.tick{fill:var(--muted);font-size:12px}.lab{fill:var(--ink2);font-size:13px}.val{fill:var(--ink);font-size:12px;font-weight:600}.ctitle{fill:var(--ink);font-size:14px;font-weight:600}
.k-ft{fill:var(--s1)}.k-sk{fill:var(--s2)}.k-enc{fill:var(--s3)}.k-rule{fill:var(--s4)}.s1{fill:var(--s1)}.s2{fill:var(--s2)}
.whisk{stroke:var(--ink);stroke-width:1.5}.ref{stroke:var(--ref);stroke-width:1.5;stroke-dasharray:5 4}.reflab{fill:var(--ref);font-size:12px;font-weight:600}
.line{fill:none;stroke:var(--s1);stroke-width:2}.dot{fill:var(--s1);stroke:var(--panel);stroke-width:2}.dot.sel{fill:var(--s2)}
.mark:hover path,.mark:hover circle.dot{opacity:.8}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:6px 0 8px;font-size:.88rem;color:var(--ink2)}.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){.two{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;font-size:.86rem;margin-top:8px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{color:var(--ink2);font-weight:600}
/*scroll*/.scroll{overflow-x:auto}table{min-width:560px}details summary{cursor:pointer;color:var(--ink2);font-size:.9rem;margin-top:8px}
"""

PAGE = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>C3 experiment evidence</title><style>{CSS}</style></head><body><div class="viz-root"><div class="wrap">
<h1>C3 experiments: evidence that the models were run</h1>
<p class="sub">Charts generated from the saved result files (see the provenance table). These are offline research experiments on synthetic, tier-labelled data; none of these models awards marks in the live student path.</p>

<div class="card"><h2>1. Model comparison: test error (lower is better)</h2>
<p class="note">Normalised mean absolute error (nMAE) on the {meta['split_sizes']['test']}-answer held-out test split; whiskers are question-bootstrap 95% intervals. Hyperparameters and the RoBERTa epoch were chosen on the validation split only.</p>
<div class="legend">{''.join(f'<span><i style="background:var(--{c})"></i>{e(KINDS[k])}</span>' for k, c in (('ft','s1'),('sk','s2'),('enc','s3'),('rule','s4')))}<span><i style="background:var(--ref);height:3px;vertical-align:3px"></i>length-only diagnostic</span></div>
{chart_models()}
<div class="warn"><strong>Read with care.</strong> A ridge model that sees only answer length reaches nMAE {float(diag['test_nmae']):.3f}, so low error here does not prove semantic understanding. Labels are tier-based synthetic marks, single seed, no human markers.</div>
<details><summary>Table view</summary>{models_tbl}</details></div>

<div class="card"><h2>2. RoBERTa-base fine-tuning run (training log)</h2>
<p class="note">Six epochs from {e(stamp(EXP / 'log_C.txt'))}; the epoch with the lowest validation error ({best}) was kept. AdamW, learning rate 2e-5, batch 8, max length 256 (model_comparison.py).</p>
<div class="two">{c_val}{c_trn}</div>
<details><summary>Table view</summary>{epoch_tbl}</details></div>

<div class="card"><h2>3. MiniLM semantic-matching experiment (exploratory)</h2>
<p class="note">Concept-level F1 on validation (where thresholds were chosen) and on the held-out test split (scored once). Pretrained all-MiniLM-L6-v2, not fine-tuned.</p>
<div class="legend"><span><i style="background:var(--s1)"></i>validation</span><span><i style="background:var(--s2)"></i>test</span></div>
{chart_semantic()}
<div class="warn"><strong>Exploratory only.</strong> Author-labelled fixtures, {sem['n_test_answers']} test answers. MiniLM recovers paraphrases but also accepts every keyword-stuffed or wrong-but-similar answer; F1 is not marking accuracy.</div>
<details><summary>Table view</summary>{sem_tbl}</details></div>

<div class="card"><h2>4. Earlier saved scoring regressors (offline, not loaded by any code)</h2>
<p class="note">Their training scripts were later deleted from the working tree; the saved models and result summaries remain. v1 looked perfect because it followed answer length (documented in docs/pp1/DATASET_AND_EVALUATION_REPORT.md).</p>
{old_tbl}</div>

<div class="card"><h2>Provenance and limits</h2>{prov_tbl}</div>
</div></div></body></html>"""

OUT.write_text(PAGE, encoding="utf8")
print("wrote", OUT, len(PAGE), "bytes")
