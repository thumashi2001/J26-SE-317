"""Validation of a marker's return against the sheet they were given, and conversion of the chosen levels into marks.

Usage: python -m datasets.gold.returns <sheet.json> <return.json>

A return holds, per item, one level id per criterion (or cannot_mark with a reason). A mark outside the rubric cannot be
recorded: marks are looked up from the chosen level. This works from the marker's own sheet only, never from the key.
Read-only.
"""

import argparse
import json
import sys
from pathlib import Path

from datasets.gold.common import GoldToolError, canonical_bytes, sha256_hex


def sheet_sha256(sheet: dict) -> str:
    """Fingerprint of a marking sheet, stored in the return so it cannot be mixed up."""
    return sha256_hex(canonical_bytes(sheet))


def _levels(sheet: dict, rubric_ref: str) -> dict[str, dict[str, dict]]:
    """Look-up of rubric levels by criterion for a sheet's rubric."""
    return {c["criterion"]: {lv["level"]: lv for lv in c["levels"]} for c in sheet["rubrics"][rubric_ref]["criteria"]}


def validate_return(sheet: dict, ret: object, expected_sheet_sha256: str | None = None) -> list[str]:
    """Every problem found (empty list = the return is complete and uses only allowed levels).

    The return must name the hash of the sheet it is checked against. Pass `expected_sheet_sha256` (from the pre-marking seal
    or the key) to also detect a sheet that changed after sealing; without it a sheet is only compared with itself.
    """
    if not isinstance(ret, dict):
        return ["return must be a JSON object"]
    problems = []
    if expected_sheet_sha256 is not None and sheet_sha256(sheet) != expected_sheet_sha256:
        problems.append("the sheet does not match its sealed hash (it changed after sealing, or it is not the sealed sheet)")
    for field in ("marker", "origin"):
        if ret.get(field) != sheet[field]:
            problems.append(f"{field} {ret.get(field)!r} does not match the sheet ({sheet[field]!r})")
    if ret.get("sheet_sha256") != sheet_sha256(sheet):
        problems.append("sheet_sha256 does not match the sheet this return is checked against")
    entries = ret.get("returns")
    if not isinstance(entries, list):
        return problems + ["returns must be a list"]
    ids = [e.get("item_id") if isinstance(e, dict) else None for e in entries]
    if len(set(ids)) != len(ids):
        problems.append("an item is returned more than once")
    expected = {i["item_id"] for i in sheet["items"]}
    if set(ids) - expected:
        problems.append(f"{len(set(ids) - expected)} returned item(s) are not on the sheet")
    if expected - set(ids):
        problems.append(f"{len(expected - set(ids))} item(s) on the sheet are missing from the return")
    by_id = {i["item_id"]: i for i in sheet["items"]}
    for e in entries:
        if not isinstance(e, dict) or e.get("item_id") not in by_id:
            continue
        item_id, allowed = e["item_id"], _levels(sheet, by_id[e["item_id"]]["rubric_ref"])
        levels = e.get("levels")
        if not isinstance(levels, dict) or set(levels) != set(allowed):
            problems.append(f"{item_id}: levels must name exactly the criteria {sorted(allowed)}")
            continue
        if e.get("cannot_mark") is True:
            if not str(e.get("reason", "")).strip():
                problems.append(f"{item_id}: cannot_mark needs a reason")
            continue
        for crit, level in levels.items():
            if level is None:
                problems.append(f"{item_id}: criterion {crit} has no level (mark every criterion or use cannot_mark with a reason)")
            elif level not in allowed[crit]:
                problems.append(f"{item_id}: {level!r} is not a level of criterion {crit}")
    return problems


def marks_from_return(sheet: dict, ret: dict, expected_sheet_sha256: str | None = None) -> dict[str, dict]:
    """Per item: chosen levels with their marks and level ranks, or cannot_mark. Raises if the return is not valid."""
    problems = validate_return(sheet, ret, expected_sheet_sha256)
    if problems:
        raise GoldToolError("; ".join(problems[:3]))
    by_id = {i["item_id"]: i for i in sheet["items"]}
    out = {}
    for e in ret["returns"]:
        if e.get("cannot_mark") is True:
            out[e["item_id"]] = {"cannot_mark": True, "reason": e["reason"]}
            continue
        allowed = _levels(sheet, by_id[e["item_id"]]["rubric_ref"])
        criteria = {}
        for crit, level in e["levels"].items():
            ranked = sorted(allowed[crit].values(), key=lambda lv: lv["mark"])
            criteria[crit] = {"level": level, "mark": allowed[crit][level]["mark"], "rank": [lv["level"] for lv in ranked].index(level),
                              "levels": len(ranked)}
        total = sum(c["mark"] for c in criteria.values())
        maximum = sum(max(lv["mark"] for lv in allowed[c].values()) for c in allowed)
        out[e["item_id"]] = {"cannot_mark": False, "criteria": criteria, "total": total, "max": maximum, "ratio": total / maximum}
    return out


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Validate a marker return against its sheet")
    ap.add_argument("sheet", type=Path)
    ap.add_argument("ret", type=Path)
    ap.add_argument("--seal", type=Path, default=None, help="pre-marking seal: also checks the sheet against its sealed hash")
    args = ap.parse_args(argv)
    try:
        sheet = json.loads(args.sheet.read_text(encoding="utf-8"))
        expected = None
        if args.seal is not None:
            expected = json.loads(args.seal.read_text(encoding="utf-8"))["files"].get(f"sheet_{sheet['marker']}.json", "not in the seal")
        problems = validate_return(sheet, json.loads(args.ret.read_text(encoding="utf-8")), expected)
    except (OSError, ValueError, KeyError) as exc:
        print(f"PROBLEM  cannot read input: {exc}")
        return 1
    for p in problems:
        print(f"PROBLEM  {p}")
    if not problems:
        print("OK  complete and uses only allowed levels (this does not say anything about who produced the marks)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
