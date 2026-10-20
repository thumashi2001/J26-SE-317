# ruff: noqa: E501
"""Pipeline-logic tests for the C3 dataset generator.

The FakeProvider below returns canned, structurally valid JSON so the PIPELINE LOGIC can be tested offline.
Nothing it produces is data and none of it may be presented as such.
"""

from __future__ import annotations

import hashlib
import json
import random
import re

import pytest

from datasets.generator import DATASET_VERSION, load_tier_spec
from datasets.generator.checks import derive_evidence_spans, derive_gold_mindmap, split_sentences
from datasets.generator.llm_tasks import LLMTasks, LLMValidationError, validate_draft
from datasets.generator.pipeline import Pipeline
from datasets.generator.planning import TierCollapse, build_question_plans, deterministic_answer
from datasets.generator.source import SourceQuestion, dry_run_stats, is_verbatim, ocr_noise_ratio
from datasets.generator.splitting import SPLITS, SplitError, build_parent_docs, check_answer_leakage, split_parents
from datasets.generator.writer import WriteError, write_csv
from services.llm.base import BaseLLMProvider, LLMRequest, LLMResponse

SPEC = load_tier_spec()
_SYL = ["ka", "to", "mi", "re", "su", "no", "la", "vi", "pe", "do", "ru", "ne", "fa", "bo", "ti", "ge", "zu", "ma"]


def vocab(n: int = 900) -> list[str]:
    rng = random.Random(7)
    words: list[str] = []
    seen: set[str] = set()
    while len(words) < n:
        w = "".join(rng.choice(_SYL) for _ in range(rng.choice([2, 3, 3, 4])))
        if w not in seen:
            seen.add(w)
            words.append(w)
    return words


VOCAB = vocab()


def seeded(text: str) -> random.Random:
    return random.Random(int(hashlib.sha256(text.encode()).hexdigest()[:12], 16))


