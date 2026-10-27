"""Schema, label and split checks for the semantic paraphrase benchmark (dataset `semantic_paraphrase_benchmark_v1`).

SIMPLE ENGLISH
    Each benchmark item asks one question: "does this student answer show this one concept?". A person (not a model) must give
    the label. This module checks that the file is well formed, that labels are only trusted when real annotator records back
    them, and that no group of related answers is shared between the development and held-out splits.

    Status of an item is DERIVED from its annotation records, never typed in by hand, so a draft can not pass itself off as a
    human label:
        draft_unreviewed   no annotations yet (only the AI-drafted `draft.proposed_label`, which is not ground truth)
        annotated          fewer than MIN_ANNOTATORS annotations
        needs_adjudication annotators disagree and no adjudication is recorded
        human_labelled     annotators agree
        adjudicated        annotators disagreed and an adjudicator decided
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[1] / "semantic_paraphrase_benchmark_v1"
LABELS = ("demonstrated", "partial", "missing", "contradicted")
CATEGORIES = ("paraphrase", "partial", "related_incorrect", "missing", "negation", "technical_alt", "keyword_trap")
SPLITS = ("dev", "heldout")
STATUSES = ("draft_unreviewed", "annotated", "needs_adjudication", "human_labelled", "adjudicated")
SCORED_STATUSES = ("human_labelled", "adjudicated")
MIN_ANNOTATORS = 2
NEAR_DUPLICATE_JACCARD = 0.8
ANNOTATOR_ID = re.compile(r"^ANN\d{2}$")
ADJUDICATOR_ID = re.compile(r"^ADJ\d{2}$")
REQUIRED = (
    "item_id",
    "group_id",
    "split",
    "question_id",
    "question_text",
    "concept",
    "student_answer",
    "category",
    "draft",
    "label_status",
    "annotations",
    "adjudication",
    "final_label",
)
_WORD = re.compile(r"[a-z0-9]+")


def load_doc(directory: Path = DATASET_DIR) -> dict:
    """Read items.json from a benchmark directory."""
    return json.loads((Path(directory) / "items.json").read_text(encoding="utf-8"))


def content_hash(items: list[dict]) -> str:
    """SHA-256 of the items in a canonical form (independent of line endings and key order)."""
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_status(item: dict) -> str:
    """Status implied by the annotation records of an item (see the module docstring)."""
    annotations = item.get("annotations") or []
    if not annotations:
        return "draft_unreviewed"
    if len(annotations) < MIN_ANNOTATORS:
        return "annotated"
    if len({a.get("label") for a in annotations}) == 1:
        return "human_labelled"
    return "adjudicated" if item.get("adjudication") else "needs_adjudication"


def derive_final_label(item: dict) -> str | None:
    """The label to score against: the agreed label, or the adjudicator's; None until a human has settled it."""
    status = derive_status(item)
    if status == "human_labelled":
        return item["annotations"][0]["label"]
    if status == "adjudicated":
        return item["adjudication"]["label"]
    return None


def _nonempty(value) -> bool:
    """True for a non-blank string."""
    return isinstance(value, str) and bool(value.strip())


def item_problems(item: dict) -> list[str]:
    """Everything wrong with one item's structure, labels and annotation records."""
    problems = [f"missing field: {k}" for k in REQUIRED if k not in item]
    if problems:
        return problems
    for key in ("item_id", "group_id", "question_id", "question_text", "concept", "student_answer"):
        if not _nonempty(item[key]):
            problems.append(f"{key} must be non-empty text")
    if item["split"] not in SPLITS:
        problems.append(f"split must be one of {SPLITS}")
    if item["category"] not in CATEGORIES:
        problems.append(f"category must be one of {CATEGORIES}")
    if item["label_status"] not in STATUSES:
        problems.append(f"label_status must be one of {STATUSES}")
    draft = item["draft"]
    if not isinstance(draft, dict) or not _nonempty(draft.get("author")):
        problems.append("draft.author must say who wrote the item text")
    elif draft.get("proposed_label") not in LABELS:
        problems.append("draft.proposed_label must be a valid label")

    seen = set()
    for index, a in enumerate(item["annotations"]):
        where = f"annotation[{index}]"
        if not ANNOTATOR_ID.match(str(a.get("annotator_id", ""))):
            problems.append(f"{where}.annotator_id must be a pseudonym like ANN01")
        if a.get("annotator_id") in seen:
            problems.append(f"{where}: the same annotator appears twice")
        seen.add(a.get("annotator_id"))
        if a.get("label") not in LABELS:
            problems.append(f"{where}.label must be one of {LABELS}")
        if not _nonempty(a.get("rationale")):
            problems.append(f"{where}.rationale is required")
    adjudication = item["adjudication"]
    if adjudication is not None:
        if not ADJUDICATOR_ID.match(str(adjudication.get("adjudicator_id", ""))):
            problems.append("adjudication.adjudicator_id must be a pseudonym like ADJ01")
        if adjudication.get("adjudicator_id") in seen:
            problems.append("adjudicator must not also be an annotator of the item")
        if adjudication.get("label") not in LABELS:
            problems.append("adjudication.label must be one of the labels")
        if not _nonempty(adjudication.get("rationale")):
            problems.append("adjudication.rationale is required")
        if len({a.get("label") for a in item["annotations"]}) <= 1:
            problems.append("adjudication recorded but the annotators did not disagree")

    if not problems:
        if item["label_status"] != derive_status(item):
            problems.append(
                f"label_status {item['label_status']!r} does not match the annotations ({derive_status(item)!r})"
            )
        if item["final_label"] != derive_final_label(item):
            problems.append("final_label does not match the human annotation/adjudication")
    return problems


