"""SE supervised simulation prototypes (se-supervised-sim-v0).

Explicitly synthetic. Does not retrain ASSISTments or SE MaskablePPO policies.
Does not claim real-SE or real-exam validation.
"""

from .protocol import PROTOCOL_VERSION, GENERATOR_VERSION

__all__ = ["PROTOCOL_VERSION", "GENERATOR_VERSION"]
