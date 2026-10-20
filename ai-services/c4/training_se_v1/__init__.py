"""SE path simulation training (protocol se-path-sim-v1).

Additive package — does not modify ``training_se`` (se-path-sim-v0).
S1 scope: 46 C1 practice topics with semester eligibility masks.
Synthetic simulation only — not measured SLIIT SE student behaviour.
"""

from .protocol import GENERATOR_VERSION, PROTOCOL_VERSION

__all__ = ["PROTOCOL_VERSION", "GENERATOR_VERSION"]
