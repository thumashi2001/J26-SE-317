"""M19.5 - Batch Authentic Past-Paper Ingestion CLI Script.

Executes full-dataset ingestion for all 8 Year 3 Software Engineering modules
from ai-services/c2/datasets/authentic/ into datasets/processed/.
"""

import argparse
import json
import sys
from pathlib import Path

# Add c2 root to sys.path
C2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C2_ROOT))

from services.batch_authentic_ingestion import BatchAuthenticIngestion


def main():
    parser = argparse.ArgumentParser(
        description="M19.5 - Batch Authentic Past-Paper Ingestion Pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform scanning, parsing and classification without writing to repository files",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Only display audit summary of authentic PDFs without ingesting",
    )
    args = parser.parse_args()

    service = BatchAuthenticIngestion()

    if args.audit_only:
        print("\n" + "=" * 70)
        print("  M19.5 AUTHENTIC DATASET AUDIT REPORT")
        print("=" * 70)
        audit_res = service.audit()
        print(f"Total PDF Files Discovered : {audit_res['total_pdfs']}")
        print(f"Text-Based PDF Papers      : {audit_res['text_based_count']}")
        print(f"Scanned Bitmap PDFs        : {audit_res['scanned_count']}")
        print(f"File Duplication Detected  : {'YES' if audit_res['has_duplicate_files'] else 'NONE (All Unique)'}")
        print("\nPapers by Module:")
        for m, c in sorted(audit_res["module_counts"].items()):
            print(f"  - {m:45}: {c} paper(s)")
        print("\nPapers by Calendar Year:")
        for y, c in sorted(audit_res["year_counts"].items()):
            print(f"  - {y}: {c} paper(s)")
        print(f"\nQuarantined Files Count: {len(audit_res['quarantined'])}")
        for q in audit_res["quarantined"]:
            print(f"  - [QUARANTINE] {q['filename']} ({q['quarantine_reason']})")
        print("=" * 70 + "\n")
        return

    print("\n" + "=" * 70)
    print("  STARTING M19.5 BATCH AUTHENTIC DATASET INGESTION")
    print(f"  Mode: {'DRY RUN (No changes saved)' if args.dry_run else 'LIVE INGESTION'}")
    print("=" * 70)

    report = service.ingest_all(dry_run=args.dry_run)
    s = report["summary"]

    print("\n" + "-" * 70)
    print("  INGESTION SUMMARY")
    print("-" * 70)
    print(f"Total PDFs Discovered            : {s['total_files_discovered']}")
    print(f"Successfully Parsed Papers       : {s['successful_files']}")
    print(f"Quarantined Scanned Papers       : {s['quarantined_files']}")
    print(f"Existing Question Records        : {s['existing_question_records']}")
    print(f"New Question Records Ingested    : {s['new_question_records_ingested']}")
    print(f"Grand Total Authentic Questions  : {s['total_question_records']}")
    print(f"Academic Years Represented       : {', '.join(str(y) for y in s['academic_years_represented'])}")
    print(f"Questions with Ambiguous Marks   : {s['ambiguous_marks_count']}")
    print(f"Provisional Classified (M17)     : {s['provisional_topic_classified_count']}")
    print(f"Unclassified / Abstained         : {s['unclassified_count']}")

    print("\nAuthentic Questions Ingested by Module:")
    for m, count in sorted(s["questions_per_module"].items()):
        print(f"  - {m:48}: {count} questions")

    if report["quarantined_papers"]:
        print(f"\nQuarantined Papers ({len(report['quarantined_papers'])}):")
        for qp in report["quarantined_papers"]:
            print(f"  - {qp['filename']} -> {qp['quarantine_reason']}")

    print("=" * 70)
    if not args.dry_run:
        print("Live ingestion completed successfully. Repository files updated.")
    else:
        print("Dry run completed. No files modified.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
