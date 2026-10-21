"""C4 AI inference service: ASSISTments research + SE simulation demos.

Run from ai-services/c4:
  uvicorn app.main:app --host 127.0.0.1 --port 8004

Node owns auth. This process must not connect to Atlas.
Each inference family loads independently; one 503 must not disable the others.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.inference.loader import (
    MaskablePpoResearchPolicy,
    PolicyLoadError,
    PredictionValidationError,
)
from services.inference.se_sim_loader import (
    SeSimLoadError,
    SeSimValidationError,
    SeSimulationPolicy,
)
from services.inference.se_sim_v1_loader import (
    SePathSimulationV1Policy,
    SeSimV1LoadError,
    SeSimV1ValidationError,
)
from services.inference.se_supervised_loader import (
    SeSupervisedLoadError,
    SeSupervisedPolicy,
    SeSupervisedValidationError,
)
from services.inference.se_path_multi_v1_loader import (
    MultiNotActive,
    MultiValidationError,
    predict as multi_predict,
    readiness as multi_readiness,
)
from services.inference.se_path_multi_v2_loader import (
    MultiV2NotActive,
    MultiValidationError as MultiV2ValidationError,
    predict as multi_v2_predict,
    readiness as multi_v2_readiness,
)
from services.inference.se_supervised_v1_loader import (
    SeSupervisedV1LoadError,
    SeSupervisedV1Policy,
    SeSupervisedV1ValidationError,
)

app = FastAPI(
    title="C4 Adaptive Learning — research + SE simulation inference",
    description=(
        "ASSISTments MaskablePPO (/v1/research/*), SE path simulation v0 "
        "(/v1/se-simulation/*), SE supervised v0 (/v1/se-supervised-simulation/*), "
        "SE path simulation v1 (/v1/se-path-simulation-v1/*), and SE supervised v1 "
        "(/v1/se-supervised-simulation-v1/*). Synthetic SE endpoints are not "
        "real-SE / real-exam validation. v1 does not replace v0."
    ),
    version="0.4.0-research+se-sim-v0+v1+se-supervised-v0+v1",
)

# Load independently: failure of one must not block the others.
policy = MaskablePpoResearchPolicy()
se_policy = SeSimulationPolicy()
se_supervised = SeSupervisedPolicy()
se_path_v1 = SePathSimulationV1Policy()
se_supervised_v1 = SeSupervisedV1Policy()


class PredictRequest(BaseModel):
    observation: List[float] = Field(
        ...,
        description=(
            "Length n_skills+4: mastery_1..K, mean_mastery, frac_mastered, "
            "elapsed_env_step_frac, prior_strength. Values in [0,1]."
        ),
    )
    action_mask: List[bool] = Field(
        ...,
        description="Length n_skills; True = valid action. At least one True required.",
    )
    skill_ids: Optional[List[str]] = Field(
        None,
        description="If provided, must equal the exact ordered catalogue used at train time.",
    )
    protocol: Optional[str] = Field(
        None,
        description="Must be c4-env-eval-v1.1 when provided.",
    )
    deterministic: bool = True
    include_uncalibrated_probability: bool = False


class SeSimPredictRequest(BaseModel):
    observation: List[float] = Field(
        ...,
        description="Exactly 28 floats [0,1] per se-path-sim-v0 observation schema.",
    )
    action_mask: List[bool] = Field(
        ...,
        description="Exactly 12 booleans. Unavailable topics must be False. ≥1 True.",
    )
    protocol: Optional[str] = Field("se-path-sim-v0", description="Must be se-path-sim-v0.")
    catalogue_hash: Optional[str] = Field(
        None,
        description="If set, must match the loaded topic catalogue SHA-256.",
    )
    deterministic: bool = True


class SeSupervisedFeaturesRequest(BaseModel):
    features: Union[Dict[str, float], List[float]] = Field(
        ...,
        description=(
            "Feature dict keyed by saved schema names, or ordered list matching "
            "the saved feature schema exactly. Missing keys are rejected (no imputation)."
        ),
    )
    protocol: Optional[str] = Field(
        "se-supervised-sim-v0",
        description="Must be se-supervised-sim-v0 when provided.",
    )


class SePathV1PredictRequest(BaseModel):
    observation: List[float] = Field(
        ...,
        description="Exactly 96 floats [0,1] per se-path-sim-v1 observation schema.",
    )
    action_mask: List[bool] = Field(
        ...,
        description=(
            "Exactly 46 booleans. Must be False for unavailable and off-semester "
            "topics. At least one True required."
        ),
    )
    semester: str = Field(
        ...,
        description="Y3S1 or Y3S2 — required for semester eligibility enforcement.",
    )
    protocol: Optional[str] = Field(
        "se-path-sim-v1", description="Must be se-path-sim-v1 when provided."
    )
    catalogue_hash: Optional[str] = Field(
        None,
        description="If set, must match the loaded 46-topic catalogue SHA-256.",
    )
    deterministic: bool = True


class SeSupervisedV1FeaturesRequest(BaseModel):
    features: Union[Dict[str, float], List[float]] = Field(
        ...,
        description=(
            "Feature dict keyed by saved v1 schema names (response 54 / exam 98), "
            "or ordered list matching the schema exactly. No imputation."
        ),
    )
    protocol: Optional[str] = Field(
        "se-supervised-sim-v1",
        description="Must be se-supervised-sim-v1 when provided.",
    )


def _check_supervised_protocol(protocol: Optional[str]) -> None:
    if protocol is not None and protocol != "se-supervised-sim-v0":
        raise SeSupervisedValidationError(
            f"protocol must be se-supervised-sim-v0 (got {protocol!r})"
        )


def _check_supervised_v1_protocol(protocol: Optional[str]) -> None:
    if protocol is not None and protocol != "se-supervised-sim-v1":
        raise SeSupervisedV1ValidationError(
            f"protocol must be se-supervised-sim-v1 (got {protocol!r})"
        )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "c4-ai",
        "assistments_research_ready": policy.ready,
        "se_simulation_ready": se_policy.ready,
        "se_supervised_simulation_ready": se_supervised.ready,
        "se_path_simulation_v1_ready": se_path_v1.ready,
        "se_supervised_simulation_v1_ready": se_supervised_v1.ready,
    }


@app.get("/ready")
def ready() -> dict[str, Any]:
    """ASSISTments research readiness (unchanged contract)."""
    info = policy.readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.get("/v1/research/catalogue")
def catalogue() -> dict[str, Any]:
    if not policy.ready:
        raise HTTPException(status_code=503, detail=policy.readiness())
    return {
        "protocol": policy.protocol,
        "skill_ids": policy.skill_ids,
        "obs_dim": policy.obs_dim,
        "n_actions": policy.n_actions,
        "observation_layout": [
            *[f"mastery::{s}" for s in policy.skill_ids],
            "mean_mastery",
            "frac_mastered",
            "elapsed_env_step_frac",
            "prior_strength",
        ],
        "domain": "assistments_research",
        "note": "Do not map these IDs to C1 SE topics.",
    }


@app.post("/v1/research/predict")
def predict(req: PredictRequest) -> dict[str, Any]:
    try:
        result = policy.predict(
            observation=req.observation,
            action_mask=req.action_mask,
            skill_ids=req.skill_ids,
            protocol=req.protocol,
            deterministic=req.deterministic,
            return_probability=req.include_uncalibrated_probability,
        )
    except PredictionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PolicyLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result.as_dict()


@app.get("/v1/se-simulation/ready")
def se_ready() -> dict[str, Any]:
    info = se_policy.readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.get("/v1/se-simulation/catalogue")
def se_catalogue() -> dict[str, Any]:
    if not se_policy.ready:
        raise HTTPException(status_code=503, detail=se_policy.readiness())
    return {
        "protocol": se_policy.protocol,
        "domain": "se_simulation",
        "synthetic": True,
        "simulation_only": True,
        "topic_ids": se_policy.topic_ids,
        "catalogue_hash": se_policy.catalogue_hash_loaded,
        "obs_dim": se_policy.obs_dim,
        "n_actions": se_policy.n_actions,
        "observation_schema": se_policy._obs_schema,
        "mask_rule": se_policy.readiness()["mask_rule"],
        "note": "Practice-only initial catalogue. Not exam readiness.",
    }


@app.post("/v1/se-simulation/predict")
def se_predict(req: SeSimPredictRequest) -> dict[str, Any]:
    try:
        result = se_policy.predict(
            observation=req.observation,
            action_mask=req.action_mask,
            protocol=req.protocol,
            catalogue_hash_client=req.catalogue_hash,
            deterministic=req.deterministic,
        )
    except SeSimValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSimLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result.as_dict()


@app.get("/v1/se-supervised-simulation/ready")
def se_supervised_ready() -> dict[str, Any]:
    info = se_supervised.readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.post("/v1/se-supervised-simulation/response")
def se_supervised_response(req: SeSupervisedFeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_protocol(req.protocol)
        return se_supervised.predict_response(req.features)
    except SeSupervisedValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/se-supervised-simulation/exam-score")
def se_supervised_exam_score(req: SeSupervisedFeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_protocol(req.protocol)
        return se_supervised.predict_exam_score(req.features)
    except SeSupervisedValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/se-supervised-simulation/pass")
def se_supervised_pass(req: SeSupervisedFeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_protocol(req.protocol)
        return se_supervised.predict_pass(req.features)
    except SeSupervisedValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# --- SE path simulation v1 (isolated; does not replace /v1/se-simulation/*) ---


@app.get("/v1/se-path-simulation-v1/ready")
def se_path_v1_ready() -> dict[str, Any]:
    info = se_path_v1.readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.get("/v1/se-path-simulation-v1/catalogue")
def se_path_v1_catalogue() -> dict[str, Any]:
    if not se_path_v1.ready:
        raise HTTPException(status_code=503, detail=se_path_v1.readiness())
    return {
        "protocol": se_path_v1.protocol,
        "domain": "se_simulation",
        "synthetic": True,
        "simulation_only": True,
        "topic_ids": se_path_v1.topic_ids,
        "catalogue_hash": se_path_v1.catalogue_hash_loaded,
        "obs_dim": se_path_v1.obs_dim,
        "n_actions": se_path_v1.n_actions,
        "y3s1_count": 28,
        "y3s2_count": 18,
        "observation_schema": se_path_v1._obs_schema,
        "demo_seed": se_path_v1.seed,
        "demo_model_hash": se_path_v1.model_hash,
        "demo_selection": se_path_v1.selection_evidence,
        "mask_rule": se_path_v1.readiness()["mask_rule"],
        "note": (
            "S1 practice catalogue (46 topics). Simulation-only. "
            "Not exam readiness. Not wired to Node student path."
        ),
    }


@app.post("/v1/se-path-simulation-v1/predict")
def se_path_v1_predict(req: SePathV1PredictRequest) -> dict[str, Any]:
    try:
        result = se_path_v1.predict(
            observation=req.observation,
            action_mask=req.action_mask,
            semester=req.semester,
            protocol=req.protocol,
            catalogue_hash_client=req.catalogue_hash,
            deterministic=req.deterministic,
        )
    except SeSimV1ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSimV1LoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result.as_dict()


# --- SE supervised simulation v1 (isolated; does not replace v0) ---


@app.get("/v1/se-supervised-simulation-v1/ready")
def se_supervised_v1_ready() -> dict[str, Any]:
    info = se_supervised_v1.readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.post("/v1/se-supervised-simulation-v1/response")
def se_supervised_v1_response(req: SeSupervisedV1FeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_v1_protocol(req.protocol)
        return se_supervised_v1.predict_response(req.features)
    except SeSupervisedV1ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedV1LoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/se-supervised-simulation-v1/exam-score")
def se_supervised_v1_exam_score(req: SeSupervisedV1FeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_v1_protocol(req.protocol)
        return se_supervised_v1.predict_exam_score(req.features)
    except SeSupervisedV1ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedV1LoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/se-supervised-simulation-v1/pass")
def se_supervised_v1_pass(req: SeSupervisedV1FeaturesRequest) -> dict[str, Any]:
    try:
        _check_supervised_v1_protocol(req.protocol)
        return se_supervised_v1.predict_pass(req.features)
    except SeSupervisedV1ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SeSupervisedV1LoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class MultiPredictRequest(BaseModel):
    observation: List[float]
    action_mask: List[bool]
    protocol: str = "se-path-multi-v1"
    catalogue_hash: Optional[str] = None


@app.get("/v1/se-path-multi-v1/ready")
def se_path_multi_ready() -> dict[str, Any]:
    info = multi_readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.post("/v1/se-path-multi-v1/predict")
def se_path_multi_predict(req: MultiPredictRequest) -> dict[str, Any]:
    if req.protocol != "se-path-multi-v1":
        raise HTTPException(status_code=400, detail="protocol must be se-path-multi-v1")
    try:
        return multi_predict(req.observation, req.action_mask, req.catalogue_hash)
    except MultiValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MultiNotActive as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/se-path-multi-v2/ready")
def se_path_multi_v2_ready() -> dict[str, Any]:
    info = multi_v2_readiness()
    if not info["ready"]:
        raise HTTPException(status_code=503, detail=info)
    return info


@app.post("/v1/se-path-multi-v2/predict")
def se_path_multi_v2_predict(req: MultiPredictRequest) -> dict[str, Any]:
    if req.protocol != "se-path-multi-v2":
        raise HTTPException(status_code=400, detail="protocol must be se-path-multi-v2")
    try:
        return multi_v2_predict(req.observation, req.action_mask, req.catalogue_hash)
    except MultiV2ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MultiV2NotActive as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
