"""Merge results_*.json from model_comparison.py into one table (markdown + csv + json) and apply the pre-registered rule.

STATUS: offline helper. Usage: python experiments/aggregate_comparison.py DIR (DIR holds results_*.json written by
model_comparison.py).
"""
import csv
import json
import sys
from pathlib import Path

# Directory holding the results_*.json files written by model_comparison.py (one per candidate group).
out = Path(sys.argv[1])
allres, meta = {}, None
# Merge every candidate from every results file into one dict keyed by candidate name.
for f in sorted(out.glob("results_*.json")):
    j = json.loads(f.read_text(encoding="utf-8"))
    meta = meta or j["meta"]
    allres.update(j["results"])
# One flat row per candidate: validation score plus test score with a question-level bootstrap interval.
rows = []
for name, r in allres.items():
    v, t = r["validation"], r["test"]
    rows.append({"candidate": name, "n_val": v["n"], "val_nmae": v["nmae"], "val_qwk": v["qwk_11bins"], "n_test": t["n"], "test_nmae": t["nmae"],
                 "test_nmae_ci95_lo": t["nmae_ci95_question_bootstrap"][0], "test_nmae_ci95_hi": t["nmae_ci95_question_bootstrap"][1],
                 "test_mae_marks": t["mae_marks"], "test_nrmse": t["nrmse"], "test_pearson": t["pearson_r"], "test_qwk": t["qwk_11bins"],
                 "test_within_0.10": t["within_0.10_of_max"], "runtime_s": r.get("runtime_seconds"), "hyperparameters": json.dumps(r["hyperparameters"])})
# Order by VALIDATION nMAE: model selection never looks at the test split.
rows.sort(key=lambda x: x["val_nmae"])
with open(out / "comparison_table.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
# Reference baselines are named R*; the winner is the best LEARNED candidate by validation nMAE only.
learned = [r for r in rows if not r["candidate"].startswith("R")]
winner = learned[0]["candidate"]
# Markdown table for the report; lower nMAE/MAE is better, higher QWK/r is better.
md = ["| candidate | val nMAE | test nMAE [95 % CI, question bootstrap] | test MAE (marks) | test QWK | test r | within 0.10 | runtime s |", "|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['candidate']} | {r['val_nmae']:.4f} | {r['test_nmae']:.4f} [{r['test_nmae_ci95_lo']:.4f}, {r['test_nmae_ci95_hi']:.4f}] | {r['test_mae_marks']:.3f} | {r['test_qwk']:.3f} | {r['test_pearson'] if r['test_pearson'] is None else round(r['test_pearson'], 3)} | {r['test_within_0.10']:.3f} | {r['runtime_s']} |")
(out / "comparison_table.md").write_text("\n".join(md) + f"\n\nValidation-selected learned candidate: **{winner}**\n", encoding="utf-8")
(out / "comparison_summary.json").write_text(json.dumps({"meta": meta, "validation_selected_learned_candidate": winner, "rows": rows}, indent=1), encoding="utf-8")
print("\n".join(md)); print("selected:", winner)
