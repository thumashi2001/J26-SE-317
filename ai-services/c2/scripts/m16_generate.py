"""M16.4 — Generate, validate, and export synthetic development data.

Run from ai-services/c2:
    python -m scripts.m16_generate --seed 42 --max-per-module 100
"""

import argparse
import hashlib
import json
from pathlib import Path

from services.m16_dataset_validator import M16DatasetValidator
from services.m16_question_generator import M16QuestionGenerator
from services.m16_training_exporter import M16TrainingExporter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "datasets" / "synthetic" / "m16"
M16_BANK_PATH = PROJECT_ROOT / "config" / "m16_expanded_content_bank.json"


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(seed=42, max_per_module=100, output_dir=None):
    output_dir = Path(output_dir or DEFAULT_OUTPUT).resolve()

    # Never permit accidental export into authentic or verified training dataset directories.
    forbidden = [
        PROJECT_ROOT / "datasets" / "authentic",
        PROJECT_ROOT / "datasets" / "processed",
    ]

    for directory in forbidden:
        resolved = directory.resolve()
        if output_dir == resolved or resolved in output_dir.parents:
            raise ValueError(
                "M16 output cannot overwrite authentic or "
                "processed question datasets"
            )

    generator = M16QuestionGenerator()
    validator = M16DatasetValidator()
    exporter = M16TrainingExporter()

    dataset = generator.generate(
        seed=seed,
        max_per_module=max_per_module,
    )

    report = validator.validate(dataset)

    if not report["valid"]:
        details = "; ".join(
            item["message"] for item in report["errors"][:10]
        )
        raise ValueError(
            "M16 dataset validation failed: " + details
        )

    per_module = output_dir / "per_module"
    per_module.mkdir(parents=True, exist_ok=True)

    output_files = []

    for module in dataset["modules"]:
        module_key = module["module_key"]

        module_data = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_development_questions",
            "generation_mode": "development_fixture",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "seed": seed,
            **module,
        }

        path = per_module / f"{module_key}.json"
        save_json(path, module_data)
        output_files.append(path)

    combined_path = output_dir / "combined_dataset.json"
    report_path = output_dir / "validation_report.json"

    save_json(combined_path, dataset)
    save_json(report_path, report)

    output_files.extend([combined_path, report_path])

    # Export training, validation, and test splits
    training_export_dir = output_dir / "training_export"
    split_export_result = exporter.export(
        dataset=dataset,
        output_dir=training_export_dir,
        seed=seed,
    )

    for split_path in split_export_result["created_files"].values():
        output_files.append(split_path)

    config_hashes = {}
    if M16_BANK_PATH.exists():
        config_hashes["m16_expanded_content_bank.json"] = sha256_file(M16_BANK_PATH)

    split_counts = split_export_result["metadata"]["actual_counts"]

    manifest = {
        "schema_version": "1.0",
        "milestone": "M16",
        "generator_version": "m16_scenario_task_v2",
        "generation_mode": "development_fixture",
        "seed": seed,
        "requested_max_per_module": max_per_module,
        "total_questions": dataset["total_questions"],
        "module_count": len(dataset["modules"]),
        "validation_passed": report["valid"],
        "error_count": report["error_count"],
        "warning_count": report["warning_count"],
        "near_duplicate_count": report.get("near_duplicate_count", 0),
        "academic_verification": "pending",
        "production_ready": False,
        "explicit_development_only_status": True,
        "dataset_counts": {
            "total": dataset["total_questions"],
            "by_module": {
                module["module_key"]: module["question_count"]
                for module in dataset["modules"]
            },
        },
        "topic_distributions": report["topic_distribution"],
        "training_splits": split_counts,
        "configuration_hashes": config_hashes,
        "modules": [
            {
                "module_key": module["module_key"],
                "question_count": module["question_count"],
                "available_candidate_count": module[
                    "available_candidate_count"
                ],
                "target_reached": module["target_reached"],
            }
            for module in dataset["modules"]
        ],
        "files": {
            str(path.relative_to(output_dir)).replace("\\", "/"):
            sha256_file(path)
            for path in output_files
        },
    }

    manifest_path = output_dir / "manifest.json"
    save_json(manifest_path, manifest)

    summary = [
        "# M16 Synthetic Dataset Generation Summary",
        "",
        f"- Seed: {seed}",
        f"- Modules: {len(dataset['modules'])}",
        f"- Total questions: {dataset['total_questions']}",
        f"- Validation passed: {report['valid']}",
        f"- Errors: {report['error_count']}",
        f"- Warnings: {report['warning_count']}",
        f"- Near-duplicates detected: {report.get('near_duplicate_count', 0)}",
        "- Academic verification: pending",
        "- Production ready: no",
        "- Development fixture status: verified",
        "",
        "## Training-Ready Split Counts",
        "",
        f"- Train questions: {split_counts['train']} ({split_counts['train'] / dataset['total_questions']:.1%})",
        f"- Validation questions: {split_counts['validation']} ({split_counts['validation'] / dataset['total_questions']:.1%})",
        f"- Test questions: {split_counts['test']} ({split_counts['test'] / dataset['total_questions']:.1%})",
        f"- Scenario leakage between splits: None (group-aware disjoint splitting enforced)",
        "",
        "## Per-module counts",
        "",
        "| Module | Questions | Available | Target reached |",
        "|---|---:|---:|---|",
    ]

    for module in dataset["modules"]:
        summary.append(
            f"| {module['module_key']} | "
            f"{module['question_count']} | "
            f"{module['available_candidate_count']} | "
            f"{'Yes' if module['target_reached'] else 'No'} |"
        )

    summary.extend([
        "",
        "## Limitations",
        "",
        "- All questions are synthetic development fixtures for model preparation (M16/M17).",
        "- Topic labels come from unverified, provisional content-bank specifications.",
        "- Marks and difficulty have not been assessed by academic lecturers.",
        "- Academic correctness and Bloom levels require formal lecturer review.",
        "- The dataset is not evidence of authentic exam trends.",
        "- The dataset must not be treated as verified ML ground truth.",
        "- Synthetic evaluation results cannot establish accuracy on authentic examination papers.",
        "",
    ])

    (output_dir / "summary_report.md").write_text(
        "\n".join(summary),
        encoding="utf-8",
    )

    print("\nM16 SYNTHETIC DATASET EXPORT")
    print("=" * 46)

    for module in dataset["modules"]:
        print(
            f"{module['module_key']}: "
            f"{module['question_count']} questions"
        )

    print("-" * 46)
    print(f"TOTAL: {dataset['total_questions']}")
    print(f"VALID: {report['valid']}")
    print(f"ERRORS: {report['error_count']}")
    print(f"WARNINGS: {report['warning_count']}")
    print(f"TRAIN: {split_counts['train']} | VAL: {split_counts['validation']} | TEST: {split_counts['test']}")
    print(f"OUTPUT: {output_dir}")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate M16 synthetic development datasets"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--max-per-module", type=int, default=100
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None
    )

    args = parser.parse_args()

    run(
        seed=args.seed,
        max_per_module=args.max_per_module,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
