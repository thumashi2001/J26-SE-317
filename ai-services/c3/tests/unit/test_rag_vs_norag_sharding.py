"""Deterministic sharding and aggregation for the multi-day RAG vs no-RAG run (no LLM calls, no network)."""

import json
import os
import stat

import pandas as pd
import pytest

from experiments import rag_vs_norag as rv
from experiments.model_comparison import load_answers_with_reference


def _test_frame(n=23):
    return pd.DataFrame({"answer_id": [f"A{i:03d}" for i in range(n)], "question_id": "Q"})


def _predictions(ids, failed=()):
    rows = []
    for i in ids:
        for cond in ("A_no_rag", "B_rag"):
            ok = (i, cond) not in failed
            rows.append({"answer_id": i, "question_id": "Q", "tier": "t", "condition": cond, "max_marks": 4.0, "expected_mark": 2.0,
                         "llm_status": "ok" if ok else "error", "predicted_mark": 3.0 if ok else None, "model": "m-1"})
    return pd.DataFrame(rows)


def test_parse_shard_accepts_i_of_k_and_rejects_everything_else():
    assert rv.parse_shard("2/9") == (2, 9) and rv.parse_shard("1/1") == (1, 1)
    for bad in ("0/9", "10/9", "3", "a/b", "1/2/3", "", "-1/3"):
        with pytest.raises(ValueError):
            rv.parse_shard(bad)


@pytest.mark.parametrize("k", [1, 2, 5, 9, 23, 30])
def test_shards_are_disjoint_and_cover_every_answer(k):
    frame = _test_frame()
    slices = [set(rv.select_answers(frame, shard=(i, k))["answer_id"]) for i in range(1, k + 1)]
    assert sum(len(s) for s in slices) == len(frame)  # disjoint
    assert set().union(*slices) == set(frame["answer_id"])  # complete
    assert max(len(s) for s in slices) - min(len(s) for s in slices) <= 1  # balanced


def test_shard_choice_does_not_depend_on_row_order_or_the_day_it_runs():
    frame = _test_frame()
    shuffled = frame.sample(frac=1, random_state=7).reset_index(drop=True)
    for i in range(1, 6):
        assert list(rv.select_answers(frame, shard=(i, 5))["answer_id"]) == list(rv.select_answers(shuffled, shard=(i, 5))["answer_id"])


def test_limit_is_a_fixed_seed_sample_and_cannot_be_combined_with_shard():
    frame = _test_frame()
    assert list(rv.select_answers(frame, limit=6)["answer_id"]) == list(rv.select_answers(frame, limit=6)["answer_id"])
    shuffled = frame.sample(frac=1, random_state=3).reset_index(drop=True)
    # --limit depends on the row order of its input (shards do not; see the order-independence test above)
    assert set(rv.select_answers(frame, limit=6)["answer_id"]) != set(rv.select_answers(shuffled, limit=6)["answer_id"])
    with pytest.raises(ValueError):
        rv.select_answers(frame, limit=5, shard=(1, 3))
    assert rv.main(["--out", "unused", "--limit", "5", "--shard", "1/3"]) == 2


def test_real_test_split_is_partitioned_by_the_shards():
    answers = load_answers_with_reference(rv.DATASET)
    test = answers[answers["split"] == "test"]
    covered = []
    for i in range(1, 10):
        covered += list(rv.select_answers(test, shard=(i, 9))["answer_id"])
    assert sorted(covered) == sorted(test["answer_id"]) and len(set(covered)) == len(test) == 90


def test_summary_counts_failures_and_never_scores_them_as_zero():
    summary = rv.summarise(_predictions(["a", "b"], failed={("a", "B_rag")}), "gemini", {"p": 1})
    assert summary["per_condition"]["B_rag"] == {"n_ok": 1, "n_failed": 1, "nmae": pytest.approx(0.25)}
    assert summary["per_condition"]["A_no_rag"]["n_failed"] == 0 and summary["models"] == ["m-1"] and summary["n_answers"] == 2


FP = {"provider": "gemini", "model": "m-1", "generation": rv.GENERATION, "prompt_templates_sha256": "p1", "top_k": 3, "threshold": 0.2,
      "embedding_model": "emb", "corpus_provenance": {"documents": 5}, "dataset": "d", "dataset_files_sha256": {"f": "h1"}}


