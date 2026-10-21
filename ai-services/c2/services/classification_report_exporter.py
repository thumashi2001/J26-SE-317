
import json
import math
from pathlib import Path

from services.json_repository import save_json


class ClassificationReportExporter:
    """Validate and export classification reports as JSON."""

    REQUIRED_SUMMARY_FIELDS = {
        "total_questions",
        "classified",
        "unclassified",
        "invalid",
        "classification_coverage_percentage",
        "unclassified_percentage",
        "invalid_percentage",
    }

    def validate_report(self, report):
        if not isinstance(report, dict):
            raise ValueError("Report must be an object")

        if report.get("schema_version") != "1.0":
            raise ValueError("Unsupported report schema version")

        summary = report.get("summary")

        if not isinstance(summary, dict):
            raise ValueError("Report summary must be an object")

        missing = self.REQUIRED_SUMMARY_FIELDS - summary.keys()

        if missing:
            raise ValueError(
                f"Missing summary fields: {sorted(missing)}"
            )

        for field in (
            "total_questions",
            "classified",
            "unclassified",
            "invalid",
        ):
            value = summary[field]

            if type(value) is not int or value < 0:
                raise ValueError(f"Invalid summary count: {field}")

        total = summary["total_questions"]

        if (
            summary["classified"]
            + summary["unclassified"]
            + summary["invalid"]
            != total
        ):
            raise ValueError("Inconsistent classification counts")

        percentage_fields = {
            "classification_coverage_percentage": "classified",
            "unclassified_percentage": "unclassified",
            "invalid_percentage": "invalid",
        }

        for percentage_field, count_field in percentage_fields.items():
            value = summary[percentage_field]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError(
                    f"Invalid percentage: {percentage_field}"
                )

            expected = (
                round(summary[count_field] / total * 100, 2)
                if total else 0.0
            )

            if not math.isclose(value, expected, abs_tol=0.011):
                raise ValueError(
                    f"Inconsistent percentage: {percentage_field}"
                )

        modules = report.get("modules")

        if not isinstance(modules, dict):
            raise ValueError("Report modules must be an object")

        module_totals = {
            "total_questions": 0,
            "classified": 0,
            "unclassified": 0,
            "invalid": 0,
        }

        for module_key, module in modules.items():
            if not isinstance(module_key, str) or not module_key.strip():
                raise ValueError("Invalid module key")

            if not isinstance(module, dict):
                raise ValueError("Invalid module report")

            for field in module_totals:
                value = module.get(field)

                if type(value) is not int or value < 0:
                    raise ValueError(
                        f"Invalid module count: {module_key}.{field}"
                    )

                module_totals[field] += value

            if (
                module["classified"]
                + module["unclassified"]
                + module["invalid"]
                != module["total_questions"]
            ):
                raise ValueError(
                    f"Inconsistent module counts: {module_key}"
                )

            coverage = module.get(
                "classification_coverage_percentage"
            )

            module_total = module["total_questions"]

            expected_coverage = (
                round(module["classified"] / module_total * 100, 2)
                if module_total else 0.0
            )

            if (
                isinstance(coverage, bool)
                or not isinstance(coverage, (int, float))
                or not math.isfinite(coverage)
                or not math.isclose(
                    coverage, expected_coverage, abs_tol=0.011
                )
            ):
                raise ValueError(
                    f"Invalid module coverage: {module_key}"
                )

        if module_totals != {
            field: summary[field] for field in module_totals
        }:
            raise ValueError(
                "Module totals do not match overall summary"
            )

        warnings = report.get("warnings")

        if (
            not isinstance(warnings, list)
            or not all(isinstance(w, str) for w in warnings)
        ):
            raise ValueError("Report warnings must be a list of strings")

        return True

    def export(self, report, output_path):
        """Validate, save and return the output file path."""
        self.validate_report(report)

        output_path = Path(output_path)

        if output_path.suffix.lower() != ".json":
            raise ValueError("Output file must have a .json extension")

        # Prevent partially written JSON from replacing an existing report.
        json.dumps(report, ensure_ascii=False, allow_nan=False)

        saved_path = save_json(report, output_path)

        return str(saved_path)