class FakeProvider(BaseLLMProvider):
    """Canned valid JSON per task, keyed off the prompt. Used for pipeline-logic tests ONLY."""

    def __init__(self, bad_rubric_first: bool = False, never_valid_rubric: bool = False):
        super().__init__("fake")
        self.bad_rubric_first = bad_rubric_first
        self.never_valid_rubric = never_valid_rubric
        self.prompts: list[str] = []
        self.rubric_calls = 0

    def is_available(self) -> bool:
        return True

    def health_check(self) -> dict:
        return {"provider": "fake"}

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.prompts.append(request.prompt)
        p = request.prompt
        if p.startswith("Analyse this exam question"):
            data = self._structure(p)
        elif p.startswith("Draft a marking reference"):
            data = self._rubric(p)
        elif p.startswith("You will write"):
            data = self._answers(p)
        elif p.startswith("Mark the student answer"):
            data = self._grade(p)
        else:
            raise AssertionError("unexpected prompt")
        return LLMResponse(
            raw_content=json.dumps(data),
            parsed_json=data,
            model_identifier="fake",
            provider_name="fake",
            is_real_execution=False,
        )

    # -- canned behaviours ---------------------------------------------------------------------------------
    def _structure(self, p: str) -> dict:
        marks = float(re.search(r"TOTAL_MARKS: (\S+)", p).group(1))
        text = re.search(r"<<<\n(.*?)\n>>>", p, re.S).group(1)
        if "DRAWDIAGRAM" in text:
            return {"answerable_as_written_text": False, "exclusion_reason": "requires_diagram"}
        m = re.search(r"^(.*?)\(a\)(.*?)\(b\)(.*)$", text, re.S)
        if not m:
            return {"answerable_as_written_text": True, "exclusion_reason": "", "stem": "", "marks_stated": False,
                    "answer_type": "explanation", "parts": [{"part_label": "", "text": text, "marks": marks}]}
        stem, pa, pb = (x.strip() for x in m.groups())
        first = round(marks / 2, 1) if "BADMARKS" not in text else marks
        return {"answerable_as_written_text": True, "exclusion_reason": "", "stem": stem, "marks_stated": False,
                "answer_type": "explanation",
                "parts": [{"part_label": "a", "text": "(a) " + pa, "marks": first},
                          {"part_label": "b", "text": "(b) " + pb, "marks": marks - first}]}  # fmt: skip

    def _rubric(self, p: str) -> dict:
        self.rubric_calls += 1
        qid = re.search(r"QUESTION_ID: (\S+)", p).group(1)
        marks = float(re.search(r"TOTAL_MARKS: (\S+)", p).group(1))
        rng = seeded(qid)
        concepts = [f"{rng.choice(VOCAB)} {rng.choice(VOCAB)}" for _ in range(5)]
        k = rng.choice([2, 3, 4])
        weights = [rng.uniform(0.5, 1.5) for _ in range(k)]
        maxes = [round(marks * w / sum(weights), 1) for w in weights[:-1]]
        maxes.append(round(marks - sum(maxes), 4))
        criteria = []
        for i, cmax in enumerate(maxes):
            fr = sorted(rng.sample([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], rng.choice([1, 2, 3])))
            marks_l = [0.0] + [round(cmax * f, 2) for f in fr] + [cmax]
            marks_l = sorted(set(marks_l))
            cc = [concepts[i]]
            criteria.append({
                "description": f"Explains {cc[0]}",
                "max_marks": cmax,
                "required_concepts": cc,
                "scoring_levels": [
                    {"label": f"L{j}", "mark": m, "descriptor": f"Level {j} of {cc[0]}",
                     "required_concepts": [] if m == 0 else cc, "min_demonstrated": 0 if m == 0 else 1}
                    for j, m in enumerate(marks_l)
                ],
            })  # fmt: skip
        ref = " ".join(rng.choice(VOCAB) for _ in range(120))
        draft = {
            "reference_answer": ref,
            "expected_concepts": concepts,
            "concept_graph": [{"source": concepts[0], "target": concepts[1], "type": "prerequisite_of"},
                              {"source": concepts[2], "target": concepts[3], "type": "part_of"}],
            "common_misconceptions": [{"claim": f"{concepts[0]} is never needed", "correct": "it is", "criterion_index": 0}],
            "criteria": criteria,
        }  # fmt: skip
        if self.never_valid_rubric or (self.bad_rubric_first and self.rubric_calls == 1):
            draft["criteria"][0]["max_marks"] += 1
        return draft

    def _answers(self, p: str) -> dict:
        count = int(re.search(r"write (\d+) distinct", p).group(1))
        concepts = [c.strip() for c in re.search(r"EXPECTED CONCEPTS: (.*)", p).group(1).split(";")]
        tier_line = re.search(r"TIER MEANING: (.*)", p).group(1)
        rng = seeded(p)
        specs = re.findall(r"Answer \d+: style=\w+ \((\d+)-(\d+) words\)", p)
        omit_blocks = re.split(r"Answer \d+: ", p.split("RUBRIC CRITERIA")[1])[1:]
        answers = []
        for i in range(count):
            lo, hi = (int(x) for x in specs[i])
            n = rng.randint(lo + 3, hi - 3)
            omitted = re.findall(r"never mention or allude to: (.*)", omit_blocks[i])
            banned = {c.strip() for c in omitted[0].split(";")} if omitted else set()
            words = [rng.choice(VOCAB) for _ in range(n)]
            status = {c: "missing" for c in concepts}
            if (
                tier_line.startswith("complete")
                or tier_line.startswith("re-express")
                or tier_line.startswith("full-credit")
            ):
                status = {c: "demonstrated" for c in concepts}
            elif (
                tier_line.startswith("mostly")
                or tier_line.startswith("covers")
                or tier_line.startswith("states a correct")
            ):
                status = {c: ("demonstrated" if j % 2 else "partial") for j, c in enumerate(concepts)}
            elif tier_line.startswith("good on"):
                status = {c: ("missing" if c in banned else "demonstrated") for c in concepts}
            elif tier_line.startswith("confident"):
                status = {c: ("incorrect" if j % 2 else "partial") for j, c in enumerate(concepts)}
            present = [c for c, s in status.items() if s in ("demonstrated", "partial", "incorrect")]
            for c in present:
                words[rng.randrange(len(words))] = c
            sentences, j = [], 0
            while j < len(words):
                step = rng.randint(5, 12)
                sentences.append(" ".join(words[j : j + step]).capitalize() + ".")
                j += step
            answers.append({"student_answer": " ".join(sentences), "concept_status": status})
        return {"answers": answers}

    def _grade(self, p: str) -> dict:
        rng = seeded(p)
        out = []
        for cid in re.findall(r"^- (\S+) \(", p, re.M):
            levels = re.findall(rf"^\s+\* ({re.escape(cid)}-L\d+) \[", p, re.M)
            out.append({"criterion_id": cid, "level_id": rng.choice(levels)})
        return {"criteria": out}