def _tokens(text: str) -> frozenset[str]:
    """Lower-case word set used for near-duplicate detection."""
    return frozenset(_WORD.findall(text.lower()))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Word-set overlap from 0 to 1."""
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def split_problems(items: list[dict]) -> list[str]:
    """Split integrity: unique ids, groups never straddle splits, no (near-)duplicate answers across splits."""
    problems = []
    ids = Counter(i["item_id"] for i in items)
    problems += [f"duplicate item_id {k}" for k, n in ids.items() if n > 1]
    group_splits = defaultdict(set)
    for item in items:
        group_splits[item["group_id"]].add(item["split"])
    problems += [f"group {g} appears in more than one split" for g, s in group_splits.items() if len(s) > 1]
    by_split = {s: [i for i in items if i["split"] == s] for s in SPLITS}
    for dev in by_split["dev"]:
        for held in by_split["heldout"]:
            sim = jaccard(_tokens(dev["student_answer"]), _tokens(held["student_answer"]))
            if sim >= NEAR_DUPLICATE_JACCARD:
                problems.append(f"near-duplicate across splits ({sim:.2f}): {dev['item_id']} ~ {held['item_id']}")
    texts = Counter((i["concept"].lower(), " ".join(i["student_answer"].lower().split())) for i in items)
    problems += [f"exact duplicate (concept, answer): {k[0]!r}" for k, n in texts.items() if n > 1]
    return problems


def validate_items(items: list[dict]) -> dict:
    """Run every check; the result lists problems per item and for the splits."""
    per_item = {i.get("item_id", f"#{n}"): p for n, i in enumerate(items) if (p := item_problems(i))}
    return {
        "item_problems": per_item,
        "split_problems": split_problems(items),
        "ok": not per_item and not split_problems(items),
    }


def integrity_report(items: list[dict]) -> dict:
    """Counts and checks for the integrity report: splits, categories, labels, label status, group sizes."""
    check = validate_items(items)
    table = {s: Counter(i["category"] for i in items if i["split"] == s) for s in SPLITS}
    proposed = {s: Counter(i["draft"]["proposed_label"] for i in items if i["split"] == s) for s in SPLITS}
    status = {s: Counter(derive_status(i) for i in items if i["split"] == s) for s in SPLITS}
    return {
        "dataset_sha256": content_hash(items),
        "n_items": len(items),
        "n_groups": len({i["group_id"] for i in items}),
        "items_per_split": {s: sum(1 for i in items if i["split"] == s) for s in SPLITS},
        "groups_per_split": {s: len({i["group_id"] for i in items if i["split"] == s}) for s in SPLITS},
        "categories_per_split": {s: dict(c) for s, c in table.items()},
        "draft_proposed_labels_per_split": {s: dict(c) for s, c in proposed.items()},
        "label_status_per_split": {s: dict(c) for s, c in status.items()},
        "human_labelled_items": sum(1 for i in items if derive_status(i) in SCORED_STATUSES),
        "valid": check["ok"],
        "item_problems": check["item_problems"],
        "split_problems": check["split_problems"],
    }


def render_markdown(report: dict) -> str:
    """Human-readable integrity report."""
    lines = [
        "# Dataset and split integrity report (generated)",
        "",
        f"Dataset content hash: `{report['dataset_sha256']}`",
        "",
        f"Valid: **{report['valid']}**. Items: {report['n_items']} in {report['n_groups']} groups. "
        f"Human-labelled (scorable) items: **{report['human_labelled_items']}**.",
        "",
        "| Split | Items | Groups | Status counts | Draft proposed labels (NOT ground truth) |",
        "|---|---|---|---|---|",
    ]
    for s in SPLITS:
        lines.append(
            f"| {s} | {report['items_per_split'][s]} | {report['groups_per_split'][s]} | "
            f"{report['label_status_per_split'][s]} | {report['draft_proposed_labels_per_split'][s]} |"
        )
    lines += ["", "| Category | " + " | ".join(SPLITS) + " |", "|---|---|---|"]
    for c in CATEGORIES:
        lines.append(f"| {c} | " + " | ".join(str(report["categories_per_split"][s].get(c, 0)) for s in SPLITS) + " |")
    for title, rows in (
        ("Item problems", [f"{k}: {v}" for k, v in report["item_problems"].items()]),
        ("Split problems", report["split_problems"]),
    ):
        lines += ["", f"## {title}", ""] + ([f"- {r}" for r in rows] or ["- none"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Validate the benchmark; print the report; write INTEGRITY_REPORT.md with --write. Exit 1 when invalid."""
    argv = sys.argv[1:] if argv is None else argv
    report = integrity_report(load_doc()["items"])
    print(json.dumps(report, indent=2) if "--json" in argv else render_markdown(report))
    if "--write" in argv:
        (DATASET_DIR / "INTEGRITY_REPORT.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
