
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.exam_structure_validator import (
    load_exam_structures,
    get_exam_structure,
    validate_exam_structure,
)


print("\n--- EXAMINATION STRUCTURE VALIDATION ---")

data = load_exam_structures()

assert len(data["structures"]) == 8
print("PASS: eight module structures loaded")

database = get_exam_structure("database_systems")

assert database is not None
assert database["structure"]["total_marks"] == 100
assert database["structure"]["question_count"] == 4

print("PASS: Database Systems structure retrieval")

result = validate_exam_structure("database_systems")

assert result["valid"] is True
assert result["ready"] is False
assert result["verification_status"] == "partially_verified"

print("PASS: partially verified structure validation")

unverified = validate_exam_structure(
    "software_project_management"
)

assert unverified["valid"] is True
assert unverified["ready"] is False
assert unverified["verification_status"] == "unverified"
assert len(unverified["warnings"]) > 0

print("PASS: unverified structure handling")

unknown = validate_exam_structure("unknown_module")

assert unknown["valid"] is False
assert "Unknown module" in unknown["errors"]

print("PASS: unknown module rejection")

for module in data["structures"]:
    module_result = validate_exam_structure(
        module["module_key"]
    )

    assert module_result["valid"] is True

print("PASS: all eight configurations validated")

print("\n--- DATABASE SYSTEMS STATUS ---")
print("Valid:", result["valid"])
print("Ready:", result["ready"])
print("Verification:", result["verification_status"])
print("Warnings:", result["warnings"])

print("\nAll examination structure validator tests passed.")
