"""Load a real MaskablePPO checkpoint for ASSISTments research inference.

Never returns fabricated actions when the model or catalogue is missing.
Does not map ASSISTments skill IDs to SLIIT SE topics.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Demo selection: highest mean validation return; lowest-seed tie-break.
# Recorded in docs/DEMO_CHECKPOINT_SELECTION.md (seed 2 for this bundle).
DEFAULT_DEMO_SEED = 2
DEFAULT_PROTOCOL = "c4-env-eval-v1.1"
BUNDLE_DIRNAME = "c4_maskable_ppo_research_bundle_20261012T062204868154Z"
EXPECTED_DEMO_HASH = "7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca"


class PolicyLoadError(RuntimeError):
    """Model / catalogue / dependency unavailable — service must not invent predictions."""


class PredictionValidationError(ValueError):
    """Malformed or incompatible request for research inference."""


def c4_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_bundle_dir() -> Path:
    env = os.environ.get("C4_BUNDLE_DIR")
    if env:
        return Path(env)
    return c4_root() / "runtime-artifacts" / BUNDLE_DIRNAME


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_bool_mask(mask: Any, n: int) -> np.ndarray:
    arr = np.asarray(mask)
    if arr.ndim != 1 or arr.shape[0] != n:
        raise PredictionValidationError(
            f"action_mask length must be {n} (got shape {arr.shape})"
        )
    if arr.dtype == bool:
        return arr
    # Accept 0/1 numeric masks
    if np.issubdtype(arr.dtype, np.number):
        if not np.isfinite(arr).all():
            raise PredictionValidationError("action_mask contains non-finite values")
        uniq = set(np.unique(arr).tolist())
        if not uniq.issubset({0, 1, 0.0, 1.0}):
            raise PredictionValidationError("action_mask numeric values must be 0 or 1")
        return arr.astype(bool)
    raise PredictionValidationError("action_mask must be boolean or 0/1 numeric")


@dataclass(frozen=True)
class PredictResult:
    action_index: int
    skill_id: str
    algorithm: str
    seed: int
    protocol: str
    model_hash: str
    uncalibrated_action_probability: float | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "action_index": self.action_index,
            "skill_id": self.skill_id,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "protocol": self.protocol,
            "model_hash": self.model_hash,
            "domain": "assistments_research",
            "note": (
                "ASSISTments skill IDs only. Not calibrated confidence. "
                "Not SLIIT SE product behaviour."
            ),
        }
        if self.uncalibrated_action_probability is not None:
            out["uncalibrated_action_probability"] = self.uncalibrated_action_probability
        return out


class MaskablePpoResearchPolicy:
    """Load-once MaskablePPO wrapper for local research inference."""

    def __init__(
        self,
        bundle_dir: Path | None = None,
        *,
        seed: int | None = None,
        require_expected_hash: bool = True,
    ):
        self.bundle_dir = Path(bundle_dir) if bundle_dir else default_bundle_dir()
        self.seed = int(os.environ.get("C4_DEMO_SEED", seed if seed is not None else DEFAULT_DEMO_SEED))
        self.protocol = DEFAULT_PROTOCOL
        self.algorithm = "maskable_ppo"
        self._model = None
        self.skill_ids: list[str] = []
        self.obs_dim = 0
        self.n_actions = 0
        self.model_path: Path | None = None
        self.model_hash: str | None = None
        self.load_error: str | None = None
        self._require_expected_hash = require_expected_hash
        self._try_load()

    @property
    def ready(self) -> bool:
        return self._model is not None and self.load_error is None

    def _try_load(self) -> None:
        try:
            self._load()
        except Exception as exc:  # noqa: BLE001 — surface any load failure as not-ready
            self._model = None
            self.load_error = str(exc)

    def _load(self) -> None:
        if not self.bundle_dir.is_dir():
            raise PolicyLoadError(f"Bundle directory not found: {self.bundle_dir}")

        catalogue_path = self.bundle_dir / "artifacts" / "skill_catalogue.json"
        if not catalogue_path.is_file():
            raise PolicyLoadError(f"Missing skill_catalogue.json at {catalogue_path}")
        cat = json.loads(catalogue_path.read_text(encoding="utf-8"))
        skills = cat.get("skills")
        if not isinstance(skills, list) or not skills:
            raise PolicyLoadError("skill_catalogue.json missing non-empty skills list")
        self.skill_ids = [str(s) for s in skills]
        self.n_actions = len(self.skill_ids)
        self.obs_dim = self.n_actions + 4  # mastery_K + mean, frac_mastered, step_frac, prior

        self.model_path = (
            self.bundle_dir / "models" / f"seed_{self.seed}" / "maskable_ppo_final.zip"
        )
        if not self.model_path.is_file():
            raise PolicyLoadError(f"Checkpoint not found: {self.model_path}")

        self.model_hash = _sha256(self.model_path)
        if self._require_expected_hash and self.seed == DEFAULT_DEMO_SEED:
            if self.model_hash != EXPECTED_DEMO_HASH:
                raise PolicyLoadError(
                    f"Demo checkpoint hash mismatch for seed {self.seed}: "
                    f"got {self.model_hash}, expected {EXPECTED_DEMO_HASH}"
                )

        try:
            from sb3_contrib import MaskablePPO
        except ImportError as exc:
            raise PolicyLoadError(
                "sb3-contrib is required for MaskablePPO inference. "
                "Install requirements.txt / requirements-training.txt."
            ) from exc

        self._model = MaskablePPO.load(str(self.model_path), device="cpu")
        # Observation space check when available
        obs_space = getattr(self._model, "observation_space", None)
        if obs_space is not None and hasattr(obs_space, "shape"):
            expected = tuple(obs_space.shape)
            if expected != (self.obs_dim,):
                raise PolicyLoadError(
                    f"Model observation shape {expected} incompatible with "
                    f"catalogue-derived obs_dim={self.obs_dim}"
                )

    def readiness(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "protocol": self.protocol,
            "model_hash": self.model_hash,
            "model_path": str(self.model_path) if self.model_path else None,
            "n_skills": len(self.skill_ids),
            "obs_dim": self.obs_dim,
            "skill_ids": list(self.skill_ids) if self.ready else [],
            "domain": "assistments_research",
            "error": self.load_error,
        }

    def validate_catalogue(self, skill_ids: list[Any] | None) -> None:
        if skill_ids is None:
            return
        incoming = [str(s) for s in skill_ids]
        if incoming != self.skill_ids:
            raise PredictionValidationError(
                "Incompatible skill catalogue: request skill_ids must match the "
                "exact ordered ASSISTments catalogue used to train this checkpoint. "
                "Do not remap SE topics into these slots."
            )

    def validate_observation(self, observation: Any) -> np.ndarray:
        try:
            obs = np.asarray(observation, dtype=np.float32)
        except (TypeError, ValueError) as exc:
            raise PredictionValidationError(f"observation must be a numeric array: {exc}") from exc
        if obs.ndim != 1 or obs.shape[0] != self.obs_dim:
            raise PredictionValidationError(
                f"observation shape must be ({self.obs_dim},) "
                f"[mastery_1..K, mean_mastery, frac_mastered, step_frac, prior_strength]; "
                f"got {obs.shape}"
            )
        if not np.isfinite(obs).all():
            raise PredictionValidationError("observation contains non-finite values")
        if (obs < 0.0).any() or (obs > 1.0).any():
            raise PredictionValidationError("observation values must be within [0, 1]")
        return obs

    def validate_protocol(self, protocol: str | None) -> None:
        if protocol is None:
            return
        if protocol != self.protocol:
            raise PredictionValidationError(
                f"protocol must be '{self.protocol}' (got '{protocol}')"
            )

    def predict(
        self,
        *,
        observation: Any,
        action_mask: Any,
        skill_ids: list[Any] | None = None,
        protocol: str | None = None,
        deterministic: bool = True,
        return_probability: bool = False,
    ) -> PredictResult:
        if not self.ready or self._model is None:
            raise PolicyLoadError(
                self.load_error or "MaskablePPO model is not loaded; refusing fake predictions"
            )

        self.validate_protocol(protocol)
        self.validate_catalogue(skill_ids)
        obs = self.validate_observation(observation)
        mask = _as_bool_mask(action_mask, self.n_actions)

        if not mask.any():
            raise PredictionValidationError(
                "action_mask has no valid actions (all-invalid). "
                "Refusing to select an action; caller must supply at least one True entry."
            )

        action, _state = self._model.predict(
            obs,
            deterministic=deterministic,
            action_masks=mask,
        )
        action_index = int(action)
        if action_index < 0 or action_index >= self.n_actions:
            raise PolicyLoadError(f"Model returned out-of-range action {action_index}")
        if not bool(mask[action_index]):
            raise PolicyLoadError(
                f"Model selected masked-invalid action {action_index}; refusing to return it"
            )

        prob: float | None = None
        if return_probability:
            # Raw policy mass under the mask — explicitly uncalibrated; not "confidence".
            try:
                import torch

                obs_t = torch.as_tensor(obs).float().unsqueeze(0)
                with torch.no_grad():
                    dist = self._model.policy.get_distribution(obs_t, action_masks=mask)
                    probs = dist.distribution.probs.squeeze(0).cpu().numpy()
                prob = float(probs[action_index])
            except Exception:  # noqa: BLE001
                prob = None

        return PredictResult(
            action_index=action_index,
            skill_id=self.skill_ids[action_index],
            algorithm=self.algorithm,
            seed=self.seed,
            protocol=self.protocol,
            model_hash=self.model_hash or "",
            uncalibrated_action_probability=prob,
        )
