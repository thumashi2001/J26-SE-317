
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

from services.syllabus_source_registry import (
    SyllabusSourceRegistry,
)


def run_tests():
    print("--- M7.1 SYLLABUS SOURCE REGISTRY TEST ---")

    registry = SyllabusSourceRegistry()
    sources = registry.get_all()

    assert len(sources) == 8
    print("PASS: eight module source configurations")

    keys = [item["module_key"] for item in sources]
    assert len(keys) == len(set(keys))
    print("PASS: unique module identifiers")

    database = registry.get_module_sources(
        "database_systems"
    )

    assert database is not None
    assert database["verification_status"] == "unverified"
    print("PASS: Database Systems source lookup")

    assert not registry.is_module_verified(
        "database_systems"
    )
    print("PASS: unverified module safeguard")

    assert registry.get_module_sources(
        "unknown_module"
    ) is None
    print("PASS: unknown module handling")

    summary = registry.get_summary()

    assert summary["total_modules"] == 8
    assert summary["verified"] == 0
    assert summary["partially_verified"] == 0
    assert summary["unverified"] == 8
    assert summary["total_references"] == 0
    print("PASS: source coverage summary")

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "sources.json"

        invalid = {
            "schema_version": "1.0",
            "sources": [
                {
                    "module_key": "database_systems",
                    "verification_status": "verified",
                    "references": [],
                }
            ],
        }

        config_path.write_text(
            json.dumps(invalid),
            encoding="utf-8",
        )

        try:
            SyllabusSourceRegistry(config_path)
        except ValueError:
            print("PASS: unsupported verification rejected")
        else:
            raise AssertionError(
                "Verified module without sources was accepted"
            )

        duplicate = {
            "schema_version": "1.0",
            "sources": [sources[0], sources[0]],
        }

        config_path.write_text(
            json.dumps(duplicate),
            encoding="utf-8",
        )

        try:
            SyllabusSourceRegistry(config_path)
        except ValueError:
            print("PASS: duplicate module rejected")
        else:
            raise AssertionError(
                "Duplicate module was accepted"
            )

    print("\nAll M7.1 syllabus source tests passed.")


if __name__ == "__main__":
    run_tests()
