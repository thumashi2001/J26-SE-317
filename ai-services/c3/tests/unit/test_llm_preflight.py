# ruff: noqa: E501
"""Model preflight: Gemini/OpenAI model checks (HTTP stubbed), live-probe regression, run_experiments --preflight."""

from __future__ import annotations

import json
import sys

import httpx
import pytest

from services.llm.base import LLMRequest
from services.llm.cache import request_cache_key
from services.llm.gemini_provider import GeminiProvider
from services.llm.preflight import (
    ModelRequirement,
    all_ok,
    run_preflight,
    write_preflight,
)

FAKE_GEMINI = "test-gemini-key-AAAA1111"
FAKE_OPENAI = "test-openai-key-BBBB2222"


# -- preflight ---------------------------------------------------------------------------------------------
def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def gemini_models(*entries):
    return {"models": [{"name": f"models/{n}", "supportedGenerationMethods": m} for n, m in entries]}


def test_preflight_gemini_llm_ok_and_sends_key_in_header_only():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=gemini_models(("gemini-2.5-pro", ["generateContent"])))

    [chk] = run_preflight(
        [ModelRequirement("generator", "gemini", "gemini-2.5-pro")], gemini_api_key=FAKE_GEMINI,
        http_client=client_for(handler),
    )  # fmt: skip
    assert chk.ok and chk.detail == "ok" and chk.role == "generator" and chk.checked_at
    assert seen[0].headers["x-goog-api-key"] == FAKE_GEMINI and FAKE_GEMINI not in str(seen[0].url)


def test_preflight_gemini_model_not_found():
    client = client_for(lambda r: httpx.Response(200, json=gemini_models(("gemini-2.5-flash", ["generateContent"]))))
    [chk] = run_preflight(
        [ModelRequirement("generator", "gemini", "gemini-9-ultra")], gemini_api_key=FAKE_GEMINI, http_client=client
    )
    assert not chk.ok and "models/gemini-9-ultra not found in ListModels" in chk.detail


def test_preflight_gemini_wrong_method_for_llm_and_for_embedding():
    models = gemini_models(("gemini-embedding-001", ["countTokens"]), ("text-only", ["embedContent"]))
    client = client_for(lambda r: httpx.Response(200, json=models))
    reqs = [
        ModelRequirement("embedding", "gemini", "gemini-embedding-001", "embedding"),
        ModelRequirement("generator", "gemini", "text-only"),
    ]
    emb, llm = run_preflight(reqs, gemini_api_key=FAKE_GEMINI, http_client=client)
    assert not emb.ok and "none of ['embedContent', 'batchEmbedContents']" in emb.detail
    assert not llm.ok and "does not support generateContent" in llm.detail


def test_preflight_gemini_embedding_ok_with_either_method():
    models = gemini_models(("gemini-embedding-001", ["embedContent"]), ("emb-batch", ["batchEmbedContents"]))
    client = client_for(lambda r: httpx.Response(200, json=models))
    reqs = [ModelRequirement("e1", "gemini", "gemini-embedding-001", "embedding"),
            ModelRequirement("e2", "gemini", "emb-batch", "embedding")]  # fmt: skip
    checks = run_preflight(reqs, gemini_api_key=FAKE_GEMINI, http_client=client)
    assert all_ok(checks) and "embedContent" in checks[0].detail and "batchEmbedContents" in checks[1].detail


@pytest.mark.parametrize("status,word", [(403, "authentication"), (401, "authentication"), (400, "invalid API key")])
def test_preflight_gemini_auth_errors_never_leak_the_key(status, word):
    client = client_for(lambda r: httpx.Response(status, json={"error": {"message": "nope"}}))
    reqs = [ModelRequirement("generator", "gemini", "gemini-2.5-pro"),
            ModelRequirement("embedding", "gemini", "gemini-embedding-001", "embedding")]  # fmt: skip
    for chk in run_preflight(reqs, gemini_api_key=FAKE_GEMINI, http_client=client):
        assert not chk.ok and f"HTTP {status}" in chk.detail and word in chk.detail
        assert FAKE_GEMINI not in json.dumps(chk.__dict__)


