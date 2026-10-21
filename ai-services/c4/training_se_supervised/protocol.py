"""Protocol markers for SE supervised simulation."""

from __future__ import annotations

PROTOCOL_VERSION = "se-supervised-sim-v0"
GENERATOR_VERSION = "se_supervised_gen_v0"

DOMAIN_MARKERS = {
    "domain": "se_simulation",
    "synthetic": True,
    "simulation_only": True,
    "real_exam_validation": False,
    "protocol": PROTOCOL_VERSION,
    "generator_version": GENERATOR_VERSION,
}

NON_CLAIMS = (
    "Synthetic performance measures agreement with the generator only.",
    "Results do not validate real SE students or actual module exams.",
    "Assumed generator parameters are not empirically fitted.",
    "Do not wire this response model into se-path-sim-v0 without a new versioned experiment.",
)