def _write_shards(tmp_path, ids, k, fingerprint=FP):
    rv.check_or_create_manifest(tmp_path, fingerprint, k)
    for i in range(1, k + 1):
        part = [x for n, x in enumerate(sorted(ids)) if n % k == i - 1]
        _predictions(part).to_csv(tmp_path / f"rag_vs_norag_predictions_shard{i}of{k}.csv", index=False)
        summary = {"run_config": {"fingerprint_sha256": rv.fingerprint_id(fingerprint)}}
        (tmp_path / f"rag_vs_norag_summary_shard{i}of{k}.json").write_text(json.dumps(summary), encoding="utf-8")


def test_aggregate_merges_complete_shards(tmp_path):
    ids = [f"A{i:03d}" for i in range(10)]
    _write_shards(tmp_path, ids, 3)
    summary = rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    assert summary["aggregated_from_shards"] == 3 and summary["n_answers"] == 10
    assert (tmp_path / rv.PRED_FILE).exists() and (tmp_path / rv.SUMMARY_FILE).exists()


def test_aggregate_refuses_a_missing_shard_overlap_and_incomplete_cover(tmp_path):
    ids = [f"A{i:03d}" for i in range(10)]
    _write_shards(tmp_path, ids, 3)
    (tmp_path / "rag_vs_norag_predictions_shard2of3.csv").unlink()
    with pytest.raises(FileNotFoundError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    _predictions(["A001"]).to_csv(tmp_path / "rag_vs_norag_predictions_shard2of3.csv", index=False)  # incomplete cover
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    _write_shards(tmp_path, ids, 3)
    _predictions(["A000"]).to_csv(tmp_path / "rag_vs_norag_predictions_shard3of3.csv", index=False)  # A000 now in two shards
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 3, set(ids), "gemini", {})
    assert not (tmp_path / rv.PRED_FILE).exists()  # nothing combined on refusal


def test_aggregate_refuses_an_answer_with_a_single_condition(tmp_path):
    ids = ["A000", "A001"]
    _write_shards(tmp_path, ids, 1)
    frame = _predictions(ids)
    frame[~((frame["answer_id"] == "A001") & (frame["condition"] == "B_rag"))].to_csv(
        tmp_path / "rag_vs_norag_predictions_shard1of1.csv", index=False)
    with pytest.raises(ValueError):
        rv.aggregate_shards(tmp_path, 1, set(ids), "gemini", {})


# ----------------------------------------- same experimental conditions in every shard

def test_fingerprint_changes_with_each_condition_that_must_stay_fixed(tmp_path, monkeypatch):
    data = tmp_path / "ds"
    data.mkdir()
    for name in rv.DATASET_FILES:
        (data / name).write_text("v1", encoding="utf-8")

    def fp(**kw):
        args = dict(provider_name="gemini", model="m-1", top_k=3, threshold=0.2, embedding_model="emb",
                    corpus_provenance={"documents": 5}, dataset_dir=data)
        return rv.build_fingerprint(**{**args, **kw})

    base = rv.fingerprint_id(fp())
    assert rv.fingerprint_id(fp()) == base  # deterministic
    for change in ({"provider_name": "openai"}, {"model": "m-2"}, {"top_k": 5}, {"threshold": 0.3}, {"embedding_model": "emb2"},
                   {"corpus_provenance": {"documents": 6}}):
        assert rv.fingerprint_id(fp(**change)) != base, change
    (data / "02_controlled_answers_eligible.csv").write_text("v2", encoding="utf-8")  # input file version
    assert rv.fingerprint_id(fp()) != base
    (data / "02_controlled_answers_eligible.csv").write_text("v1", encoding="utf-8")
    assert rv.fingerprint_id(fp()) == base
    monkeypatch.setattr(rv, "SYSTEM_RULES", "a different system prompt")  # prompt text
    assert rv.fingerprint_id(fp()) != base


def test_prompt_template_change_changes_the_fingerprint(tmp_path, monkeypatch):
    data = tmp_path / "ds"
    data.mkdir()
    for name in rv.DATASET_FILES:
        (data / name).write_text("x", encoding="utf-8")
    one = rv.build_fingerprint("g", "m", 3, 0.2, "e", {}, data)
    original = rv.build_prompt
    monkeypatch.setattr(rv, "build_prompt", lambda **kw: original(**kw) + " extra instruction")
    assert rv.build_fingerprint("g", "m", 3, 0.2, "e", {}, data)["prompt_templates_sha256"] != one["prompt_templates_sha256"]


