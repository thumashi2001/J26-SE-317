"""Agreement between two markers' returns, with every figure labelled by where the marks came from.

Usage: python -m datasets.gold.agreement <sheet_A> <return_A> <sheet_B> <return_B> [--allow-simulated] [--boot N] [--seed S]

The statistics are textbook definitions implemented here and checked in the tests against independent references (scikit-learn's
weighted kappa, the Shrout and Fleiss intraclass-correlation example, brute-force alpha). They are computed on whatever returns
are supplied: the tool cannot tell who produced them. A report built from a 'toy_fixture' sheet says SIMULATED and states that
it contains no human marks. Intervals come from a bootstrap that resamples questions (rubric refs), not answers.
Read-only.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from datasets.gold.common import SIMULATED_NOTICE, GoldToolError
from datasets.gold.returns import marks_from_return


def _same_length(a: list, b: list) -> None:
    """Raise if the two rating lists differ in length."""
    if len(a) != len(b):
        raise GoldToolError(f"the two ratings have different lengths ({len(a)} and {len(b)})")


def _ranks_in_range(values, k: int) -> None:
    """Raise unless every rank is an integer from 0 to k-1."""
    if any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < k for v in values if v is not None):
        raise GoldToolError(f"every rank must be an integer from 0 to {k - 1}")


def exact_agreement(a: list, b: list) -> float | None:
    """Share of items where both markers gave the same value."""
    _same_length(a, b)
    return sum(x == y for x, y in zip(a, b, strict=True)) / len(a) if a else None


def mean_abs_difference(a: list[float], b: list[float]) -> float | None:
    """Average absolute difference between the two markers' values."""
    _same_length(a, b)
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a) if a else None