def test_preflight_no_key_makes_no_http_call_and_names_the_variable():
    def handler(request):
        raise AssertionError("no HTTP call may be made without a key")

    reqs = [ModelRequirement("generator", "gemini", "gemini-2.5-pro"), ModelRequirement("verifier", "openai", "gpt-x")]
    g, o = run_preflight(reqs, gemini_api_key="", openai_api_key="", http_client=client_for(handler))
    assert not g.ok and "GEMINI_API_KEY is not set" in g.detail
    assert not o.ok and "OPENAI_API_KEY is not set" in o.detail


def test_preflight_openai_ok_not_found_and_auth_error():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        name = request.url.path.rsplit("/", 1)[-1]
        if name == "gpt-4o-mini":
            return httpx.Response(200, json={"id": name, "object": "model"})
        if name == "forbidden":
            return httpx.Response(401, json={"error": {"message": "bad key"}})
        return httpx.Response(404, json={"error": {"message": "does not exist"}})

    reqs = [ModelRequirement("verifier", "openai", m) for m in ("gpt-4o-mini", "gpt-nope", "forbidden")]
    ok, missing, auth = run_preflight(reqs, openai_api_key=FAKE_OPENAI, http_client=client_for(handler))
    assert ok.ok and seen["auth"] == f"Bearer {FAKE_OPENAI}"
    assert not missing.ok and "gpt-nope" in missing.detail and "404" in missing.detail
    assert not auth.ok and "HTTP 401" in auth.detail and FAKE_OPENAI not in auth.detail
    assert seen["url"].endswith("/models/forbidden") or "/models/" in seen["url"]


def test_preflight_openai_connection_error_is_a_failure_not_a_crash():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    [chk] = run_preflight(
        [ModelRequirement("verifier", "openai", "gpt-4o-mini")], openai_api_key=FAKE_OPENAI,
        http_client=client_for(handler),
    )  # fmt: skip
    assert not chk.ok and "ConnectError" in chk.detail


def test_preflight_unknown_provider_fails():
    [chk] = run_preflight([ModelRequirement("x", "anthropic", "m")])
    assert not chk.ok and "unsupported provider" in chk.detail


def test_preflight_json_has_required_fields_and_no_secrets(tmp_path):
    client = client_for(lambda r: httpx.Response(403, json={}))
    checks = run_preflight(
        [ModelRequirement("generator", "gemini", "gemini-2.5-pro")], gemini_api_key=FAKE_GEMINI, http_client=client
    )
    path = tmp_path / "preflight.json"
    write_preflight(path, checks)
    text = path.read_text(encoding="utf-8")
    body = json.loads(text)
    assert body["all_ok"] is False
    assert set(body["checks"][0]) >= {"role", "provider", "model", "ok", "detail", "checked_at"}
    assert FAKE_GEMINI not in text and "x-goog-api-key" not in text.lower() and "authorization" not in text.lower()


def test_gemini_verify_model_keeps_working_with_patched_get_json(monkeypatch):
    monkeypatch.setattr(
        "services.llm.gemini_provider.get_json",
        lambda url, headers, timeout=15.0, client=None: gemini_models(("gemini-2.5-pro", ["generateContent"])),
    )
    assert GeminiProvider(api_key=FAKE_GEMINI).verify_model("gemini-2.5-pro") == (True, "ok")


# -- run_experiments --preflight ---------------------------------------------------------------------------------------
@pytest.fixture
def exp(monkeypatch):
    import importlib

    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)  # never read the real .env in tests
    return importlib.import_module("experiments.run_experiments")