def make_questions(n: int, modules: int = 2, seed: int = 3) -> list[SourceQuestion]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        body = " ".join(rng.choice(VOCAB) for _ in range(18))
        text = f"Explain {body}."
        if i % 5 == 4:
            text = f"Describe {body} (a) Define {rng.choice(VOCAB)} terms. (b) Discuss {rng.choice(VOCAB)} limits."
        out.append(SourceQuestion(f"Q{i:03d}", f"SE30{i % modules}0", "synthetic", "", text, [10.0, 20.0, 25.0][i % 3]))
    return out


def make_tasks(fake: FakeProvider | None = None) -> LLMTasks:
    f = fake or FakeProvider()
    return LLMTasks(f, f, SPEC, sleep=lambda s: None)


# -- tests ---------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def rubric_draft():
    def build(qid: str, marks: float = 10.0):
        prompt = f"Draft a marking reference\nQUESTION_ID: {qid}\nTOTAL_MARKS: {marks:g}\n"
        return validate_draft(FakeProvider()._rubric(prompt), qid, marks, SPEC)

    return build


def test_planning_strict_order_nonflat_and_labels_are_level_sums(rubric_draft):
    all_norm = []
    for i in range(40):
        qid = f"P{i}"
        d = rubric_draft(qid, [10.0, 25.0][i % 2])
        try:
            plans = build_question_plans(qid, d.rubric, SPEC, 1, 2, [0])
        except TierCollapse:
            continue
        means = {
            t: sum(p.normalized for p in plans if p.tier == t) / sum(1 for p in plans if p.tier == t)
            for t in SPEC["core_tiers"]
        }
        assert means["FULL"] >= means["MOSTLY_CORRECT"] > means["PARTIAL"] >= means["MISSING_CONCEPT"]
        assert means["MISSING_CONCEPT"] >= means["MISCONCEPTION"] >= means["IRRELEVANT"] == 0
        assert means["MISCONCEPTION"] <= 0.5
        marks = {c.criterion_id: {lv.level_id: lv.mark for lv in c.scoring_levels} for c in d.rubric.criteria}
        for p in plans:
            assert p.expected_mark == pytest.approx(
                sum(marks[x["criterion_id"]][x["level_id"]] for x in p.criterion_levels)
            )
            assert p.expected_mark == pytest.approx(sum(x["mark"] for x in p.criterion_levels))
            all_norm.append(round(p.normalized, 3))
        assert any(p.tier == "IRRELEVANT" and p.expected_mark == 0 for p in plans)
        for p in plans:
            if p.tier == "MISSING_CONCEPT":
                assert p.omitted_concepts
    assert len(set(all_norm)) > 25  # labels are not concentrated on a handful of ratios


