"""Helpers for Colab ZIP extraction and path discovery."""

from __future__ import annotations

from pathlib import Path


def find_c4_root(start: Path | str | None = None) -> Path:
    """Locate ai-services/c4 containing training_se/ after ZIP extract."""
    start = Path(start or Path.cwd()).resolve()
    candidates = [start, *start.parents]
    # Also search common extract layouts
    for base in list(candidates):
        for pattern in (
            base / "ai-services" / "c4",
            base / "c4",
            base,
        ):
            if (pattern / "training_se" / "protocol.py").is_file():
                return pattern.resolve()
    # Walk down a few levels
    for base in candidates[:3]:
        for path in base.rglob("training_se/protocol.py"):
            return path.parents[1].resolve()
    raise FileNotFoundError(
        "Could not find ai-services/c4 with training_se/. "
        "Re-run the ZIP upload/extract cell, then this imports cell."
    )


def require_symbol(name: str, value: object) -> None:
    if value is None:
        raise RuntimeError(
            f"Required name {name!r} is missing. Run the prerequisite notebook cells "
            "in order (install → extract → mount → imports)."
        )
