"""Export frozen S1 catalogue + feature names into backend C4 JS (C4-owned)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

C4 = Path(__file__).resolve().parents[1]
REPO = C4.parents[1]
sys.path.insert(0, str(C4))

from catalogues.c1_practice_full_2026_10 import (  # noqa: E402
    N_TOPICS,
    ORDERED_TOPICS,
    TOPIC_LABEL,
    TOPIC_MODULE,
    TOPIC_SEMESTER,
    Y3S1_TOPICS,
    Y3S2_TOPICS,
    catalogue_hash,
)
from training_se_supervised_v1.features_exam import exam_feature_names  # noqa: E402
from training_se_supervised_v1.features_response import response_feature_names  # noqa: E402

OUT = REPO / "backend" / "src" / "modules" / "c4" / "data" / "simCatalogue.generated.js"


def main() -> None:
    topics = list(ORDERED_TOPICS)
    parts = [
        "/** Auto-synced from ai-services/c4/catalogues/c1_practice_full_2026_10.py — do not hand-edit topic order. */",
        f"export const SIM_CATALOGUE_HASH = {json.dumps(catalogue_hash())};",
        f"export const SIM_N_TOPICS = {N_TOPICS};",
        f"export const SIM_OBS_DIM = {2 * N_TOPICS + 4};",
        f"export const SIM_ORDERED_TOPICS = Object.freeze({json.dumps(topics)});",
        f"export const SIM_Y3S1_TOPICS = Object.freeze({json.dumps(list(Y3S1_TOPICS))});",
        f"export const SIM_Y3S2_TOPICS = Object.freeze({json.dumps(list(Y3S2_TOPICS))});",
        f"export const SIM_TOPIC_SEMESTER = Object.freeze({json.dumps({t: TOPIC_SEMESTER[t] for t in topics})});",
        f"export const SIM_TOPIC_LABEL = Object.freeze({json.dumps({t: TOPIC_LABEL[t] for t in topics})});",
        f"export const SIM_TOPIC_MODULE = Object.freeze({json.dumps({t: TOPIC_MODULE[t] for t in topics})});",
        f"export const SIM_RESPONSE_FEATURE_NAMES = Object.freeze({json.dumps(response_feature_names())});",
        f"export const SIM_EXAM_FEATURE_NAMES = Object.freeze({json.dumps(exam_feature_names())});",
        "export const SIM_PASS_THRESHOLD = 0.55;",
        "export const SIM_CLASSIFICATION_PROB_THRESHOLD = 0.5;",
        "export const SIM_MASTERY_THRESHOLD = 0.8;",
        """
export function simTopicIndex(topic) {
  const i = SIM_ORDERED_TOPICS.indexOf(topic);
  if (i < 0) {
    const err = new Error(`Unknown sim topic: ${topic}`);
    err.status = 400;
    throw err;
  }
  return i;
}

export function simSemesterEligibilityMask(semester) {
  if (semester !== 'Y3S1' && semester !== 'Y3S2') {
    const err = new Error('semester must be Y3S1 or Y3S2');
    err.status = 400;
    throw err;
  }
  return SIM_ORDERED_TOPICS.map((t) => SIM_TOPIC_SEMESTER[t] === semester);
}
""".strip(),
    ]
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
