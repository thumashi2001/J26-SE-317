"""C4 reinforcement-learning training pipeline (data, simulator, env, train, export)."""

from .protocol import ENV_PROTOCOL_VERSION

__version__ = "0.2.0"
GENERATOR_VERSION = "c4-sim-0.1.0"
__all__ = ["__version__", "GENERATOR_VERSION", "ENV_PROTOCOL_VERSION"]
