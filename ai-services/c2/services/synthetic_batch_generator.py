
"""M11.2.5 - Multi-module synthetic paper batch coordinator.

Coordinates paper creation, validation and optional export.
The caller supplies a paper factory that produces one paper draft.
Production operation is deliberately unavailable.
"""

import hashlib
import json
import re
from pathlib import Path

from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)


class SyntheticBatchGenerator:
    def __init__(self, export_root=None):
        self.export_root = (
            Path(export_root)
            if export_root is not None
            else (
                Path(__file__).resolve().parents[1]
                / "datasets"
                / "synthetic"
                / "drafts"
            )
        )

    @staticmethod
    def _validate_targets(targets):
        if not isinstance(targets, dict) or not targets:
            raise ValueError(
                "targets must be a nonempty module-to-count mapping"
            )

        for module_key, count in targets.items():
            if (
                not isinstance(module_key, str)
                or not re.fullmatch(
                    r"[a-z][a-z0-9_]*",
                    module_key,
                )
            ):
                raise ValueError(
                    f"Invalid module key: {module_key!r}"
                )

            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
            ):
                raise ValueError(
                    f"Invalid paper count for {module_key}"
                )

    @staticmethod
    def _paper_seed(base_seed, module_key, index):
        material = (
            f"{base_seed}:{module_key}:{index}"
        ).encode("utf-8")

        return int.from_bytes(
            hashlib.sha256(material).digest()[:8],
            "big",
        )

    def generate(
        self,
        targets,
        paper_factory,
        base_seed=42,
        mode="development_fixture",
        export=False,
    ):
        """
        paper_factory(module_key, paper_index, seed) -> paper dict

        The factory is responsible for generating a fresh
        question batch and assembling one paper using
        SyntheticPaperBuilder.

        This coordinator validates and optionally exports
        each returned paper.
        """
        self._validate_targets(targets)

        if mode != "development_fixture":
            raise ValueError(
                "Batch generation is development-only; "
                "production requires verified academic "
                "configuration integration"
            )

        if (
            isinstance(base_seed, bool)
            or not isinstance(base_seed, int)
        ):
            raise ValueError(
                "base_seed must be an integer"
            )

        if not callable(paper_factory):
            raise ValueError(
                "paper_factory must be callable"
            )

        if not isinstance(export, bool):
            raise ValueError(
                "export must be a boolean"
            )

        results = []
        all_paper_ids = set()

        for module_key, target_count in targets.items():
            module_result = {
                "module_key": module_key,
                "requested": target_count,
                "generated": 0,
                "exported": 0,
                "failed": 0,
                "papers": [],
                "errors": [],
            }

            exporter = SyntheticDatasetExporter(
                self.export_root / module_key
            )

            for index in range(1, target_count + 1):
                seed = self._paper_seed(
                    base_seed,
                    module_key,
                    index,
                )

                try:
                    paper = paper_factory(
                        module_key,
                        index,
                        seed,
                    )

                    if not isinstance(paper, dict):
                        raise ValueError(
                            "Factory did not return a paper"
                        )

                    if paper.get("module_key") != module_key:
                        raise ValueError(
                            "Factory returned wrong module"
                        )

                    validation = exporter.validate(paper)

                    if not validation["valid"]:
                        raise ValueError(
                            "Paper validation failed: "
                            + "; ".join(validation["errors"])
                        )

                    paper_id = paper["paper_id"]

                    if paper_id in all_paper_ids:
                        raise ValueError(
                            "Duplicate paper ID in batch"
                        )

                    all_paper_ids.add(paper_id)

                    paper_result = {
                        "index": index,
                        "paper_id": paper_id,
                        "seed": seed,
                        "total_marks": paper["total_marks"],
                        "exported": False,
                    }

                    # A validated paper counts as generated,
                    # even if a subsequent export fails.
                    module_result["generated"] += 1

                    if export:
                        export_result = exporter.export(paper)
                        paper_result["exported"] = True
                        paper_result["file_path"] = (
                            export_result["file_path"]
                        )
                        module_result["exported"] += 1

                    module_result["papers"].append(
                        paper_result
                    )

                except (
                    ValueError,
                    TypeError,
                    KeyError,
                    OSError,
                ) as error:
                    module_result["failed"] += 1
                    module_result["errors"].append({
                        "index": index,
                        "error": str(error),
                    })

            results.append(module_result)

        report = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_batch_report",
            "generation_mode": mode,
            "release_status": "not_approved",
            "base_seed": base_seed,
            "export_enabled": export,
            "module_count": len(targets),
            "requested_papers": sum(targets.values()),
            "generated_papers": sum(
                item["generated"] for item in results
            ),
            "exported_papers": sum(
                item["exported"] for item in results
            ),
            "failed_attempts": sum(
                item["failed"] for item in results
            ),
            "modules": results,
        }

        # A report can be inspected without exporting data.
        # No filesystem writes occur when export=False.
        json.dumps(report, allow_nan=False)

        return report
