"""Load MaskablePPO SE path simulation checkpoint (se-path-sim-v1).

Isolated from se-path-sim-v0 / ASSISTments. Simulation-only demo inference.
Does not wire into Node student heuristic.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from catalogues.c1_practice_full_2026_10 import (
    N_TOPICS,
    ORDERED_TOPICS,
    Y3S1_TOPICS,
    Y3S2_TOPICS,
    catalogue_hash,
    semester_eligibility_mask,
)
from training_se_v1.observation import OBS_DIM, availability_from_obs, mastery_from_obs

PROTOCOL = "se-path-sim-v1"
DOMAIN = "se_simulation"
EXPECTED_CATALOGUE_HASH = (
    "95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622"
)
# Demo seed from saved validation means across Y3S1+Y3S2 (see SE_DEMO_CHECKPOINT_SELECTION_V1.md).
DEFAULT_DEMO_SEED = 2
EXPECTED_DEMO_HASH = (
    "53d2c5d60698b7debe96ed42db1b6e22089ef96875c75e63a205550dd6c3c029"
)
BUNDLE_RUN = "train_full_se-path-sim-v1_20261013T181643.681Z"
MASTERY_THRESHOLD = 0.80


class SeSimV1LoadError(RuntimeError):
    """SE path v1 artifacts unavailable — v1 endpoints must 503 without faking or falling back to v0."""


class SeSimV1ValidationError(ValueError):
    """Malformed SE path v1 predict request."""


def c4_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_se_path_v1_bundle_dir() -> Path:
    env = os.environ.get("C4_SE_PATH_V1_BUNDLE_DIR")
    if env:
        return Path(env)
    return c4_root() / "runtime-artifacts" / "se_path_sim_v1" / BUNDLE_RUN


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_bool_mask(mask: Any, n: int) -> np.ndarray:
    arr = np.asarray(mask)
    if arr.ndim != 1 or arr.shape[0] != n:
        raise SeSimV1ValidationError(
            f"action_mask length must be {n} (got shape {arr.shape})"
        )
    if arr.dtype == bool:
        return arr.copy()
    if np.issubdtype(arr.dtype, np.number):
        if not np.isfinite(arr).all():
            raise SeSimV1ValidationError("action_mask contains non-finite values")
        uniq = set(np.unique(arr).tolist())
        if not uniq.issubset({0, 1, 0.0, 1.0}):
            raise SeSimV1ValidationError("action_mask numeric values must be 0 or 1")
        return arr.astype(bool)
    try:
        return np.asarray([bool(x) for x in arr], dtype=bool)
    except Exception as exc:  # noqa: BLE001
        raise SeSimV1ValidationError("action_mask must be boolean or 0/1") from exc


def select_demo_seed_from_selection_val(selection: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Highest mean of Y3S1+Y3S2 validation returns; ties → lowest seed."""
    by = selection.get("by_semester") or {}
    if "Y3S1" not in by or "Y3S2" not in by:
        raise SeSimV1LoadError("selection_val.json missing by_semester Y3S1/Y3S2")
    avgs: dict[int, float] = {}
    detail: dict[str, Any] = {"per_seed": {}}
    for seed in (0, 1, 2):
        vals = []
        per = {}
        for sem in ("Y3S1", "Y3S2"):
            block = (by[sem].get("seeds") or {}).get(str(seed)) or {}
            summary = (block.get("maskable_ppo") or {}).get("summary") or {}
            ret = summary.get("return") or {}
            if not isinstance(ret, dict) or "mean" not in ret:
                raise SeSimV1LoadError(
                    f"Missing summary.return.mean for seed {seed} semester {sem}"
                )
            vals.append(float(ret["mean"]))
            per[sem] = float(ret["mean"])
        avgs[seed] = float(sum(vals) / len(vals))
        detail["per_seed"][str(seed)] = {**per, "mean_across_semesters": avgs[seed]}
    chosen = sorted(avgs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    detail["selected_seed"] = chosen
    detail["rule"] = (
        "highest mean of Y3S1 and Y3S2 validation return.mean; "
        "exact ties use lowest seed; final-test unused"
    )
    return chosen, detail


@dataclass(frozen=True)
class SeSimV1PredictResult:
    action_index: int
    topic_id: str
    algorithm: str
    seed: int
    protocol: str
    model_hash: str
    catalogue_hash: str
    semester: str
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
            "semester": self.semester,
            "domain": self.domain,
            "synthetic": self.synthetic,
            "simulation_only": self.simulation_only,
            "note": (
                "SE path simulation v1 demo only (S1 / 46 topics). "
                "Not validated on real SE students. Not exam-readiness. "
                "Not the Node weakest_stored_mastery_v1 product heuristic. "
                "Does not use se-path-sim-v0."
            ),
        }


