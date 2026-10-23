"""Disagreements between two markers, an adjudication template, and the final per-criterion labels.

Rules (from GOLD_PROTOCOL.md): the adjudicator is not one of the two markers; marks are never averaged; both original returns
are kept untouched; an item with a disagreement nobody resolved, or one a marker could not mark, is excluded and counted, not
dropped silently. The final labels carry the origin of the sheets, so a toy-fixture result can never pass as a real one.
Read-only.
"""

from datasets.gold.agreement import _pairs
from datasets.gold.common import SIMULATED_NOTICE, GoldToolError
from datasets.gold.returns import _levels


def disagreements(sheet_a: dict, ret_a: dict, sheet_b: dict, ret_b: dict, sealed: dict[str, str] | None = None) -> list[dict]:
    both, _ = _pairs(sheet_a, ret_a, sheet_b, ret_b, sealed)
    return [{"item_id": i, "criterion": c, "level_a": a["criteria"][c]["level"], "level_b": b["criteria"][c]["level"]}
            for i, _, a, b in both for c in a["criteria"] if a["criteria"][c]["level"] != b["criteria"][c]["level"]]


def adjudication_template(found: list[dict], adjudicator: str) -> dict:
    return {"adjudicator": adjudicator, "decisions": [{"item_id": d["item_id"], "criterion": d["criterion"], "level": None, "reason": ""}
                                                     for d in found]}


def apply_adjudication(sheet_a: dict, ret_a: dict, sheet_b: dict, ret_b: dict, adjudication: dict,
                       sealed: dict[str, str] | None = None) -> dict:
    both, cannot = _pairs(sheet_a, ret_a, sheet_b, ret_b, sealed)
    found = {(d["item_id"], d["criterion"]) for d in disagreements(sheet_a, ret_a, sheet_b, ret_b, sealed)}
    adjudicator = str(adjudication.get("adjudicator", "")).strip()
    if not adjudicator or adjudicator in (sheet_a["marker"], sheet_b["marker"]):
        raise GoldToolError("the adjudicator must be named and must not be one of the two markers")
    ref = {i["item_id"]: i["rubric_ref"] for i in sheet_a["items"]}
    decided: dict[tuple[str, str], str] = {}
    for dec in adjudication.get("decisions", []):
        key = (dec.get("item_id"), dec.get("criterion"))
        if key not in found:
            raise GoldToolError(f"decision for {key} does not match any disagreement")
        if key in decided:
            raise GoldToolError(f"more than one decision for {key}")
        if not str(dec.get("reason", "")).strip():
            raise GoldToolError(f"decision for {key} needs a reason")
        if dec.get("level") not in _levels(sheet_a, ref[key[0]])[key[1]]:
            raise GoldToolError(f"decision for {key} names a level that is not in the rubric")
        decided[key] = dec["level"]
    labels, unresolved, counts = {}, [], {"criteria_agreed": 0, "criteria_adjudicated": 0}
    for item_id, _, a, _b in both:
        rubric = _levels(sheet_a, ref[item_id])
        if any((item_id, c) in found and (item_id, c) not in decided for c in a["criteria"]):
            unresolved.append(item_id)
            continue
        item = {}
        for c in a["criteria"]:
            if (item_id, c) in decided:
                level, source = decided[(item_id, c)], "adjudicated"
            else:
                level, source = a["criteria"][c]["level"], "agreed"
            counts["criteria_adjudicated" if source == "adjudicated" else "criteria_agreed"] += 1
            item[c] = {"level": level, "mark": rubric[c][level]["mark"], "source": source}
        labels[item_id] = item
    origin = sheet_a["origin"]
    return {"origin": origin, "simulated": origin == "toy_fixture", "notice": SIMULATED_NOTICE if origin == "toy_fixture" else None,
            "adjudicator": adjudicator, "labels": labels,
            "excluded": {**{i: "cannot_mark" for i in cannot}, **{i: "unresolved_disagreement" for i in unresolved}},
            "counts": {"items_on_sheet": len(sheet_a["items"]), "items_labelled": len(labels), "items_excluded_cannot_mark": len(cannot),
                       "items_excluded_unresolved": len(unresolved), **counts}}