def test_a_later_shard_with_different_conditions_is_refused_before_any_call(tmp_path):
    rv.check_or_create_manifest(tmp_path, FP, 9)
    rv.check_or_create_manifest(tmp_path, dict(FP), 9)  # identical conditions: fine
    with pytest.raises(ValueError, match="top_k"):
        rv.check_or_create_manifest(tmp_path, {**FP, "top_k": 5}, 9)
    with pytest.raises(ValueError, match="model"):
        rv.check_or_create_manifest(tmp_path, {**FP, "model": "m-2"}, 9)
    with pytest.raises(ValueError, match="9 shards"):
        rv.check_or_create_manifest(tmp_path, FP, 8)  # a different shard count would break the disjoint cover


def test_aggregate_refuses_shards_run_under_different_conditions_or_models(tmp_path):
    ids = [f"A{i:03d}" for i in range(6)]
    _write_shards(tmp_path, ids, 2)
    (tmp_path / "rag_vs_norag_summary_shard2of2.json").write_text(json.dumps({"run_config": {"fingerprint_sha256": "other"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="different conditions"):
        rv.aggregate_shards(tmp_path, 2, set(ids), "gemini", {})
    _write_shards(tmp_path, ids, 2)
    other = _predictions(["A001", "A003", "A005"])
    other["model"] = "m-2-silently-updated"
    other.to_csv(tmp_path / "rag_vs_norag_predictions_shard2of2.csv", index=False)
    with pytest.raises(ValueError, match="more than one model"):
        rv.aggregate_shards(tmp_path, 2, set(ids), "gemini", {})
    (tmp_path / "run_manifest.json").chmod(stat.S_IREAD | stat.S_IWRITE)  # it is read-only by design
    (tmp_path / "run_manifest.json").unlink()
    with pytest.raises(FileNotFoundError, match="run_manifest"):
        rv.aggregate_shards(tmp_path, 2, set(ids), "gemini", {})


# --------------------------------------------- code/configuration fingerprint and the manifest file

def _code_tree(root, rag="r1", llm="l1", loader="m1", script="s1"):
    (root / "experiments").mkdir(parents=True, exist_ok=True)
    (root / "services" / "rag").mkdir(parents=True, exist_ok=True)
    (root / "services" / "llm").mkdir(parents=True, exist_ok=True)
    (root / "experiments" / "rag_vs_norag.py").write_text(script, encoding="utf-8")
    (root / "experiments" / "model_comparison.py").write_text(loader, encoding="utf-8")
    (root / "services" / "rag" / "rag_marking.py").write_text(rag, encoding="utf-8")
    (root / "services" / "llm" / "gemini_provider.py").write_text(llm, encoding="utf-8")
    return root


def _dataset(root, text="x"):
    root.mkdir(parents=True, exist_ok=True)
    for name in rv.DATASET_FILES:
        (root / name).write_text(text, encoding="utf-8")
    return root


def _fp(code_root, data_root, **kw):
    args = dict(provider_name="gemini", model="m-1", top_k=3, threshold=0.2, embedding_model="emb", corpus_provenance={"documents": 5})
    return rv.build_fingerprint(**{**args, **kw}, dataset_dir=data_root, code_root=code_root)


def test_experiment_source_changes_change_the_fingerprint_but_line_endings_do_not(tmp_path):
    data = _dataset(tmp_path / "ds")
    base = rv.fingerprint_id(_fp(_code_tree(tmp_path / "c0"), data))
    assert rv.fingerprint_id(_fp(_code_tree(tmp_path / "c1"), data)) == base  # same content, other folder
    for name, kwargs in (("rag", {"rag": "r2"}), ("llm", {"llm": "l2"}), ("loader", {"loader": "m2"}), ("script", {"script": "s2"})):
        assert rv.fingerprint_id(_fp(_code_tree(tmp_path / f"c_{name}", **kwargs), data)) != base, name
    crlf = _code_tree(tmp_path / "crlf")
    (crlf / "services" / "rag" / "rag_marking.py").write_bytes(b"a\r\nb")
    lf = _code_tree(tmp_path / "lf", rag="a\nb")
    assert rv.code_hashes(crlf)["services/rag/rag_marking.py"] == rv.code_hashes(lf)["services/rag/rag_marking.py"]
    extra = _code_tree(tmp_path / "extra")
    (extra / "services" / "rag" / "new_module.py").write_text("x", encoding="utf-8")  # a new file in a tracked package
    assert rv.fingerprint_id(_fp(extra, data)) != base


def test_result_affecting_environment_settings_change_the_fingerprint(tmp_path, monkeypatch):
    data, code = _dataset(tmp_path / "ds"), _code_tree(tmp_path / "c")
    for name in rv.ENV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    base = rv.fingerprint_id(_fp(code, data))
    for name in ("C3_GEMINI_MODEL", "C3_GEMINI_THINKING_BUDGET", "C3_EMBEDDING_PROVIDER", "C3_LOCAL_EMBEDDING_MODEL"):
        monkeypatch.setenv(name, "changed")
        assert rv.fingerprint_id(_fp(code, data)) != base, name
        monkeypatch.delenv(name)
    assert rv.fingerprint_id(_fp(code, data)) == base
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value")  # keys are never part of the fingerprint
    assert "secret-value" not in json.dumps(_fp(code, data), default=str) and rv.fingerprint_id(_fp(code, data)) == base


def test_git_info_reports_commit_and_uncommitted_experiment_files(tmp_path):
    info = rv.git_info()
    assert set(info) == {"git_commit", "git_dirty_files"}
    assert info["git_commit"] is None or len(info["git_commit"]) == 40
    assert info["git_dirty_files"] is None or isinstance(info["git_dirty_files"], list)
    assert rv.git_info(root=tmp_path) == {"git_commit": None, "git_dirty_files": None}  # not a repository


def test_manifest_is_created_exclusively_read_only_and_never_overwritten(tmp_path):
    rv.check_or_create_manifest(tmp_path, FP, 9, {"git_commit": "abc"})
    path = tmp_path / rv.MANIFEST_FILE
    original = path.read_bytes()
    assert not os.access(path, os.W_OK) and not path.stat().st_mode & stat.S_IWRITE
    with pytest.raises(ValueError):
        rv.check_or_create_manifest(tmp_path, {**FP, "model": "other"}, 9)  # later shard with other conditions
    rv.check_or_create_manifest(tmp_path, FP, 9, {"git_commit": "different-later-commit"})  # same conditions: accepted
    assert path.read_bytes() == original  # neither call rewrote it
    assert json.loads(original)["created_with"] == {"git_commit": "abc"}


def test_a_manifest_that_was_edited_is_detected_everywhere(tmp_path):
    rv.check_or_create_manifest(tmp_path, FP, 2)
    path = tmp_path / rv.MANIFEST_FILE
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["fingerprint"]["model"] = "edited-after-the-fact"  # tampering so a different model would pass
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="modified or corrupted"):
        rv.check_or_create_manifest(tmp_path, {**FP, "model": "edited-after-the-fact"}, 2)
    ids = ["A000", "A001"]
    for i in (1, 2):
        _predictions([ids[i - 1]]).to_csv(tmp_path / f"rag_vs_norag_predictions_shard{i}of2.csv", index=False)
        (tmp_path / f"rag_vs_norag_summary_shard{i}of2.json").write_text(json.dumps({"run_config": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="modified or corrupted"):
        rv.aggregate_shards(tmp_path, 2, set(ids), "gemini", {})


def test_aggregate_records_commits_and_flags_uncommitted_code(tmp_path):
    ids = [f"A{i:03d}" for i in range(4)]
    _write_shards(tmp_path, ids, 2)
    for i, (commit, dirty) in enumerate((("c1", []), ("c2", ["services/rag/rag_marking.py"])), start=1):
        path = tmp_path / f"rag_vs_norag_summary_shard{i}of2.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["run_config"].update({"git_commit": commit, "git_dirty_files": dirty})
        path.write_text(json.dumps(doc), encoding="utf-8")
    summary = rv.aggregate_shards(tmp_path, 2, set(ids), "gemini", {})
    assert summary["code_version"] == {"git_commits": ["c1", "c2"], "git_dirty_files": ["services/rag/rag_marking.py"],
                                       "reproducible_from_one_commit": False}  # identical code, but not one commit / a dirty tree


# -------------------------- refusal happens before any LLM call (main() with fakes; no network, no model download)

class _FakeProvider:
    model = "m-1"
    calls = 0

    def is_available(self):
        return True

    def generate(self, request):
        type(self).calls += 1
        raise AssertionError("an LLM call was made")


class _FakeEmbedder:
    model = "emb"


@pytest.fixture
def fake_stack(monkeypatch):
    _FakeProvider.calls = 0
    for name in rv.ENV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(rv, "get_llm_provider", lambda name: _FakeProvider())
    monkeypatch.setattr(rv, "get_embedding_provider", lambda name=None: _FakeEmbedder())
    monkeypatch.setattr(rv, "build_training_corpus", lambda dataset: ([], {"documents": 5}))
    monkeypatch.setattr(rv, "CurriculumVectorStore", lambda *a, **k: object())
    return _FakeProvider


def _baseline_fp(**kw):
    args = dict(provider_name="gemini", model="m-1", top_k=3, threshold=0.2, embedding_model="emb", corpus_provenance={"documents": 5})
    return rv.build_fingerprint(**{**args, **kw})


def _main(out, shard="1/9", *extra):
    return rv.main(["--out", str(out), "--provider", "gemini", "--run-live", "--shard", shard, *extra])


@pytest.mark.parametrize("field,make", [
    ("model", lambda tmp, mp: _baseline_fp(model="m-2")),
    ("provider", lambda tmp, mp: _baseline_fp(provider_name="openai")),
    ("top_k", lambda tmp, mp: _baseline_fp(top_k=5)),
    ("threshold", lambda tmp, mp: _baseline_fp(threshold=0.4)),
    ("embedding_model", lambda tmp, mp: _baseline_fp(embedding_model="emb-2")),
    ("corpus_provenance", lambda tmp, mp: _baseline_fp(corpus_provenance={"documents": 6})),
    ("dataset_files_sha256", lambda tmp, mp: _baseline_fp(dataset_dir=_dataset(tmp / "other_ds", "changed"))),
    ("code_files_sha256", lambda tmp, mp: _baseline_fp(code_root=_code_tree(tmp / "other_code", script="changed"))),
    ("environment", lambda tmp, mp: (mp.setenv("C3_GEMINI_MODEL", "other-model"), _baseline_fp(), mp.delenv("C3_GEMINI_MODEL"))[1]),
])
def test_changed_conditions_are_refused_before_any_llm_call(tmp_path, monkeypatch, capsys, fake_stack, field, make):
    out = tmp_path / "run"
    out.mkdir()
    rv.check_or_create_manifest(out, make(tmp_path, monkeypatch), 9)  # what an earlier shard recorded
    before = (out / rv.MANIFEST_FILE).read_bytes()
    assert _main(out) == 2
    err = capsys.readouterr().err
    assert "differ from the first shard in:" in err and field in err  # the refusal names the changed field
    assert fake_stack.calls == 0 and (out / rv.MANIFEST_FILE).read_bytes() == before
    assert sorted(p.name for p in out.iterdir()) == [rv.MANIFEST_FILE]  # no shard output was produced


def test_prompt_text_change_is_refused_before_any_llm_call(tmp_path, monkeypatch, capsys, fake_stack):
    out = tmp_path / "run"
    out.mkdir()
    with monkeypatch.context() as m:
        m.setattr(rv, "SYSTEM_RULES", "an earlier, different system prompt")
        rv.check_or_create_manifest(out, _baseline_fp(), 9)
    assert _main(out) == 2 and "prompt_templates_sha256" in capsys.readouterr().err and fake_stack.calls == 0


def test_changed_shard_count_is_refused_before_any_llm_call(tmp_path, capsys, fake_stack):
    out = tmp_path / "run"
    out.mkdir()
    rv.check_or_create_manifest(out, _baseline_fp(), 9)
    assert _main(out, "1/8") == 2 and "9 shards, not 8" in capsys.readouterr().err and fake_stack.calls == 0


def test_limit_and_shard_together_are_refused_before_anything_else(tmp_path, capsys, fake_stack):
    assert _main(tmp_path / "x", "1/9", "--limit", "5") == 2 and fake_stack.calls == 0
