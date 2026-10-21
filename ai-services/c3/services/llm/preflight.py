"""
AdaptiveLearnSE Component 3 - Model preflight.

Before any real generation/experiment call, confirm that every model the run will use exists for the
configured account and supports the method we call. Nothing is substituted: if a model is not ok the
caller aborts with the exact reason. The written preflight.json holds no API keys and no request headers.

  Gemini : GeminiProvider.verify_model (ListModels, generateContent); embedding models must list
           embedContent or batchEmbedContents in supportedGenerationMethods.
  OpenAI : GET {OPENAI_BASE_URL}/models/{id} with Bearer auth (404 = not found, 401/403 = auth error).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .base import LLMRequest
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

EMBEDDING_METHODS = ("embedContent", "batchEmbedContents")
KEY_ENV = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


@dataclass(frozen=True)
class ModelRequirement:
    role: str  # e.g. "generator", "verifier", "llm:gemini", "embedding"
    provider: str  # gemini | openai
    model: str
    kind: str = "llm"  # llm | embedding


@dataclass
class ModelCheck:
    role: str
    provider: str
    model: str
    ok: bool
    detail: str
    checked_at: str
    kind: str = "llm"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _result(req: ModelRequirement, ok: bool, detail: str) -> ModelCheck:
    return ModelCheck(req.role, req.provider, req.model, ok, detail, _now(), req.kind)


def _http_reason(status: int) -> str:
    if status in (401, 403):
        return f"HTTP {status} authentication/permission error (check the API key)"
    if status == 400:
        return "HTTP 400 bad request (Gemini reports an invalid API key as 400)"
    if status == 404:
        return "HTTP 404 not found"
    if status == 429:
        return "HTTP 429 rate limited / quota exhausted"
    return f"HTTP {status}"


def _check_gemini(req: ModelRequirement, api_key: str | None, http_client: httpx.Client | None) -> ModelCheck:
    provider = GeminiProvider(model=req.model, api_key=api_key)
    if not provider.is_available():
        return _result(req, False, f"{KEY_ENV['gemini']} is not set; cannot verify the model")
    provider.http_client = http_client
    if req.kind == "llm":
        ok, detail = provider.verify_model(req.model)
        return _result(req, ok, detail)
    wanted = f"models/{req.model}"
    try:
        entries = provider.list_models()
    except httpx.HTTPStatusError as exc:
        return _result(req, False, f"ListModels failed: {_http_reason(exc.response.status_code)}")
    except Exception as exc:  # noqa: BLE001 - reported verbatim as the failure reason
        return _result(req, False, f"ListModels failed: {type(exc).__name__}: {exc}")
    for entry in entries:
        if entry.get("name") == wanted:
            methods = entry.get("supportedGenerationMethods", [])
            found = [m for m in EMBEDDING_METHODS if m in methods]
            if found:
                return _result(req, True, f"ok (supports {', '.join(found)})")
            return _result(req, False, f"{wanted} supports {methods} but none of {list(EMBEDDING_METHODS)}")
    return _result(req, False, f"{wanted} not found in ListModels")


def _check_openai(req: ModelRequirement, api_key: str | None, http_client: httpx.Client | None) -> ModelCheck:
    provider = OpenAIProvider(model=req.model, api_key=api_key)
    if not provider.is_available():
        return _result(req, False, f"{KEY_ENV['openai']} is not set; cannot verify the model")
    client = http_client or httpx.Client(timeout=20.0)
    try:
        res = client.get(
            f"{provider.base_url}/models/{req.model}",
            headers={"Authorization": f"Bearer {provider.api_key}"},
        )
    except httpx.HTTPError as exc:
        return _result(req, False, f"request failed: {type(exc).__name__}")
    finally:
        if http_client is None:
            client.close()
    if res.status_code == 200:
        note = "" if req.kind == "llm" else " (the OpenAI models endpoint does not expose supported methods)"
        return _result(req, True, "ok" + note)
    if res.status_code == 404:
        return _result(req, False, f"model '{req.model}' not found (HTTP 404)")
    return _result(req, False, _http_reason(res.status_code))


def _probe(req: ModelRequirement, check: ModelCheck, api_key: str | None) -> ModelCheck:
    """Make one tiny REAL call. A model can be listed yet not callable (e.g. retired for new users -> HTTP 404,
    or zero free-tier quota -> HTTP 429), so listing alone is not proof."""
    if not check.ok or req.kind != "llm":
        return check
    provider = (
        GeminiProvider(model=req.model, api_key=api_key)
        if req.provider == "gemini"
        else OpenAIProvider(model=req.model, api_key=api_key)
    )
    res = provider.generate(
        LLMRequest(prompt='Reply with exactly this JSON: {"ok": true}', model=req.model, temperature=0.0,
                   max_tokens=64, response_format="json", timeout_seconds=60.0)
    )
    if res.is_success and res.is_real_execution:
        served = f"; served as {res.model_identifier}" if res.model_identifier != req.model else ""
        return _result(req, True, f"{check.detail}; live call ok{served}")
    detail = (res.error_message or "live call failed")[:300]
    return _result(req, False, f"listed but NOT callable: {detail}")


def run_preflight(
    requirements: list[ModelRequirement],
    *,
    gemini_api_key: str | None = None,
    openai_api_key: str | None = None,
    http_client: httpx.Client | None = None,
    probe: bool = False,
) -> list[ModelCheck]:
    """Check every requirement (keys default to the environment). Never raises for an unreachable model.

    probe=True additionally makes one tiny real generation call per LLM model (costs a few tokens)."""
    checks = []
    for req in requirements:
        if req.provider == "gemini":
            check = _check_gemini(req, gemini_api_key, http_client)
            key = gemini_api_key
        elif req.provider == "openai":
            check = _check_openai(req, openai_api_key, http_client)
            key = openai_api_key
        else:
            checks.append(_result(req, False, f"unsupported provider '{req.provider}' (use gemini or openai)"))
            continue
        checks.append(_probe(req, check, key) if probe else check)
    return checks


def all_ok(checks: list[ModelCheck]) -> bool:
    return bool(checks) and all(c.ok for c in checks)


def write_preflight(path: Path, checks: list[ModelCheck]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"all_ok": all_ok(checks), "checked_at": _now(), "checks": [asdict(c) for c in checks]}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def format_checks(checks: list[ModelCheck]) -> str:
    return "\n".join(f"  [{'ok' if c.ok else 'FAIL'}] {c.role}: {c.provider}/{c.model} - {c.detail}" for c in checks)


def preflight_or_report(requirements: list[ModelRequirement], out_path: Path, **kwargs) -> tuple[bool, str]:
    """Run, write preflight.json, and return (all_ok, printable summary)."""
    kwargs.setdefault("probe", False)
    checks = run_preflight(requirements, **kwargs)
    write_preflight(out_path, checks)
    return all_ok(checks), format_checks(checks)
