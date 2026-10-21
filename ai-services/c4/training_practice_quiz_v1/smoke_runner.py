"""Local smoke for the this-quiz pass pipeline. Does not activate a student model."""

from __future__ import annotations

import os
import json
from pathlib import Path

from training_practice_quiz_v1.generate import generate_rows
from training_practice_quiz_v1.protocol import INCOMPATIBLE_ARTIFACT, INCOMPATIBLE_REASON
from training_practice_quiz_v1.serving import assess_bundle, export_inactive_bundle
from training_practice_quiz_v1.train import finite_report, run_selection, split_rows

SMOKE_LEARNERS = 80
FULL_LEARNERS = 400
SMOKE_SEED = 17018


def run_smoke(learners: int = SMOKE_LEARNERS, seed: int = SMOKE_SEED) -> dict:
    rows = generate_rows(seed, learners)
    report = run_selection(split_rows(rows))
    report["smoke_learners"] = learners
    report["smoke_seed"] = seed
    report["incompatible_live_artifact"] = INCOMPATIBLE_ARTIFACT
    report["incompatible_reason"] = INCOMPATIBLE_REASON
    finite_report(report)
    report["run_mode"] = "full_synthetic_not_activated" if learners >= FULL_LEARNERS else "smoke"
    if report["activation_allowed"] or report["serves_students"]:
        raise RuntimeError("smoke must not activate student serving")
    return report


def main() -> None:
    full = os.environ.get("PRACTICE_QUIZ_FULL") == "1"
    learners = FULL_LEARNERS if full else SMOKE_LEARNERS
    report = run_smoke(learners=learners)
    out = Path(__file__).resolve().parents[1] / "experiments" / "results" / "practice_quiz_pass_v1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    exported = export_inactive_bundle(report, out / "inactive_bundle")
    assessed = assess_bundle(out / "inactive_bundle")
    if assessed.get("usable"):
        raise RuntimeError("inactive bundle must not be usable")
    print(
        "OK c4-practice-quiz-pass-v1 "
        f"mode={report['run_mode']} selected={report['selected_pass_model']} "
        f"test_brier={report['test_brier']:.4f} sha256={exported['sha256'][:12]} "
        "activation_allowed=false"
    )


if __name__ == "__main__":
    main()
