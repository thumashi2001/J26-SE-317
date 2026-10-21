
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_PATH = BASE_DIR / "config" / "modules.json"


def test_module_configuration():
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = json.load(file)

    modules = config["modules"]

    assert config["schema_version"] == "1.0"
    assert config["academic_year"] == 3

    assert len(modules) == 8

    keys = [module["module_key"] for module in modules]

    assert len(keys) == len(set(keys)), (
        "Duplicate module keys detected"
    )

    semester_1 = [
        module for module in modules
        if module["semester"] == 1
    ]

    semester_2 = [
        module for module in modules
        if module["semester"] == 2
    ]

    assert len(semester_1) == 4
    assert len(semester_2) == 4

    assert all(
        module["module_name"].strip()
        for module in modules
    )

    database_systems = next(
        module for module in modules
        if module["module_key"] == "database_systems"
    )

    assert database_systems["module_code"] == "IT3020"

    assert all(
        isinstance(module["topics"], list)
        for module in modules
    )

    print("\n--- MODULE CONFIGURATION VALIDATION ---")
    print("Total modules:", len(modules))
    print("Semester 1 modules:", len(semester_1))
    print("Semester 2 modules:", len(semester_2))

    print("\nPASS: configuration schema")
    print("PASS: eight module definitions")
    print("PASS: unique module identifiers")
    print("PASS: semester distribution")
    print("PASS: module metadata structure")


if __name__ == "__main__":
    test_module_configuration()

    print("\nAll module configuration tests passed.")
