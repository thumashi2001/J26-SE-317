
import json
from pathlib import Path


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "modules.json"
)


class ModuleRegistry:
    """
    Load, validate and query Year 3 module configurations.
    """

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)

        with self.config_path.open(
            "r", encoding="utf-8"
        ) as file:
            self.config = json.load(file)

        self.modules = self.config.get("modules", [])
        self.validate()

    def validate(self):
        if self.config.get("schema_version") != "1.0":
            raise ValueError(
                "Unsupported module configuration version"
            )

        if not isinstance(self.modules, list):
            raise ValueError(
                "Modules must be a list"
            )

        if len(self.modules) != 8:
            raise ValueError(
                "Expected exactly eight Year 3 modules"
            )

        keys = set()
        codes = set()

        for module in self.modules:
            if not isinstance(module, dict):
                raise ValueError(
                    "Each module must be an object"
                )

            key = module.get("module_key")
            name = module.get("module_name")
            semester = module.get("semester")
            code = module.get("module_code")

            if not isinstance(key, str) or not key.strip():
                raise ValueError("Invalid module key")

            if key in keys:
                raise ValueError(
                    f"Duplicate module key: {key}"
                )

            keys.add(key)

            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    f"{key}: missing module name"
                )

            if semester not in (1, 2):
                raise ValueError(
                    f"{key}: invalid semester"
                )

            if code is not None:
                if not isinstance(code, str) or not code.strip():
                    raise ValueError(
                        f"{key}: invalid module code"
                    )

                if code in codes:
                    raise ValueError(
                        f"Duplicate module code: {code}"
                    )

                codes.add(code)

            if not isinstance(module.get("topics"), list):
                raise ValueError(
                    f"{key}: topics must be a list"
                )

            structure = module.get("exam_structure")

            if structure is not None and not isinstance(
                structure, dict
            ):
                raise ValueError(
                    f"{key}: exam_structure must be an object or null"
                )

        for semester in (1, 2):
            count = sum(
                module["semester"] == semester
                for module in self.modules
            )

            if count != 4:
                raise ValueError(
                    f"Expected four modules in semester {semester}"
                )

        return True

    def get_all(self):
        return list(self.modules)

    def get_by_key(self, module_key):
        return next(
            (
                module for module in self.modules
                if module["module_key"] == module_key
            ),
            None
        )

    def get_by_code(self, module_code):
        return next(
            (
                module for module in self.modules
                if module["module_code"] == module_code
            ),
            None
        )

    def get_by_semester(self, semester):
        return [
            module for module in self.modules
            if module["semester"] == semester
        ]
