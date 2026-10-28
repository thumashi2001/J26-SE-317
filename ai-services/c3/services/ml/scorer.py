"""Advisory AI score estimate: a fine-tuned transformer that reads (reference answer, student answer) and estimates the
mark ratio (0..1).

WHAT THIS IS
    The model was fine-tuned in experiments/model_comparison_extra.py and chosen on VALIDATION only. It is an
    ADVISORY second opinion shown next to the rubric mark. It never changes a mark: the rubric engine (F2) stays the
        only
    source of marks, and the lecturer stays the final authority.

WHAT THIS IS NOT
    Its training labels are tier-derived (not human-marked), so agreement with the rubric mark or with the dataset is
        not
    evidence of agreement with human markers. It is disabled unless C3_ML_MODEL_DIR points at a checkpoint folder, and
        any
    failure (no torch, missing files, bad input) returns None so marking continues without it.

Checkpoint folder layout (written by model_comparison_extra.py): model.pt (state_dict + model_name + max_len), tokenizer
files, and optionally config.json (so loading needs no network).

STATUS: optional runtime component of POST /c3/assess; off by default.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("c3.ml_scorer")

ENV_DIR = "C3_ML_MODEL_DIR"
MAX_CHARS = 4000  # inputs are truncated by the tokenizer anyway; this only bounds work on absurdly long text


class MLScorer:
    """Lazy, thread-safe wrapper around one saved checkpoint. Construct cheaply; the model loads on first use."""

    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self._lock = threading.Lock()
        self._loaded = False
        self._failure: str | None = None
        self._model: Any = None
        self._tok: Any = None
        self._max_len = 256
        self.model_name: str | None = None

    def configured(self) -> bool:
        """True when a checkpoint file exists in the configured folder."""
        return bool(self.model_dir and (self.model_dir / "model.pt").is_file())

    def _load(self) -> None:
        """Load once. Any problem is remembered in _failure instead of being raised."""
        with self._lock:
            if self._loaded or self._failure:
                return
            try:
                import torch
                from torch import nn
                from transformers import AutoConfig, AutoModel, AutoTokenizer

                blob = torch.load(self.model_dir / "model.pt", map_location="cpu", weights_only=True)
                self.model_name = blob["model_name"]
                self._max_len = int(blob.get("max_len", 256))
                local_cfg = (self.model_dir / "config.json").is_file()
                config = AutoConfig.from_pretrained(self.model_dir if local_cfg else self.model_name)
                tok = AutoTokenizer.from_pretrained(self.model_dir)

                class Reg(nn.Module):  # same architecture as training: encoder -> CLS -> linear -> sigmoid
                    """Trained model: encoder, first-token vector, one linear layer, sigmoid (a 0..1 mark ratio)."""
                    def __init__(self):
                        super().__init__()
                        self.enc = AutoModel.from_config(config)
                        self.head = nn.Linear(config.hidden_size, 1)

                    def forward(self, **kw):
                        """Run the encoder and return the estimated mark ratio for each input."""
                        return torch.sigmoid(self.head(self.enc(**kw).last_hidden_state[:, 0])).squeeze(-1)

                model = Reg()
                model.load_state_dict(blob["state_dict"])
                model.eval()
                self._model, self._tok, self._loaded = model, tok, True
            except Exception as exc:  # optional component: never break marking
                self._failure = f"{type(exc).__name__}: {exc}"[:300]
                logger.warning("ML scorer unavailable: %s", self._failure)

    def estimate_ratio(self, reference_answer: str, student_answer: str) -> float | None:
        """Estimated mark ratio in [0, 1], or None when unavailable (not configured, failed to load, or empty input)."""
        if not self.configured() or not reference_answer.strip():
            return None
        self._load()
        if not self._loaded:
            return None
        try:
            import torch

            batch = self._tok([reference_answer[:MAX_CHARS]], [student_answer[:MAX_CHARS]], truncation=True,
                             max_length=self._max_len, padding=True, return_tensors="pt")
            with torch.no_grad():
                return float(min(1.0, max(0.0, self._model(**batch).float().item())))
        except Exception as exc:
            logger.warning("ML scorer inference failed: %s", exc)
            return None

    def status(self) -> dict[str, Any]:
        """Safe status for /health (no model load, no network)."""
        return {"configured": self.configured(), "loaded": self._loaded, "model": self.model_name,
                "failure": self._failure}


_scorer: MLScorer | None = None
_scorer_dir: str | None = None
_registry_lock = threading.Lock()


def get_scorer() -> MLScorer:
    """Process-wide scorer for the current C3_ML_MODEL_DIR (re-created if the variable changes, e.g. in tests)."""
    global _scorer, _scorer_dir
    current = os.getenv(ENV_DIR) or None
    with _registry_lock:
        if _scorer is None or current != _scorer_dir:
            _scorer, _scorer_dir = MLScorer(current), current
        return _scorer
