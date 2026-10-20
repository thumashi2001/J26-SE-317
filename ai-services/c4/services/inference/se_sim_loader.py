"""Load MaskablePPO SE simulation checkpoint (se-path-sim-v0).

Simulation-only demo inference. Not validated on real SE students.
Does not affect ASSISTments research loader.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from training_se.catalogue import N_TOPICS, ORDERED_TOPICS, catalogue_hash
from training_se.observation import OBS_DIM, availability_from_obs, mastery_from_obs

PROTOCOL = "se-path-sim-v0"
DOMAIN = "se_simulation"
# Demo checkpoint chosen NOW from saved per-seed validation means (highest = seed 0).
# Not a preregistered choice — see docs/SE_DEMO_CHECKPOINT_SELECTION.md.
DEFAULT_DEMO_SEED = 0
EXPECTED_DEMO_HASH = "265bbf85cdd4b1096ba90752e2cc39f1d45daf8655ad97346f2f7d64f38c0468"
BUNDLE_STEM = "c4_se_simulation_bundle_20261012T084659312700Z"
MASTERY_THRESHOLD = 0.80


class SeSimLoadError(RuntimeError):
    """SE simulation artifacts unavailable — SE endpoints must 503 without faking."""


class SeSimValidationError(ValueError):
    """Malformed SE simulation predict request."""


def c4_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_se_bundle_dir() -> Path:
    env = os.environ.get("C4_SE_BUNDLE_DIR")
    if env:
        return Path(env)
    return c4_root() / "runtime-artifacts" / "se_path_sim_v0" / BUNDLE_STEM


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_bool_mask(mask: Any, n: int) -> np.ndarray:
    arr = np.asarray(mask)
    if arr.ndim != 1 or arr.shape[0] != n:
        raise SeSimValidationError(f"action_mask length must be {n} (got shape {arr.shape})")
    if arr.dtype == bool:
        return arr.copy()
    if np.issubdtype(arr.dtype, np.number):
        if not np.isfinite(arr).all():
            raise SeSimValidationError("action_mask contains non-finite values")
        uniq = set(np.unique(arr).tolist())
        if not uniq.issubset({0, 1, 0.0, 1.0}):
            raise SeSimValidationError("action_mask numeric values must be 0 or 1")
        return arr.astype(bool)
    # list of bools / strings
    try:
        return np.asarray([bool(x) for x in arr], dtype=bool)
    except Exception as exc:  # noqa: BLE001
        raise SeSimValidationError("action_mask must be boolean or 0/1") from exc


@dataclass(frozen=True)
class SeSimPredictResult:
    action_index: int
    topic_id: str
    algorithm: str
    seed: int
    protocol: str
    model_hash: str
    catalogue_hash: str
    domain: str = DOMAIN
    synthetic: bool = True
    simulation_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_index": self.action_index,
            "topic_id": self.topic_id,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "protocol": self.protocol,
            "model_hash": self.model_hash,
            "catalogue_hash": self.catalogue_hash,
            "domain": self.domain,
            "synthetic": self.synthetic,
            "simulation_only": self.simulation_only,
            "note": (
                "SE simulation demo only. Not validated on real SE students. "
                "Not exam-readiness or calibrated confidence. "
                "Not the Node weakest_stored_mastery_v1 product heuristic."
            ),
        }


class SeSimulationPolicy:
    """Load-once SE MaskablePPO for /v1/se-simulation/*."""

    def __init__(
        self,
        bundle_dir: Path | None = None,
        *,
        seed: int | None = None,
        require_expected_hash: bool = True,
    ):
        self.bundle_dir = Path(bundle_dir) if bundle_dir else default_se_bundle_dir()
        self.export_dir = self.bundle_dir / "export_bundle"
        self.seed = int(os.environ.get("C4_SE_DEMO_SEED", seed if seed is not None else DEFAULT_DEMO_SEED))
        self.protocol = PROTOCOL
        self.algorithm = "maskable_ppo"
        self.topic_ids: list[str] = list(ORDERED_TOPICS)
        self.obs_dim = OBS_DIM
        self.n_actions = N_TOPICS
        self.catalogue_hash_expected = catalogue_hash()
        self.catalogue_hash_loaded: str | None = None
        self.model_path: Path | None = None
        self.model_hash: str | None = None
        self.load_error: str | None = None
        self._model = None
        self._require_expected_hash = require_expected_hash
        self._obs_schema: dict[str, Any] | None = None
        self._try_load()

    @property
    def ready(self) -> bool:
        return self._model is not None and self.load_error is None

    def _try_load(self) -> None:
        try:
            self._load()
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self.load_error = str(exc)

    def _load(self) -> None:
        if not self.export_dir.is_dir():
            raise SeSimLoadError(
                f"SE export_bundle not found at {self.export_dir}. "
                "Run: python scripts/import_se_simulation_bundle.py"
            )

        cat_path = self.export_dir / "topic_catalogue.json"
        schema_path = self.export_dir / "observation_schema.json"
        if not cat_path.is_file() or not schema_path.is_file():
            raise SeSimLoadError("Missing topic_catalogue.json or observation_schema.json")

        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        topics = [str(t) for t in cat.get("topics") or []]
        if topics != list(ORDERED_TOPICS):
            raise SeSimLoadError(
                "Loaded catalogue topics do not match training_se.ORDERED_TOPICS"
            )
        self.catalogue_hash_loaded = str(cat.get("sha256") or "")
        if self.catalogue_hash_loaded != self.catalogue_hash_expected:
            raise SeSimLoadError(
                f"Catalogue hash mismatch: bundle {self.catalogue_hash_loaded} "
                f"!= code {self.catalogue_hash_expected}"
            )

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if int(schema.get("dim", -1)) != OBS_DIM:
            raise SeSimLoadError(f"Observation schema dim {schema.get('dim')} != {OBS_DIM}")
        self._obs_schema = schema

        self.model_path = (
            self.export_dir / "models" / f"seed_{self.seed}" / "maskable_ppo_final.zip"
        )
        if not self.model_path.is_file():
            raise SeSimLoadError(f"Checkpoint not found: {self.model_path}")
        self.model_hash = _sha256(self.model_path)
        if self._require_expected_hash and self.seed == DEFAULT_DEMO_SEED:
            if self.model_hash != EXPECTED_DEMO_HASH:
                raise SeSimLoadError(
                    f"Demo checkpoint hash mismatch for seed {self.seed}: "
                    f"got {self.model_hash}, expected {EXPECTED_DEMO_HASH}"
                )

        try:
            from sb3_contrib import MaskablePPO
        except ImportError as exc:
            raise SeSimLoadError(
                "sb3-contrib required for SE simulation MaskablePPO inference"
            ) from exc

        self._model = MaskablePPO.load(str(self.model_path), device="cpu")
        obs_space = getattr(self._model, "observation_space", None)
        if obs_space is not None and hasattr(obs_space, "shape"):
            if tuple(obs_space.shape) != (OBS_DIM,):
                raise SeSimLoadError(
                    f"Model obs shape {obs_space.shape} incompatible with dim={OBS_DIM}"
                )

    def readiness(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "protocol": self.protocol,
            "domain": DOMAIN,
            "synthetic": True,
            "simulation_only": True,
            "model_hash": self.model_hash,
            "catalogue_hash": self.catalogue_hash_loaded,
            "model_path": str(self.model_path) if self.model_path else None,
            "n_topics": self.n_actions,
            "obs_dim": self.obs_dim,
            "topic_ids": list(self.topic_ids) if self.ready else [],
            "mask_rule": (
                "Training/eval masks: available topics with mastery < 0.8; "
                "if all available topics are mastered, reopen all available topics. "
                "Unavailable topics are never permitted. All-invalid requests are rejected."
            ),
            "error": self.load_error,
        }

    def validate_observation(self, observation: Any) -> np.ndarray:
        try:
            obs = np.asarray(observation, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise SeSimValidationError(f"observation must be numeric: {exc}") from exc
        if obs.ndim != 1 or obs.shape[0] != OBS_DIM:
            raise SeSimValidationError(
                f"observation shape must be ({OBS_DIM},); got {obs.shape}"
            )
        if not np.isfinite(obs).all():
            raise SeSimValidationError("observation contains NaN or Inf")
        if (obs < 0.0).any() or (obs > 1.0).any():
            raise SeSimValidationError("observation values must be within [0, 1]")

        mastery = mastery_from_obs(obs.astype(np.float32))
        avail = availability_from_obs(obs.astype(np.float32))
        # availability must be 0/1
        for i, a in enumerate(avail):
            if a not in (0.0, 1.0):
                raise SeSimValidationError(
                    f"available[{i}] must be 0 or 1 (got {a})"
                )
        # unavailable mastery slots must be 0
        for i in range(N_TOPICS):
            if avail[i] < 0.5 and mastery[i] != 0.0:
                raise SeSimValidationError(
                    f"unavailable topic index {i} must have mastery 0 "
                    f"(got {mastery[i]}); missing ≠ genuine zero"
                )

        mean_m, frac_m, step_frac, prior = obs[24:28]
        avail_bool = avail > 0.5
        if avail_bool.any():
            expected_mean = float(mastery[avail_bool].mean())
            expected_frac = float((mastery[avail_bool] >= MASTERY_THRESHOLD).mean())
        else:
            expected_mean = 0.0
            expected_frac = 0.0
        if abs(float(mean_m) - expected_mean) > 1e-4:
            raise SeSimValidationError(
                f"mean_mastery inconsistent with available mastery "
                f"(got {mean_m}, expected {expected_mean})"
            )
        if abs(float(frac_m) - expected_frac) > 1e-4:
            raise SeSimValidationError(
                f"frac_mastered inconsistent with available mastery "
                f"(got {frac_m}, expected {expected_frac})"
            )
        return obs.astype(np.float32)

    def validate_mask(self, action_mask: Any, obs: np.ndarray) -> np.ndarray:
        mask = _as_bool_mask(action_mask, N_TOPICS)
        # Strict booleans already; reject if any True on unavailable
        avail = availability_from_obs(obs) > 0.5
        for i in range(N_TOPICS):
            if mask[i] and not avail[i]:
                raise SeSimValidationError(
                    f"action_mask[{i}] is True but topic is unavailable; "
                    "unavailable topics are never permitted"
                )
        if not mask.any():
            raise SeSimValidationError(
                "action_mask has no valid actions (all-invalid). "
                "Refusing to select an action. "
                "Training reopen rule only applies when at least one topic is available."
            )
        return mask

    def validate_catalogue_hash(self, catalogue_hash_client: str | None) -> None:
        if catalogue_hash_client is None:
            return
        if catalogue_hash_client != self.catalogue_hash_loaded:
            raise SeSimValidationError(
                f"catalogue_hash mismatch: request {catalogue_hash_client} "
                f"!= loaded {self.catalogue_hash_loaded}"
            )

    def validate_protocol(self, protocol: str | None) -> None:
        if protocol is None:
            return
        if protocol != PROTOCOL:
            raise SeSimValidationError(f"protocol must be '{PROTOCOL}' (got '{protocol}')")

    def predict(
        self,
        *,
        observation: Any,
        action_mask: Any,
        protocol: str | None = None,
        catalogue_hash_client: str | None = None,
        deterministic: bool = True,
    ) -> SeSimPredictResult:
        if not self.ready or self._model is None:
            raise SeSimLoadError(
                self.load_error or "SE simulation model not loaded; refusing fake predictions"
            )
        self.validate_protocol(protocol)
        self.validate_catalogue_hash(catalogue_hash_client)
        obs = self.validate_observation(observation)
        mask = self.validate_mask(action_mask, obs)

        action, _state = self._model.predict(
            obs,
            deterministic=deterministic,
            action_masks=mask,
        )
        action_index = int(action)
        if action_index < 0 or action_index >= N_TOPICS:
            raise SeSimLoadError(f"Model returned out-of-range action {action_index}")
        if not bool(mask[action_index]):
            # Do not silently remap
            raise SeSimLoadError(
                f"Model selected masked-invalid action {action_index}; refusing to return it"
            )
        if availability_from_obs(obs)[action_index] < 0.5:
            raise SeSimLoadError(
                f"Model selected unavailable topic index {action_index}; refusing"
            )

        return SeSimPredictResult(
            action_index=action_index,
            topic_id=self.topic_ids[action_index],
            algorithm=self.algorithm,
            seed=self.seed,
            protocol=self.protocol,
            model_hash=self.model_hash or "",
            catalogue_hash=self.catalogue_hash_loaded or "",
        )
