
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from services.topic_classification_validator import (
    TopicClassificationValidator,
)


print("\n--- M6.2 TOPIC CLASSIFICATION VALIDATION ---")

validator = TopicClassificationValidator()


def make_record(**changes):
    record = {
        "question_id": "IT3020-2023-Q1(a)",
        "module_key": "database_systems",
        "topic_id": None,
        "subtopic": None,
        "classification_method": "unclassified",
        "confidence_score": None,
        "verification_status": "unverified",
    }

    record.update(changes)
    return record


def check(name, record, expected_valid):
    result = validator.validate(record)

    assert result["valid"] == expected_valid, (
        f"{name}: unexpected result {result}"
    )

    print(f"PASS: {name}")


check(
    "valid unclassified question",
    make_record(),
    True,
)

check(
    "missing required field",
    {
        key: value
        for key, value in make_record().items()
        if key != "question_id"
    },
    False,
)

check(
    "unknown module rejection",
    make_record(module_key="unknown_module"),
    False,
)

check(
    "unknown topic rejection",
    make_record(
        topic_id="UNKNOWN_TOPIC",
        classification_method="manual",
    ),
    False,
)

check(
    "invalid confidence score",
    make_record(confidence_score=1.5),
    False,
)

check(
    "negative confidence score",
    make_record(confidence_score=-0.2),
    False,
)

check(
    "invalid classification method",
    make_record(classification_method="unknown"),
    False,
)

check(
    "invalid verification status",
    make_record(verification_status="approved"),
    False,
)

check(
    "unclassified question with assigned topic",
    make_record(topic_id="DB_SQL"),
    False,
)

check(
    "unclassified question marked verified",
    make_record(verification_status="verified"),
    False,
)

check(
    "empty question identifier",
    make_record(question_id=""),
    False,
)

check(
    "invalid subtopic type",
    make_record(subtopic=123),
    False,
)

print(
    "\nAll M6.2 topic classification "
    "validator tests passed."
)
