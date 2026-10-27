"""Derive c3_phase3_v5_repaired_v2 from the repaired set by quarantining (never relabelling) evidence-backed problem questions.

Usage: python -m datasets.repair.derive_v2 [--src DIR] [--dst DIR]
Rules: nothing is edited, generated or moved between splits; whole questions are quarantined with a reason; validation/test
splits are untouched (their results were already examined, so they must not change).
"""

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
QUARANTINE_QUESTIONS = {
    "PP-SE3080-099": "cross-split near-duplicate of test question PP-SE3080-107 (cosine 0.903 > 0.8); train copy removed so the test split is unchanged",
    "PP-SE3080-102": "anomalous labels: PARTIAL scored equal to FULL and MOSTLY_CORRECT scored 0 with identical answer strings (see review_queue.csv)",
    "PP-SE3040-009": "code/diagram-dependent question cannot be assessed from text alone (scope review)",
}


def read(p):
    """Read a CSV file into a list of rows plus its column names."""
    with open(p, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def write(p, fields, rows):
    """Write rows to a CSV with Unix line endings."""
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sha(p):
    """SHA-256 of a file's contents."""
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=HERE / "c3_phase3_v5_repaired")
    ap.add_argument("--dst", type=Path, default=HERE / "c3_phase3_v5_repaired_v2")
    a = ap.parse_args(argv)
    if a.dst.exists():
        raise SystemExit(f"refusing to overwrite {a.dst}")
    shutil.copytree(a.src, a.dst)
    ledger = []
    f, elig = read(a.dst / "02_controlled_answers_eligible.csv")
    qf, quar = read(a.dst / "quarantine.csv")
    keep = []
    for r in elig:
        reason = QUARANTINE_QUESTIONS.get(r["question_id"])
        if reason:
            q = {k: r.get(k, "") for k in qf}
            q["quarantine_reason"] = "v2: " + reason
            quar.append(q)
            ledger.append((r["answer_id"], r["question_id"], r["split"], reason))
        else:
            keep.append(r)
    write(a.dst / "02_controlled_answers_eligible.csv", f, keep)
    write(a.dst / "quarantine.csv", qf, quar)
    for split in ("train", "validation", "test"):
        sf, rows = read(a.dst / f"controlled_answers_{split}.csv")
        write(a.dst / f"controlled_answers_{split}.csv", sf, [r for r in rows if r["question_id"] not in QUARANTINE_QUESTIONS])
    bf, qb = read(a.dst / "01_question_bank.csv")
    for r in qb:
        if r["question_id"] in QUARANTINE_QUESTIONS:
            r["eligibility_status"] = "quarantined_v2"
            r["eligibility_reason"] = QUARANTINE_QUESTIONS[r["question_id"]]
    write(a.dst / "01_question_bank.csv", bf, qb)
    for split in ("train", "validation", "test"):
        sf, rows = read(a.dst / f"question_bank_{split}.csv")
        write(a.dst / f"question_bank_{split}.csv", sf, [r for r in rows if r["question_id"] not in QUARANTINE_QUESTIONS])
    write(a.dst / "v2_repair_ledger.csv", ["answer_id", "question_id", "split", "reason"],
          [dict(zip(["answer_id", "question_id", "split", "reason"], x)) for x in ledger])
    m = json.load(open(a.dst / "manifest.json", encoding="utf-8"))
    m["dataset_version"] = "C3-Phase3-v5-repaired-v2"
    m["v2_derivation"] = {"source": a.src.name, "quarantined_questions": QUARANTINE_QUESTIONS, "answers_moved": len(ledger)}
    m["files"] = {n: sha(a.dst / n) for n in sorted(m["files"]) if (a.dst / n).exists()}
    m["files"]["v2_repair_ledger.csv"] = sha(a.dst / "v2_repair_ledger.csv")
    json.dump(m, open(a.dst / "manifest.json", "w", encoding="utf-8"), indent=2, sort_keys=True)
    print(f"v2 written to {a.dst}: eligible {len(keep)} (was {len(elig)}), moved {len(ledger)}")


if __name__ == "__main__":
    main()