def test_required_models_cover_llm_and_embedding_without_duplicates(exp, monkeypatch):
    monkeypatch.setenv("C3_GEMINI_MODEL", "gemini-test-llm")
    monkeypatch.setenv("C3_OPENAI_MODEL", "gpt-test-llm")
    monkeypatch.setenv("C3_EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setenv("C3_GEMINI_EMBEDDING_MODEL", "gemini-test-emb")
    reqs = exp.required_models(["baseline", "E", "A", "B", "C", "F"], ["gemini", "openai"], "gemini")
    got = {(r.provider, r.model, r.kind) for r in reqs}
    assert got == {
        ("gemini", "gemini-test-llm", "llm"), ("openai", "gpt-test-llm", "llm"),
        ("gemini", "gemini-test-emb", "embedding"),
    }  # fmt: skip
    assert len(reqs) == 3
    assert exp.required_models(["baseline", "E"], ["gemini"]) == []


def test_run_experiments_preflight_flag_exits_2_on_failure_before_loading_the_release(exp, monkeypatch, tmp_path):
    monkeypatch.setattr(exp.fw, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path, **kw: (False, "  [FAIL] llm:gemini - HTTP 403"))
    monkeypatch.setattr(exp, "load_release", lambda *a, **k: pytest.fail("release must not load"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--preflight", "--conditions", "A", "--providers", "gemini"])
    assert exp.main() == 2


def test_run_experiments_aborts_before_any_condition_when_preflight_fails(exp, monkeypatch, tmp_path):
    monkeypatch.setattr(exp.fw, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path, **kw: (False, "  [FAIL] llm:openai - 404"))
    monkeypatch.setattr(exp, "load_release", lambda *a, **k: pytest.fail("release must not load"))
    monkeypatch.setattr(exp.cond, "run_llm_condition", lambda *a, **k: pytest.fail("no LLM call allowed"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--conditions", "A", "--providers", "openai"])
    assert exp.main() == 2


def test_run_experiments_preflight_flag_ok_returns_0(exp, monkeypatch, tmp_path):
    monkeypatch.setattr(exp.fw, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path, **kw: (True, "  [ok] llm:gemini"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--preflight", "--conditions", "A", "--providers", "gemini"])
    assert exp.main() == 0


def test_llm_request_cache_key_distinguishes_model_so_roles_never_share_answers():

    req = LLMRequest(prompt="same")
    assert request_cache_key("openai", "gpt-a", req) != request_cache_key("openai", "gpt-b", req)
    assert request_cache_key("openai", "m", req) != request_cache_key("gemini", "m", req)


class TestLiveProbe:
    """A model that is listed but retired/quota-less must fail preflight when probing (real incident: 2.5 models)."""

    def _listed_ok(self, monkeypatch):
        from services.llm import preflight as pf

        monkeypatch.setattr(
            pf, "_check_gemini", lambda req, key, client: pf._result(req, True, "ok")
        )
        return pf

    def test_listed_but_not_callable_fails(self, monkeypatch):
        from services.llm import preflight as pf
        from services.llm.base import LLMResponse

        self._listed_ok(monkeypatch)

        class Dead:
            def __init__(self, **kw):
                pass

            def generate(self, request):
                return LLMResponse(raw_content="", model_identifier="m", provider_name="gemini", is_success=False,
                                   error_message="HTTPStatusError: 404 no longer available to new users")

        monkeypatch.setattr(pf, "GeminiProvider", Dead)
        req = pf.ModelRequirement("generator", "gemini", "gemini-x")
        (check,) = pf.run_preflight([req], gemini_api_key="k", probe=True)
        assert check.ok is False
        assert "NOT callable" in check.detail and "no longer available" in check.detail

    def test_callable_model_passes_and_reports_served_version(self, monkeypatch):
        from services.llm import preflight as pf
        from services.llm.base import LLMResponse

        self._listed_ok(monkeypatch)

        class Live:
            def __init__(self, **kw):
                pass

            def generate(self, request):
                return LLMResponse(raw_content="{}", parsed_json={"ok": True}, model_identifier="gemini-served-2",
                                   provider_name="gemini", is_success=True, is_real_execution=True)

        monkeypatch.setattr(pf, "GeminiProvider", Live)
        req = pf.ModelRequirement("generator", "gemini", "gemini-alias")
        (check,) = pf.run_preflight([req], gemini_api_key="k", probe=True)
        assert check.ok is True
        assert "served as gemini-served-2" in check.detail

    def test_probe_off_makes_no_generation_call(self, monkeypatch):
        from services.llm import preflight as pf

        self._listed_ok(monkeypatch)
        monkeypatch.setattr(pf, "GeminiProvider", lambda **kw: (_ for _ in ()).throw(AssertionError("probe ran")))
        (check,) = pf.run_preflight([pf.ModelRequirement("g", "gemini", "m")], gemini_api_key="k", probe=False)
        assert check.ok is True
