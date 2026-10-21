"""Generator/verifier roles, .env loading, blind-grade isolation and model preflight.

Everything here is offline: HTTP is stubbed with httpx.MockTransport or patched, providers are fakes, and the
conftest autouse fixture blocks real network access. Keys used below are obviously fake test strings.
"""

from __future__ import annotations

import json
import re
import sys

import httpx
import pytest
from test_dataset_generator import SPEC, FakeProvider, make_questions

import datasets.generate_c3_dataset as gen_cli
import datasets.generator.roles as roles
from datasets.generator import prompts
from datasets.generator.llm_tasks import LLMTasks, rubric_text
from datasets.generator.pipeline import Pipeline
from datasets.generator.roles import (
    Role,
    RoleConfigError,
    load_env,
    missing_key_vars,
    resolve_roles,
    role_meta,
    same_family,
    verifier_cache_name,
)
from services.llm.base import LLMRequest
from services.llm.gemini_provider import GeminiProvider
from services.llm.openai_provider import OpenAIProvider
from services.llm.preflight import (
    ModelRequirement,
    all_ok,
    run_preflight,
    write_preflight,
)

FAKE_GEMINI = "test-gemini-key-AAAA1111"
FAKE_OPENAI = "test-openai-key-BBBB2222"
ROLE_VARS = (
    "C3_GENERATOR_MODEL", "C3_VERIFIER_PROVIDER", "C3_VERIFIER_MODEL", "GEMINI_API_KEY", "OPENAI_API_KEY",
)  # fmt: skip


@pytest.fixture
def clean_env(monkeypatch):
    for name in ROLE_VARS:
        monkeypatch.setenv(name, "placeholder")  # registers an undo so values set by load_env cannot leak
        monkeypatch.delenv(name)
    return monkeypatch


class RealFlagFake(FakeProvider):
    """FakeProvider whose responses are flagged real so CachedLLMProvider stores them (pipeline logic only)."""

    def generate(self, request):
        res = super().generate(request)
        res.is_real_execution = True
        return res


# -- .env loading -------------------------------------------------------------------------------------------
def test_load_env_reads_dotenv_and_real_environment_wins(tmp_path, clean_env):
    env_file = tmp_path / ".env"
    env_file.write_text("C3_VERIFIER_MODEL=from-dotenv\nC3_GENERATOR_MODEL=gen-from-dotenv\n", encoding="utf-8")
    clean_env.setattr(roles, "ENV_FILE", env_file)
    clean_env.setenv("C3_GENERATOR_MODEL", "gen-from-real-env")
    load_env()
    generator, verifier = resolve_roles()
    assert generator.model == "gen-from-real-env"  # a real environment variable beats .env
    assert verifier.model == "from-dotenv"  # .env fills what the environment leaves unset


def test_cli_entry_points_call_load_env(clean_env, monkeypatch):
    calls = []
    monkeypatch.setattr(gen_cli, "load_env", lambda: calls.append("generate"))
    gen_cli.main(["--dry-run", "--limit", "2"])
    import datasets.validate_dataset as val

    monkeypatch.setattr(val, "load_env", lambda: calls.append("validate"))
    val.main(["/no/such/dir"])
    assert calls == ["generate", "validate"]


# -- roles ------------------------------------------------------------------------------------------------------
def test_default_roles_generator_gemini_verifier_openai(clean_env):
    generator, verifier = resolve_roles()
    assert (generator.provider, generator.model) == ("gemini", "gemini-2.5-pro")
    assert (verifier.provider, verifier.model) == ("openai", "gpt-4o-mini")
    assert isinstance(generator.build(), GeminiProvider) and isinstance(verifier.build(), OpenAIProvider)
    assert generator.build().model == "gemini-2.5-pro" and verifier.build().model == "gpt-4o-mini"
    meta = role_meta(generator, verifier)
    assert meta["verifier_same_model_family_as_generator"] is False
    assert verifier_cache_name(verifier) == "verifier_openai.jsonl"


def test_gemini_verifier_is_same_family_and_has_its_own_cache_file(clean_env):
    clean_env.setenv("C3_VERIFIER_PROVIDER", "gemini")
    clean_env.setenv("C3_VERIFIER_MODEL", "gemini-2.5-flash")
    generator, verifier = resolve_roles()
    assert isinstance(verifier.build(), GeminiProvider) and verifier.build().model == "gemini-2.5-flash"
    assert same_family(generator, verifier) is True
    assert verifier_cache_name(verifier) == "verifier_gemini.jsonl"