class SePathSimulationV1Policy:
    """Load-once SE MaskablePPO for /v1/se-path-simulation-v1/*."""

    def __init__(
        self,
        bundle_dir: Path | None = None,
        *,
        seed: int | None = None,
        require_expected_hash: bool = True,
    ):
        self.bundle_dir = Path(bundle_dir) if bundle_dir else default_se_path_v1_bundle_dir()
        self.export_dir = self.bundle_dir / "export_bundle"
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
        self.selection_evidence: dict[str, Any] = {}
        env_seed = os.environ.get("C4_SE_PATH_V1_DEMO_SEED")
        if seed is not None:
            self.seed = int(seed)
        elif env_seed is not None:
            self.seed = int(env_seed)
        else:
            self.seed = DEFAULT_DEMO_SEED
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
            raise SeSimV1LoadError(
                f"SE path v1 export_bundle not found at {self.export_dir}. "
                "Import the v1 Colab backup first; refusing to use se-path-sim-v0."
            )

        man_path = self.export_dir / "manifest.json"
        cat_path = self.export_dir / "topic_catalogue.json"
        schema_path = self.export_dir / "observation_schema.json"
        sel_path = self.export_dir / "selection_val.json"
        for p in (man_path, cat_path, schema_path, sel_path):
            if not p.is_file():
                raise SeSimV1LoadError(f"Missing required artifact: {p.name}")

        man = json.loads(man_path.read_text(encoding="utf-8"))
        if man.get("protocol") != PROTOCOL:
            raise SeSimV1LoadError(
                f"manifest protocol {man.get('protocol')!r} != {PROTOCOL!r}"
            )
        if man.get("domain") != DOMAIN or man.get("synthetic") is not True:
            raise SeSimV1LoadError("manifest missing domain=se_simulation / synthetic=true")
        if str(man.get("catalogue_hash") or "") != EXPECTED_CATALOGUE_HASH:
            raise SeSimV1LoadError(
                f"manifest catalogue_hash mismatch: {man.get('catalogue_hash')}"
            )

        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        topics = [str(t) for t in cat.get("topics") or []]
        if topics != list(ORDERED_TOPICS):
            raise SeSimV1LoadError(
                "Loaded catalogue topics do not match catalogues.c1_practice_full_2026_10"
            )
        if int(cat.get("n_topics") or -1) != 46:
            raise SeSimV1LoadError(f"n_topics {cat.get('n_topics')} != 46")
        if len(cat.get("y3s1_topics") or []) != 28 or len(cat.get("y3s2_topics") or []) != 18:
            raise SeSimV1LoadError("semester membership counts must be Y3S1=28, Y3S2=18")
        self.catalogue_hash_loaded = str(cat.get("sha256") or "")
        if self.catalogue_hash_loaded != EXPECTED_CATALOGUE_HASH:
            raise SeSimV1LoadError(
                f"Catalogue hash mismatch: bundle {self.catalogue_hash_loaded} "
                f"!= expected {EXPECTED_CATALOGUE_HASH}"
            )
        if self.catalogue_hash_loaded != self.catalogue_hash_expected:
            raise SeSimV1LoadError(
                f"Catalogue hash mismatch vs live code: "
                f"{self.catalogue_hash_loaded} != {self.catalogue_hash_expected}"
            )

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if int(schema.get("dim", -1)) != OBS_DIM or OBS_DIM != 96:
            raise SeSimV1LoadError(
                f"Observation schema dim {schema.get('dim')} incompatible with {OBS_DIM}"
            )
        if int(schema.get("n_actions", -1)) != 46:
            raise SeSimV1LoadError(f"n_actions {schema.get('n_actions')} != 46")
        if schema.get("protocol") not in (None, PROTOCOL):
            raise SeSimV1LoadError(f"observation schema protocol {schema.get('protocol')!r}")
        self._obs_schema = schema

        selection = json.loads(sel_path.read_text(encoding="utf-8"))
        selected_seed, evidence = select_demo_seed_from_selection_val(selection)
        self.selection_evidence = evidence
        # Default seed must match documented validation selection unless overridden.
        if (
            os.environ.get("C4_SE_PATH_V1_DEMO_SEED") is None
            and self.seed == DEFAULT_DEMO_SEED
            and selected_seed != DEFAULT_DEMO_SEED
        ):
            raise SeSimV1LoadError(
                f"Documented DEFAULT_DEMO_SEED={DEFAULT_DEMO_SEED} disagrees with "
                f"selection_val-derived seed {selected_seed}"
            )

        self.model_path = (
            self.export_dir / "models" / f"seed_{self.seed}" / "maskable_ppo_final.zip"
        )
        if not self.model_path.is_file():
            raise SeSimV1LoadError(f"Checkpoint not found: {self.model_path}")
        self.model_hash = _sha256(self.model_path)
        if self._require_expected_hash and self.seed == DEFAULT_DEMO_SEED:
            if self.model_hash != EXPECTED_DEMO_HASH:
                raise SeSimV1LoadError(
                    f"Demo checkpoint hash mismatch for seed {self.seed}: "
                    f"got {self.model_hash}, expected {EXPECTED_DEMO_HASH}"
                )

        try:
            from sb3_contrib import MaskablePPO
        except ImportError as exc:
            raise SeSimV1LoadError(
                "sb3-contrib required for SE path v1 MaskablePPO inference"
            ) from exc

        self._model = MaskablePPO.load(str(self.model_path), device="cpu")
        obs_space = getattr(self._model, "observation_space", None)
        if obs_space is not None and hasattr(obs_space, "shape"):
            if tuple(obs_space.shape) != (OBS_DIM,):
                raise SeSimV1LoadError(
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
            "y3s1_topics": len(Y3S1_TOPICS),
            "y3s2_topics": len(Y3S2_TOPICS),
            "topic_ids": list(self.topic_ids) if self.ready else [],
            "demo_selection": self.selection_evidence if self.ready else None,
            "mask_rule": (
                "Valid actions = semester_eligible AND available AND "
                "(mastery < 0.8, with reopen-all-available-in-semester if all "
                "eligible available topics are mastered). "
                "Topics outside the request semester are never permitted. "
                "All-invalid masks are rejected."
            ),
            "error": self.load_error,
            "note": "Isolated from se-path-sim-v0; missing artifacts do not fall back.",
        }

    def validate_semester(self, semester: str | None) -> str:
        if semester not in ("Y3S1", "Y3S2"):
            raise SeSimV1ValidationError(
                "semester must be 'Y3S1' or 'Y3S2' (required for v1 mask enforcement)"
            )
        return semester

    def validate_observation(self, observation: Any) -> np.ndarray:
        try:
            obs = np.asarray(observation, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise SeSimV1ValidationError(f"observation must be numeric: {exc}") from exc
        if obs.ndim != 1 or obs.shape[0] != OBS_DIM:
            raise SeSimV1ValidationError(
                f"observation shape must be ({OBS_DIM},); got {obs.shape}"
            )
        if not np.isfinite(obs).all():
            raise SeSimV1ValidationError("observation contains NaN or Inf")
        if (obs < 0.0).any() or (obs > 1.0).any():
            raise SeSimV1ValidationError("observation values must be within [0, 1]")

        mastery = mastery_from_obs(obs.astype(np.float32))
        avail = availability_from_obs(obs.astype(np.float32))
        for i, a in enumerate(avail):
            if a not in (0.0, 1.0):
                raise SeSimV1ValidationError(f"available[{i}] must be 0 or 1 (got {a})")
        for i in range(N_TOPICS):
            if avail[i] < 0.5 and mastery[i] != 0.0:
                raise SeSimV1ValidationError(
                    f"unavailable topic index {i} must have mastery 0 "
                    f"(got {mastery[i]}); missing ≠ genuine zero"
                )

        extras = obs[2 * N_TOPICS : OBS_DIM]
        mean_m, frac_m, step_frac, prior = extras
        avail_bool = avail > 0.5
        if avail_bool.any():
            expected_mean = float(mastery[avail_bool].mean())
            expected_frac = float((mastery[avail_bool] >= MASTERY_THRESHOLD).mean())
        else:
            expected_mean = 0.0
            expected_frac = 0.0
        if abs(float(mean_m) - expected_mean) > 1e-4:
            raise SeSimV1ValidationError(
                f"mean_mastery inconsistent with available mastery "
                f"(got {mean_m}, expected {expected_mean})"
            )
        if abs(float(frac_m) - expected_frac) > 1e-4:
            raise SeSimV1ValidationError(
                f"frac_mastered inconsistent with available mastery "
                f"(got {frac_m}, expected {expected_frac})"
            )
        return obs.astype(np.float32)

    def validate_mask(
        self, action_mask: Any, obs: np.ndarray, *, semester: str
    ) -> np.ndarray:
        mask = _as_bool_mask(action_mask, N_TOPICS)
        semester_ok = np.asarray(semester_eligibility_mask(semester), dtype=bool)
        avail = availability_from_obs(obs) > 0.5
        for i in range(N_TOPICS):
            if not mask[i]:
                continue
            # Semester check first so off-semester bits are reported as ineligible
            # even when observation availability for that slot is also 0.
            if not semester_ok[i]:
                raise SeSimV1ValidationError(
                    f"action_mask[{i}] is True but topic is not eligible for {semester}"
                )
            if not avail[i]:
                raise SeSimV1ValidationError(
                    f"action_mask[{i}] is True but topic is unavailable"
                )
        if not mask.any():
            raise SeSimV1ValidationError(
                "action_mask has no valid actions (all-invalid). "
                "Refusing to select an action."
            )
        return mask

    def validate_catalogue_hash(self, catalogue_hash_client: str | None) -> None:
        if catalogue_hash_client is None:
            return
        if catalogue_hash_client != self.catalogue_hash_loaded:
            raise SeSimV1ValidationError(
                f"catalogue_hash mismatch: request {catalogue_hash_client} "
                f"!= loaded {self.catalogue_hash_loaded}"
            )

    def validate_protocol(self, protocol: str | None) -> None:
        if protocol is None:
            return
        if protocol != PROTOCOL:
            raise SeSimV1ValidationError(
                f"protocol must be '{PROTOCOL}' (got '{protocol}')"
            )

    def predict(
        self,
        *,
        observation: Any,
        action_mask: Any,
        semester: str,
        protocol: str | None = None,
        catalogue_hash_client: str | None = None,
        deterministic: bool = True,
    ) -> SeSimV1PredictResult:
        if not self.ready or self._model is None:
            raise SeSimV1LoadError(
                self.load_error
                or "SE path v1 model not loaded; refusing fake predictions / v0 fallback"
            )
        self.validate_protocol(protocol)
        self.validate_catalogue_hash(catalogue_hash_client)
        sem = self.validate_semester(semester)
        obs = self.validate_observation(observation)
        mask = self.validate_mask(action_mask, obs, semester=sem)

        action, _state = self._model.predict(
            obs,
            deterministic=deterministic,
            action_masks=mask,
        )
        action_index = int(action)
        if action_index < 0 or action_index >= N_TOPICS:
            raise SeSimV1LoadError(f"Model returned out-of-range action {action_index}")
        if not bool(mask[action_index]):
            raise SeSimV1LoadError(
                f"Model selected masked-invalid action {action_index}; refusing"
            )
        if availability_from_obs(obs)[action_index] < 0.5:
            raise SeSimV1LoadError(
                f"Model selected unavailable topic index {action_index}; refusing"
            )
        if not semester_eligibility_mask(sem)[action_index]:
            raise SeSimV1LoadError(
                f"Model selected off-semester topic index {action_index}; refusing"
            )

        return SeSimV1PredictResult(
            action_index=action_index,
            topic_id=self.topic_ids[action_index],
            algorithm=self.algorithm,
            seed=self.seed,
            protocol=self.protocol,
            model_hash=self.model_hash or "",
            catalogue_hash=self.catalogue_hash_loaded or "",
            semester=sem,
        )
