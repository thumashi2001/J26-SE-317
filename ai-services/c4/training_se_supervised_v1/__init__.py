"""SE supervised simulation (protocol se-supervised-sim-v1).

Additive package — does not modify ``training_se_supervised`` (v0).
S1: 46-topic catalogue; semester-restricted practice and mock exams.
"""

from .protocol import GENERATOR_VERSION, PROTOCOL_VERSION

__all__ = ["PROTOCOL_VERSION", "GENERATOR_VERSION"]
