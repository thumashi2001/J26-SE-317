
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.module_registry import ModuleRegistry


def test_module_registry():
    registry = ModuleRegistry()

    assert len(registry.get_all()) == 8
    assert len(registry.get_by_semester(1)) == 4
    assert len(registry.get_by_semester(2)) == 4

    database = registry.get_by_key("database_systems")

    assert database is not None
    assert database["module_code"] == "IT3020"

    assert (
        registry.get_by_code("IT3020")["module_name"]
        == "Database Systems"
    )

    assert registry.get_by_key("unknown_module") is None

    print("PASS: module registry loading")
    print("PASS: module lookup by key and code")
    print("PASS: semester-based module retrieval")


def test_duplicate_module_detection():
    registry = ModuleRegistry()

    config = json.loads(json.dumps(registry.config))

    config["modules"][1]["module_key"] = (
        config["modules"][0]["module_key"]
    )

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "modules.json"

        config_path.write_text(
            json.dumps(config), encoding="utf-8"
        )

        try:
            ModuleRegistry(config_path)
        except ValueError as error:
            assert "Duplicate module key" in str(error)
        else:
            raise AssertionError(
                "Duplicate module key was accepted"
            )

    print("PASS: duplicate module detection")


def test_invalid_semester_detection():
    registry = ModuleRegistry()

    config = json.loads(json.dumps(registry.config))

    config["modules"][0]["semester"] = 3

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "modules.json"

        config_path.write_text(
            json.dumps(config), encoding="utf-8"
        )

        try:
            ModuleRegistry(config_path)
        except ValueError as error:
            assert "invalid semester" in str(error)
        else:
            raise AssertionError(
                "Invalid semester was accepted"
            )

    print("PASS: invalid semester detection")


if __name__ == "__main__":
    test_module_registry()
    test_duplicate_module_detection()
    test_invalid_semester_detection()

    print("\nAll module registry tests passed.")