def test_unknown_verifier_provider_is_rejected(clean_env):
    clean_env.setenv("C3_VERIFIER_PROVIDER", "anthropic")
    with pytest.raises(RoleConfigError, match="gemini, openai"):
        resolve_roles()


def test_missing_key_vars_reports_names_only(clean_env):
    generator, verifier = resolve_roles()
    assert missing_key_vars([generator, verifier]) == ["GEMINI_API_KEY", "OPENAI_API_KEY"]
    clean_env.setenv("GEMINI_API_KEY", FAKE_GEMINI)
    assert missing_key_vars([generator, verifier]) == ["OPENAI_API_KEY"]
    clean_env.setenv("C3_VERIFIER_PROVIDER", "gemini")
    assert missing_key_vars(list(resolve_roles())) == []


def test_cli_missing_keys_names_only_variable_names_and_exits_2(clean_env, capsys, tmp_path):
    clean_env.setenv("GEMINI_API_KEY", FAKE_GEMINI)
    assert gen_cli.main(["--limit", "1", "--out", str(tmp_path / "o")]) == 2
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err and "GEMINI_API_KEY" not in err  # only the MISSING variable is named
    assert FAKE_GEMINI not in err


def test_dry_run_prints_roles_models_and_required_env_names(clean_env, capsys):
    clean_env.setenv("GEMINI_API_KEY", FAKE_GEMINI)
    assert gen_cli.main(["--dry-run", "--limit", "5"]) == 0
    out = capsys.readouterr().out
    assert "generator" in out and "gemini / gemini-2.5-pro" in out and "GEMINI_API_KEY (set)" in out
    assert "verifier" in out and "openai / gpt-4o-mini" in out and "OPENAI_API_KEY (NOT SET)" in out
    assert "C3_VERIFIER_PROVIDER" in out and "verifier_openai.jsonl" in out
    assert FAKE_GEMINI not in out


# -- blind grader isolation ---------------------------------------------------------------------------------------
class RecordingGrader(RealFlagFake):
    pass


def test_blind_grade_prompt_contains_only_question_rubric_and_answer(clean_env):
    gen, ver = RealFlagFake(), RecordingGrader()
    tasks = LLMTasks(gen, ver, SPEC, sleep=lambda s: None)
    pipe = Pipeline(tasks, SPEC, 7, 2, "g", "v")
    data, failures = pipe.run(make_questions(10))
    assert data is not None and not failures
    assert ver.prompts and all(p.startswith("Mark the student answer") for p in ver.prompts)
    assert not any(p.startswith(("Analyse", "Draft", "You will write")) for p in ver.prompts)
    forbidden_words = [
        *SPEC["core_tiers"], *SPEC["edge_tiers"], *SPEC["styles"], *SPEC["registers"],
        "keyword_stuffed", "generic_padding", "unrelated_essay", "same_domain_wrong_topic",
        "expected_mark", "normalized", "target", "sub_kind", "register",
    ]  # fmt: skip
    pattern = re.compile("|".join(re.escape(w) for w in forbidden_words))
    answer_ids = [a["answer_id"] for a in data.answers]
    for prompt in ver.prompts:
        assert not pattern.search(prompt), pattern.search(prompt).group(0)
        assert not any(aid in prompt for aid in answer_ids)  # ids embed the tier name


def test_blind_grade_prompt_is_exactly_question_marks_rubric_answer(clean_env):
    from datasets.generator.llm_tasks import validate_draft

    ver = RecordingGrader()
    tasks = LLMTasks(RealFlagFake(), ver, SPEC, sleep=lambda s: None)
    draft = validate_draft(FakeProvider()._rubric("QUESTION_ID: Z1\nTOTAL_MARKS: 10\n"), "Z1", 10.0, SPEC)
    tasks.blind_grade("Z1-FULL-1", "Explain caching.", 10.0, draft.rubric, "My answer text.")
    expected = prompts.render(
        prompts.BLIND_GRADE, marks="10", question_text="Explain caching.", rubric=rubric_text(draft.rubric),
        answer="My answer text.",
    )  # fmt: skip
    assert ver.prompts == [expected]


