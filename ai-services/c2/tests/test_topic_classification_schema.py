
import json
from pathlib import Path

CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "topic_classification_schema.json"
)

print("\n--- M6.1 TOPIC CLASSIFICATION SCHEMA TEST ---")

with CONFIG_PATH.open("r", encoding="utf-8") as file:
    schema = json.load(file)

assert schema["schema_version"] == "1.0"
print("PASS: schema version")

required = schema["required_fields"]
definitions = schema["field_definitions"]

assert len(required) == len(set(required))
assert all(field in definitions for field in required)
print("PASS: required fields defined")

assert definitions["topic_id"]["type"] == [
    "string", "null"
]
print("PASS: nullable topic identifier")

assert definitions["confidence_score"]["minimum"] == 0.0
assert definitions["confidence_score"]["maximum"] == 1.0
print("PASS: confidence score range")

methods = definitions["classification_method"]["allowed_values"]

assert "unclassified" in methods
assert "manual" in methods
assert "rule_based" in methods
assert "ml_model" in methods
print("PASS: classification methods")

statuses = definitions["verification_status"]["allowed_values"]

assert "unverified" in statuses
assert "verified" in statuses
assert "pending_review" in statuses
print("PASS: verification statuses")

print("\nAll M6.1 schema tests passed.")