def weighted_kappa(a: list[int], b: list[int], k: int) -> float | None:
    """Quadratic weighted kappa for two raters on ordinal ranks 0..k-1; None when it is undefined."""
    _same_length(a, b)
    _ranks_in_range([*a, *b], k)
    n = len(a)
    if n == 0 or k < 2:
        return None
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        observed[x][y] += 1
    rows, cols = [sum(r) for r in observed], [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = sum(((i - j) / (k - 1)) ** 2 * observed[i][j] for i in range(k) for j in range(k))
    den = sum(((i - j) / (k - 1)) ** 2 * rows[i] * cols[j] / n for i in range(k) for j in range(k))
    return None if den == 0 else 1.0 - num / den


def krippendorff_alpha_ordinal(units: list[list[int | None]], k: int) -> float | None:
    """Krippendorff's alpha with the ordinal metric; units are rows of ranks (None = missing); None when undefined."""
    _ranks_in_range([v for unit in units for v in unit], k)
    o = [[0.0] * k for _ in range(k)]
    for unit in units:
        values = [v for v in unit if v is not None]
        if len(values) < 2:
            continue
        for i, c in enumerate(values):
            for j, d in enumerate(values):
                if i != j:
                    o[c][d] += 1.0 / (len(values) - 1)
    n_c = [sum(row) for row in o]
    n = sum(n_c)
    if n <= 1:
        return None

    def delta2(c: int, d: int) -> float:
        """Squared distance term used by Krippendorff's alpha for two ranks."""
        lo, hi = min(c, d), max(c, d)
        return (sum(n_c[lo:hi + 1]) - (n_c[c] + n_c[d]) / 2.0) ** 2

    d_obs = sum(o[c][d] * delta2(c, d) for c in range(k) for d in range(k)) / n
    d_exp = sum(n_c[c] * n_c[d] * delta2(c, d) for c in range(k) for d in range(k)) / (n * (n - 1))
    return None if d_exp == 0 else 1.0 - d_obs / d_exp


def icc(matrix: list[list[float]], kind: str = "2,1") -> float | None:
    """Intraclass correlation (Shrout and Fleiss 1,1 / 2,1 / 3,1) for a complete subjects x raters matrix."""
    n, k = len(matrix), len(matrix[0]) if matrix else 0
    if any(len(row) != k for row in matrix):
        raise GoldToolError("the ratings matrix must be complete: every subject needs a rating from every rater")
    if n < 2 or k < 2:
        return None
    grand = sum(map(sum, matrix)) / (n * k)
    row_means = [sum(r) / k for r in matrix]
    col_means = [sum(matrix[i][j] for i in range(n)) / n for j in range(k)]
    ssr = k * sum((m - grand) ** 2 for m in row_means)
    ssc = n * sum((m - grand) ** 2 for m in col_means)
    sse = sum((matrix[i][j] - row_means[i] - col_means[j] + grand) ** 2 for i in range(n) for j in range(k))
    msr, msc, mse = ssr / (n - 1), ssc / (k - 1), sse / ((n - 1) * (k - 1))
    msw = (ssc + sse) / (n * (k - 1))
    if kind == "1,1":
        num, den = msr - msw, msr + (k - 1) * msw
    elif kind == "2,1":
        num, den = msr - mse, msr + (k - 1) * mse + k * (msc - mse) / n
    elif kind == "3,1":
        num, den = msr - mse, msr + (k - 1) * mse
    else:
        raise GoldToolError("kind must be '1,1', '2,1' or '3,1'")
    return None if den == 0 else num / den


def question_bootstrap(rows: list[dict], stat, n_boot: int, seed: object, alpha: float = 0.05) -> dict:
    """Percentile interval for stat(rows) resampling whole questions (the 'question' key) with replacement."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["question"]].append(r)
    names, rng, values = sorted(groups), random.Random(str(seed)), []
    point = stat(rows)
    if len(names) < 2:
        return {"estimate": point, "ci": None, "note": "fewer than two questions; no interval"}
    for _ in range(n_boot):
        sample = [r for q in (rng.choice(names) for _ in names) for r in groups[q]]
        v = stat(sample)
        if v is not None:
            values.append(v)
    values.sort()
    if len(values) < max(10, n_boot // 2):
        return {"estimate": point, "ci": None, "note": "statistic undefined in too many resamples"}
    lo, hi = values[int(alpha / 2 * len(values))], values[min(len(values) - 1, int((1 - alpha / 2) * len(values)))]
    return {"estimate": point, "ci": [lo, hi], "questions": len(names), "resamples": n_boot}


def _pairs(sheet_a: dict, ret_a: dict, sheet_b: dict, ret_b: dict, sealed: dict[str, str] | None = None):
    """Matched, validated marks of two markers. `sealed` maps marker pseudonym to the sheet hash recorded in the seal."""
    sealed = sealed or {}
    for field in ("origin", "group", "rubrics"):
        if sheet_a[field] != sheet_b[field]:
            raise GoldToolError(f"the two sheets differ in {field}; they are not two copies of one marking task")
    if {i["item_id"] for i in sheet_a["items"]} != {i["item_id"] for i in sheet_b["items"]}:
        raise GoldToolError("the two sheets do not contain the same items")
    if sheet_a["marker"] == sheet_b["marker"]:
        raise GoldToolError("both returns come from the same marker pseudonym")
    ma = marks_from_return(sheet_a, ret_a, sealed.get(sheet_a["marker"]))
    mb = marks_from_return(sheet_b, ret_b, sealed.get(sheet_b["marker"]))
    ref = {i["item_id"]: i["rubric_ref"] for i in sheet_a["items"]}
    both, excluded = [], []
    for item_id in sorted(ma):
        if ma[item_id]["cannot_mark"] or mb[item_id]["cannot_mark"]:
            excluded.append(item_id)
        else:
            both.append((item_id, ref[item_id], ma[item_id], mb[item_id]))
    return both, excluded


def agreement_report(sheet_a: dict, ret_a: dict, sheet_b: dict, ret_b: dict, n_boot: int = 1000, seed: object = "agreement",
                     sealed: dict[str, str] | None = None) -> dict:
    """Agreement statistics between two markers (exact, weighted, difference, bootstrap intervals)."""
    both, excluded = _pairs(sheet_a, ret_a, sheet_b, ret_b, sealed)
    origin = sheet_a["origin"]
    criteria = [{"question": q, "item": i, "crit": c, "k": a["criteria"][c]["levels"], "a": a["criteria"][c]["rank"],
                 "b": b["criteria"][c]["rank"]} for i, q, a, b in both for c in a["criteria"]]
    by_k: dict[int, list[dict]] = defaultdict(list)
    for r in criteria:
        by_k[r["k"]].append(r)
    exact = lambda rows: exact_agreement([r["a"] for r in rows], [r["b"] for r in rows])  # noqa: E731
    per_k = {}
    for k, rows in sorted(by_k.items()):
        per_k[str(k)] = {
            "criterion_decisions": len(rows), "exact_agreement": exact(rows),
            "weighted_kappa_quadratic": weighted_kappa([r["a"] for r in rows], [r["b"] for r in rows], k),
            "krippendorff_alpha_ordinal": krippendorff_alpha_ordinal([[r["a"], r["b"]] for r in rows], k)}
    totals = [{"question": q, "a": a["ratio"], "b": b["ratio"]} for _, q, a, b in both]
    return {
        "provenance": {"origin": origin, "simulated": origin == "toy_fixture",
                       "notice": SIMULATED_NOTICE if origin == "toy_fixture" else
                       "Computed from the returns supplied; this tool cannot verify who produced them.",
                       "human_marks": False if origin == "toy_fixture" else "claimed by the origin label, not verified"},
        "markers": [sheet_a["marker"], sheet_b["marker"]],
        "items": {"on_sheet": len(sheet_a["items"]), "compared": len(both), "excluded_cannot_mark": len(excluded)},
        "method": "levels are ranks within each criterion (ordered by mark); statistics are reported per number of levels k "
                  "because criteria with different k are not on one scale; intervals resample questions",
        "per_number_of_levels": per_k,
        "overall_exact_agreement": question_bootstrap(criteria, exact, n_boot, seed),
        "total_mark_ratio": {
            "items": len(totals),
            "mean_abs_difference": question_bootstrap(totals, lambda rs: mean_abs_difference([r["a"] for r in rs], [r["b"] for r in rs]), n_boot, seed),
            "icc_2_1": icc([[r["a"], r["b"]] for r in totals], "2,1")},
        "limits": ["Agreement is not validity: two markers can agree and both be wrong.",
                   "Kappa and alpha are unstable when almost all decisions fall on few levels; read them with the exact agreement.",
                   "With few questions the intervals are wide.",
                   "No acceptance threshold is applied here; thresholds belong in the study plan fixed before marking."],
    }


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Agreement report for two markers")
    for name in ("sheet_a", "return_a", "sheet_b", "return_b"):
        ap.add_argument(name, type=Path)
    ap.add_argument("--seal", type=Path, default=None, help="pre-marking seal: also checks both sheets against their sealed hashes")
    ap.add_argument("--allow-simulated", action="store_true", help="required to compute on a toy_fixture sheet")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", default="agreement")
    args = ap.parse_args(argv)
    try:
        load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
        sa, ra, sb, rb = load(args.sheet_a), load(args.return_a), load(args.sheet_b), load(args.return_b)
        if sa["origin"] == "toy_fixture" and not args.allow_simulated:
            raise GoldToolError("these are toy-fixture (simulated) sheets; pass --allow-simulated to compute a clearly labelled report")
        sealed = None
        if args.seal is not None:
            files = load(args.seal)["files"]
            sealed = {m: files.get(f"sheet_{m}.json", "not in the seal") for m in (sa["marker"], sb["marker"])}
        print(json.dumps(agreement_report(sa, ra, sb, rb, args.boot, args.seed, sealed), indent=2, sort_keys=True))
    except (GoldToolError, OSError, ValueError, KeyError) as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