def test_style_and_register_independent_of_tier(rubric_draft):
    rank = {s: i for i, s in enumerate(SPEC["styles"])}
    by_tier: dict[str, list[int]] = {}
    for i in range(30):
        d = rubric_draft(f"S{i}")
        try:
            plans = build_question_plans(f"S{i}", d.rubric, SPEC, 5, 2)
        except TierCollapse:
            continue
        for p in plans:
            if p.tier in SPEC["core_tiers"]:
                by_tier.setdefault(p.tier, []).append(rank[p.style])
    means = [sum(v) / len(v) for v in by_tier.values()]
    assert max(means) - min(means) < 0.3
    assert all({0, 1, 2} <= set(v) for v in by_tier.values())


def test_planning_is_deterministic(rubric_draft):
    d = rubric_draft("D1")
    a = build_question_plans("D1", d.rubric, SPEC, 9, 2)
    b = build_question_plans("D1", d.rubric, SPEC, 9, 2)
    assert [(p.answer_id, p.expected_mark, p.style, p.register) for p in a] == [
        (p.answer_id, p.expected_mark, p.style, p.register) for p in b
    ]


def test_tier_collapse_when_rubric_cannot_order(rubric_draft):
    d = rubric_draft("C1")
    spec = json.loads(json.dumps(SPEC))
    spec["order_chain"].append({"higher": "IRRELEVANT", "lower": "FULL", "strict": True})
    with pytest.raises(TierCollapse):
        build_question_plans("C1", d.rubric, spec, 1, 2)


def test_deterministic_edge_answers(rubric_draft):
    d = rubric_draft("E1")
    plans = build_question_plans("E1", d.rubric, SPEC, 4, 2)
    short = next(p for p in plans if p.tier == "TOO_SHORT")
    empty = next(p for p in plans if p.tier == "EMPTY")
    assert len(deterministic_answer(short, "Explain latency caching strategies for services", 0).split()) < 8
    assert deterministic_answer(empty, "x", 0).strip() == ""
    assert short.expected_mark == 0 and empty.expected_mark == 0


def test_structure_splits_multipart_and_sums_marks():
    tasks = make_tasks()
    q = SourceQuestion("M1", "SE3010", "synthetic", "", "Stem text here. (a) Define foo. (b) Discuss bar.", 10.0)
    res = tasks.structure_question(q)
    assert res.answerable and [p.part_label for p in res.parts] == ["a", "b"]
    assert sum(p.marks for p in res.parts) == pytest.approx(10.0)
    assert all(is_verbatim(p.text, q.question_text) for p in res.parts)
    single = tasks.structure_question(SourceQuestion("M2", "SE3010", "synthetic", "", "Explain foo.", 5.0))
    assert [p.part_label for p in single.parts] == [""] and single.parts[0].text == "Explain foo."


def test_structure_bad_part_marks_raise_validation_error():
    tasks = make_tasks()
    q = SourceQuestion("M3", "SE3010", "synthetic", "", "Stem. BADMARKS (a) Define foo. (b) Discuss bar.", 10.0)
    with pytest.raises(LLMValidationError):
        tasks.structure_question(q)


def test_pipeline_records_exclusions_and_parts():
    pipe = Pipeline(make_tasks(), SPEC, 1, 2, "fake-gen", "fake-ver")
    ex = pipe.process_question(
        SourceQuestion("X1", "SE3010", "past_paper", "", "Please DRAWDIAGRAM of the system.", 10.0)
    )
    assert ex.excluded and ex.excluded["reason"] == "requires_diagram" and ex.excluded["stage"] == "scope"
    bad = pipe.process_question(SourceQuestion("X2", "SE3010", "past_paper", "", "Stem. BADMARKS (a) A. (b) B.", 10.0))
    assert bad.excluded and bad.excluded["stage"] == "structure"
    ok = pipe.process_question(
        SourceQuestion("X4", "SE3010", "past_paper", "", "Stem. (a) Define foo. (b) Discuss bar.", 10.0)
    )
    assert [p.question_id for p in ok.parts] == ["X4-a", "X4-b"] and {p.parent_id for p in ok.parts} == {"X4"}
    assert sum(p.marks for p in ok.parts) == pytest.approx(10.0)


