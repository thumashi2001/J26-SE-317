"""CLI: repair the existing C3-Phase3-v5-FINAL dataset into datasets/c3_phase3_v5_repaired/.

  python datasets/repair_c3_dataset.py --verify-original
  python datasets/repair_c3_dataset.py --sample          # 3 canonical + 2 block-A + 1 block-B questions, timestamped dir
  python datasets/repair_c3_dataset.py                   # full repair (refuses to overwrite a non-empty default dir)
  python datasets/repair_c3_dataset.py --out DIR         # explicit output directory (may overwrite)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datasets.repair.common import (  # noqa: E402
    ARCHIVE_DIR,
    DATASETS_DIR,
    DEFAULT_OUT_DIR,
    OriginalIntegrityError,
    OutputExistsError,
    verify_original,
)
from datasets.repair.repair import diff_table, run_repair  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify-original", action="store_true", help="only verify the archive SHA256SUMS and exit")
    ap.add_argument("--sample", action="store_true", help="repair 6 sample questions into a timestamped SAMPLE dir")
    ap.add_argument("--out", type=Path, default=None, help="output directory (explicit; may overwrite)")
    ap.add_argument("--archive", type=Path, default=ARCHIVE_DIR)
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.verify_original:
            verified = verify_original(args.archive)
            print(f"OK: {len(verified)} original files match SHA256SUMS.txt")
            return 0
        if args.sample:
            out = args.out or DATASETS_DIR / f"c3_phase3_v5_repaired_SAMPLE_{time.strftime('%Y%m%d_%H%M%S')}"
        else:
            out = args.out or DEFAULT_OUT_DIR
        result = run_repair(out, sample=args.sample, archive_dir=args.archive, allow_nonempty=args.out is not None,
                            validate=not args.no_validate)
    except (OriginalIntegrityError, OutputExistsError) as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        return 2
    print(f"output: {result['out_dir']}")
    print("accounting:", result["manifest"]["accounting"])
    if args.sample:
        table = diff_table(result["diff"])
        (Path(result["out_dir"]) / "sample_diff_table.md").write_text(table + "\n", encoding="utf-8", newline="\n")
        print(table)
    report = result.get("validation")
    if report:
        for c in report["checks"]:
            print(f"[{c['status'].upper():4}] {'HARD' if c['hard'] else 'soft'} {c['name']}: {c['summary']}")
        print(f"validation: {report['overall']} hard_failures={report['hard_failures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
