"""Protocol markers for SE supervised simulation v1."""

from __future__ import annotations

PROTOCOL_VERSION = "se-supervised-sim-v1"
GENERATOR_VERSION = "se_supervised_gen_v1"

DOMAIN_MARKERS = {
    "domain": "se_simulation",
    "synthetic": True,
    "simulation_only": True,
    "real_exam_validation": False,
    "protocol": PROTOCOL_VERSION,
    "generator_version": GENERATOR_VERSION,
    "scope_decision": "S1",
}

NON_CLAIMS = (
    "Synthetic performance measures agreement with the generator only.",
    "Results do not validate real SE students or actual module exams.",
    "Assumed generator parameters are not empirically fitted.",
    "Do not wire this response model into se-path-sim-v1 without a new versioned experiment.",
    "PASS_THRESHOLD 0.55 is a labelled synthetic exam-score cutoff, not an institutional rule.",
    "Classification probability operating point is separate from PASS_THRESHOLD.",
)