# -- manifest + end-to-end CLI with fakes -----------------------------------------------------------------------------
@pytest.fixture
def cli_env(clean_env, monkeypatch):
    fakes = {"generator": RealFlagFake(), "verifier": RealFlagFake()}
    monkeypatch.setattr(Role, "build", lambda self: fakes[self.name])
    monkeypatch.setattr(gen_cli, "load_source", lambda limit=None: make_questions(12))
    monkeypatch.setattr(gen_cli, "preflight_or_report", lambda reqs, path: (True, "  [ok] stubbed preflight"))
    return fakes


def test_cli_run_records_roles_in_manifest_and_uses_separate_verifier_cache(cli_env, tmp_path, capsys):
    out = tmp_path / "rel"
    assert gen_cli.main(["--out", str(out), "--seed", "5"]) == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generator_provider"] == "gemini" and manifest["generator_model"] == "gemini-2.5-pro"
    assert manifest["verifier_provider"] == "openai" and manifest["verifier_model"] == "gpt-4o-mini"
    assert manifest["verifier_same_model_family_as_generator"] is False
    cache = out / "_llm_cache"
    assert (cache / "generator.jsonl").stat().st_size > 0 and (cache / "verifier_openai.jsonl").stat().st_size > 0
    assert not (cache / "verifier.jsonl").exists()
    assert (out / "validation_report.json").exists()
    card = (out / "DATASET_CARD.md").read_text(encoding="utf-8")
    assert "same model family as generator: False" in card
    assert SPEC["thresholds"]["ratio_metric_scope"] in card  # card states the ratio-metric scope from tier_spec
    assert "Model preflight" in capsys.readouterr().out


def test_cli_aborts_with_exit_2_when_preflight_fails_and_makes_no_provider_call(cli_env, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        gen_cli, "preflight_or_report",
        lambda reqs, path: (False, "  [FAIL] verifier: openai/gpt-x - model 'gpt-x' not found (HTTP 404)"),
    )  # fmt: skip
    assert gen_cli.main(["--out", str(tmp_path / "o")]) == 2
    captured = capsys.readouterr()
    assert "not found (HTTP 404)" in captured.out and "preflight failed" in captured.err
    assert cli_env["generator"].prompts == [] and cli_env["verifier"].prompts == []


def test_cli_preflight_flag_only_verifies_and_never_generates(cli_env, tmp_path):
    assert gen_cli.main(["--preflight", "--out", str(tmp_path / "o")]) == 0
    assert cli_env["generator"].prompts == [] and not (tmp_path / "o" / "manifest.json").exists()


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
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path: (False, "  [FAIL] llm:gemini - HTTP 403"))
    monkeypatch.setattr(exp, "load_release", lambda *a, **k: pytest.fail("release must not load"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--preflight", "--conditions", "A", "--providers", "gemini"])
    assert exp.main() == 2


def test_run_experiments_aborts_before_any_condition_when_preflight_fails(exp, monkeypatch, tmp_path):
    monkeypatch.setattr(exp.fw, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path: (False, "  [FAIL] llm:openai - 404"))
    monkeypatch.setattr(exp, "load_release", lambda *a, **k: pytest.fail("release must not load"))
    monkeypatch.setattr(exp.cond, "run_llm_condition", lambda *a, **k: pytest.fail("no LLM call allowed"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--conditions", "A", "--providers", "openai"])
    assert exp.main() == 2


def test_run_experiments_preflight_flag_ok_returns_0(exp, monkeypatch, tmp_path):
    monkeypatch.setattr(exp.fw, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(exp, "preflight_or_report", lambda reqs, path: (True, "  [ok] llm:gemini"))
    monkeypatch.setattr(sys, "argv", ["run_experiments", "--preflight", "--conditions", "A", "--providers", "gemini"])
    assert exp.main() == 0


def test_llm_request_cache_key_distinguishes_model_so_roles_never_share_answers():
    from services.llm.cache import request_cache_key

    req = LLMRequest(prompt="same")
    assert request_cache_key("openai", "gpt-a", req) != request_cache_key("openai", "gpt-b", req)
    assert request_cache_key("openai", "m", req) != request_cache_key("gemini", "m", req)
