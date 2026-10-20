"""The five LLM tasks. Every call goes through a (cached) provider; nothing is simulated or silently skipped."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.schemas.marking import EvidenceRule, Rubric, RubricCriterion, ScoringLevel
from services.llm.base import BaseLLMProvider, LLMRequest
from services.llm.gemini_provider import strip_json_fence
from services.marking.rubric_validator import RubricValidationError, validate_rubric

from . import prompts
from .source import SourceQuestion, hyphen_ws_equivalent, is_verbatim, normalize_ws

EXCLUSION_REASONS = {"requires_code", "requires_diagram", "requires_unavailable_figure", "other"}


class LLMTaskError(RuntimeError):
    """Infrastructure failure: provider kept failing. Reported, never swallowed."""

    def __init__(self, task: str, key: str, message: str) -> None:
        super().__init__(f"[{task}] {key}: {message}")
        self.task, self.key, self.message = task, key, message


class LLMValidationError(LLMTaskError):
    """The model answered but never produced output that passes validation after all retries."""


@dataclass
class PartSpec:
    part_label: str
    text: str
    marks: float


@dataclass
class StructureResult:
    answerable: bool
    exclusion_reason: str
    stem: str
    parts: list[PartSpec]
    answer_type: str
    marks_stated: bool
    prompt_hash: str = ""


@dataclass
class DraftedRubric:
    reference_answer: str
    expected_concepts: list[str]
    concept_graph: list[dict[str, str]]
    misconceptions: list[dict[str, Any]]
    rubric: Rubric
    prompt_hash: str = ""


@dataclass
class GeneratedAnswer:
    text: str
    concept_status: dict[str, str]
    prompt_hash: str = ""


@dataclass
class BlindGrade:
    levels: dict[str, str]  # criterion_id -> level_id
    prompt_hash: str = ""


@dataclass
class TaskStats:
    calls: dict[str, int] = field(default_factory=dict)
    failures: list[dict[str, str]] = field(default_factory=list)


def _words(text: str) -> int:
    return len(text.split())


def parse_response_json(raw: str, parsed: dict | None) -> dict:
    if isinstance(parsed, dict):
        return parsed
    data = json.loads(strip_json_fence(raw))
    if not isinstance(data, dict):
        raise ValueError("response JSON is not an object")
    return data


def rubric_text(rubric: Rubric, with_marks: bool = True) -> str:
    lines = []
    for c in rubric.criteria:
        lines.append(f"- {c.criterion_id} ({c.description})" + (f" max {c.max_marks:g}" if with_marks else ""))
        for lv in sorted(c.scoring_levels, key=lambda lv: lv.mark):
            mark = f" [{lv.mark:g}]" if with_marks else ""
            lines.append(f"    * {lv.level_id}{mark}: {lv.label} - {lv.descriptor}")
    return "\n".join(lines)


def reference_word_target(marks: float) -> int:
    return int(min(240, max(90, 70 + 12 * marks)))


def validate_draft(draft: dict, question_id: str, marks: float, spec: dict) -> DraftedRubric:
    """Validate a drafted rubric against the C3 schema, rubric_validator and our dataset rules."""
    th = spec["thresholds"]
    errors: list[str] = []
    deny = {s.casefold() for s in spec["placeholder_concepts"]}

    ref = draft.get("reference_answer")
    if not isinstance(ref, str) or not (th["reference_words_min"] <= _words(ref) <= th["reference_words_max"]):
        errors.append(
            f"reference_answer must be {th['reference_words_min']}-{th['reference_words_max']} words "
            f"(got {_words(ref) if isinstance(ref, str) else 'none'})"
        )

    concepts_raw = draft.get("expected_concepts")
    concepts: list[str] = []
    if not isinstance(concepts_raw, list) or not all(isinstance(c, str) for c in concepts_raw):
        errors.append("expected_concepts must be a list of strings")
    else:
        concepts = [normalize_ws(c) for c in concepts_raw]
        if not th["min_expected_concepts"] <= len(concepts) <= th["max_expected_concepts"]:
            errors.append(
                f"expected_concepts must have {th['min_expected_concepts']}-{th['max_expected_concepts']} items"
            )
        if len({c.casefold() for c in concepts}) != len(concepts):
            errors.append("expected_concepts contains duplicates")
        for c in concepts:
            if not c or c.casefold() in deny:
                errors.append(f"placeholder or blank concept: {c!r}")
    canon = {c.casefold(): c for c in concepts}

    graph: list[dict[str, str]] = []
    for edge in draft.get("concept_graph") or []:
        if not isinstance(edge, dict):
            errors.append("concept_graph edges must be objects")
            continue
        s, t, ty = (str(edge.get(k, "")).strip() for k in ("source", "target", "type"))
        if s.casefold() not in canon or t.casefold() not in canon or s.casefold() == t.casefold():
            errors.append(f"concept_graph edge endpoints must be distinct expected_concepts: {s!r}->{t!r}")
        elif ty not in spec["graph_edge_types"]:
            errors.append(f"concept_graph edge type {ty!r} not in {spec['graph_edge_types']}")
        else:
            graph.append({"source": canon[s.casefold()], "target": canon[t.casefold()], "type": ty})

    crit_raw = draft.get("criteria")
    criteria: list[RubricCriterion] = []
    if not isinstance(crit_raw, list) or not th["min_criteria"] <= len(crit_raw) <= th["max_criteria"]:
        errors.append(f"criteria must be a list of {th['min_criteria']}-{th['max_criteria']} items")
        crit_raw = []
    total = 0.0
    for ci, c in enumerate(crit_raw):
        cid = f"{question_id}-C{ci + 1}"
        try:
            cmax = round(float(c["max_marks"]), 4)
            total += cmax
            c_concepts = []
            for name in c.get("required_concepts") or []:
                if str(name).casefold() not in canon:
                    errors.append(f"{cid}: required concept {name!r} is not in expected_concepts")
                else:
                    c_concepts.append(canon[str(name).casefold()])
            if not c_concepts:
                errors.append(f"{cid}: needs at least one required_concepts entry")
            lv_raw = c["scoring_levels"]
            if not th["min_levels"] <= len(lv_raw) <= th["max_levels"]:
                errors.append(f"{cid}: needs {th['min_levels']}-{th['max_levels']} scoring levels")
            levels: list[ScoringLevel] = []
            for li, lv in enumerate(lv_raw):
                lv_concepts = []
                for name in lv.get("required_concepts") or []:
                    if str(name).casefold() not in canon:
                        errors.append(f"{cid} level {li}: concept {name!r} is not in expected_concepts")
                    else:
                        lv_concepts.append(canon[str(name).casefold()])
                md = int(lv.get("min_demonstrated") or 0)
                rule = (
                    EvidenceRule(type="required_concept_count", minimum_demonstrated=md)
                    if md > 0 and lv_concepts
                    else None
                )
                levels.append(
                    ScoringLevel(
                        level_id=f"{cid}-L{li}",
                        label=str(lv.get("label") or f"Level {li}"),
                        mark=round(float(lv["mark"]), 4),
                        descriptor=str(lv["descriptor"]),
                        required_concepts=lv_concepts,
                        evidence_rule=rule,
                    )
                )
            marks_list = [lv.mark for lv in levels]
            if levels and marks_list[0] != 0:
                errors.append(f"{cid}: first scoring level must have mark 0")
            if any(b <= a for a, b in zip(marks_list, marks_list[1:], strict=False)):
                errors.append(f"{cid}: level marks must strictly increase")
            if levels and abs(marks_list[-1] - cmax) > 1e-6:
                errors.append(f"{cid}: top level mark {marks_list[-1]} != max_marks {cmax}")
            if levels and not levels[-1].required_concepts:
                errors.append(f"{cid}: top level needs required_concepts")
            criteria.append(
                RubricCriterion(
                    criterion_id=cid,
                    description=str(c["description"]),
                    max_marks=cmax,
                    required_concepts=c_concepts,
                    scoring_levels=levels,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"criterion {ci}: malformed ({type(exc).__name__}: {exc})")
    if crit_raw and abs(total - marks) > 1e-6:
        errors.append(f"criteria max_marks sum to {total:g} but the question has {marks:g} marks")
    if len(criteria) >= 3 and len({c.max_marks for c in criteria}) == 1:
        errors.append("all criteria have equal weight; vary the weights to reflect emphasis")

    misconceptions = []
    for m in draft.get("common_misconceptions") or []:
        if isinstance(m, dict) and str(m.get("claim", "")).strip():
            try:
                idx = int(m.get("criterion_index", 0))
            except (TypeError, ValueError):
                idx = 0
            misconceptions.append(
                {"claim": str(m["claim"]).strip(), "correct": str(m.get("correct", "")).strip(), "criterion_index": idx}
            )
    if not misconceptions:
        errors.append("common_misconceptions must contain at least one {claim, correct, criterion_index}")

    rubric: Rubric | None = None
    if not errors:
        rubric = Rubric(rubric_id=f"RUB-{question_id}", title=f"Rubric for {question_id}", criteria=criteria)
        try:
            validate_rubric(rubric)
        except RubricValidationError as exc:
            errors.extend(exc.errors)
    if errors or rubric is None:
        raise ValueError("; ".join(errors))
    return DraftedRubric(
        reference_answer=normalize_ws(ref),
        expected_concepts=concepts,
        concept_graph=graph,
        misconceptions=misconceptions,
        rubric=rubric,
    )


class LLMTasks:
    def __init__(
        self,
        generator: BaseLLMProvider,
        verifier: BaseLLMProvider,
        spec: dict,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.generator, self.verifier, self.spec = generator, verifier, spec
        self.sleep = sleep
        self.timeout = timeout_seconds
        self.stats = TaskStats()

    # -- core call loop -------------------------------------------------------------------------------
    def _call(
        self,
        task: str,
        key: str,
        build_prompt: Callable[[str], str],
        validate: Callable[[dict], Any],
        provider: BaseLLMProvider,
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[Any, str]:
        retries = self.spec["thresholds"]["max_llm_retries"]
        feedback = ""
        last = "no attempt made"
        validation_failed = False
        for attempt in range(retries):
            prompt = build_prompt(feedback)
            request = LLMRequest(
                prompt=prompt,
                system_prompt=system,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format="json",
                timeout_seconds=self.timeout,
            )
            self.stats.calls[task] = self.stats.calls.get(task, 0) + 1
            response = provider.generate(request)
            if not response.is_success:
                last = response.error_message or "provider reported failure"
                validation_failed = False
                self.sleep(min(30.0, 2.0**attempt))
                continue
            try:
                result = validate(parse_response_json(response.raw_content, response.parsed_json))
            except (ValueError, KeyError, TypeError) as exc:
                last = f"validation failed: {exc}"
                validation_failed = True
                feedback = f"\nYour previous reply was REJECTED because: {exc}\nReturn a corrected full JSON reply."
                continue
            return result, hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        err = LLMValidationError if validation_failed else LLMTaskError
        raise err(task, key, last)

    # -- task 1 ---------------------------------------------------------------------------------------
    def structure_question(self, q: SourceQuestion) -> StructureResult:
        def build(fb: str) -> str:
            return prompts.render(
                prompts.STRUCTURE_QUESTION,
                question_id=q.question_id,
                marks=f"{q.marks:g}",
                question_text=q.question_text,
                feedback=fb,
            )

        def validate(d: dict) -> StructureResult:
            answerable = d.get("answerable_as_written_text")
            if not isinstance(answerable, bool):
                raise ValueError("answerable_as_written_text must be a boolean")
            if not answerable:
                reason = str(d.get("exclusion_reason") or "").strip()
                if reason not in EXCLUSION_REASONS:
                    raise ValueError(f"exclusion_reason must be one of {sorted(EXCLUSION_REASONS)}")
                return StructureResult(False, reason, "", [], "", False)
            parts_raw = d.get("parts")
            if not isinstance(parts_raw, list) or not parts_raw:
                raise ValueError("parts must be a non-empty list")
            stem = normalize_ws(str(d.get("stem") or ""))
            parts = [
                PartSpec(str(p.get("part_label") or "").strip(), normalize_ws(str(p["text"])), float(p["marks"]))
                for p in parts_raw
            ]
            if any(p.marks <= 0 for p in parts):
                raise ValueError("every part needs marks > 0")
            if abs(sum(p.marks for p in parts) - q.marks) > 1e-6:
                raise ValueError(
                    f"part marks sum to {sum(p.marks for p in parts):g} but the question total is {q.marks:g}"
                )
            if len(parts) == 1:
                parts = [PartSpec("", normalize_ws(q.question_text), q.marks)]
                stem = ""
            else:
                labels = [p.part_label for p in parts]
                if any(not lb for lb in labels) or len(set(labels)) != len(labels):
                    raise ValueError("multi-part questions need unique non-empty part_label values")
                if stem and not is_verbatim(stem, q.question_text):
                    raise ValueError("stem is not verbatim from the question text")
                for p in parts:
                    if not is_verbatim(p.text, q.question_text):
                        raise ValueError(f"part {p.part_label} text is not verbatim from the question text")
            return StructureResult(
                True, "", stem, parts, str(d.get("answer_type") or "explanation"), bool(d.get("marks_stated"))
            )

        result, h = self._call(
            "structure_question", q.question_id, build, validate, self.generator, prompts.SYSTEM_GENERATOR, 0.0, 4096
        )
        result.prompt_hash = h
        return result

    def clean_text(self, question_id: str, raw: str) -> str:
        def build(fb: str) -> str:
            return prompts.render(prompts.CLEAN_TEXT, question_text=raw) + fb

        def validate(d: dict) -> str:
            cleaned = normalize_ws(str(d.get("clean_text") or ""))
            if not hyphen_ws_equivalent(raw, cleaned):
                raise ValueError("clean_text changed more than whitespace/hyphenation")
            return cleaned

        result, _ = self._call(
            "clean_text", question_id, build, validate, self.generator, prompts.SYSTEM_GENERATOR, 0.0, 4096
        )
        return result

    # -- task 2 ---------------------------------------------------------------------------------------
    def draft_rubric(self, question_id: str, module: str, marks: float, question_text: str) -> DraftedRubric:
        target = reference_word_target(marks)

        def build(fb: str) -> str:
            return prompts.render(
                prompts.DRAFT_RUBRIC,
                question_id=question_id,
                module=module,
                marks=f"{marks:g}",
                question_text=question_text,
                ref_words=f"about {target} (80-250)",
                feedback=fb,
            )

        result, h = self._call(
            "draft_rubric",
            question_id,
            build,
            lambda d: validate_draft(d, question_id, marks, self.spec),
            self.generator,
            prompts.SYSTEM_GENERATOR,
            0.3,
            8192,
        )
        result.prompt_hash = h
        return result

    # -- task 4 ---------------------------------------------------------------------------------------
    def generate_answers(
        self,
        key: str,
        question_text: str,
        marks: float,
        reference: str,
        concepts: list[str],
        tier: str,
        answer_specs: str,
        count: int,
        attempt: int = 0,
        feedback: str = "",
        extra_rules: str = "",
    ) -> list[GeneratedAnswer]:
        canon = {c.casefold(): c for c in concepts}
        valid_status = set(self.spec["concept_status_values"])

        def build(fb: str) -> str:
            variation = f"\n(Variation token: attempt {attempt}; produce fresh wording.)" if attempt else ""
            return prompts.render(
                prompts.GENERATE_ANSWERS,
                count=str(count),
                marks=f"{marks:g}",
                question_text=question_text,
                reference=reference,
                concepts="; ".join(concepts),
                tier_instruction=prompts.TIER_INSTRUCTIONS[tier],
                answer_specs=answer_specs,
                extra_rules=extra_rules,
                feedback=feedback + fb + variation,
            )

        def validate(d: dict) -> list[GeneratedAnswer]:
            answers = d.get("answers")
            if not isinstance(answers, list) or len(answers) != count:
                raise ValueError(f"'answers' must be a list of exactly {count} items")
            out = []
            for i, a in enumerate(answers):
                text = a.get("student_answer")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(f"answer {i + 1} has no student_answer text")
                status_raw = a.get("concept_status")
                if not isinstance(status_raw, dict):
                    raise ValueError(f"answer {i + 1} lacks concept_status")
                status: dict[str, str] = {}
                for name, val in status_raw.items():
                    if str(name).casefold() not in canon or val not in valid_status:
                        raise ValueError(f"answer {i + 1} concept_status has bad entry {name!r}: {val!r}")
                    status[canon[str(name).casefold()]] = val
                missing = [c for c in concepts if c not in status]
                if missing:
                    raise ValueError(f"answer {i + 1} concept_status lacks {missing}")
                out.append(GeneratedAnswer(text=text.strip(), concept_status=status))
            return out

        result, h = self._call(
            "generate_answers", key, build, validate, self.generator, prompts.SYSTEM_STUDENT, 0.9, 8192
        )
        for r in result:
            r.prompt_hash = h
        return result

    # -- task 5 ---------------------------------------------------------------------------------------
    def blind_grade(self, key: str, question_text: str, marks: float, rubric: Rubric, answer: str) -> BlindGrade:
        valid = {c.criterion_id: {lv.level_id for lv in c.scoring_levels} for c in rubric.criteria}

        def build(fb: str) -> str:
            return (
                prompts.render(
                    prompts.BLIND_GRADE,
                    marks=f"{marks:g}",
                    question_text=question_text,
                    rubric=rubric_text(rubric),
                    answer=answer,
                )
                + fb
            )

        def validate(d: dict) -> dict[str, str]:
            rows = d.get("criteria")
            if not isinstance(rows, list):
                raise ValueError("criteria must be a list")
            levels = {str(r.get("criterion_id")): str(r.get("level_id")) for r in rows if isinstance(r, dict)}
            if set(levels) != set(valid):
                raise ValueError(f"criteria ids must be exactly {sorted(valid)}")
            for cid, lid in levels.items():
                if lid not in valid[cid]:
                    raise ValueError(f"unknown level_id {lid!r} for {cid}")
            return levels

        levels, h = self._call("blind_grade", key, build, validate, self.verifier, prompts.SYSTEM_GRADER, 0.0, 2048)
        return BlindGrade(levels=levels, prompt_hash=h)


_WS = re.compile(r"\s+")


def one_line(text: str) -> str:
    return _WS.sub(" ", text).strip()