def test_rubric_retry_feeds_back_validation_error_then_succeeds():
    fake = FakeProvider(bad_rubric_first=True)
    res = make_tasks(fake).draft_rubric("R1", "SE3010", 10.0, "Explain stuff.")
    assert res.rubric.rubric_id == "RUB-R1" and fake.rubric_calls == 2
    assert "REJECTED" in fake.prompts[1] and "sum" in fake.prompts[1]


def test_rubric_retry_exhaustion_is_a_validation_error_and_exclusion():
    fake = FakeProvider(never_valid_rubric=True)
    with pytest.raises(LLMValidationError):
        make_tasks(fake).draft_rubric("R2", "SE3010", 10.0, "Explain stuff.")
    assert fake.rubric_calls == SPEC["thresholds"]["max_llm_retries"]
    pipe = Pipeline(make_tasks(FakeProvider(never_valid_rubric=True)), SPEC, 1, 2, "g", "v")
    oc = pipe.process_question(SourceQuestion("R3", "SE3010", "synthetic", "", "Explain stuff here please.", 10.0))
    assert oc.excluded and oc.excluded["stage"] == "rubric"


def test_validate_draft_rejects_placeholders_and_missing_zero_level(rubric_draft):
    raw = FakeProvider()._rubric("QUESTION_ID: V1\nTOTAL_MARKS: 10\n")
    placeholder = json.loads(json.dumps(raw))
    placeholder["expected_concepts"][0] = "conceptual understanding"
    with pytest.raises(ValueError, match="placeholder"):
        validate_draft(placeholder, "V1", 10.0, SPEC)
    no_zero = json.loads(json.dumps(raw))
    no_zero["criteria"][0]["scoring_levels"][0]["mark"] = 0.1
    with pytest.raises(ValueError, match="mark 0"):
        validate_draft(no_zero, "V1", 10.0, SPEC)


def _split_rows(n_parents: int = 40):
    rng = random.Random(11)
    rows = []
    for i in range(n_parents):
        topic = [rng.choice(VOCAB) for _ in range(12)]
        for part in ("a", "b") if i % 7 == 0 else ("",):
            rows.append({
                "parent_question_id": f"P{i}", "question_id": f"P{i}-{part}" if part else f"P{i}",
                "module_code": f"SE30{i % 3}0", "max_marks": [10, 25][i % 2],
                "question_text": " ".join(topic), "expected_concepts": [rng.choice(VOCAB) for _ in range(4)],
            })  # fmt: skip
    return rows


def test_splitting_keeps_parts_together_covers_modules_and_has_no_leak():
    rows = _split_rows()
    docs = build_parent_docs(rows)
    split_of = split_parents(docs, SPEC, 123)
    assert set(split_of.values()) == set(SPLITS)
    for mod in {r["module_code"] for r in rows}:
        assert {split_of[r["parent_question_id"]] for r in rows if r["module_code"] == mod} == set(SPLITS)
    n = len(split_of)
    assert 0.55 <= sum(v == "train" for v in split_of.values()) / n <= 0.85
    assert split_parents(docs, SPEC, 123) == split_of  # deterministic


def test_splitting_groups_near_duplicate_topics_and_fails_on_duplicate_answers():
    rows = _split_rows(30)
    rows.append(
        {**rows[0], "parent_question_id": "CLONE", "question_id": "CLONE", "module_code": rows[0]["module_code"]}
    )
    split_of = split_parents(build_parent_docs(rows), SPEC, 5)
    assert split_of["CLONE"] == split_of["P0"]
    with pytest.raises(SplitError):
        check_answer_leakage({"train": ["Same text here."], "test": ["same   text here"]})
    check_answer_leakage({"train": ["", " "], "test": ["", "   "]})  # EMPTY answers are exempt


