# ruff: noqa: E501
"""Rate-limit / resume safety of the LLM layer and the dataset generator (stubbed HTTP + fake providers only).

Covers: retries produce one cache record, --resume reuses the cache with zero duplicate calls and byte-identical
outputs, torn cache lines, the C3_LLM_RPM limiter (spacing, sharing across threads, per-provider overrides) and
HTTP 429 Retry-After handling.
"""

from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import httpx
import pytest
from test_dataset_generator import SPEC, FakeProvider, make_questions

import services.llm.gemini_provider as gemini_mod
import services.llm.http_utils as hu
from datasets.generator.llm_tasks import LLMTasks
from datasets.generator.pipeline import Pipeline
from datasets.generator.source import SourceQuestion
from datasets.generator.writer import write_release
from services.llm.base import LLMRequest, LLMResponse
from services.llm.cache import CachedLLMProvider, request_cache_key
from services.llm.gemini_provider import GeminiProvider

FAKE_KEY = "test-gemini-key-CCCC3333"


@pytest.fixture(autouse=True)
def isolated_limiters(monkeypatch):
    monkeypatch.setattr(hu, "_limiters", {})
    for name in ("C3_LLM_RPM", "C3_LLM_RPM_GEMINI", "C3_LLM_RPM_OPENAI", "C3_LLM_MAX_RETRIES"):
        monkeypatch.delenv(name, raising=False)


def sleeps_recorder(monkeypatch, advance=True):
    """Replace the `time` module seen by http_utils: sleep() is recorded (never slept) and advances a fake clock."""
    state = SimpleNamespace(now=1000.0, sleeps=[])

    def sleep(seconds):
        state.sleeps.append(seconds)
        if advance:
            state.now += seconds

    monkeypatch.setattr(hu, "time", SimpleNamespace(monotonic=lambda: state.now, sleep=sleep))
    return state


def mock_post(handler):
    """post_json_with_retry bound to a MockTransport client (so GeminiProvider.generate runs its real code path)."""
    client = httpx.Client(transport=httpx.MockTransport(handler))

    def post(url, **kw):
        return hu.post_json_with_retry(url, client=client, **kw)

    return post


def gemini_ok(text):
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2, "totalTokenCount": 5},
        "modelVersion": "gemini-test",
    }


STRUCTURE_REPLY = json.dumps(
    {
        "answerable_as_written_text": True, "exclusion_reason": "", "stem": "", "marks_stated": False,
        "answer_type": "explanation", "parts": [{"part_label": "", "text": "Explain foo.", "marks": 5}],
    }
)  # fmt: skip


