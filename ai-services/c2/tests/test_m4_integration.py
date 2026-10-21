
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.module_registry import ModuleRegistry
from services.dataset_coverage import generate_coverage_report
from services.synthetic_rules import SyntheticRules


def test_m4_integration():
    registry = ModuleRegistry()

    rules = SyntheticRules(registry=registry)

    report = generate_coverage_report(registry=registry)

    assert len(registry.get_all()) == 8
    assert len(report["modules"]) == 8

    for module in registry.get_all():
        key = module["module_key"]

        coverage = next(
            row for row in report["modules"]
            if row["module_key"] == key
        )

        assert coverage["semester"] == module["semester"]
        assert coverage["module_name"] == module["module_name"]

        readiness = rules.check_module_readiness(key)

        assert readiness["module_key"] == key
        assert isinstance(readiness["ready"], bool)

    totals = report["totals"]

    assert totals["authentic_papers"] >= 0
    assert totals["authentic_questions"] >= 0
    assert totals["synthetic_papers"] >= 0
    assert totals["synthetic_questions"] >= 0

    print("\n--- M4 INTEGRATION SUMMARY ---")
    print("Registered modules:", len(registry.get_all()))
    print("Authentic papers:", totals["authentic_papers"])
    print("Authentic questions:", totals["authentic_questions"])
    print("Synthetic papers:", totals["synthetic_papers"])
    print("Synthetic questions:", totals["synthetic_questions"])
    print("Modules with authentic data:",
          totals["modules_with_authentic_papers"])

    print("\nPASS: module registry integration")
    print("PASS: dataset coverage integration")
    print("PASS: synthetic rules integration")


if __name__ == "__main__":
    test_m4_integration()

    print("\nAll M4 integration tests passed.")
