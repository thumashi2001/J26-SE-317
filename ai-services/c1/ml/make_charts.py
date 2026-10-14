"""Draws the report charts from reports/results.json. Run after train_compare.py."""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "reports", "results.json")))
OUT = lambda f: os.path.join(HERE, "reports", f)
NAMES = R["names"]
INK, MUTED, GRID, GOOD, GREY = "#13222f", "#5a6b7b", "#e3e9ef", "#0b8f73", "#9aa9b8"
# colour-blind safe set (Okabe-Ito subset), each line is also labelled directly
LINE = {"rule_twin": "#D55E00", "bkt_forget": "#E69F00", "pfa": "#CC79A7", "logreg": "#0072B2", "gbm": "#009E73"}
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def fig_auc():
    keys = sorted(NAMES, key=lambda k: R["next_answer"][k]["auc"])
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
    for i, k in enumerate(keys):
        r = R["next_answer"][k]
        c = GOOD if k in ("gbm", "logreg", "mlp") else GREY
        ax.plot([r["auc_lo"], r["auc_hi"]], [i, i], color=c, lw=2.2, solid_capstyle="round")
        ax.plot(r["auc"], i, "o", color=c, ms=8, mec="white", mew=1.5)
        ax.text(r["auc_hi"] + 0.006, i, f'{r["auc"]:.3f}', va="center", fontsize=9, color=INK)
    ax.axvline(0.5, color=MUTED, lw=1, ls=":")
    ax.text(0.503, -0.55, "chance (0.50)", fontsize=8, color=MUTED)
    ax.axvline(R["oracle"]["auc"], color=MUTED, lw=1, ls="--")
    ax.text(R["oracle"]["auc"] - 0.003, 0.05, "best possible on this data (0.75)", fontsize=8, color=MUTED, ha="right")
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([NAMES[k] for k in keys], fontsize=10)
    ax.set_xlim(0.47, 0.78)
    ax.set_xlabel("AUC on students the models never saw (higher is better). Bars show the 95% range.")
    ax.set_title("Predicting whether the next answer is correct", loc="left", pad=10, fontsize=13, fontweight="bold")
    ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT("fig1_auc.png")); plt.close(fig)


def fig_exam():
    keys = sorted(NAMES, key=lambda k: -R["exam"][k]["mae"])
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    for i, k in enumerate(keys):
        e = R["exam"][k]
        c = GOOD if e["mae"] < 5.0 else GREY
        ax.barh(i, e["mae"], color=c, height=0.62)
        ax.text(e["mae"] + 0.3, i, f'{e["mae"]:.1f} points   (leans {"high" if e["bias"] > 0 else "low"} by {abs(e["bias"]):.1f})', va="center", fontsize=9)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([NAMES[k] for k in keys], fontsize=10)
    ax.set_xlim(0, 36)
    ax.set_xlabel("Average error in exam-day marks out of 100 (lower is better)")
    ax.set_title("Predicting the exam-day score", loc="left", fontsize=13, fontweight="bold")
    ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT("fig2_exam.png")); plt.close(fig)


def fig_calibration():
    fig, ax = plt.subplots(figsize=(6.4, 6), dpi=160)
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
    ax.text(0.62, 0.55, "perfect", fontsize=8, color=MUTED, rotation=38)
    for k in ("rule_twin", "bkt_forget", "gbm"):
        pts = R["calibration"][k]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o", color=LINE[k], lw=2, ms=6, mec="white", label=NAMES[k])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("What the model said (chance of a correct answer)")
    ax.set_ylabel("What really happened")
    ax.set_title("Can the number be trusted as a probability?", loc="left", fontsize=12.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(True, color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT("fig3_calibration.png")); plt.close(fig)


def fig_history():
    labs = list(R["by_history"].keys())
    fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
    ends = {}
    for k in ("rule_twin", "bkt_forget", "pfa", "logreg", "gbm"):
        ys = [R["by_history"][l][k] for l in labs]
        ax.plot(range(len(labs)), ys, "-o", color=LINE[k], lw=2, ms=6, mec="white")
        ends[k] = ys[-1]
    # spread the end labels so they never overlap
    order = sorted(ends, key=lambda k: ends[k])
    pos, last = {}, -1
    for k in order:
        pos[k] = max(ends[k], last + 0.013)
        last = pos[k]
    for k in order:
        ax.text(len(labs) - 1 + 0.08, pos[k], NAMES[k], fontsize=8.5, va="center", color=INK)
    ax.set_xticks(range(len(labs)))
    ax.set_xticklabels([f'{l}\n(n={R["by_history"][l]["n"]})' for l in labs], fontsize=9)
    ax.set_xlim(-0.2, len(labs) + 0.9)
    ax.set_ylim(0.48, 0.72)
    ax.set_xlabel("Earlier answers the student already gave on this topic")
    ax.set_ylabel("AUC")
    ax.set_title("How much history does a model need?", loc="left", fontsize=13, fontweight="bold")
    ax.grid(True, color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT("fig4_history.png")); plt.close(fig)


def fig_signals():
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=160, gridspec_kw={"width_ratios": [1.1, 1]})
    pretty = {"is_multi": "Question type (multi-answer)", "twin_score": "Rule-based twin score", "topic_prior": "Topic difficulty", "stu_fast": "Share of very fast answers",
              "n_prev": "Earlier answers on topic", "stu_acc": "Student accuracy so far", "stu_hint": "Hint use", "fail": "Earlier wrong answers", "succ": "Earlier right answers",
              "days_since": "Days since last practice", "ema": "Recent accuracy on topic", "mod_acc": "Accuracy in same module", "stu_leave": "Tab leaves", "stu_time_ratio": "Answer speed"}
    top = R["importance"][:8][::-1]
    a.barh(range(len(top)), [t[1] for t in top], color=GOOD, height=0.62)
    a.set_yticks(range(len(top))); a.set_yticklabels([pretty.get(t[0], t[0]) for t in top], fontsize=9)
    a.set_xlabel("AUC lost when the signal is scrambled")
    a.set_title("Which signals the model relies on", loc="left", fontsize=11.5, fontweight="bold")
    a.xaxis.grid(True, color=GRID); a.set_axisbelow(True)
    ab = list(R["ablation"].items())[::-1]
    base = R["ablation"]["All signals"]["auc"]
    for i, (k, v) in enumerate(ab):
        b.plot([0.64, v["auc"]], [i, i], color=GRID, lw=1.5)
        b.plot(v["auc"], i, "o", color=GOOD if k == "All signals" else GREY, ms=10, mec="white", mew=1.5)
        b.text(v["auc"] + 0.0007, i, f'{v["auc"]:.4f}', va="center", fontsize=9)
    b.set_yticks(range(len(ab))); b.set_yticklabels([k.replace(" (time, hints, tab leaves)", "") for k, _ in ab], fontsize=9)
    b.set_xlim(0.64, 0.664)
    b.set_xlabel("AUC after retraining without that group")
    b.set_title("What each group of signals adds", loc="left", fontsize=11.5, fontweight="bold")
    b.xaxis.grid(True, color=GRID); b.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT("fig5_signals.png")); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_auc, fig_exam, fig_calibration, fig_history, fig_signals):
        f()
    print("charts written")
