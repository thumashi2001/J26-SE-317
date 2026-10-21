# ruff: noqa: E501
"""Ratio-metric boundaries, exclusion traceability, source coverage and the machine-readable validation report.

Pipeline logic only: the FakeProvider returns canned structurally valid JSON; nothing here is data.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from test_dataset_generator import SPEC, FakeProvider, make_questions, make_tasks

import datasets.generate_c3_dataset as gen_cli
import datasets.validate_dataset as val
from datasets.generator import DATASET_VERSION
from datasets.generator.checks import ratio_concentration
from datasets.generator.llm_tasks import LLMTasks
from datasets.generator.pipeline import EXCLUSION_CLASSES, Pipeline
from datasets.generator.roles import Role
from datasets.generator.source import SOURCE_FILE_LABEL, SourceQuestion, load_source
from datasets.generator.writer import EXCLUDED_COLUMNS, write_release
from services.llm.base import LLMResponse

THRESHOLD = SPEC["thresholds"]["max_share_on_top7_ratios"]


# -- ratio_concentration boundaries (value 0.45 and hard-check status are unchanged) ---------------------------------
def test_threshold_value_scope_text_and_status_unchanged():
    assert THRESHOLD == 0.45
    assert SPEC["thresholds"]["ratio_metric_scope"] == (
        "dataset-wide, hard check, labels strictly between 0 and 1, top-7 most frequent ratios rounded to 3 d.p., "
        "denominator = number of such labels"
    )
    assert "RATIO_CONCENTRATION" in val.ALL_CODES


def test_ratio_all_anchor_labels_give_zero():
    assert ratio_concentration([0.0, 1.0, 0.0, 1.0, 1.0]) == 0.0
    assert ratio_concentration([]) == 0.0


def test_ratio_single_inner_value_is_fully_concentrated():
    assert ratio_concentration([0.0, 0.5, 1.0, 0.5, 0.5]) == 1.0


def _distinct(count: int, avoid=()):
    out = []
    k = 1
    while len(out) < count:
        v = round(k / 1000, 3)
        if v not in avoid:
            out.append(v)
        k += 1
    return out


def _with_top7(counts: list[int], n_singles: int) -> list[float]:
    """Seven repeated ratios with the given counts plus n_singles distinct once-only ratios."""
    top = [0.101, 0.202, 0.303, 0.404, 0.505, 0.606, 0.707]
    ratios = [r for r, c in zip(top, counts, strict=True) for _ in range(c)]
    return ratios + _distinct(n_singles, avoid=set(top))


def test_ratio_exactly_at_threshold_passes_and_just_above_fails():
    exact = _with_top7([2, 2, 1, 1, 1, 1, 1], 11)  # 9 of 20 inner labels = 0.45 exactly
    assert len([r for r in exact if 0 < r < 1]) == 20
    c = ratio_concentration(exact)
    assert c == 0.45 and not c > THRESHOLD  # the validator violates on `>` only
    above = _with_top7([65, 65, 65, 64, 64, 64, 64], 549)  # 451 of 1000 = 0.451
    c2 = ratio_concentration(above)
    assert c2 == 0.451 and c2 > THRESHOLD


def test_ratio_anchors_excluded_from_numerator_and_denominator():
    inner = _distinct(8)  # 8 distinct inner labels -> 7 of 8
    padded = [0.0] * 500 + [1.0] * 500 + inner
    assert ratio_concentration(padded) == ratio_concentration(inner) == 7 / 8


def test_ratio_groups_at_three_decimal_places():
    ratios = [0.3333, 0.33333, *_distinct(8, avoid={0.333})]  # both round to 0.333 -> one group of two
    assert ratio_concentration(ratios) == (2 + 6) / 10


def test_ratio_counts_each_of_top7_only():
    # 8 equally frequent ratios: only 7 groups count
    ratios = [r for r in _distinct(8) for _ in range(3)]
    assert ratio_concentration(ratios) == pytest.approx(21 / 24)


# -- fixtures: a tiny release containing every kind of exclusion --------------------------------------------------------
class OcrAwareFake(FakeProvider):
    """Handles the clean_text prompt by returning the text unchanged (so the noise remains)."""

    def generate(self, request):
        if request.prompt.startswith("The exam question below was scanned"):
            import re

            raw = re.search(r"<<<\n(.*?)\n>>>", request.prompt, re.S).group(1)
            data = {"clean_text": raw}
            return LLMResponse(
                raw_content=json.dumps(data), parsed_json=data, model_identifier="fake", provider_name="fake"
            )
        return super().generate(request)


def extra_questions():
    return [
        SourceQuestion("QX", "SE3000", "synthetic", "", "Please DRAWDIAGRAM of it.", 10.0),
        SourceQuestion("QB", "SE3000", "synthetic", "", "Stem. BADMARKS (a) Define foo. (b) Discuss bar.", 10.0),
        SourceQuestion("QO", "SE3010", "synthetic", "", "Explain � � caching � strategies foo bar.", 10.0),
    ]


@pytest.fixture(scope="module")
def data():
    tasks = LLMTasks(OcrAwareFake(), OcrAwareFake(), SPEC, sleep=lambda s: None)
    pipe = Pipeline(tasks, SPEC, 20261021, 2, "fake-gen", "fake-ver")
    qs = make_questions(12) + extra_questions()
    result, failures = pipe.run(qs)
    assert result is not None and not failures
    return result


def release(tmp_path: Path, d, name="rel") -> Path:
    out = tmp_path / name
    write_release(out, d, SPEC, 1)
    return out


def codes(path: Path, **kw) -> set[str]:
    return {v.code for v in val.validate_release(path, **kw)}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# -- exclusion traceability ----------------------------------------------------------------------------------------------
def test_exclusion_rows_carry_class_reason_diagnostic_and_source_row(data):
    by_id = {e["question_id"]: e for e in data.excluded}
    assert {"QX", "QB", "QO"} <= set(by_id)  # plus whatever the fake pipeline itself rejects
    qx, qb, qo = by_id["QX"], by_id["QB"], by_id["QO"]
    assert qx["exclusion_class"] == "intentional_scope" and qx["reason"] == "requires_diagram"
    assert qb["exclusion_class"] == "intentional_quality" and qb["reason"] == "structure_invalid_after_retries"
    assert qo["exclusion_class"] == "intentional_quality" and qo["reason"] == "ocr_noise_unrepairable"
    assert "ocr_noise_ratio=" in qo["diagnostic"]
    assert [qx["source_row"], qb["source_row"], qo["source_row"]] == [13, 14, 15]
    for e in data.excluded:
        assert e["exclusion_class"] in EXCLUSION_CLASSES[:2]
        assert e["source_file"] == SOURCE_FILE_LABEL == "datasets/source/questions_source.csv"
        assert e["parent_question_id"] == e["question_id"] and e["diagnostic"].strip() and e["reason"].strip()
        assert set(EXCLUDED_COLUMNS) <= set(e)


def test_source_rows_are_one_based_positions_in_the_source_file():
    rows = load_source(limit=3)
    assert [q.source_row for q in rows] == [1, 2, 3]
    assert SOURCE_FILE_LABEL == "datasets/source/questions_source.csv"


def test_rubric_exclusion_of_one_part_uses_part_id_and_parent_id():
    pipe = Pipeline(make_tasks(FakeProvider(never_valid_rubric=True)), SPEC, 1, 2, "g", "v")
    q = SourceQuestion("QP", "SE3010", "synthetic", "", "Stem text. (a) Define foo. (b) Discuss bar.", 10.0, 7)
    oc = pipe.process_question(q)
    ex = oc.excluded
    assert ex["question_id"] == "QP-a" and ex["parent_question_id"] == "QP"
    assert ex["reason"] == "rubric_invalid_after_retries" and ex["exclusion_class"] == "intentional_quality"
    assert "sum" in ex["diagnostic"] and ex["source_row"] == 7


def test_tier_collapse_is_an_intentional_exclusion_with_diagnostic():
    spec = copy.deepcopy(SPEC)
    spec["order_chain"].append({"higher": "IRRELEVANT", "lower": "FULL", "strict": True})
    f = FakeProvider()
    pipe = Pipeline(LLMTasks(f, f, spec, sleep=lambda s: None), spec, 1, 2, "g", "v")
    oc = pipe.process_question(SourceQuestion("QT", "SE3010", "synthetic", "", "Explain stuff here please.", 10.0, 4))
    assert oc.excluded["reason"] == "tier_collapse" and oc.excluded["exclusion_class"] == "intentional_quality"
    assert oc.excluded["diagnostic"] and oc.excluded["question_id"] == "QT" and oc.failure is None


def test_unexpected_exceptions_are_processing_failures_not_exclusions():
    class Boom(FakeProvider):
        def generate(self, request):
            raise RuntimeError("provider exploded")

    pipe = Pipeline(make_tasks(Boom()), SPEC, 1, 2, "g", "v")
    oc = pipe.process_question(SourceQuestion("QE", "SE3010", "synthetic", "", "Explain stuff here please.", 10.0, 2))
    assert oc.excluded is None and oc.failure["task"] == "unexpected" and "provider exploded" in oc.failure["message"]
    data, failures = pipe.run([SourceQuestion("QE", "SE3010", "synthetic", "", "Explain stuff here please.", 10.0)])
    assert data is None and failures[0]["question_id"] == "QE"


def test_provider_failure_makes_cli_exit_nonzero_and_writes_no_exclusion_csv(monkeypatch, tmp_path, capsys):
    class AlwaysFails(FakeProvider):
        def generate(self, request):
            return LLMResponse(raw_content="", model_identifier="f", provider_name="f", is_success=False,
                               error_message="HTTP 500 from stub")  # fmt: skip

    monkeypatch.setattr(Role, "build", lambda self: AlwaysFails())
    monkeypatch.setattr(gen_cli, "load_source", lambda limit=None: make_questions(3))
    monkeypatch.setattr(gen_cli, "preflight_or_report", lambda reqs, path, **kw: (True, "ok"))
    monkeypatch.setattr(LLMTasks, "__init__", _fast_init(LLMTasks.__init__))
    out = tmp_path / "o"
    assert gen_cli.main(["--out", str(out)]) == 1
    assert "FAILED" in capsys.readouterr().err
    assert not (out / "excluded_questions.csv").exists() and not (out / "manifest.json").exists()


def _fast_init(orig):
    def init(self, generator, verifier, spec, sleep=None, timeout_seconds=180.0):
        orig(self, generator, verifier, spec, sleep=lambda s: None, timeout_seconds=timeout_seconds)

    return init


def test_manifest_counts_exclusions_per_class_reason_and_top_reasons(data, tmp_path):
    manifest = json.loads((release(tmp_path, data) / "manifest.json").read_text(encoding="utf-8"))
    c = manifest["counts"]
    assert c["excluded_by_class"] == dict(sorted(Counter(e["exclusion_class"] for e in data.excluded).items()))
    assert c["excluded_by_class"]["intentional_scope"] == 1 and c["excluded_by_class"]["intentional_quality"] >= 2
    assert c["excluded_by_reason"] == dict(sorted(Counter(e["reason"] for e in data.excluded).items()))
    assert {"ocr_noise_unrepairable", "requires_diagram", "structure_invalid_after_retries"} <= set(c["excluded_by_reason"])
    assert {r["reason"] for r in c["excluded_top_reasons"]} == set(c["excluded_by_reason"])
    assert c["excluded_top_reasons"] == sorted(c["excluded_top_reasons"], key=lambda r: -r["count"])
    assert all(isinstance(r["count"], int) for r in c["excluded_top_reasons"])
    assert manifest["source_file"] == SOURCE_FILE_LABEL and len(manifest["source_question_ids"]) == 15


def test_excluded_csv_has_all_traceability_columns(data, tmp_path):
    rows = read_csv(release(tmp_path, data) / "excluded_questions.csv")
    assert list(rows[0]) == EXCLUDED_COLUMNS
    assert {"13", "14", "15"} <= {r["source_row"] for r in rows}


# -- validator: traceability + coverage ----------------------------------------------------------------------------------------
def patch_csv(path: Path, name: str, old: str, new: str) -> None:
    f = path / name
    text = f.read_text(encoding="utf-8")
    assert old in text
    f.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_clean_release_with_exclusions_passes_validation(data, tmp_path):
    assert val.validate_release(release(tmp_path, data)) == []


@pytest.mark.parametrize(
    "old,new",
    [
        ("intentional_scope", "processing_failure"),  # processing failures must never be an exclusion row
        ("intentional_scope", "whatever"),
    ],
)
def test_validator_rejects_missing_or_invalid_exclusion_class(data, tmp_path, old, new):
    out = release(tmp_path, data)
    patch_csv(out, "excluded_questions.csv", old, new)
    assert "EXCLUDED_UNTRACEABLE" in codes(out)


def test_validator_rejects_bad_source_row_and_missing_source_file(data, tmp_path):
    out = release(tmp_path, data)
    patch_csv(out, "excluded_questions.csv", "datasets/source/questions_source.csv", "")
    patch_csv(out, "excluded_questions.csv", ",13,", ",zero,")
    msgs = [v.message for v in val.validate_release(out) if v.code == "EXCLUDED_UNTRACEABLE"]
    assert any("source_file" in m for m in msgs) and any("source_row" in m for m in msgs)


def test_validator_flags_source_row_that_disagrees_with_source_position(data, tmp_path):
    out = release(tmp_path, data)
    patch_csv(out, "excluded_questions.csv", ",13,", ",5,")
    assert any("position" in v.message for v in val.validate_release(out) if v.code == "EXCLUDED_UNTRACEABLE")


def test_validator_needs_a_reason(data, tmp_path):
    out = release(tmp_path, data)
    patch_csv(out, "excluded_questions.csv", "requires_diagram", " ")
    assert "EXCLUDED_NO_REASON" in codes(out)


def test_old_format_excluded_file_is_reported_not_crashed(data, tmp_path):
    out = release(tmp_path, data)
    rows = read_csv(out / "excluded_questions.csv")
    with (out / "excluded_questions.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["question_id", "module_code", "source_type", "question_text_raw", "stage", "reason", "dataset_version"])
        for r in rows:
            w.writerow([r[k] for k in ("question_id", "module_code", "source_type", "question_text_raw", "stage", "reason",
                                       "dataset_version")])  # fmt: skip
    assert "EXCLUDED_UNTRACEABLE" in codes(out)


def test_unaccounted_source_question_is_a_violation(data, tmp_path):
    d = copy.deepcopy(data)
    d.excluded = [e for e in d.excluded if e["question_id"] != "QX"]  # QX silently vanishes
    vios = [v for v in val.validate_release(release(tmp_path, d)) if v.code == "UNACCOUNTED_SOURCE_QUESTION"]
    assert vios and vios[0].ids == ["QX"]


def test_every_kept_or_excluded_source_question_is_accounted(data, tmp_path):
    out = release(tmp_path, data)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    kept = {q["parent_question_id"] for q in data.questions}
    assert set(manifest["source_question_ids"]) == kept | {e["parent_question_id"] for e in data.excluded}
    assert "UNACCOUNTED_SOURCE_QUESTION" in val.ALL_CODES


def test_part_level_exclusion_counts_via_parent_and_source_csv_option(data, tmp_path):
    # rename an excluded row to a part id: the parent id still accounts for the source question
    d = copy.deepcopy(data)
    qx = next(e for e in d.excluded if e["question_id"] == "QX")
    qx["question_id"], qx["parent_question_id"] = "QX-a", "QX"
    out = release(tmp_path, d)
    assert "UNACCOUNTED_SOURCE_QUESTION" not in codes(out)
    # explicit --source file: ids come from the file (first manifest.source_questions rows)
    src = tmp_path / "src.csv"
    ids = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["source_question_ids"]
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["question_id"])
        w.writerows([[i] for i in [*ids, "NOT-PROCESSED"]])
    assert "UNACCOUNTED_SOURCE_QUESTION" not in codes(out, source_csv=src)  # only the first N rows are in scope
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["question_id"])
        w.writerows([["GHOST"], *[[i] for i in ids[1:]]])
    assert "UNACCOUNTED_SOURCE_QUESTION" in codes(out, source_csv=src)


# -- ratio metric per split (informational) ------------------------------------------------------------------------------------------
def test_validator_reports_ratio_metric_per_split_without_enforcing_it(data, tmp_path, monkeypatch):
    out = release(tmp_path, data)
    violations, stats = val.validate_with_stats(out)
    rc = stats["ratio_concentration"]
    assert violations == [] and set(rc["per_split_informational"]) == {"train", "validation", "test"}
    assert rc["scope"] == SPEC["thresholds"]["ratio_metric_scope"] and rc["enforced"] is True
    n_total = sum(1 for _ in read_csv(out / "answers.csv"))
    monkeypatch.setattr(val, "ratio_concentration", lambda xs, *a: 0.1 if len(xs) == n_total else 0.99)
    violations, stats = val.validate_with_stats(out)
    assert "RATIO_CONCENTRATION" not in {v.code for v in violations}  # per-split value is not a violation
    assert any("split 'train'" in w and "informational" in w for w in stats["warnings"])


def test_dataset_wide_ratio_check_is_still_a_hard_check_at_the_boundary(data, tmp_path, monkeypatch):
    out = release(tmp_path, data)
    monkeypatch.setattr(val, "ratio_concentration", lambda xs, *a: 0.45)
    assert "RATIO_CONCENTRATION" not in codes(out)
    monkeypatch.setattr(val, "ratio_concentration", lambda xs, *a: 0.451)
    assert "RATIO_CONCENTRATION" in codes(out)


# -- machine-readable report -------------------------------------------------------------------------------------------------------------
def test_json_report_for_valid_release(data, tmp_path, capsys):
    out = release(tmp_path, data)
    assert val.main([str(out), "--json"]) == 0  # no value -> <dir>/validation_report.json
    report = json.loads((out / "validation_report.json").read_text(encoding="utf-8"))
    assert report["passed"] is True and report["violations"] == [] and report["dataset_version"] == DATASET_VERSION
    assert report["directory"] == str(out) and report["report_schema"].startswith("c3-validation-report")
    c = report["counts"]
    assert c["questions"] == len(data.questions) and c["answers"] == len(data.answers)
    assert c["answers_by_split"] == dict(sorted(Counter(a["split"] for a in data.answers).items()))
    assert c["excluded_by_class"] == dict(sorted(Counter(e["exclusion_class"] for e in data.excluded).items()))
    f = report["files"]["answers.csv"]
    assert f["sha256"] == hashlib.sha256((out / "answers.csv").read_bytes()).hexdigest()
    assert "manifest.json" in report["files"] and "validation_report.json" not in report["files"]
    assert {ch["code"] for ch in report["checks"]} == set(val.ALL_CODES)
    assert all(ch["passed"] and ch["ran"] for ch in report["checks"])
    rc = report["ratio_concentration"]
    assert rc["threshold"] == 0.45 and set(rc["per_split_informational"]) == {"train", "validation", "test"}
    assert set(report["tier_means"]) == set(SPEC["core_tiers"]) | set(SPEC["edge_tiers"])
    assert set(report["length_correlation"]) == {"overall_pearson", "within_question_mean_pearson", "n_within"}
    assert isinstance(report["warnings"], list) and "Wrote validation report" in capsys.readouterr().out


def test_json_report_with_explicit_path_and_broken_release_exits_1(data, tmp_path):
    d = copy.deepcopy(data)
    victims = [a for a in d.answers if a["tier"] not in ("EMPTY", "TOO_SHORT")][:30]  # 30 ids -> report keeps 20
    for a in victims:
        a["student_answer"] += " The answer does not cover the topic."
    out = release(tmp_path, d)
    target = tmp_path / "custom" / "report.json"
    target.parent.mkdir()
    assert val.main([str(out), "--json", str(target)]) == 1
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["passed"] is False
    banned = next(v for v in report["violations"] if v["code"] == "BANNED_PHRASE")
    assert banned["n_ids"] == 30 and len(banned["ids"]) == 20 and banned["message"]
    failed = {ch["code"] for ch in report["checks"] if not ch["passed"]}
    assert "BANNED_PHRASE" in failed and failed == {v["code"] for v in report["violations"]}


def test_json_report_for_release_with_missing_files(data, tmp_path):
    out = release(tmp_path, data)
    (out / "answers.csv").unlink()
    assert val.main([str(out), "--json"]) == 1
    report = json.loads((out / "validation_report.json").read_text(encoding="utf-8"))
    assert report["passed"] is False and report["violations"][0]["code"] == "FILE_MISSING"
    assert not any(ch["ran"] for ch in report["checks"] if ch["passed"])  # checks that never ran are not claimed as run