# -- (a) a retried request is cached and consumed exactly once ----------------------------------------------------------
def test_retry_inside_post_json_yields_one_cache_record_and_one_output_record(monkeypatch, tmp_path):
    state = sleeps_recorder(monkeypatch)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": "overloaded"})
        return httpx.Response(200, json=gemini_ok(STRUCTURE_REPLY))

    monkeypatch.setattr(gemini_mod, "post_json_with_retry", mock_post(handler))
    cached = CachedLLMProvider(GeminiProvider(api_key=FAKE_KEY, model="gemini-test"), tmp_path / "gen.jsonl")
    tasks = LLMTasks(cached, cached, SPEC, sleep=lambda s: None)
    q = SourceQuestion("QA", "SE3010", "synthetic", "", "Explain foo.", 5.0)

    result = tasks.structure_question(q)  # the "output record"
    assert [p.text for p in result.parts] == ["Explain foo."] and len(result.parts) == 1
    assert len(calls) == 2 and state.sleeps == [1.0]  # one 503 -> one backoff -> success
    lines = [json.loads(x) for x in (tmp_path / "gen.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1 and lines[0]["response"]["retries"] == 1  # one record, retry count preserved
    assert FAKE_KEY not in (tmp_path / "gen.jsonl").read_text(encoding="utf-8")

    again = tasks.structure_question(q)  # identical request: served from cache, no new HTTP call, no new record
    assert len(calls) == 2 and again.parts[0].text == "Explain foo."
    assert len((tmp_path / "gen.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_failed_attempts_are_never_cached(monkeypatch, tmp_path):
    sleeps_recorder(monkeypatch)
    monkeypatch.setenv("C3_LLM_MAX_RETRIES", "1")
    monkeypatch.setattr(gemini_mod, "post_json_with_retry", mock_post(lambda r: httpx.Response(503, json={})))
    cached = CachedLLMProvider(GeminiProvider(api_key=FAKE_KEY, model="gemini-test"), tmp_path / "c.jsonl")
    res = cached.generate(LLMRequest(prompt="x"))
    assert not res.is_success
    assert not (tmp_path / "c.jsonl").exists() or (tmp_path / "c.jsonl").read_text(encoding="utf-8") == ""


# -- (b) resume after an interruption ----------------------------------------------------------------------------------------
class CountingReal(FakeProvider):
    """Deterministic fake flagged as real (so it is cached). Counts successful calls by request key and can fail."""

    def __init__(self, shared: dict, role: str):
        super().__init__()
        self.shared, self.role = shared, role

    def generate(self, request):
        if self.shared.get("interrupt_after") is not None and len(self.shared["ok_keys"]) >= self.shared["interrupt_after"]:
            if self.shared["mode"] == "keyboard":
                raise KeyboardInterrupt
            raise RuntimeError("simulated provider outage")
        res = super().generate(request)
        res.is_real_execution = True
        self.shared["ok_keys"].append((self.role, request_cache_key("fake", "fake", request)))
        return res


def run_pipeline(out, shared, questions, resume_cache=True):
    cache = out / "_llm_cache"
    gen = CachedLLMProvider(CountingReal(shared, "generator"), cache / "generator.jsonl")
    ver = CachedLLMProvider(CountingReal(shared, "verifier"), cache / "verifier_openai.jsonl")
    tasks = LLMTasks(gen, ver, SPEC, sleep=lambda s: None)
    pipe = Pipeline(tasks, SPEC, 4242, 2, "fake-gen", "fake-ver")
    data, failures = pipe.run(questions)
    return data, failures, (gen, ver)


def release_bytes(out):
    return {p.name: p.read_bytes() for p in sorted(out.iterdir()) if p.is_file()}


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    out = tmp_path_factory.mktemp("uninterrupted")
    shared = {"ok_keys": [], "interrupt_after": None, "mode": "keyboard"}
    qs = make_questions(12)
    data, failures, _ = run_pipeline(out, shared, qs)
    assert data is not None and not failures
    write_release(out, data, SPEC, 4242)
    return SimpleNamespace(out=out, calls=list(shared["ok_keys"]), questions=qs)


@pytest.mark.parametrize("mode", ["keyboard", "outage"])
def test_resume_reuses_cache_without_duplicate_calls_and_gives_identical_files(reference, tmp_path, mode):
    n_ref = len(reference.calls)
    assert n_ref > 40 and len(set(reference.calls)) == n_ref  # the reference run itself never repeats a request
    stop = n_ref // 2
    shared = {"ok_keys": [], "interrupt_after": stop, "mode": mode}
    if mode == "keyboard":
        with pytest.raises(KeyboardInterrupt):
            run_pipeline(tmp_path, shared, reference.questions)
    else:
        data, failures, _ = run_pipeline(tmp_path, shared, reference.questions)
        assert data is None and failures and all(f["task"] in ("unexpected", "structure_question") or f["message"]
                                                 for f in failures)  # fmt: skip
    first_phase = list(shared["ok_keys"])
    assert len(first_phase) == stop

    shared2 = {"ok_keys": [], "interrupt_after": None, "mode": mode}
    data, failures, (gen, ver) = run_pipeline(tmp_path, shared2, reference.questions)
    assert data is not None and not failures
    write_release(tmp_path, data, SPEC, 4242)

    second_phase = shared2["ok_keys"]
    assert not set(first_phase) & set(second_phase)  # nothing that completed before was asked again
    assert len(first_phase) + len(second_phase) == n_ref  # exactly the work of one uninterrupted run
    assert set(first_phase) | set(second_phase) == set(reference.calls)
    assert gen.hits + ver.hits >= len(first_phase) // 2 and gen.hits + ver.hits > 0

    a, b = release_bytes(reference.out), release_bytes(tmp_path)
    assert set(a) == set(b)
    assert {k for k in a if a[k] != b[k]} == set()  # byte-identical release files for the same seed


def test_cache_has_one_record_per_distinct_request_after_resume(reference):
    for name in ("generator.jsonl", "verifier_openai.jsonl"):
        keys = [json.loads(x)["key"] for x in (reference.out / "_llm_cache" / name).read_text("utf-8").splitlines()]
        assert len(keys) == len(set(keys)) > 0


# -- (c) torn cache line ------------------------------------------------------------------------------------------------------------
class OnePrompt(FakeProvider):
    def generate(self, request):
        res = LLMResponse(raw_content=json.dumps({"v": request.prompt}), parsed_json={"v": request.prompt},
                          model_identifier="m", provider_name="fake", is_real_execution=True)  # fmt: skip
        self.prompts.append(request.prompt)
        return res


def test_torn_last_cache_line_is_tolerated_and_does_not_corrupt_later_records(tmp_path):
    path = tmp_path / "c.jsonl"
    c1 = CachedLLMProvider(OnePrompt(), path)
    c1.generate(LLMRequest(prompt="one"))
    c1.generate(LLMRequest(prompt="two"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"key": "deadbeef", "response": {"raw_con')  # interrupted mid-write, no newline

    inner = OnePrompt()
    c2 = CachedLLMProvider(inner, path)
    assert len(c2._entries) == 2
    assert c2.generate(LLMRequest(prompt="one")).cached and inner.prompts == []  # still served from cache
    c2.generate(LLMRequest(prompt="three"))  # new record appended after the torn fragment
    assert inner.prompts == ["three"]

    inner3 = OnePrompt()
    c3 = CachedLLMProvider(inner3, path)
    assert len(c3._entries) == 3  # before the fix "three" was glued to the torn fragment and lost
    for p in ("one", "two", "three"):
        assert c3.generate(LLMRequest(prompt=p)).cached
    assert inner3.prompts == []


def test_cache_ignores_non_record_json_lines(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('[]\n"str"\n{"no_key": 1}\n{"key": "k"}\n', encoding="utf-8")
    assert CachedLLMProvider(OnePrompt(), path)._entries == {}


# -- (d) C3_LLM_RPM limiter -------------------------------------------------------------------------------------------------------------
def test_rate_limiter_spaces_request_starts_by_60_over_rpm(monkeypatch):
    state = sleeps_recorder(monkeypatch)
    limiter = hu.RateLimiter(30)  # 30 requests started per minute -> one every 2 s
    starts = []
    for _ in range(4):
        limiter.wait()
        starts.append(state.now)
    assert starts == [1000.0, 1002.0, 1004.0, 1006.0] and state.sleeps == [2.0, 2.0, 2.0]
    assert hu.RateLimiter(0).min_interval == 0 and hu.RateLimiter(-5).min_interval == 0


def test_every_retry_attempt_counts_as_a_started_request(monkeypatch):
    sleeps_recorder(monkeypatch)
    statuses = iter([503, 503, 200])
    waits = []

    class Spy(hu.RateLimiter):
        def wait(self):
            waits.append(1)

    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(next(statuses), json={"ok": True})))  # fmt: skip
    body, retries = hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, limiter=Spy(10),
                                            client=client)  # fmt: skip
    assert body == {"ok": True} and retries == 2 and len(waits) == 3


def test_one_limiter_instance_per_provider_key_shared_across_threads():
    barrier = threading.Barrier(16)
    got = []

    def grab():
        barrier.wait()
        got.append((hu.get_rate_limiter("gemini"), hu.get_rate_limiter("openai")))

    threads = [threading.Thread(target=grab) for _ in range(16)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len({id(g) for g, _ in got}) == 1 and len({id(o) for _, o in got}) == 1
    assert got[0][0] is not got[0][1] and len(hu._limiters) == 2


def test_threads_share_one_schedule_so_total_throughput_is_capped(monkeypatch):
    state = sleeps_recorder(monkeypatch, advance=False)  # frozen clock: all six callers arrive "at once"
    limiter = hu.get_rate_limiter("gemini")
    monkeypatch.setattr(limiter, "min_interval", 1.0)
    barrier = threading.Barrier(6)

    def worker():
        barrier.wait()
        limiter.wait()

    threads = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    # six simultaneous callers are spread 1 s apart regardless of which thread wins the lock
    assert sorted(state.sleeps) == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_rpm_env_semantics_and_per_provider_overrides(monkeypatch):
    monkeypatch.setenv("C3_LLM_RPM", "30")
    assert hu.get_rate_limiter("gemini").min_interval == 2.0 and hu.get_rate_limiter("openai").min_interval == 2.0
    hu._limiters.clear()
    monkeypatch.setenv("C3_LLM_RPM_GEMINI", "120")
    monkeypatch.setenv("C3_LLM_RPM_OPENAI", "")  # empty -> falls back to C3_LLM_RPM
    assert hu.get_rate_limiter("gemini").min_interval == 0.5
    assert hu.get_rate_limiter("gemini-embedding").min_interval == 0.5
    assert hu.get_rate_limiter("openai").min_interval == 2.0 and hu.get_rate_limiter("openai-embedding").min_interval == 2.0
    hu._limiters.clear()
    monkeypatch.setenv("C3_LLM_RPM_OPENAI", "0")  # an explicit 0 disables limiting for that provider only
    assert hu.rpm_for("openai") == 0.0 and hu.rpm_for("gemini") == 120.0
    monkeypatch.delenv("C3_LLM_RPM")
    monkeypatch.delenv("C3_LLM_RPM_GEMINI")
    assert hu.rpm_for("gemini") == 0 and hu.get_rate_limiter("gemini").min_interval == 0
    assert "STARTED per minute" in hu.__doc__ and "C3_LLM_RPM_GEMINI" in hu.__doc__


# -- (e) HTTP 429 / Retry-After --------------------------------------------------------------------------------------------------------------
def test_429_with_retry_after_seconds_is_honoured(monkeypatch):
    state = sleeps_recorder(monkeypatch)
    answers = iter([httpx.Response(429, headers={"Retry-After": "7"}, json={}), httpx.Response(200, json={"a": 1})])
    client = httpx.Client(transport=httpx.MockTransport(lambda r: next(answers)))
    body, retries = hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, client=client)
    assert body == {"a": 1} and retries == 1 and state.sleeps == [7.0]


def test_429_without_or_with_unparseable_retry_after_uses_exponential_backoff(monkeypatch):
    state = sleeps_recorder(monkeypatch)
    answers = iter([
        httpx.Response(429, json={}),
        httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, json={}),
        httpx.Response(200, json={"a": 1}),
    ])  # fmt: skip
    client = httpx.Client(transport=httpx.MockTransport(lambda r: next(answers)))
    hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, client=client)
    assert state.sleeps == [1.0, 2.0]


def test_persistent_429_stops_after_max_retries_and_non_retryable_status_is_not_retried(monkeypatch):
    state = sleeps_recorder(monkeypatch)
    n = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: n.append(1) or httpx.Response(429, headers={"Retry-After": "3"}, json={})))  # fmt: skip
    with pytest.raises(httpx.HTTPStatusError):
        hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, max_retries=2, client=client)
    assert len(n) == 3 and state.sleeps == [3.0, 3.0]
    m = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: m.append(1) or httpx.Response(400, json={})))
    with pytest.raises(httpx.HTTPStatusError):
        hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, client=client)
    assert len(m) == 1


def test_transport_errors_are_retried_then_raised(monkeypatch):
    state = sleeps_recorder(monkeypatch)

    def handler(request):
        raise httpx.ConnectError("down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.ConnectError):
        hu.post_json_with_retry("http://x/y", headers={}, payload={}, timeout=5, max_retries=2, client=client)
    assert state.sleeps == [1.0, 2.0]

