
import json
from pathlib import Path


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "syllabus_sources.json"
)


class SyllabusSourceRegistry:
    VALID_STATUSES = {
        "unverified",
        "partially_verified",
        "verified",
    }

    def __init__(self, config_path=None):
        self.config_path = Path(
            config_path if config_path is not None
            else DEFAULT_CONFIG
        )

        with self.config_path.open(
            "r", encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Registry must be an object")

        if data.get("schema_version") != "1.0":
            raise ValueError(
                "Unsupported syllabus source schema version"
            )

        self.sources = data.get("sources")
        self._validate()

    def _validate(self):
        if not isinstance(self.sources, list):
            raise ValueError("Sources must be a list")

        seen = set()

        for source in self.sources:
            if not isinstance(source, dict):
                raise ValueError("Source entry must be an object")

            module_key = source.get("module_key")
            status = source.get("verification_status")
            references = source.get("references")

            if (
                not isinstance(module_key, str)
                or not module_key.strip()
            ):
                raise ValueError("Invalid module key")

            if module_key in seen:
                raise ValueError(
                    f"Duplicate module: {module_key}"
                )

            seen.add(module_key)

            if status not in self.VALID_STATUSES:
                raise ValueError(
                    f"Invalid verification status: {module_key}"
                )

            if not isinstance(references, list):
                raise ValueError(
                    f"References must be a list: {module_key}"
                )

            if status == "verified" and not references:
                raise ValueError(
                    f"Verified module requires references: "
                    f"{module_key}"
                )

            for reference in references:
                if not isinstance(reference, dict):
                    raise ValueError(
                        f"Invalid reference: {module_key}"
                    )

                for field in (
                    "source_type",
                    "title",
                    "location",
                ):
                    value = reference.get(field)

                    if (
                        not isinstance(value, str)
                        or not value.strip()
                    ):
                        raise ValueError(
                            f"Invalid reference {field}: "
                            f"{module_key}"
                        )

                ref_status = reference.get(
                    "verification_status"
                )

                if ref_status not in self.VALID_STATUSES:
                    raise ValueError(
                        f"Invalid reference status: {module_key}"
                    )

            if status == "verified":
                if not any(
                    reference["verification_status"]
                    == "verified"
                    for reference in references
                ):
                    raise ValueError(
                        f"Verified module needs a verified "
                        f"reference: {module_key}"
                    )

    def get_all(self):
        return self.sources

    def get_module_sources(self, module_key):
        for source in self.sources:
            if source["module_key"] == module_key:
                return source

        return None

    def is_module_verified(self, module_key):
        source = self.get_module_sources(module_key)

        return (
            source is not None
            and source["verification_status"] == "verified"
        )

    def get_summary(self):
        summary = {
            "total_modules": len(self.sources),
            "verified": 0,
            "partially_verified": 0,
            "unverified": 0,
            "total_references": 0,
        }

        for source in self.sources:
            status = source["verification_status"]
            summary[status] += 1
            summary["total_references"] += len(
                source["references"]
            )

        return summary
