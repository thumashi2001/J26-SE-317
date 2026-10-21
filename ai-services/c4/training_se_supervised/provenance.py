"""Runtime / dependency provenance capture."""

from __future__ import annotations

import platform
import sys
from typing import Any

from .protocol import DOMAIN_MARKERS, GENERATOR_VERSION, PROTOCOL_VERSION


def capture_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "protocol": PROTOCOL_VERSION,
        "generator_version": GENERATOR_VERSION,
        **DOMAIN_MARKERS,
    }
    for mod in ("numpy", "pandas", "sklearn", "joblib", "scipy"):
        try:
            m = __import__(mod if mod != "sklearn" else "sklearn")
            versions[mod] = getattr(m, "__version__", "unknown")
        except Exception as exc:  # noqa: BLE001
            versions[mod] = f"unavailable:{exc}"
    return versions
