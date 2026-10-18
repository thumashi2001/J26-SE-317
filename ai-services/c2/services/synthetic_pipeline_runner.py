
"""M11.2.6.3 - End-to-end synthetic draft paper pipeline.

Development fixtures only. Prevents repeated scenario use across
papers in the same run. No academic approval is implied.
"""

import hashlib
import re

from services.synthetic_batch_generator import SyntheticBatchGenerator
from services.synthetic_generation_adapter import SyntheticGenerationAdapter
from services.synthetic_scenario_enricher import SyntheticScenarioEnricher


class SyntheticPipelineRunner:
    def __init__(
        self,
        export_root=None,
        adapter=None,
        enricher=None,
    ):
        self.batch_generator = SyntheticBatchGenerator(export_root)
        self.adapter = (
            adapter if adapter is not None
            else SyntheticGenerationAdapter()
        )
        self.enricher = (
            enricher if enricher is not None
            else SyntheticScenarioEnricher()
        )

    @staticmethod
    def _question_signatures(paper):
        signatures = set()

        for main in paper["questions"]:
            for sub in main["subquestions"]:
                question = sub["question"]
                text = question["question_text"]
                scenario_id = question.get("scenario_id")

                if not scenario_id:
                    raise ValueError(
                        "Enriched question is missing scenario ID"
                    )

                # Scenario identifiers are only local to the
                # supplied scenario bank. Text fingerprints
                # provide an additional cross-paper check.
                for kind, value in (
                    ("scenario", scenario_id),
                    ("text", text),
                ):
                    normalized = " ".join(
                        value.casefold().split()
                    )
                    digest = hashlib.sha256(
                        normalized.encode("utf-8")
                    ).hexdigest()
                    signatures.add((kind, digest))

        return signatures

    def run(
        self,
        targets,
        module_configs,
        base_seed=42,
        export=False,
        mode="development_fixture",
    ):
        if mode != "development_fixture":
            raise ValueError(
                "End-to-end production generation is blocked"
            )

        if not isinstance(module_configs, dict):
            raise ValueError(
                "module_configs must be a mapping"
            )

        SyntheticBatchGenerator._validate_targets(targets)

        for module_key in targets:
            if not re.fullmatch(
                r"[a-z][a-z0-9_]*", module_key
            ):
                raise ValueError("Invalid module key")

            config = module_configs.get(module_key)

            if not isinstance(config, dict):
                raise ValueError(
                    f"Missing configuration for {module_key}"
                )

            if (
                "structure" not in config
                or "pool_configs" not in config
            ):
                raise ValueError(
                    f"Incomplete configuration for {module_key}"
                )

        used_signatures = set()

        def paper_factory(module_key, paper_index, seed):
            config = module_configs[module_key]

            generated = self.adapter.build_paper(
                config["structure"],
                config["pool_configs"],
                seed=seed,
                mode="development_fixture",
            )

            enriched = self.enricher.enrich(
                generated["paper"]
            )

            paper = enriched["paper"]
            signatures = self._question_signatures(paper)

            duplicates = signatures & used_signatures

            if duplicates:
                raise ValueError(
                    "Repeated question or scenario across papers"
                )

            # The batch coordinator performs final validation
            # and optional export after this factory returns.
            used_signatures.update(signatures)

            return paper

        report = self.batch_generator.generate(
            targets,
            paper_factory,
            base_seed=base_seed,
            mode=mode,
            export=export,
        )

        report["pipeline"] = (
            "c2_real_generator_scenario_pipeline_v1"
        )
        report["cross_paper_duplicate_detection"] = True
        report["academic_review_status"] = "pending"

        return report