def test_evidence_spans_and_mindmap_derivation():
    text = "The cache reduces latency. Unrelated filler appears here. The eviction policy removes old entries!"
    status = {
        "cache latency": "demonstrated",
        "eviction policy": "partial",
        "write through": "missing",
        "ttl": "incorrect",
    }
    spans = derive_evidence_spans(text, status)
    assert spans == {"cache latency": [0], "eviction policy": [2]}
    assert max(i for v in spans.values() for i in v) < len(split_sentences(text))
    graph = [
        {"source": "cache latency", "target": "eviction policy", "type": "causes"},
        {"source": "write through", "target": "eviction policy", "type": "part_of"},
    ]
    mm = derive_gold_mindmap(status, graph, "PARTIAL")
    ids = {n["id"] for n in mm["nodes"]}
    assert len(mm["edges"]) == 1 and all(e["source"] in ids and e["target"] in ids for e in mm["edges"])
    assert {n["label"]: n["status"] for n in mm["nodes"]} == status
    assert derive_gold_mindmap(status, graph, "IRRELEVANT") == {"nodes": [], "edges": []}
    assert derive_gold_mindmap(status, graph, "EMPTY") == {"nodes": [], "edges": []}


def test_writer_refuses_nan_none_and_blank_values(tmp_path):
    cols = ["answer_id", "tier", "student_answer", "expected_mark"]
    good = {"answer_id": "a", "tier": "FULL", "student_answer": "text", "expected_mark": 1.0}
    write_csv(tmp_path / "ok.csv", cols, [good], SPEC)
    for bad in (
        {**good, "student_answer": "nan"},
        {**good, "student_answer": "None"},
        {**good, "student_answer": "  "},
        {**good, "expected_mark": float("nan")},
        {**good, "student_answer": None},
        {**good, "student_answer": "has {unresolved} slot"},
    ):
        with pytest.raises(WriteError):
            write_csv(tmp_path / "bad.csv", cols, [bad], SPEC)
    write_csv(tmp_path / "e.csv", cols, [{**good, "tier": "EMPTY", "student_answer": ""}], SPEC)


def test_source_helpers():
    assert ocr_noise_ratio("clean sentence about caching") == 0.0
    assert ocr_noise_ratio("bad � token � here") > 0.3
    stats = dry_run_stats(make_questions(10), 0.03)
    assert stats["questions"] == 10 and stats["multipart_marker_candidates"]


def test_cli_dry_run_needs_no_api_key(monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from datasets.generate_c3_dataset import main

    assert main(["--dry-run", "--limit", "20"]) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "source questions: 20" in out and "Estimated LLM calls" in out


def test_cli_real_run_without_key_fails_loudly(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from datasets.generate_c3_dataset import main

    assert main(["--limit", "1", "--out", str(tmp_path / "o")]) == 2
    assert "GEMINI_API_KEY" in capsys.readouterr().err


def test_pipeline_end_to_end_with_fake_is_consistent(tmp_path):
    pipe = Pipeline(make_tasks(), SPEC, 20261021, 2, "fake-gen", "fake-ver")
    qs = make_questions(15, modules=2)
    qs.append(SourceQuestion("QX", "SE3000", "synthetic", "", "Please DRAWDIAGRAM of it.", 10.0))
    data, failures = pipe.run(qs)
    assert not failures and data is not None
    assert {e["question_id"] for e in data.excluded} >= {"QX"}
    tiers = {a["tier"] for a in data.answers}
    assert tiers == set(SPEC["core_tiers"]) | set(SPEC["edge_tiers"])
    assert {q["split"] for q in data.questions} == set(SPLITS)
    assert all(a["dataset_version"] == DATASET_VERSION for a in data.answers)
    by_parent: dict[str, set[str]] = {}
    for q in data.questions:
        by_parent.setdefault(q["parent_question_id"], set()).add(q["split"])
    assert all(len(v) == 1 for v in by_parent.values())
    graded = [a for a in data.answers if a["verification"] == "blind_llm"]
    assert graded and all(0.0 <= a["blind_grade_agreement"] <= 1.0 for a in graded)
